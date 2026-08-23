from pathlib import Path


def test_compose_declares_separate_main_and_gpu_cv_services():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "pgvector/pgvector:pg16" in compose
    assert "main-api:" in compose
    assert "cv-service:" in compose
    assert "profiles: [gpu]" in compose
    assert '"8000:8000"' in compose
    assert '"8001:8001"' in compose
    assert "/opt/fishora/model/export:ro" in compose


def test_images_install_the_expected_extras_and_start_uvicorn():
    main = Path("deploy/main-api.Dockerfile").read_text(encoding="utf-8")
    cv = Path("deploy/cv-service.Dockerfile").read_text(encoding="utf-8")
    assert 'pip install --no-cache-dir "."' in main
    assert 'apps.main_api.main:app' in main
    assert 'pip install --no-cache-dir ".[cv]"' in cv
    assert 'apps.cv_service.main:app' in cv
