"""Task 4: offline corpus stages and the mandatory human approval gate.

The four offline agent-stage files (research, fact_extraction, verification,
knowledge_editor) are the handoff boundary from externally run agents. Only the
CLI approval action (exact `APPROVE` token, explicit chunk IDs, non-empty
reviewer) may create `verified` copies. The main API never runs this process.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

STAGES = ["research", "fact_extraction", "verification", "knowledge_editor"]

FISHBASE_SOURCE = {
    "id": "fishbase_chanos_chanos",
    "title": "Chanos chanos, Milkfish",
    "source_type": "species_summary",
    "url": "https://www.fishbase.se/summary/Chanos-chanos.html",
    "publisher": "FishBase",
    "reviewed_at": "2026-08-23T00:00:00+00:00",
    "verification_status": "candidate",
}
MARINADE_SOURCE = {
    "id": "marinade_4962",
    "title": "Karakteristik Proses Pengolahan Bandeng (Chanos chanos) Presto Skala UMKM",
    "source_type": "journal_article",
    "url": "https://doi.org/10.31629/marinade.v5i02.4962",
    "publisher": "Marinade (Politeknik Negeri Nusa Utara)",
    "reviewed_at": "2026-08-23T00:00:00+00:00",
    "verification_status": "candidate",
}


def claim(claim_id, source_id, category, content, source_quote, stage, species_label="bandeng"):
    return {
        "claim_id": claim_id,
        "source_id": source_id,
        "species_label": species_label,
        "category": category,
        "content": content,
        "source_quote": source_quote,
        "stage": stage,
        "verification_status": "candidate",
    }


def write_offline_dir(tmp_path, sources, claims_by_stage):
    for stage in STAGES:
        payload = {"stage": stage, "sources": sources, "records": claims_by_stage[stage]}
        (tmp_path / f"{stage}.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


@pytest.fixture
def valid_offline_dir(tmp_path):
    """Two bandeng claims (fishbase identity + marinade processing) in all four stages."""
    sources = [FISHBASE_SOURCE, MARINADE_SOURCE]
    claims = [
        claim(
            "claim_bandeng_identity_001",
            "fishbase_chanos_chanos",
            "identity",
            "Bandeng is the milkfish Chanos chanos (Fabricius, 1775), family Chanidae.",
            "Teleostei (teleosts) > Gonorynchiformes (Milkfishes) > Chanidae (Milkfish)",
            "x",
        ),
        claim(
            "claim_bandeng_processing_001",
            "marinade_4962",
            "processing_methods",
            "Bandeng presto is pressure-cooked milkfish with softened bones at UMKM scale.",
            "KARAKTERISTIK PROSES PENGOLAHAN BANDENG (Chanos chanos) PRESTO SKALA UMKM",
            "x",
        ),
    ]
    per_stage = {stage: [dict(c, stage=stage) for c in claims] for stage in STAGES}
    return write_offline_dir(tmp_path, sources, per_stage)


@pytest.fixture
def valid_candidate_dir(valid_offline_dir, tmp_path):
    from apps.main_api.services.corpus import collect_candidate_stages

    candidate_dir = tmp_path / "candidates"
    collect_candidate_stages(valid_offline_dir, candidate_dir)
    return candidate_dir


@pytest.fixture
def review_file(tmp_path):
    path = tmp_path / "review.json"
    path.write_text(json.dumps({"approved_chunk_ids": ["chunk_bandeng_identity_001"]}), encoding="utf-8")
    return path


def _collect(tmp_path, sources, claims_by_stage):
    from apps.main_api.services.corpus import collect_candidate_stages

    stage_dir = write_offline_dir(tmp_path, sources, claims_by_stage)
    return collect_candidate_stages(stage_dir, tmp_path / "candidates")


# --- collect: stage files and lineage -------------------------------------


def test_collect_requires_all_four_offline_agent_stage_files(tmp_path):
    from apps.main_api.services.corpus import collect_candidate_stages

    (tmp_path / "research.json").write_text("[]", encoding="utf-8")
    raised = False
    try:
        collect_candidate_stages(tmp_path, tmp_path / "candidates")
    except FileNotFoundError as error:
        raised = "fact_extraction.json" in str(error)
    assert raised


def test_collect_rejects_editor_chunk_with_missing_lineage(valid_offline_dir, tmp_path):
    # knowledge_editor gains a claim that no other stage has.
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"].append(
        claim("claim_bandeng_taste_001", "fishbase_chanos_chanos", "taste_texture",
              "no lineage", "some quote", "knowledge_editor")
    )
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError, match="research"):
        _collect(tmp_path, editor["sources"], {s: json.loads((valid_offline_dir / f"{s}.json").read_text(encoding="utf-8"))["records"] for s in STAGES})


def test_collect_rejects_mismatched_claim_or_source_ids(valid_offline_dir, tmp_path):
    # Same claim_id but a source_id the research stage never used for it.
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["source_id"] = "marinade_4962"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        _collect(tmp_path, editor["sources"], {s: json.loads((valid_offline_dir / f"{s}.json").read_text(encoding="utf-8"))["records"] for s in STAGES})
    message = str(error.value)
    assert "claim_bandeng_identity_001" in message and "marinade_4962" in message


def test_collect_rejects_unsupported_category(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["category"] = "nutrition"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValidationError):
        _collect(tmp_path, editor["sources"], {s: json.loads((valid_offline_dir / f"{s}.json").read_text(encoding="utf-8"))["records"] for s in STAGES})


def test_collect_rejects_unsupported_label(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["species_label"] = "shark"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValidationError):
        _collect(tmp_path, editor["sources"], {s: json.loads((valid_offline_dir / f"{s}.json").read_text(encoding="utf-8"))["records"] for s in STAGES})


def test_collect_rejects_missing_source_quote(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["source_quote"] = ""
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError, match="source quote"):
        _collect(tmp_path, editor["sources"], {s: json.loads((valid_offline_dir / f"{s}.json").read_text(encoding="utf-8"))["records"] for s in STAGES})


def test_collect_rejects_non_candidate_status(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["verification_status"] = "verified"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValidationError):
        _collect(tmp_path, editor["sources"], {s: json.loads((valid_offline_dir / f"{s}.json").read_text(encoding="utf-8"))["records"] for s in STAGES})


def test_collect_writes_only_candidate_records_with_source_metadata(valid_offline_dir, tmp_path):
    from apps.main_api.services.corpus import collect_candidate_stages

    candidate_dir = tmp_path / "candidates"
    count = collect_candidate_stages(valid_offline_dir, candidate_dir)
    assert count == 2
    files = sorted(p.name for p in candidate_dir.iterdir())
    assert files == ["chunk_bandeng_identity_001.json", "chunk_bandeng_processing_001.json"]
    record = json.loads((candidate_dir / "chunk_bandeng_identity_001.json").read_text(encoding="utf-8"))
    assert record["claim_id"] == "claim_bandeng_identity_001"
    assert record["chunk"]["verification_status"] == "candidate"
    assert record["source"]["id"] == "fishbase_chanos_chanos"
    assert record["source"]["title"] == "Chanos chanos, Milkfish"
    assert record["source"]["publisher"] == "FishBase"
    assert record["source"]["url"].startswith("https://www.fishbase.se/")
    assert record["chunk"]["source_quote"] and record["chunk"]["content"]


# --- approve: the mandatory human approval gate ----------------------------


def test_approval_requires_explicit_human_confirmation(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    try:
        approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "",
                           datetime.now(timezone.utc))
    except PermissionError as error:
        assert "APPROVE" in str(error)
    else:
        raise AssertionError("approval without the exact confirmation token must fail")


def test_approval_rejects_any_confirmation_other_than_exact_token(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    for token in ("approve", "APPROVED", "approve ", "Approve"):
        with pytest.raises(PermissionError, match="APPROVE"):
            approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                               tmp_path / "approval.json", "operator", token,
                               datetime.now(timezone.utc))


def test_approval_requires_non_empty_reviewer(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    for reviewer in ("", "   "):
        with pytest.raises(ValueError, match="reviewer"):
            approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                               tmp_path / "approval.json", reviewer, "APPROVE",
                               datetime.now(timezone.utc))


def test_approval_requires_explicit_approved_chunk_ids(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    for ids in ([], ["   "]):
        review = tmp_path / "review.json"
        review.write_text(json.dumps({"approved_chunk_ids": ids}), encoding="utf-8")
        with pytest.raises(ValueError, match="approved_chunk_ids"):
            approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                               tmp_path / "approval.json", "operator", "APPROVE",
                               datetime.now(timezone.utc))


def test_approval_rejects_unknown_chunk_id(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    review = tmp_path / "review.json"
    review.write_text(json.dumps({"approved_chunk_ids": ["chunk_bandeng_taste_001"]}), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="chunk_bandeng_taste_001"):
        approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc))


def test_approval_requires_human_reviewed_source(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    record = json.loads((valid_candidate_dir / "chunk_bandeng_identity_001.json").read_text(encoding="utf-8"))
    record["source"]["reviewed_at"] = None
    (valid_candidate_dir / "chunk_bandeng_identity_001.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="reviewed by a human"):
        approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc))


def test_approval_copies_only_approved_records_as_verified(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    approved_at = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    manifest = approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                                  tmp_path / "approval.json", "operator", "APPROVE", approved_at)
    assert manifest.reviewer == "operator"
    assert manifest.approved_at == approved_at
    assert manifest.approved_chunk_ids == ["chunk_bandeng_identity_001"]
    assert manifest.approved_source_ids == ["fishbase_chanos_chanos"]
    approved = json.loads((tmp_path / "approved" / "chunk_bandeng_identity_001.json").read_text(encoding="utf-8"))
    assert approved["chunk"]["verification_status"] == "verified"
    assert approved["source"]["verification_status"] == "verified"
    assert approved["source"]["reviewed_at"] == approved_at.isoformat()
    assert not (tmp_path / "approved" / "chunk_bandeng_processing_001.json").exists()


def test_approval_leaves_candidate_files_unchanged(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    before = {p.name: p.read_bytes() for p in valid_candidate_dir.iterdir()}
    approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                       tmp_path / "approval.json", "operator", "APPROVE",
                       datetime.now(timezone.utc))
    after = {p.name: p.read_bytes() for p in valid_candidate_dir.iterdir()}
    assert before == after


def test_approved_records_are_the_only_records_accepted_by_ingestion_contract(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates, require_approved_manifest

    manifest = approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                                  tmp_path / "approval.json", "operator", "APPROVE",
                                  datetime.now(timezone.utc))
    assert manifest.reviewer == "operator"
    assert require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json").approved_chunk_ids == manifest.approved_chunk_ids


# --- require_approved_manifest --------------------------------------------


def test_require_approved_manifest_rejects_missing_file(tmp_path):
    from apps.main_api.services.corpus import require_approved_manifest

    with pytest.raises(FileNotFoundError):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json")


def test_require_approved_manifest_rejects_malformed_manifest(tmp_path):
    from apps.main_api.services.corpus import require_approved_manifest

    (tmp_path / "approval.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json")


def test_require_approved_manifest_rejects_candidate_only_input(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import require_approved_manifest

    (tmp_path / "approved").mkdir()
    # A candidate copy masquerading as an approved copy: same JSON, still candidate status.
    (tmp_path / "approved" / "chunk_bandeng_identity_001.json").write_bytes(
        (valid_candidate_dir / "chunk_bandeng_identity_001.json").read_bytes()
    )
    (tmp_path / "approval.json").write_text(json.dumps({
        "reviewer": "operator",
        "approved_at": "2026-08-23T12:00:00+00:00",
        "approved_chunk_ids": ["chunk_bandeng_identity_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="candidate-only"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json")


def test_require_approved_manifest_rejects_missing_approved_copy(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates, require_approved_manifest

    approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                       tmp_path / "approval.json", "operator", "APPROVE",
                       datetime.now(timezone.utc))
    (tmp_path / "approved" / "chunk_bandeng_identity_001.json").unlink()
    with pytest.raises(FileNotFoundError, match="chunk_bandeng_identity_001"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json")


# --- require_approved_manifest --------------------------------------------