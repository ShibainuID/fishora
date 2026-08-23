from io import BytesIO

import pytest
from PIL import Image

from apps.main_api.errors import CvUnavailable
from apps.main_api.ports import AppDependencies

from tests.main_api.fakes import FakeCVClient, FakePredictionRepository


def jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 16), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def _app(*, settings=None, cv_client=None, species_repo=None, prediction_repo=None, image_store=None):
    from apps.main_api.main import create_main_app

    return create_main_app(
        settings=settings,
        deps=AppDependencies(
            cv_client=cv_client, species_repo=species_repo, prediction_repo=prediction_repo, image_store=image_store
        ),
    )


def test_identify_persists_pending_prediction_and_maps_all_top_three_species(cv_result, species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    cv = FakeCVClient(cv_result)
    response = TestClient(_app(cv_client=cv, species_repo=species_repo, prediction_repo=prediction_repo, image_store=image_store)).post(
        "/api/v1/fish/identify",
        files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "pending"
    assert len(body["top_candidates"]) == 3
    assert [c["normalized_label"] for c in body["top_candidates"]] == ["tuna", "tenggiri", "gembolo"]
    assert [c["species_id"] for c in body["top_candidates"]] == ["species_tuna", "species_tenggiri", "species_gembolo"]
    assert body["prediction"]["species_id"] == "species_tuna"
    assert body["prediction"]["confidence"] == 0.71
    assert body["model_version"] == "test-model-1"
    assert body["status"] == "confident_prediction"
    record = prediction_repo.get(body["prediction_id"])
    assert record is not None
    assert record.verification_status == "pending"
    assert record.predicted_species_id == "species_tuna"
    assert record.image_reference == f"images/{record.id}.jpg"
    assert record.model_version == "test-model-1"
    assert len(image_store.saved) == 1
    assert image_store.deleted == []  # no compensation on success
    assert cv.calls == 1


def test_cv_timeout_maps_to_retriable_503_without_persisting(species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    app = _app(
        cv_client=FakeCVClient(error=CvUnavailable("cv timeout")),
        species_repo=species_repo,
        prediction_repo=prediction_repo,
        image_store=image_store,
    )
    response = TestClient(app).post(
        "/api/v1/fish/identify",
        files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 503
    assert prediction_repo.all() == []
    assert image_store.saved == []


def test_cv_failure_response_does_not_disclose_internal_url_or_credentials(species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    app = _app(
        cv_client=FakeCVClient(error=CvUnavailable("http://cv-service:8001 Authorization secret-key")),
        species_repo=species_repo,
        prediction_repo=prediction_repo,
        image_store=image_store,
    )
    response = TestClient(app).post("/api/v1/fish/identify", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 503
    assert "cv-service" not in response.text
    assert "secret-key" not in response.text
    assert prediction_repo.all() == []
    assert image_store.saved == []


@pytest.mark.parametrize(
    ("payload", "content_type", "max_bytes", "expected_status"),
    [
        (b"not-an-image", "image/jpeg", 10485760, 400),
        (b"not-an-image", "image/gif", 10485760, 415),
    ],
)
def test_image_trust_boundary_rejects_invalid_media_before_cv(payload, content_type, max_bytes, expected_status, species_repo, prediction_repo, image_store):
    from apps.main_api.config import MainSettings
    from fastapi.testclient import TestClient

    cv = FakeCVClient()
    settings = MainSettings(database_url="postgresql+psycopg://fishora:fishora@localhost:55432/fishora", cv_max_image_bytes=max_bytes)
    app = _app(settings=settings, cv_client=cv, species_repo=species_repo, prediction_repo=prediction_repo, image_store=image_store)
    response = TestClient(app).post("/api/v1/fish/identify", files={"file": ("fish.jpg", payload, content_type)})
    assert response.status_code == expected_status
    assert cv.calls == 0
    assert prediction_repo.all() == []
    assert image_store.saved == []


def test_image_trust_boundary_rejects_oversize_before_cv(species_repo, prediction_repo, image_store):
    from apps.main_api.config import MainSettings
    from fastapi.testclient import TestClient

    cv = FakeCVClient()
    settings = MainSettings(database_url="postgresql+psycopg://fishora:fishora@localhost:55432/fishora", cv_max_image_bytes=1)
    app = _app(settings=settings, cv_client=cv, species_repo=species_repo, prediction_repo=prediction_repo, image_store=image_store)
    response = TestClient(app).post("/api/v1/fish/identify", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 413
    assert cv.calls == 0


def test_low_confidence_envelope_still_returns_200_and_pending(cv_low_confidence, species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    app = _app(
        cv_client=FakeCVClient(cv_low_confidence),
        species_repo=species_repo,
        prediction_repo=prediction_repo,
        image_store=image_store,
    )
    response = TestClient(app).post("/api/v1/fish/identify", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "low_confidence_human_verification_required"
    assert body["verification_status"] == "pending"
    assert len(body["top_candidates"]) == 3
    assert prediction_repo.get(body["prediction_id"]).verification_status == "pending"


def test_unsupported_cv_label_is_upstream_contract_error_without_persistence(cv_unsupported_label, species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    app = _app(
        cv_client=FakeCVClient(cv_unsupported_label),
        species_repo=species_repo,
        prediction_repo=prediction_repo,
        image_store=image_store,
    )
    response = TestClient(app).post("/api/v1/fish/identify", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 502
    assert prediction_repo.all() == []
    assert image_store.saved == []


def test_filesystem_image_store_saves_opaque_reference(tmp_path):
    from apps.main_api.services.image_store import FilesystemImageStore

    store = FilesystemImageStore(tmp_path)
    reference = store.save("pred_abc123", jpeg_bytes(), "image/jpeg")
    assert reference == "images/pred_abc123.jpg"
    assert (tmp_path / "pred_abc123.jpg").read_bytes() == jpeg_bytes()


def test_filesystem_image_store_delete_removes_only_that_file(tmp_path):
    from apps.main_api.services.image_store import FilesystemImageStore

    store = FilesystemImageStore(tmp_path)
    store.save("pred_one", jpeg_bytes(), "image/jpeg")
    store.save("pred_two", jpeg_bytes(), "image/jpeg")
    store.delete("images/pred_one.jpg")
    assert not (tmp_path / "pred_one.jpg").exists()
    assert (tmp_path / "pred_two.jpg").exists()  # sibling untouched


class FailingPredictionRepository(FakePredictionRepository):
    def create(self, *args, **kwargs):
        raise RuntimeError("db commit failed")


def test_prediction_persistence_failure_deletes_saved_image(cv_result, species_repo, image_store):
    from fastapi.testclient import TestClient

    app = _app(
        cv_client=FakeCVClient(cv_result),
        species_repo=species_repo,
        prediction_repo=FailingPredictionRepository(),
        image_store=image_store,
    )
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/fish/identify",
        files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 500
    assert image_store.saved == []  # the newly saved image was compensated away
    assert len(image_store.deleted) == 1  # exactly one delete: the newly saved image

def test_complete_fake_bundle_needs_no_settings_env_or_db_factory(monkeypatch, cv_result, species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    monkeypatch.delenv("FISHORA_DATABASE_URL", raising=False)
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)

    def _forbid_settings(*args, **kwargs):
        raise AssertionError("MainSettings must not be constructed with a complete fake bundle")

    monkeypatch.setattr("apps.main_api.main.MainSettings", _forbid_settings)

    app = _app(
        cv_client=FakeCVClient(cv_result),
        species_repo=species_repo,
        prediction_repo=prediction_repo,
        image_store=image_store,
    )
    assert app.state.settings is None  # no settings object constructed
    assert app.state.deps.session_factory is None  # no DB factory constructed

    client = TestClient(app)
    response = client.post("/api/v1/fish/identify", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")})
    assert response.status_code == 200
    assert response.json()["verification_status"] == "pending"

    prediction_id = response.json()["prediction_id"]
    verify = client.post("/api/v1/fish/verify", json={"prediction_id": prediction_id, "verified_species_id": "species_tuna"})
    assert verify.status_code == 200
    assert verify.json()["verification_status"] == "confirmed"
