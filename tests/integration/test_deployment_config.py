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
    # Both apps launch from the same detected interpreter. Asserted through the
    # $PY variable rather than a hardcoded .venv/bin path, because the script
    # now also supports the Windows Scripts/ layout. The invariant is one
    # shared environment, not one particular spelling of it.
    assert '"$PY" -m uvicorn apps.main_api.main:app' in script
    assert '"$PY" -m uvicorn apps.cv_service.main:app' in script
    assert 'PY=".venv/bin/python"' in script
    assert 'PY=".venv/Scripts/python.exe"' in script
    assert "docker compose up -d db" in script
    assert "FISHORA_CV_EXPORT_DIR" in script
    assert "FISHORA_CV_DEVICE" in script
    assert "Missing .env" not in script
    assert not Path("deploy/main-api.Dockerfile").exists()
    assert not Path("deploy/cv-service.Dockerfile").exists()


def test_local_start_script_keeps_frontend_and_api_addresses_in_step():
    """The browser calls the API cross-origin, so the frontend's API base URL
    and the API's CORS allow-list must both derive from the same port
    variables. A hardcoded value in either place is the bug this guards: it
    works until someone changes a port, and then fails with no visible cause."""
    script = Path("scripts/run_local.sh").read_text(encoding="utf-8")
    assert "FISHORA_FRONTEND_PORT" in script
    assert "${FISHORA_MAIN_API_PORT}" in script.split("NEXT_PUBLIC_API_BASE_URL=")[1]
    assert "${FISHORA_FRONTEND_PORT}" in script.split("FISHORA_CORS_ALLOW_ORIGINS=")[1]
    # The frontend stays optional: a machine without Node still runs the
    # backend and the CV service.
    assert "FISHORA_SKIP_FRONTEND" in script
    assert "pnpm dev" in script
