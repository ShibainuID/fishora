"""Semantic chunking of approved knowledge records.

One candidate record is one semantic unit (species, source, category): it is
kept whole when at or below ``max_tokens`` even when far below ``min_tokens``
— short units are never merged to reach a target size. Longer content splits
on sentence boundaries; a single sentence larger than the window is split at
token-ID boundaries (each window decoded independently, so partial tokens at
the cut stay safe). Overlap (``overlap_tokens``) is applied only when a
record actually splits, and every emitted chunk stays within ``max_tokens``
tokenizer tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from apps.main_api.ports import Tokenizer
from apps.main_api.services.corpus import CandidateChunk, Category

# Sentences end at ., ! or ? followed by whitespace; newlines also split.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|[\r\n]+")


@dataclass(frozen=True)
class ChunkPayload:
    id: str
    species_label: str
    source_id: str
    category: Category
    content: str


def _sentences(text: str) -> list[str]:
    return [part for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]


def chunk_candidate(
    candidate: CandidateChunk,
    tokenizer: Tokenizer,
    min_tokens: int = 300,
    max_tokens: int = 600,
    overlap_tokens: int = 50,
) -> list[ChunkPayload]:
    """Split one candidate into semantic chunks of at most ``max_tokens`` tokens.

    ``min_tokens`` is advisory only: a section below it is never split, and
    sections are never merged to reach it (the candidate is already one
    semantic unit). Chunks below ``max_tokens`` keep whole sentences; a single
    sentence above the window is cut at token-ID boundaries. When splitting,
    every chunk after the first carries the previous chunk's last
    ``overlap_tokens`` tokens as leading context.
    """
    def payload(content: str) -> ChunkPayload:
        return ChunkPayload(
            id=candidate.id,
            species_label=candidate.species_label,
            source_id=candidate.source_id,
            category=candidate.category,
            content=content,
        )

    if len(tokenizer.encode(candidate.content)) <= max_tokens:
        return [payload(candidate.content)]

    window = max_tokens - overlap_tokens
    stride = window - overlap_tokens
    units: list[list[int]] = []
    for sentence in _sentences(candidate.content):
        ids = tokenizer.encode(sentence)
        if not ids:
            continue
        if len(ids) <= window:
            units.append(ids)
            continue
        # One sentence exceeds the window: slice its token IDs safely.
        start = 0
        while start < len(ids):
            units.append(ids[start : start + window])
            if start + window >= len(ids):
                break
            start += stride

    chunks: list[list[int]] = []
    current: list[int] = []
    for unit in units:
        if not current or len(current) + len(unit) <= max_tokens:
            current.extend(unit)
        else:
            chunks.append(current)
            # Overlap only when splitting: lead the next chunk with the
            # previous chunk's tail (at most overlap_tokens tokens).
            current = list(current[-overlap_tokens:]) + unit
    if current:
        chunks.append(current)
    return [payload(tokenizer.decode(ids)) for ids in chunks]