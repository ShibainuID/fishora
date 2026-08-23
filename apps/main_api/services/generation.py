"""One-call grounded generation via the OpenCode Go Responses API.

The OpenCodeGoClient talks to the Responses API (``client.responses.create``,
never chat.completions) with a strict JSON-schema output format and returns
``response.output_text``. Timeout/connection failures become
``OpenCodeUnavailable`` carrying only the retrieved chunk ids; credentials,
internal URLs, and headers never appear in messages. The production client
rejects a blank API key, and is constructed lazily (see KnowledgeGenerator)
so empty-evidence requests never touch it.
"""

from __future__ import annotations

from pathlib import Path

import openai
from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.errors import OpenCodeUnavailable

SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1] / "prompts" / "knowledge_card_system.txt"
).read_text(encoding="utf-8")


class GeneratedCitation(BaseModel):
    """The LLM may emit only source ids; all title/url/publisher metadata is
    enriched server-side from retrieved evidence, never trusted from text."""

    source_id: str


class GeneratedKnowledgeCard(BaseModel):
    """Strict generated payload: extra fields are rejected outright."""

    model_config = ConfigDict(extra="forbid")

    common_name: str
    scientific_name: str | None
    taxonomy_status: str
    physical_characteristics: str | None
    taste: str | None
    texture: str | None
    processing_methods: list[str]
    commercial_uses: list[str]
    similar_or_substitute_species: list[str]
    potential_buyer_segments: list[str]
    limitations: list[str]
    sources: list[GeneratedCitation]


class OpenCodeGoClient:
    """Responses-API client: one ``responses.create`` call per generation."""

    def __init__(self, settings):
        # SecretStr stays secret: only get_secret_value() ever leaves the object.
        api_key = settings.opencode_go_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "OPENCODE_GO_API_KEY must be set to construct the production OpenCode client"
            )
        self._client = OpenAI(
            base_url=settings.opencode_go_base_url,
            api_key=api_key,
            timeout=settings.opencode_go_timeout_seconds,
        )
        self._model = settings.opencode_go_model

    def generate(self, system_prompt: str, evidence: list[RetrievedChunk], species: SpeciesRecord) -> str:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=system_prompt,
                input=_user_payload(species, evidence),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "generated_knowledge_card",
                        "schema": GeneratedKnowledgeCard.model_json_schema(),
                        "strict": True,
                    }
                },
            )
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise OpenCodeUnavailable(
                "opencode go generation unavailable",
                [chunk.chunk_id for chunk in evidence],
            ) from exc
        return response.output_text


def _user_payload(species: SpeciesRecord, evidence: list[RetrievedChunk]) -> str:
    """Indonesian payload: relational species fields plus the supplied
    evidence passages, each delimited by source_id/species/category/content."""
    lines = [
        "Data relasional spesies (wajib diikuti, jangan ditimpa):",
        f"- nama umum: {species.common_name_id}",
        f"- nama ilmiah: {species.scientific_name}",
        f"- peringkat taksonomi: {species.taxonomic_rank}",
        f"- status taksonomi: {species.taxonomy_status}",
        "",
        "Bukti yang disediakan (hanya ini yang boleh dipakai):",
    ]
    for chunk in evidence:
        lines.append(
            f"[source_id: {chunk.source_id}] [spesies: {chunk.species_id}] "
            f"[kategori: {chunk.category}]"
        )
        lines.append(chunk.content)
    return "\n".join(lines)