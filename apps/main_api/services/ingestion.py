"""Approved-only corpus ingestion into Postgres/pgvector.

Nothing is ingested without the signed approval manifest: the HMAC key is
required and forwarded to Task 4's ``require_approved_manifest``, so unsigned
or candidate-only input is rejected before any database work. Every record,
label, status, signature, model and vector dimension is validated before the
single transactional commit; the repository writes sources and chunks in one
transaction and rolls everything back on any failure.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from apps.main_api.contracts import KnowledgeChunkWrite, KnowledgeSourceWrite
from apps.main_api.ports import Embedder, KnowledgeRepository, SpeciesRepository
from apps.main_api.services.chunking import chunk_candidate
from apps.main_api.services.corpus import VerifiedRecord, require_approved_manifest
from apps.main_api.services.embeddings import E5_DIMENSION, E5_MODEL_NAME


def _verified_records(approved_dir: Path, chunk_ids: list[str]) -> list[VerifiedRecord]:
    """Re-read the approved files; require_approved_manifest already validated
    their status, attestation and HMAC signature, so this only parses them."""
    return [
        VerifiedRecord.model_validate(
            json.loads((approved_dir / f"{chunk_id}.json").read_text(encoding="utf-8"))
        )
        for chunk_id in chunk_ids
    ]


def _validated_vectors(payload_ids: list[str], vectors: list[list[float]]) -> None:
    """Reject malformed embedding batches before any database write."""
    if len(vectors) != len(payload_ids):
        raise ValueError(
            f"embedder returned {len(vectors)} vectors for {len(payload_ids)} passages"
        )
    for payload_id, vector in zip(payload_ids, vectors):
        if len(vector) != E5_DIMENSION:
            raise ValueError(
                f"embedding for {payload_id} has {len(vector)} dimensions; expected {E5_DIMENSION}"
            )
        if not all(math.isfinite(value) for value in vector):
            raise ValueError(f"embedding for {payload_id} contains non-finite values")
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-3):
            raise ValueError(
                f"embedding for {payload_id} is not L2-normalized (norm {norm:.4f})"
            )


def ingest_approved_corpus(
    approved_dir: Path,
    approval_manifest: Path,
    species_repo: SpeciesRepository,
    knowledge_repo: KnowledgeRepository,
    embedder: Embedder,
    approval_key: str,
) -> int:
    """Validate the signed approval and ingest every verified chunk.

    Returns the number of verified chunks written. Raises before touching the
    store on: a missing/unsigned/mismatched manifest (no approval key, wrong
    key, altered files, candidate-only records), an unknown species label, a
    store already containing another embedding model, or any vector whose
    length is not 768.
    """
    manifest = require_approved_manifest(approved_dir, approval_manifest, approval_key)
    if embedder.model_name != E5_MODEL_NAME:
        raise ValueError(
            f"ingestion requires the {E5_MODEL_NAME} embedding model, got {embedder.model_name!r}"
        )
    records = _verified_records(approved_dir, manifest.approved_chunk_ids)

    species_ids: dict[str, str] = {}
    for record in records:
        label = record.chunk.species_label
        if label not in species_ids:
            species = species_repo.get_by_normalized_label(label)
            if species is None:
                raise ValueError(
                    f"unknown species label {label!r}; seed the taxonomy before ingestion"
                )
            species_ids[label] = species.id

    models = knowledge_repo.embedding_models_in_store()
    if models and models != {embedder.model_name}:
        raise ValueError(
            "knowledge store already contains another embedding model "
            f"({sorted(models)}); refusing to mix with {embedder.model_name}"
        )

    sources = {
        record.source.id: KnowledgeSourceWrite(
            id=record.source.id,
            title=record.source.title,
            source_type=record.source.source_type,
            url=record.source.url,
            publisher=record.source.publisher,
            reviewed_at=record.source.reviewed_at,
            verification_status="verified",
        )
        for record in records
    }

    chunks: list[KnowledgeChunkWrite] = []
    for record in records:
        payloads = chunk_candidate(record.chunk, embedder.tokenizer)
        vectors = embedder.embed_passages([payload.content for payload in payloads])
        _validated_vectors([payload.id for payload in payloads], vectors)
        for index, (payload, vector) in enumerate(zip(payloads, vectors)):
            chunks.append(
                KnowledgeChunkWrite(
                    id=payload.id if index == 0 else f"{payload.id}__{index + 1}",
                    species_id=species_ids[record.chunk.species_label],
                    source_id=payload.source_id,
                    category=payload.category,
                    content=payload.content,
                    embedding=[float(value) for value in vector],
                    embedding_model=embedder.model_name,
                    verification_status="verified",
                )
            )

    return knowledge_repo.insert_verified(list(sources.values()), chunks)