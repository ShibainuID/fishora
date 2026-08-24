"""Browser access control for the frontend.

The frontend runs on its own origin (localhost:3000 in local development)
while the API runs on localhost:8000. Without CORS the browser refuses every
request before it reaches FastAPI, so these tests cover the one thing that
makes the frontend able to talk to the backend at all.

Credentials are allowed because the buyer/operator session is a cookie, which
means the allowed origins must be an explicit list: the wildcard is invalid
alongside credentialed requests and browsers reject the pair.
"""

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
    # Starlette answers the preflight, but never with an allow-origin for an
    # origin outside the list. The absence of the header is the denial.
    assert "access-control-allow-origin" not in response.headers


def test_cors_works_without_any_settings_object(main_app):
    """A complete fake dependency bundle passes settings=None (see
    create_main_app), so CORS must fall back to the configured default rather
    than constructing MainSettings and demanding a DATABASE_URL."""
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
    # Both spellings: Next.js prints localhost, some browsers and tools resolve
    # to the loopback address instead, and a mismatch there looks like a CORS
    # bug with no visible cause.
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://127.0.0.1:3000" in settings.cors_origins


def test_blank_origins_setting_denies_everything(monkeypatch):
    """An explicitly empty list is a deployment choice (API-only, no browser
    client), not an accident that should silently become a wildcard."""
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://x:y@localhost:5432/z")
    monkeypatch.setenv("FISHORA_CORS_ALLOW_ORIGINS", "")
    settings = MainSettings()
    assert settings.cors_origins == []
