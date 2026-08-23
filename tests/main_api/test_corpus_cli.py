"""Task 4: the offline corpus-pipeline CLI and its main-API isolation."""

import json
from pathlib import Path

import pytest

APPROVAL_KEY = "cli-test-key"


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


def _review_file(tmp_path, chunk_id="chunk_bandeng_identity_001", source_id="fishbase_chanos_chanos"):
    path = tmp_path / "review.json"
    path.write_text(json.dumps({
        "approved_chunk_ids": [chunk_id],
        "approved_source_ids": [source_id],
        "source_reviews": {source_id: {"reviewer": "operator", "reviewed_at": "2026-08-24T08:00:00+00:00"}},
    }), encoding="utf-8")
    return path


def test_cli_collect_and_approve_roundtrip(tmp_path, valid_offline_dir, monkeypatch):
    from scripts.corpus_pipeline import main

    candidate_dir = tmp_path / "candidates"
    assert main(["collect", "--stage-dir", str(valid_offline_dir), "--candidate-dir", str(candidate_dir)]) == 2
    monkeypatch.setenv("FISHORA_CORPUS_APPROVAL_KEY", APPROVAL_KEY)
    manifest = main(["approve", "--candidate-dir", str(candidate_dir), "--review-file", str(_review_file(tmp_path)),
                     "--approved-dir", str(tmp_path / "approved"),
                     "--approval-manifest", str(tmp_path / "approval.json"),
                     "--reviewer", "operator", "--confirmation", "APPROVE"])
    assert manifest.reviewer == "operator"
    assert manifest.approved_chunk_ids == ["chunk_bandeng_identity_001"]
    assert (tmp_path / "approved" / "chunk_bandeng_identity_001.json").is_file()
    signed = json.loads((tmp_path / "approval.json").read_text(encoding="utf-8"))
    assert signed["signature"] and signed["manifest"]["reviewer"] == "operator"


def test_cli_approve_requires_approval_key_env(tmp_path, valid_offline_dir, monkeypatch):
    from scripts.corpus_pipeline import main

    candidate_dir = tmp_path / "candidates"
    main(["collect", "--stage-dir", str(valid_offline_dir), "--candidate-dir", str(candidate_dir)])
    monkeypatch.delenv("FISHORA_CORPUS_APPROVAL_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["approve", "--candidate-dir", str(candidate_dir), "--review-file", str(_review_file(tmp_path)),
              "--approved-dir", str(tmp_path / "approved"),
              "--approval-manifest", str(tmp_path / "approval.json"),
              "--reviewer", "operator", "--confirmation", "APPROVE"])


def test_cli_approve_requires_confirmation_argument(tmp_path, valid_offline_dir, monkeypatch):
    from scripts.corpus_pipeline import main

    candidate_dir = tmp_path / "candidates"
    main(["collect", "--stage-dir", str(valid_offline_dir), "--candidate-dir", str(candidate_dir)])
    monkeypatch.setenv("FISHORA_CORPUS_APPROVAL_KEY", APPROVAL_KEY)
    with pytest.raises(SystemExit):
        main(["approve", "--candidate-dir", str(candidate_dir), "--review-file", str(_review_file(tmp_path)),
              "--approved-dir", str(tmp_path / "approved"),
              "--approval-manifest", str(tmp_path / "approval.json"),
              "--reviewer", "operator"])


def test_cli_ingest_requires_approval_key_env(tmp_path, monkeypatch, capsys):
    from scripts.corpus_pipeline import main

    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://unused")
    monkeypatch.delenv("FISHORA_CORPUS_APPROVAL_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["ingest", "--approved-dir", str(tmp_path / "approved"),
              "--approval-manifest", str(tmp_path / "approval.json"),
              "--embedding-model", "intfloat/multilingual-e5-base"])
    assert "FISHORA_CORPUS_APPROVAL_KEY" in capsys.readouterr().err


def test_cli_ingest_requires_database_url_env(tmp_path, monkeypatch, capsys):
    """Credentials must come from the environment, never from process args."""
    from scripts.corpus_pipeline import main

    monkeypatch.setenv("FISHORA_CORPUS_APPROVAL_KEY", APPROVAL_KEY)
    monkeypatch.delenv("FISHORA_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit):
        main(["ingest", "--approved-dir", str(tmp_path / "approved"),
              "--approval-manifest", str(tmp_path / "approval.json"),
              "--embedding-model", "intfloat/multilingual-e5-base"])
    assert "FISHORA_DATABASE_URL" in capsys.readouterr().err


def test_cli_ingest_never_accepts_candidate_dir_as_approved(tmp_path, monkeypatch, capsys):
    """The committed candidate corpus must never be an approved input."""
    from scripts.corpus_pipeline import main

    repo_root = Path(__file__).resolve().parents[2]
    candidates = repo_root / "artifacts/knowledge_sources/candidates"
    monkeypatch.setenv("FISHORA_CORPUS_APPROVAL_KEY", APPROVAL_KEY)
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://unused")
    with pytest.raises(SystemExit):
        main(["ingest", "--approved-dir", str(candidates),
              "--approval-manifest", str(tmp_path / "approval.json"),
              "--embedding-model", "intfloat/multilingual-e5-base"])
    assert "candidate" in capsys.readouterr().err


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