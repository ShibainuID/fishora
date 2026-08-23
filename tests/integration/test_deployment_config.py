from pathlib import Path


def test_compose_runs_only_pgvector():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "pgvector/pgvector:pg16" in compose
    assert '"55432:5432"' in compose
    assert "main-api:" not in compose
    assert "cv-service:" not in compose
    assert "profiles:" not in compose


def test_local_start_script_runs_both_apps_from_one_environment():
    script = Path("scripts/run_local.sh").read_text(encoding="utf-8")
    assert ".venv/bin/uvicorn apps.main_api.main:app" in script
    assert ".venv/bin/uvicorn apps.cv_service.main:app" in script
    assert "docker compose up -d db" in script
    assert "FISHORA_CV_EXPORT_DIR" in script
    assert "FISHORA_CV_DEVICE" in script
    assert "Missing .env" not in script
    assert not Path("deploy/main-api.Dockerfile").exists()
    assert not Path("deploy/cv-service.Dockerfile").exists()
