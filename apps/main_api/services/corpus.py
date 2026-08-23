"""Offline-only corpus stages and the mandatory human approval gate.

This service runs only from the offline operator CLI (`scripts` package); the
main API never imports the CLI and never runs corpus commands at request time.
Research, fact-extraction, verification and knowledge-editor agents hand data
to this boundary as four UTF-8 JSON stage files; only the CLI approval action
may create `verified` copies.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

Category = Literal[
    "identity", "physical_characteristics", "taste_texture",
    "processing_methods", "commercial_uses", "substitutes",
]
SpeciesLabel = Literal[
    "bandeng", "gelama_bunga", "gembolo", "gulamah", "kembung",
    "kuniran", "mujair", "nila", "senangin", "tenggiri", "tuna",
]
Stage = Literal["research", "fact_extraction", "verification", "knowledge_editor"]

APPROVAL_TOKEN = "APPROVE"
STAGE_FILES = ("research.json", "fact_extraction.json", "verification.json", "knowledge_editor.json")
LINEAGE_STAGES = ("research", "fact_extraction", "verification")


class OfflineStageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    source_id: str
    species_label: SpeciesLabel
    category: Category
    content: str
    source_quote: str
    stage: Stage
    verification_status: Literal["candidate"]


class CandidateSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_type: str
    url: str
    publisher: str
    reviewed_at: datetime | None
    verification_status: Literal["candidate"]


class OfflineStageFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Stage
    sources: list[CandidateSource]
    records: list[OfflineStageRecord]


class CandidateChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    species_label: SpeciesLabel
    source_id: str
    category: Category
    content: str
    source_quote: str
    stage: Literal["knowledge_editor"]
    verification_status: Literal["candidate"]


class CandidateRecord(BaseModel):
    """On-disk candidate record: the editor chunk plus its source lineage."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    chunk: CandidateChunk
    source: CandidateSource


class ApprovalManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str
    approved_at: datetime
    approved_chunk_ids: list[str]
    approved_source_ids: list[str]


def _read_stage_file(stage_dir: Path, name: str) -> OfflineStageFile:
    path = stage_dir / name
    if not path.is_file():
        raise FileNotFoundError(f"{name} not found in {stage_dir}")
    stage = name[: -len(".json")]
    model = OfflineStageFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    if model.stage != stage:
        raise ValueError(f"{name} declares stage {model.stage!r}, expected {stage!r}")
    return model


def collect_candidate_stages(stage_dir: Path, candidate_dir: Path) -> int:
    """Read the four offline agent-stage files and write candidate records.

    Every knowledge_editor record must have matching research, fact-extraction
    and verification records with the same (claim_id, source_id). Only
    `candidate` records are written; nothing is written to an approved
    directory or database.
    """
    missing = [name for name in STAGE_FILES if not (stage_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"{missing[0]} not found in {stage_dir}")
    stage_files = {name: _read_stage_file(stage_dir, name) for name in STAGE_FILES}
    editor = stage_files["knowledge_editor.json"]
    lineage = {
        stage: {(r.claim_id, r.source_id) for r in stage_files[f"{stage}.json"].records}
        for stage in LINEAGE_STAGES
    }
    sources = {source.id: source for source in editor.sources}

    records: list[CandidateRecord] = []
    seen_ids: set[str] = set()
    for record in editor.records:
        key = (record.claim_id, record.source_id)
        for stage in LINEAGE_STAGES:
            if key not in lineage[stage]:
                raise ValueError(
                    f"missing {stage} lineage for claim {record.claim_id!r} source {record.source_id!r}"
                )
        source = sources.get(record.source_id)
        if source is None:
            raise ValueError(f"source {record.source_id!r} not declared in knowledge_editor.json")
        if not record.source_quote.strip():
            raise ValueError(f"claim {record.claim_id!r} has an empty source quote")
        chunk = CandidateChunk(
            id="chunk_" + record.claim_id[len("claim_"):],
            species_label=record.species_label,
            source_id=record.source_id,
            category=record.category,
            content=record.content,
            source_quote=record.source_quote,
            stage="knowledge_editor",
            verification_status="candidate",
        )
        if chunk.id in seen_ids:
            raise ValueError(f"duplicate chunk id {chunk.id!r}")
        seen_ids.add(chunk.id)
        records.append(CandidateRecord(claim_id=record.claim_id, chunk=chunk, source=source))

    candidate_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        (candidate_dir / f"{record.chunk.id}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )
    return len(records)


def approve_candidates(
    candidate_dir: Path,
    review_file: Path,
    approved_dir: Path,
    approval_manifest: Path,
    reviewer: str,
    confirmation: str,
    approved_at: datetime,
) -> ApprovalManifest:
    """Mandatory human approval gate.

    Requires a non-empty reviewer, the exact confirmation token ``APPROVE``,
    explicit chunk IDs from the review file, and a source reviewed by a human.
    Copies only the approved records into ``approved_dir`` as `verified` and
    writes the manifest. Candidate files remain unchanged.
    """
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer must be a non-empty human identifier")
    if confirmation != APPROVAL_TOKEN:
        raise PermissionError(f"approval requires the exact confirmation token {APPROVAL_TOKEN}")
    if not review_file.is_file():
        raise FileNotFoundError(f"review file not found: {review_file}")
    review = json.loads(review_file.read_text(encoding="utf-8"))
    approved_ids = review.get("approved_chunk_ids") if isinstance(review, dict) else None
    if not isinstance(approved_ids, list) or not approved_ids or not all(
        isinstance(chunk_id, str) and chunk_id.strip() for chunk_id in approved_ids
    ):
        raise ValueError("review file must list explicit approved_chunk_ids")

    records: dict[str, CandidateRecord] = {}
    for chunk_id in approved_ids:
        path = candidate_dir / f"{chunk_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"candidate chunk not found: {chunk_id}")
        record = CandidateRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if record.chunk.verification_status != "candidate" or record.source.verification_status != "candidate":
            raise ValueError(f"{chunk_id} is not a candidate record")
        if record.source.reviewed_at is None:
            raise ValueError(
                f"source {record.source.id!r} of {chunk_id} was not reviewed by a human"
            )
        records[chunk_id] = record

    approved_dir.mkdir(parents=True, exist_ok=True)
    for chunk_id, record in records.items():
        approved = {
            "claim_id": record.claim_id,
            "chunk": record.chunk.model_dump(mode="json") | {"verification_status": "verified"},
            "source": record.source.model_dump(mode="json")
            | {"verification_status": "verified", "reviewed_at": approved_at.isoformat()},
        }
        (approved_dir / f"{chunk_id}.json").write_text(
            json.dumps(approved, indent=2), encoding="utf-8"
        )

    manifest = ApprovalManifest(
        reviewer=reviewer,
        approved_at=approved_at,
        approved_chunk_ids=list(records),
        approved_source_ids=sorted({record.source.id for record in records.values()}),
    )
    approval_manifest.parent.mkdir(parents=True, exist_ok=True)
    approval_manifest.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


def require_approved_manifest(approved_dir: Path, approval_manifest: Path) -> ApprovalManifest:
    """Return the manifest only when every listed chunk has a verified copy.

    Rejects a missing or malformed manifest and candidate-only input (a listed
    chunk whose approved copy is still `candidate`).
    """
    if not approval_manifest.is_file():
        raise FileNotFoundError(f"approval manifest not found: {approval_manifest}")
    try:
        manifest = ApprovalManifest.model_validate(
            json.loads(approval_manifest.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"approval manifest is malformed: {error}") from error
    for chunk_id in manifest.approved_chunk_ids:
        path = approved_dir / f"{chunk_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"approved copy not found: {chunk_id}")
        record = json.loads(path.read_text(encoding="utf-8"))
        chunk = record.get("chunk", {}) if isinstance(record, dict) else {}
        source = record.get("source", {}) if isinstance(record, dict) else {}
        if chunk.get("verification_status") != "verified" or source.get("verification_status") != "verified":
            raise ValueError(f"{chunk_id} is candidate-only input, not an approved verified copy")
    return manifest