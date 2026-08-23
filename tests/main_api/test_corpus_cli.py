"""Task 4: the offline corpus-pipeline CLI and its main-API isolation."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def valid_offline_dir(tmp_path):
    """Two bandeng claims (identity + processing) in all four agent stages."""
    from tests.main_api.test_corpus import FISHBASE_SOURCE, MARINADE_SOURCE, STAGES, claim, write_offline_dir

    claims = [
        claim("claim_bandeng_identity_001", "fishbase_chanos_chanos", "identity",
              "Bandeng is the milkfish Chanos chanos, family Chanidae.",
              "Teleostei (teleosts) > Gonorynchiformes (Milkfishes) > Chanidae (Milkfish)", "x"),
        claim("claim_bandeng_processing_001", "marinade_4962", "processing_methods",
              "Bandeng presto is pressure-cooked milkfish at UMKM scale.",
              "KARAKTERISTIK PROSES PENGOLAHAN BANDENG (Chanos chanos) PRESTO SKALA UMKM", "x"),
    ]
    per_stage = {stage: [dict(c, stage=stage) for c in claims] for stage in STAGES}
    return write_offline_dir(tmp_path, [FISHBASE_SOURCE, MARINADE_SOURCE], per_stage)


def test_cli_collect_and_approve_roundtrip(tmp_path, valid_offline_dir):
    from scripts.corpus_pipeline import main

    candidate_dir = tmp_path / "candidates"
    assert main(["collect", "--stage-dir", str(valid_offline_dir), "--candidate-dir", str(candidate_dir)]) == 2
    review_file = tmp_path / "review.json"
    review_file.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_identity_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
        "source_reviews": {"fishbase_chanos_chanos": {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
    }), encoding="utf-8")
    manifest = main(["approve", "--candidate-dir", str(candidate_dir), "--review-file", str(review_file),
                     "--approved-dir", str(tmp_path / "approved"),
                     "--approval-manifest", str(tmp_path / "approval.json"),
                     "--reviewer", "operator", "--confirmation", "APPROVE"])
    assert manifest.reviewer == "operator"
    assert manifest.approved_chunk_ids == ["chunk_bandeng_identity_001"]
    assert (tmp_path / "approved" / "chunk_bandeng_identity_001.json").is_file()
    assert (tmp_path / "approval.json").is_file()


def test_cli_approve_requires_confirmation_argument(tmp_path, valid_offline_dir):
    from scripts.corpus_pipeline import main

    candidate_dir = tmp_path / "candidates"
    main(["collect", "--stage-dir", str(valid_offline_dir), "--candidate-dir", str(candidate_dir)])
    review_file = tmp_path / "review.json"
    review_file.write_text(json.dumps({
        "approved_chunk_ids": ["chunk_bandeng_identity_001"],
        "approved_source_ids": ["fishbase_chanos_chanos"],
        "source_reviews": {"fishbase_chanos_chanos": {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
    }), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["approve", "--candidate-dir", str(candidate_dir), "--review-file", str(review_file),
              "--approved-dir", str(tmp_path / "approved"),
              "--approval-manifest", str(tmp_path / "approval.json"),
              "--reviewer", "operator"])


def test_main_api_never_invokes_corpus_pipeline():
    """No main-API module may import the operator CLI package (`scripts`)."""
    apps_root = Path(__file__).resolve().parents[2] / "apps" / "main_api"
    offenders = [
        str(path.relative_to(apps_root))
        for path in apps_root.rglob("*.py")
        if "import scripts" in path.read_text(encoding="utf-8")
        or "from scripts" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []