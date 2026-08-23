"""Offline-only corpus stages and the mandatory human approval gate.

This service runs only from the offline operator CLI (`scripts` package); the
main API never imports the CLI and never runs corpus commands at request time.
Research, fact-extraction, verification and knowledge-editor agents hand data
to this boundary as four UTF-8 JSON stage files. Candidates carry no human
approval metadata; only the CLI approval action with per-source attestation
may create `verified` copies.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

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
# Safe filename component: lowercase alphanumerics and underscores only, so
# IDs can never carry path separators, traversal or absolute paths.
SAFE_ID = re.compile(r"^[a-z0-9_]+$")


def _require_safe_id(value: str, what: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"unsafe {what} {value!r}: must match {SAFE_ID.pattern}")
    return value


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

    @field_validator("claim_id")
    @classmethod
    def _safe_claim_id(cls, value: str) -> str:
        return _require_safe_id(value, "claim id")

    @field_validator("source_id")
    @classmethod
    def _safe_source_id(cls, value: str) -> str:
        return _require_safe_id(value, "source id")


class CandidateSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_type: str
    url: str
    publisher: str
    reviewed_at: datetime | None
    verification_status: Literal["candidate"]

    @field_validator("id")
    @classmethod
    def _safe_id(cls, value: str) -> str:
        return _require_safe_id(value, "source id")


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

    @field_validator("id")
    @classmethod
    def _safe_id(cls, value: str) -> str:
        return _require_safe_id(value, "chunk id")


class CandidateRecord(BaseModel):
    """On-disk candidate record: the editor chunk plus its source lineage."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    chunk: CandidateChunk
    source: CandidateSource


class VerifiedChunk(BaseModel):
    """Strict schema for an approved chunk copy; nothing but `verified` parses."""

    model_config = ConfigDict(extra="forbid")

    id: str
    species_label: SpeciesLabel
    source_id: str
    category: Category
    content: str
    source_quote: str
    stage: Literal["knowledge_editor"]
    verification_status: Literal["verified"]

    @field_validator("id")
    @classmethod
    def _safe_id(cls, value: str) -> str:
        return _require_safe_id(value, "chunk id")


class VerifiedSource(BaseModel):
    """Strict schema for an approved source copy with human attestation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_type: str
    url: str
    publisher: str
    reviewed_at: datetime
    reviewer: str
    verification_status: Literal["verified"]

    @field_validator("id")
    @classmethod
    def _safe_id(cls, value: str) -> str:
        return _require_safe_id(value, "source id")

    @field_validator("reviewer")
    @classmethod
    def _reviewer_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source reviewer must be a non-empty human identifier")
        return value


class VerifiedRecord(BaseModel):
    """On-disk approved record: verified chunk plus verified, attested source."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    chunk: VerifiedChunk
    source: VerifiedSource


class SourceReview(BaseModel):
    """Human attestation for one approved source, supplied in the review file."""

    model_config = ConfigDict(extra="forbid")

    reviewer: str
    reviewed_at: datetime

    @field_validator("reviewer")
    @classmethod
    def _reviewer_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source reviewer must be a non-empty human identifier")
        return value


class ReviewFile(BaseModel):
    """Human review input: explicit chunk IDs, source IDs and attestations."""

    model_config = ConfigDict(extra="forbid")

    approved_chunk_ids: list[str]
    approved_source_ids: list[str]
    source_reviews: dict[str, SourceReview]

    @field_validator("approved_chunk_ids")
    @classmethod
    def _explicit_chunk_ids(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("review file must list explicit approved_chunk_ids")
        for chunk_id in value:
            _require_safe_id(chunk_id, "approved_chunk_ids entry")
        return value

    @field_validator("approved_source_ids")
    @classmethod
    def _explicit_source_ids(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("review file must list explicit approved_source_ids")
        for source_id in value:
            _require_safe_id(source_id, "approved_source_ids entry")
        return value

    @model_validator(mode="after")
    def _attestation_coverage(self) -> "ReviewFile":
        if set(self.approved_source_ids) != set(self.source_reviews):
            raise ValueError("every approved source needs a source_reviews attestation")
        return self


class ApprovalManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer: str
    approved_at: datetime
    approved_chunk_ids: list[str]
    approved_source_ids: list[str]

    @field_validator("reviewer")
    @classmethod
    def _reviewer_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("manifest reviewer must be a non-empty human identifier")
        return value

    @field_validator("approved_chunk_ids", "approved_source_ids")
    @classmethod
    def _safe_ids(cls, value: list[str]) -> list[str]:
        for record_id in value:
            _require_safe_id(record_id, "manifest id")
        return value


def _safe_record_path(root: Path, record_id: str) -> Path:
    """Return ``root/<record_id>.json`` only when the ID is a safe filename
    component and no symlink or path escape is involved."""
    _require_safe_id(record_id, "record id")
    if root.is_symlink():
        raise ValueError(f"refusing symlinked root directory: {root}")
    path = root / f"{record_id}.json"
    if path.is_symlink():
        raise ValueError(f"refusing symlinked record file: {path}")
    if path.resolve().parent != root.resolve():
        raise ValueError(f"record path escapes its root: {record_id}")
    return path


def _assert_distinct_roots(candidate_dir: Path, approved_dir: Path) -> None:
    candidate_root = candidate_dir.resolve()
    approved_root = approved_dir.resolve()
    if candidate_root == approved_root:
        raise ValueError("candidate_dir and approved_dir must differ")
    if approved_root.is_relative_to(candidate_root):
        raise ValueError("approved_dir must not be nested inside candidate_dir")
    if candidate_root.is_relative_to(approved_root):
        raise ValueError("candidate_dir must not be nested inside approved_dir")


def _read_stage_file(stage_dir: Path, name: str) -> OfflineStageFile:
    path = stage_dir / name
    if not path.is_file():
        raise FileNotFoundError(f"{name} not found in {stage_dir}")
    stage = name[: -len(".json")]
    model = OfflineStageFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    if model.stage != stage:
        raise ValueError(f"{name} declares stage {model.stage!r}, expected {stage!r}")
    source_ids = {source.id for source in model.sources}
    seen: set[tuple[str, str]] = set()
    for record in model.records:
        if record.stage != stage:
            raise ValueError(
                f"{name} record {record.claim_id!r} declares stage {record.stage!r}, "
                f"expected {stage!r}"
            )
        if not record.content.strip():
            raise ValueError(f"{name} record {record.claim_id!r} has empty content")
        if not record.source_quote.strip():
            raise ValueError(f"{name} record {record.claim_id!r} has an empty source quote")
        if record.source_id not in source_ids:
            raise ValueError(
                f"{name} record {record.claim_id!r} references undeclared source {record.source_id!r}"
            )
        key = (record.claim_id, record.source_id)
        if key in seen:
            raise ValueError(f"duplicate lineage record {key!r} in {name}")
        seen.add(key)
    return model


def collect_candidate_stages(stage_dir: Path, candidate_dir: Path) -> int:
    """Read the four offline agent-stage files and write candidate records.

    Every record in every stage file is validated (stage matches filename,
    non-empty content and source quote, safe IDs, declared sources); every
    knowledge_editor record must have matching research, fact-extraction and
    verification records with the same (claim_id, source_id), and vice versa.
    Only `candidate` records are written; nothing is written to an approved
    directory or database.
    """
    missing = [name for name in STAGE_FILES if not (stage_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"{missing[0]} not found in {stage_dir}")
    stage_files = {name: _read_stage_file(stage_dir, name) for name in STAGE_FILES}
    stage_keys = {
        name[: -len(".json")]: {(r.claim_id, r.source_id) for r in stage_files[name].records}
        for name in STAGE_FILES
    }
    editor_keys = stage_keys["knowledge_editor"]
    for stage in LINEAGE_STAGES:
        keys = stage_keys[stage]
        for key in editor_keys - keys:
            raise ValueError(f"missing {stage} lineage for claim {key[0]!r} source {key[1]!r}")
        for key in keys - editor_keys:
            raise ValueError(
                f"claim {key[0]!r} source {key[1]!r} has no knowledge_editor record in {stage}"
            )

    editor = stage_files["knowledge_editor.json"]
    sources = {source.id: source for source in editor.sources}
    records: list[CandidateRecord] = []
    seen_ids: set[str] = set()
    for record in editor.records:
        source = sources[record.source_id]
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
        path = _safe_record_path(candidate_dir, record.chunk.id)
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
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
    explicit chunk and source IDs from the review file, and a per-source human
    attestation (reviewer + reviewed_at). Copies only the approved records into
    ``approved_dir`` as `verified`, writing the attestation metadata; candidate
    files remain unchanged.
    """
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer must be a non-empty human identifier")
    if confirmation != APPROVAL_TOKEN:
        raise PermissionError(f"approval requires the exact confirmation token {APPROVAL_TOKEN}")
    _assert_distinct_roots(candidate_dir, approved_dir)
    if not review_file.is_file():
        raise FileNotFoundError(f"review file not found: {review_file}")
    try:
        review = ReviewFile.model_validate(json.loads(review_file.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"review file is malformed: {error}") from error

    records: dict[str, CandidateRecord] = {}
    for chunk_id in review.approved_chunk_ids:
        path = _safe_record_path(candidate_dir, chunk_id)
        if not path.is_file():
            raise FileNotFoundError(f"candidate chunk not found: {chunk_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        chunk = data.get("chunk", {}) if isinstance(data, dict) else {}
        source = data.get("source", {}) if isinstance(data, dict) else {}
        if chunk.get("verification_status") != "candidate" or source.get("verification_status") != "candidate":
            raise ValueError(f"{chunk_id} is not a candidate record")
        try:
            record = CandidateRecord.model_validate(data)
        except ValidationError as error:
            raise ValueError(f"{chunk_id} is malformed: {error}") from error
        if record.chunk.id != chunk_id:
            raise ValueError(f"candidate file {chunk_id} contains chunk {record.chunk.id!r}")
        if record.chunk.source_id not in review.approved_source_ids:
            raise ValueError(
                f"chunk {chunk_id} source {record.chunk.source_id!r} is not in approved_source_ids"
            )
        records[chunk_id] = record

    approved_dir.mkdir(parents=True, exist_ok=True)
    for chunk_id, record in records.items():
        attestation = review.source_reviews[record.source.id]
        approved = VerifiedRecord(
            claim_id=record.claim_id,
            chunk=VerifiedChunk.model_validate(
                record.chunk.model_dump() | {"verification_status": "verified"}
            ),
            source=VerifiedSource.model_validate(
                record.source.model_dump()
                | {
                    "verification_status": "verified",
                    "reviewed_at": attestation.reviewed_at,
                    "reviewer": attestation.reviewer,
                }
            ),
        )
        _safe_record_path(approved_dir, chunk_id).write_text(
            approved.model_dump_json(indent=2), encoding="utf-8"
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
    """Return the manifest only when every approved record is genuinely verified.

    Rejects a missing or malformed manifest, empty ID lists, manifest IDs that
    do not match the actual approved files, candidate-only or malformed
    records, unapproved chunk sources, and sources without human attestation.
    """
    if not approval_manifest.is_file():
        raise FileNotFoundError(f"approval manifest not found: {approval_manifest}")
    try:
        manifest = ApprovalManifest.model_validate(
            json.loads(approval_manifest.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"approval manifest is malformed: {error}") from error
    if not manifest.approved_chunk_ids:
        raise ValueError("approval manifest must list approved_chunk_ids")
    if not manifest.approved_source_ids:
        raise ValueError("approval manifest must list approved_source_ids")

    for chunk_id in manifest.approved_chunk_ids:
        path = _safe_record_path(approved_dir, chunk_id)
        if not path.is_file():
            raise FileNotFoundError(f"approved copy not found: {chunk_id}")
    actual_ids = sorted(p.stem for p in approved_dir.iterdir() if p.suffix == ".json")
    if actual_ids != sorted(manifest.approved_chunk_ids):
        raise ValueError(
            f"manifest chunk ids do not match approved files: "
            f"{sorted(manifest.approved_chunk_ids)} != {actual_ids}"
        )

    records: list[VerifiedRecord] = []
    for chunk_id in manifest.approved_chunk_ids:
        path = _safe_record_path(approved_dir, chunk_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{chunk_id} is malformed: {error}") from error
        chunk = data.get("chunk", {}) if isinstance(data, dict) else {}
        source = data.get("source", {}) if isinstance(data, dict) else {}
        if chunk.get("verification_status") != "verified" or source.get("verification_status") != "verified":
            raise ValueError(f"{chunk_id} is candidate-only input, not an approved verified copy")
        try:
            record = VerifiedRecord.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError(f"{chunk_id} is malformed: {error}") from error
        if record.chunk.id != chunk_id:
            raise ValueError(f"approved file {chunk_id} contains chunk {record.chunk.id!r}")
        if record.chunk.source_id != record.source.id:
            raise ValueError(f"chunk {chunk_id} source_id does not match its source record")
        records.append(record)

    embedded_sources = {record.source.id for record in records}
    if embedded_sources != set(manifest.approved_source_ids):
        raise ValueError(
            "manifest approved_source_ids do not match approved records: "
            f"{sorted(manifest.approved_source_ids)} != {sorted(embedded_sources)}"
        )
    for record in records:
        if record.chunk.source_id not in manifest.approved_source_ids:
            raise ValueError(
                f"chunk {record.chunk.id} source {record.chunk.source_id!r} is not approved"
            )
        if not record.source.reviewer.strip():
            raise ValueError(f"source {record.source.id!r} lacks a human reviewer attestation")
    return manifest