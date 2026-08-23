"""Task 4: offline corpus stages and the mandatory human approval gate.

The four offline agent-stage files (research, fact_extraction, verification,
knowledge_editor) are the handoff boundary from externally run agents. Only the
CLI approval action (exact `APPROVE` token, explicit chunk AND source IDs,
per-source human attestation, non-empty reviewer) may create `verified` copies.
The main API never runs this process.
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
    "reviewed_at": None,
    "verification_status": "candidate",
}
MARINADE_SOURCE = {
    "id": "marinade_4962",
    "title": "Karakteristik Proses Pengolahan Bandeng (Chanos chanos) Presto Skala UMKM",
    "source_type": "journal_article",
    "url": "https://doi.org/10.31629/marinade.v5i02.4962",
    "publisher": "Marinade (jurnal pengolahan produk perikanan)",
    "reviewed_at": None,
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
    tmp_path.mkdir(parents=True, exist_ok=True)
    for stage in STAGES:
        payload = {"stage": stage, "sources": sources, "records": claims_by_stage[stage]}
        (tmp_path / f"{stage}.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def _read_records(stage_dir, stage):
    return json.loads((stage_dir / f"{stage}.json").read_text(encoding="utf-8"))["records"]


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
    path.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_identity_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
        "source_reviews": {
            "fishbase_chanos_chanos": {
                "reviewer": "operator",
                "reviewed_at": "2026-08-24T08:00:00+00:00",
            },
        },
    }), encoding="utf-8")
    return path


def _collect(tmp_path, sources, claims_by_stage):
    from apps.main_api.services.corpus import collect_candidate_stages

    stage_dir = write_offline_dir(tmp_path, sources, claims_by_stage)
    return collect_candidate_stages(stage_dir, tmp_path / "candidates")


def approve_test_corpus(tmp_path, *, long_processing=False, include_processing=True, approval_key="test-key"):
    """Build a throwaway approved corpus (never the committed artifacts).

    Two bandeng claims (identity + processing); the processing claim carries a
    180-sentence section when ``long_processing`` is set, and is left out of
    the approval when ``include_processing`` is False. Returns the approved
    directory and the signed approval manifest path.
    """
    from apps.main_api.services.corpus import approve_candidates, collect_candidate_stages

    long_text = " ".join("Kalimat ikan bandeng menjelaskan ciri tubuh dan konteks sumber." for _ in range(180))
    claims = [
        claim(
            "claim_bandeng_identity_001",
            "fishbase_chanos_chanos",
            "identity",
            "Bandeng is the milkfish Chanos chanos, family Chanidae.",
            "Teleostei (teleosts) > Gonorynchiformes",
            "x",
        ),
        claim(
            "claim_bandeng_processing_001",
            "marinade_4962",
            "processing_methods",
            long_text if long_processing else "Bandeng presto is pressure-cooked milkfish at UMKM scale.",
            "KARAKTERISTIK PROSES PENGOLAHAN BANDENG",
            "x",
        ),
    ]
    stage_dir = write_offline_dir(
        tmp_path / "offline",
        [FISHBASE_SOURCE, MARINADE_SOURCE],
        {stage: [dict(c, stage=stage) for c in claims] for stage in STAGES},
    )
    candidate_dir = tmp_path / "candidates"
    collect_candidate_stages(stage_dir, candidate_dir)
    approved_chunk_ids = ["chunk_bandeng_identity_001"]
    approved_source_ids = ["fishbase_chanos_chanos"]
    if include_processing:
        approved_chunk_ids.append("chunk_bandeng_processing_001")
        approved_source_ids.append("marinade_4962")
    review = tmp_path / "review.json"
    review.write_text(json.dumps({
        "approved_chunk_ids": approved_chunk_ids,
        "approved_source_ids": approved_source_ids,
        "source_reviews": {
            source_id: {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}
            for source_id in approved_source_ids
        },
    }), encoding="utf-8")
    approved_dir = tmp_path / "approved"
    manifest_path = tmp_path / "approval.json"
    approve_candidates(
        candidate_dir, review, approved_dir, manifest_path, "operator", "APPROVE",
        datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc), approval_key=approval_key,
    )
    return approved_dir, manifest_path


def _approve(valid_candidate_dir, review_file, tmp_path, approved_at=None, approval_key="test-key"):
    from apps.main_api.services.corpus import approve_candidates

    return approve_candidates(
        valid_candidate_dir, review_file, tmp_path / "approved",
        tmp_path / "approval.json", "operator", "APPROVE",
        approved_at or datetime.now(timezone.utc), approval_key=approval_key,
    )


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
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"].append(
        claim("claim_bandeng_taste_001", "fishbase_chanos_chanos", "taste_texture",
              "no lineage", "some quote", "knowledge_editor")
    )
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError, match="research"):
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_mismatched_claim_or_source_ids(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["source_id"] = "marinade_4962"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})
    message = str(error.value)
    assert "claim_bandeng_identity_001" in message and "marinade_4962" in message


def test_collect_rejects_unsupported_category(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["category"] = "nutrition"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValidationError):
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_unsupported_label(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["species_label"] = "shark"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValidationError):
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_missing_source_quote(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["source_quote"] = ""
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError, match="source quote"):
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_non_candidate_status(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["records"][0]["verification_status"] = "verified"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValidationError):
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


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
    assert record["source"]["reviewed_at"] is None
    assert record["chunk"]["source_quote"] and record["chunk"]["content"]


# --- collect: every stage record is validated (not just the editor) -------


def test_collect_rejects_record_stage_mismatching_filename(valid_offline_dir, tmp_path):
    research = json.loads((valid_offline_dir / "research.json").read_text(encoding="utf-8"))
    research["records"][0]["stage"] = "knowledge_editor"
    (valid_offline_dir / "research.json").write_text(json.dumps(research), encoding="utf-8")
    with pytest.raises(ValueError, match="research.json"):
        _collect(tmp_path, research["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_empty_content_in_any_stage_record(valid_offline_dir, tmp_path):
    research = json.loads((valid_offline_dir / "research.json").read_text(encoding="utf-8"))
    research["records"][0]["content"] = ""
    (valid_offline_dir / "research.json").write_text(json.dumps(research), encoding="utf-8")
    with pytest.raises(ValueError, match="empty content"):
        _collect(tmp_path, research["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_lineage_record_without_editor_match(valid_offline_dir, tmp_path):
    research = json.loads((valid_offline_dir / "research.json").read_text(encoding="utf-8"))
    research["records"].append(
        claim("claim_bandeng_taste_001", "fishbase_chanos_chanos", "taste_texture",
              "research-only", "some quote", "research")
    )
    (valid_offline_dir / "research.json").write_text(json.dumps(research), encoding="utf-8")
    with pytest.raises(ValueError, match="knowledge_editor"):
        _collect(tmp_path, research["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_duplicate_lineage_key(valid_offline_dir, tmp_path):
    verification = json.loads((valid_offline_dir / "verification.json").read_text(encoding="utf-8"))
    verification["records"].append(dict(verification["records"][0]))
    (valid_offline_dir / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        _collect(tmp_path, verification["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


# --- collect/approve: path traversal, absolute IDs, symlinks --------------


def test_collect_rejects_unsafe_claim_id(valid_offline_dir, tmp_path):
    research = json.loads((valid_offline_dir / "research.json").read_text(encoding="utf-8"))
    research["records"][0]["claim_id"] = "../evil"
    (valid_offline_dir / "research.json").write_text(json.dumps(research), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        _collect(tmp_path, research["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_unsafe_source_id(valid_offline_dir, tmp_path):
    editor = json.loads((valid_offline_dir / "knowledge_editor.json").read_text(encoding="utf-8"))
    editor["sources"][0]["id"] = "a/../b"
    (valid_offline_dir / "knowledge_editor.json").write_text(json.dumps(editor), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        _collect(tmp_path, editor["sources"], {s: _read_records(valid_offline_dir, s) for s in STAGES})


def test_collect_rejects_symlinked_candidate_target(valid_offline_dir, tmp_path):
    from apps.main_api.services.corpus import collect_candidate_stages

    candidate_dir = tmp_path / "candidates"
    candidate_dir.mkdir()
    (tmp_path / "elsewhere.json").write_text("{}", encoding="utf-8")
    (candidate_dir / "chunk_bandeng_identity_001.json").symlink_to(tmp_path / "elsewhere.json")
    with pytest.raises(ValueError, match="symlink"):
        collect_candidate_stages(valid_offline_dir, candidate_dir)


def test_approve_rejects_traversal_and_absolute_chunk_ids(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    for bad_id in ("../other", "/etc/passwd", "a/b"):
        review = tmp_path / "review.json"
        review.write_text(json.dumps({
            "approved_chunk_ids": [bad_id],
            "approved_source_ids": ["fishbase_chanos_chanos"],
            "source_reviews": {"fishbase_chanos_chanos": {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="unsafe"):
            approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                               tmp_path / "approval.json", "operator", "APPROVE",
                               datetime.now(timezone.utc), approval_key="test-key")


def test_approve_rejects_symlinked_candidate_file(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    target = tmp_path / "real.json"
    target.write_text("{}", encoding="utf-8")
    victim = valid_candidate_dir / "chunk_bandeng_identity_001.json"
    victim.unlink()
    victim.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_require_approved_manifest_rejects_symlinked_approved_copy(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    approved_path = tmp_path / "approved" / "chunk_bandeng_identity_001.json"
    approved_path.unlink()
    approved_path.symlink_to(tmp_path / "approval.json")
    with pytest.raises(ValueError, match="symlink"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


# --- approve: the mandatory human approval gate ----------------------------


def test_approval_requires_explicit_human_confirmation(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    try:
        approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "",
                           datetime.now(timezone.utc), approval_key="test-key")
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
                               datetime.now(timezone.utc), approval_key="test-key")


def test_approval_requires_non_empty_reviewer(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    for reviewer in ("", "   "):
        with pytest.raises(ValueError, match="reviewer"):
            approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                               tmp_path / "approval.json", reviewer, "APPROVE",
                               datetime.now(timezone.utc), approval_key="test-key")


def test_approval_requires_explicit_approved_chunk_ids(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    for ids in ([], ["   "]):
        review = tmp_path / "review.json"
        review.write_text(json.dumps({
            "approved_chunk_ids": ids,
            "approved_source_ids": ["fishbase_chanos_chanos"],
            "source_reviews": {"fishbase_chanos_chanos": {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
        }), encoding="utf-8")
        with pytest.raises(ValueError, match="approved_chunk_ids"):
            approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                               tmp_path / "approval.json", "operator", "APPROVE",
                               datetime.now(timezone.utc), approval_key="test-key")


def test_approval_requires_explicit_approved_source_ids(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    review = tmp_path / "review.json"
    review.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_identity_001"],
        "approved_source_ids": [],
        "source_reviews": {},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="approved_source_ids"):
        approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_requires_source_attestation_for_every_approved_source(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    review = tmp_path / "review.json"
    review.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_identity_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
        "source_reviews": {},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="attestation"):
        approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_rejects_unknown_chunk_id(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    review = tmp_path / "review.json"
    review.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_taste_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
        "source_reviews": {"fishbase_chanos_chanos": {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
    }), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="chunk_bandeng_taste_001"):
        approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_rejects_chunk_whose_source_is_not_approved(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import approve_candidates

    review = tmp_path / "review.json"
    review.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_processing_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
        "source_reviews": {"fishbase_chanos_chanos": {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="approved_source_ids"):
        approve_candidates(valid_candidate_dir, review, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_copies_only_approved_records_as_verified(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    approved_at = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    manifest = approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                                  tmp_path / "approval.json", "operator", "APPROVE", approved_at, approval_key="test-key")
    assert manifest.reviewer == "operator"
    assert manifest.approved_at == approved_at
    assert manifest.approved_chunk_ids == ["chunk_bandeng_identity_001"]
    assert manifest.approved_source_ids == ["fishbase_chanos_chanos"]
    approved = json.loads((tmp_path / "approved" / "chunk_bandeng_identity_001.json").read_text(encoding="utf-8"))
    assert approved["chunk"]["verification_status"] == "verified"
    assert approved["source"]["verification_status"] == "verified"
    assert approved["source"]["reviewer"] == "operator"
    assert approved["source"]["reviewed_at"] == "2026-08-24T08:00:00Z"
    assert not (tmp_path / "approved" / "chunk_bandeng_processing_001.json").exists()


def test_approval_leaves_candidate_files_unchanged(tmp_path, valid_candidate_dir, review_file):
    before = {p.name: p.read_bytes() for p in valid_candidate_dir.iterdir()}
    _approve(valid_candidate_dir, review_file, tmp_path)
    after = {p.name: p.read_bytes() for p in valid_candidate_dir.iterdir()}
    assert before == after


def test_approved_records_are_the_only_records_accepted_by_ingestion_contract(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates, require_approved_manifest

    manifest = approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                                  tmp_path / "approval.json", "operator", "APPROVE",
                                  datetime.now(timezone.utc), approval_key="test-key")
    assert manifest.reviewer == "operator"
    assert require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key").approved_chunk_ids == manifest.approved_chunk_ids


# --- approve: candidate/approved root separation ---------------------------


def test_approval_rejects_identical_candidate_and_approved_dirs(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    with pytest.raises(ValueError, match="must differ"):
        approve_candidates(valid_candidate_dir, review_file, valid_candidate_dir,
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_rejects_approved_dir_nested_in_candidate_dir(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    with pytest.raises(ValueError, match="nested"):
        approve_candidates(valid_candidate_dir, review_file, valid_candidate_dir / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_rejects_candidate_dir_nested_in_approved_dir(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    with pytest.raises(ValueError, match="nested"):
        approve_candidates(valid_candidate_dir, review_file, tmp_path,
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


def test_approval_rejects_symlink_alias_of_candidate_dir(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    alias = tmp_path / "alias"
    alias.symlink_to(valid_candidate_dir, target_is_directory=True)
    with pytest.raises(ValueError, match="must differ"):
        approve_candidates(valid_candidate_dir, review_file, alias,
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


# --- signed approval manifest (HMAC-SHA256) -------------------------------


def test_approval_requires_approval_key(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    with pytest.raises(ValueError, match="approval key"):
        approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key=None)


def test_approval_rejects_blank_approval_key(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    for key in ("", "   "):
        with pytest.raises(ValueError, match="approval key"):
            approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                               tmp_path / "approval.json", "operator", "APPROVE",
                               datetime.now(timezone.utc), approval_key=key)


def test_approval_never_stores_or_logs_the_key(tmp_path, valid_candidate_dir, review_file):
    _approve(valid_candidate_dir, review_file, tmp_path, approval_key="super-secret-key")
    manifest_text = (tmp_path / "approval.json").read_text(encoding="utf-8")
    approved_text = (tmp_path / "approved" / "chunk_bandeng_identity_001.json").read_text(encoding="utf-8")
    assert "super-secret-key" not in manifest_text
    assert "super-secret-key" not in approved_text


def test_require_approved_manifest_rejects_missing_key(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    with pytest.raises(ValueError, match="approval key"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key=None)


def test_require_approved_manifest_rejects_unsigned_manifest(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    signed = json.loads((tmp_path / "approval.json").read_text(encoding="utf-8"))
    del signed["signature"]
    (tmp_path / "approval.json").write_text(json.dumps(signed), encoding="utf-8")
    with pytest.raises(ValueError, match="unsigned"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_wrong_key(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    with pytest.raises(ValueError, match="signature"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="wrong-key")


def test_require_approved_manifest_rejects_altered_approved_file(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    approved_path = tmp_path / "approved" / "chunk_bandeng_identity_001.json"
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    approved["chunk"]["content"] = "HACKED CONTENT"
    approved_path.write_text(json.dumps(approved), encoding="utf-8")
    with pytest.raises(ValueError, match="signature|altered"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_hand_written_verified_records(tmp_path, valid_candidate_dir):
    from apps.main_api.services.corpus import require_approved_manifest

    (tmp_path / "approved").mkdir()
    record = json.loads((valid_candidate_dir / "chunk_bandeng_identity_001.json").read_text(encoding="utf-8"))
    record["chunk"]["verification_status"] = "verified"
    record["source"]["verification_status"] = "verified"
    record["source"]["reviewed_at"] = "2026-08-24T08:00:00Z"
    record["source"]["reviewer"] = "forged"
    (tmp_path / "approved" / "chunk_bandeng_identity_001.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "approval.json").write_text(json.dumps({
        "manifest": {
            "reviewer": "operator",
            "approved_at": "2026-08-23T12:00:00+00:00",
            "approved_chunk_ids": ["chunk_bandeng_identity_001"],
            "approved_source_ids": ["fishbase_chanos_chanos"],
        },
        "signature": "0" * 64,
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="signature|altered"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


# --- reviewed_at only written by approval ---------------------------------


def test_collect_rejects_source_reviewed_at_in_offline_input(tmp_path):
    from apps.main_api.services.corpus import collect_candidate_stages

    sources = [dict(FISHBASE_SOURCE, reviewed_at="2026-08-24T08:00:00+00:00")]
    claims = [claim("claim_bandeng_identity_001", "fishbase_chanos_chanos", "identity",
                    "content", "quote", "x")]
    per_stage = {stage: [dict(c, stage=stage) for c in claims] for stage in STAGES}
    stage_dir = write_offline_dir(tmp_path, sources, per_stage)
    with pytest.raises(ValueError, match="reviewed_at"):
        collect_candidate_stages(stage_dir, tmp_path / "candidates")


def test_approve_rejects_candidate_source_carrying_reviewed_at(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import approve_candidates

    record_path = valid_candidate_dir / "chunk_bandeng_identity_001.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["source"]["reviewed_at"] = "2026-08-24T08:00:00+00:00"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="reviewed_at"):
        approve_candidates(valid_candidate_dir, review_file, tmp_path / "approved",
                           tmp_path / "approval.json", "operator", "APPROVE",
                           datetime.now(timezone.utc), approval_key="test-key")


# --- committed corpus: evidence integrity ---------------------------------


def test_committed_corpus_has_no_synthetic_approval_and_covers_all_labels():
    """The committed candidate corpus carries no human approval metadata:
    sources have no reviewed_at, every claim has a support quote, and all 11
    labels are covered (gembolo only as the unresolved-identity limitation)."""
    from apps.main_api.services.corpus import SAFE_ID, CandidateRecord

    candidates_dir = Path(__file__).resolve().parents[2] / "artifacts/knowledge_sources/candidates"
    records = [
        CandidateRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(candidates_dir.glob("*.json"))
    ]
    assert records, "committed candidate corpus must exist"
    assert {r.chunk.species_label for r in records} == {
        "bandeng", "gelama_bunga", "gembolo", "gulamah", "kembung", "kuniran",
        "mujair", "nila", "senangin", "tenggiri", "tuna",
    }
    for record in records:
        assert SAFE_ID.fullmatch(record.claim_id), record.claim_id
        assert SAFE_ID.fullmatch(record.source.id), record.source.id
        assert record.source.reviewed_at is None, (
            f"no synthetic human approval on candidates: {record.chunk.id}"
        )
        assert record.source.url and record.source.title and record.source.publisher
        assert record.chunk.source_quote.strip(), record.chunk.id
    gembolo = next(r for r in records if r.chunk.species_label == "gembolo")
    assert gembolo.source.url.startswith("https://www.fishbase.se/"), "gembolo needs a traceable URL"
    assert "unresolved" in gembolo.chunk.content.lower()
    jbau = next(r for r in records if r.source.id == "jbau_86202")
    assert jbau.source.title == (
        "Quality evaluation of fish burger from tilapia (Oreochromis mossambicus) "
        "during frozen storage (-18\u00b0C)"
    ), "JBAU source must use the canonical title"


# --- require_approved_manifest --------------------------------------------


def test_load_verified_records_returns_strictly_verified_records(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import load_verified_records

    _approve(valid_candidate_dir, review_file, tmp_path)
    records = load_verified_records(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")
    assert [record.chunk.id for record in records] == ["chunk_bandeng_identity_001"]
    assert records[0].chunk.verification_status == "verified"
    assert records[0].source.verification_status == "verified"
    assert records[0].source.reviewer == "operator"


def test_load_verified_records_rechecks_hashes_after_gate(tmp_path, valid_candidate_dir, review_file, monkeypatch):
    """A file swapped after require_approved_manifest passes is caught before
    parsing: no TOCTOU window between signature verification and record use."""
    from apps.main_api.services import corpus

    _approve(valid_candidate_dir, review_file, tmp_path)
    approved_dir = tmp_path / "approved"
    manifest_path = tmp_path / "approval.json"
    original = corpus.require_approved_manifest

    def gate_with_swap(*args, **kwargs):
        result = original(*args, **kwargs)
        path = approved_dir / "chunk_bandeng_identity_001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["chunk"]["content"] = "SWAPPED AFTER VERIFICATION"
        path.write_text(json.dumps(data), encoding="utf-8")
        return result

    monkeypatch.setattr(corpus, "require_approved_manifest", gate_with_swap)
    with pytest.raises(ValueError, match="altered|signature"):
        corpus.load_verified_records(approved_dir, manifest_path, approval_key="test-key")


def test_require_approved_manifest_rejects_missing_file(tmp_path):
    from apps.main_api.services.corpus import require_approved_manifest

    with pytest.raises(FileNotFoundError):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_malformed_manifest(tmp_path):
    from apps.main_api.services.corpus import require_approved_manifest

    (tmp_path / "approval.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_empty_id_lists(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    original = json.loads((tmp_path / "approval.json").read_text(encoding="utf-8"))
    for field in ("approved_chunk_ids", "approved_source_ids"):
        signed = json.loads(json.dumps(original))
        signed["manifest"][field] = []
        (tmp_path / "approval.json").write_text(json.dumps(signed), encoding="utf-8")
        with pytest.raises(ValueError, match=field):
            require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_candidate_only_input(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    (tmp_path / "approved" / "chunk_bandeng_identity_001.json").write_bytes(
        (valid_candidate_dir / "chunk_bandeng_identity_001.json").read_bytes()
    )
    with pytest.raises(ValueError, match="candidate-only"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_missing_approved_copy(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    (tmp_path / "approved" / "chunk_bandeng_identity_001.json").unlink()
    with pytest.raises(FileNotFoundError, match="chunk_bandeng_identity_001"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_extra_approved_file(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    (tmp_path / "approved" / "chunk_bandeng_processing_001.json").write_bytes(
        (tmp_path / "approved" / "chunk_bandeng_identity_001.json").read_bytes()
    )
    with pytest.raises(ValueError, match="do not match"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_unapproved_chunk_source(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    signed = json.loads((tmp_path / "approval.json").read_text(encoding="utf-8"))
    signed["manifest"]["approved_source_ids"] = ["marinade_4962"]
    (tmp_path / "approval.json").write_text(json.dumps(signed), encoding="utf-8")
    with pytest.raises(ValueError, match="approved_source_ids do not match"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_missing_source_reviewer(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    approved_path = tmp_path / "approved" / "chunk_bandeng_identity_001.json"
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    approved["source"]["reviewer"] = ""
    approved_path.write_text(json.dumps(approved), encoding="utf-8")
    with pytest.raises(ValueError, match="reviewer"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_malformed_approved_record(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    (tmp_path / "approved" / "chunk_bandeng_identity_001.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")


def test_require_approved_manifest_rejects_unsafe_manifest_ids(tmp_path, valid_candidate_dir, review_file):
    from apps.main_api.services.corpus import require_approved_manifest

    _approve(valid_candidate_dir, review_file, tmp_path)
    signed = json.loads((tmp_path / "approval.json").read_text(encoding="utf-8"))
    signed["manifest"]["approved_chunk_ids"] = ["../evil"]
    (tmp_path / "approval.json").write_text(json.dumps(signed), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        require_approved_manifest(tmp_path / "approved", tmp_path / "approval.json", approval_key="test-key")