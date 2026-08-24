"""Browser access control: without CORS every request fails before FastAPI."""

from fastapi.testclient import TestClient

from apps.main_api.config import MainSettings

ALLOWED = "http://localhost:3000"
DISALLOWED = "https://evil.example"


def test_preflight_from_the_frontend_origin_is_allowed(main_app):
    client = TestClient(main_app)
    response = client.options(
        "/api/v1/fish/identify",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"


def test_actual_request_carries_the_allow_origin_header(main_app):
    client = TestClient(main_app)
    response = client.post(
        "/api/v1/fish/verify",
        json={"prediction_id": "pred_confirm", "verified_species_id": "species_tuna"},
        headers={"Origin": ALLOWED},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_unknown_origin_is_not_granted_access(main_app):
    client = TestClient(main_app)
    response = client.options(
        "/api/v1/fish/identify",
        headers={
            "Origin": DISALLOWED,
            "Access-Control-Request-Method": "POST",
        },
    )
    # The absence of the allow-origin header is the denial.
    assert "access-control-allow-origin" not in response.headers


def test_cors_works_without_any_settings_object(main_app):
    """settings=None must fall back to the default, not construct MainSettings."""
    client = TestClient(main_app)
    response = client.options(
        "/api/v1/fish/identify",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_origins_are_comma_separated_and_whitespace_tolerant(monkeypatch):
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.setenv(
        "FISHORA_CORS_ALLOW_ORIGINS",
        "http://localhost:3000, https://fishora.example ,http://127.0.0.1:3000",
    )
    settings = MainSettings()
    assert settings.cors_origins == [
        "http://localhost:3000",
        "https://fishora.example",
        "http://127.0.0.1:3000",
    ]


def test_default_origins_cover_local_frontend_development(monkeypatch):
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.delenv("FISHORA_CORS_ALLOW_ORIGINS", raising=False)
    settings = MainSettings()
    # Both spellings, since tools disagree on which one they resolve.
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://127.0.0.1:3000" in settings.cors_origins


def test_blank_origins_setting_denies_everything(monkeypatch):
    """An empty list is a valid API-only deployment, not a wildcard."""
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.setenv("FISHORA_CORS_ALLOW_ORIGINS", "")
    settings = MainSettings()
    assert settings.cors_origins == []
