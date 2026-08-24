"""Operator-declared species when the CV service is unavailable."""

from io import BytesIO

import pytest
from PIL import Image

from apps.main_api.errors import UnsupportedSpecies
from apps.main_api.ports import AppDependencies
from apps.main_api.services.manual_entry import MANUAL_MODEL_VERSION, ManualEntryService

from tests.main_api.fakes import FakeCVClient


def jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 16), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def _service(species_repo, prediction_repo, image_store, max_image_bytes=10 * 1024 * 1024):
    return ManualEntryService(
        species_repo=species_repo,
        prediction_repo=prediction_repo,
        image_store=image_store,
        max_image_bytes=max_image_bytes,
    )


def _app(species_repo, prediction_repo, image_store):
    from apps.main_api.main import create_main_app

    return create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(None),
            species_repo=species_repo,
            prediction_repo=prediction_repo,
            image_store=image_store,
            embedder=object(),
        )
    )


def test_manual_entry_yields_a_verified_prediction(species_repo, prediction_repo, image_store):
    result = _service(species_repo, prediction_repo, image_store).declare(
        jpeg_bytes(), filename="ikan.jpg", content_type="image/jpeg", species_id="species_tenggiri"
    )

    stored = prediction_repo.get(result.prediction_id)
    # Publishing a lot and generating a knowledge card both gate on exactly
    # these two fields, so a manual entry has to satisfy them or the operator
    # stays blocked when the model is down.
    assert stored.verification_status in ("confirmed", "corrected")
    assert stored.verified_species_id == "species_tenggiri"


def test_manual_entry_is_distinguishable_from_a_confirmed_model_prediction(
    species_repo, prediction_repo, image_store
):
    result = _service(species_repo, prediction_repo, image_store).declare(
        jpeg_bytes(), filename="ikan.jpg", content_type="image/jpeg", species_id="species_tenggiri"
    )

    stored = prediction_repo.get(result.prediction_id)
    # The audit trail must not claim the model agreed: there was no model call.
    assert stored.model_version == MANUAL_MODEL_VERSION
    assert stored.confidence == 0.0
    assert stored.top_candidates == []


def test_manual_entry_persists_the_operator_image(species_repo, prediction_repo, image_store):
    _service(species_repo, prediction_repo, image_store).declare(
        jpeg_bytes(), filename="ikan.jpg", content_type="image/jpeg", species_id="species_nila"
    )
    assert len(image_store.saved) == 1


def test_unsupported_species_is_rejected_before_anything_is_written(
    species_repo, prediction_repo, image_store
):
    with pytest.raises(UnsupportedSpecies):
        _service(species_repo, prediction_repo, image_store).declare(
            jpeg_bytes(), filename="ikan.jpg", content_type="image/jpeg", species_id="species_shark"
        )
    assert image_store.saved == []
    assert prediction_repo.all() == []


def test_oversized_image_is_rejected_before_anything_is_written(
    species_repo, prediction_repo, image_store
):
    from apps.contracts import ImageValidationError

    with pytest.raises(ImageValidationError):
        _service(species_repo, prediction_repo, image_store, max_image_bytes=1).declare(
            jpeg_bytes(), filename="ikan.jpg", content_type="image/jpeg", species_id="species_nila"
        )
    assert image_store.saved == []
    assert prediction_repo.all() == []


def test_endpoint_returns_the_verified_prediction(species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    client = TestClient(_app(species_repo, prediction_repo, image_store))
    response = client.post(
        "/api/v1/fish/manual",
        files={"file": ("ikan.jpg", jpeg_bytes(), "image/jpeg")},
        data={"species_id": "species_tenggiri"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verified_species_id"] == "species_tenggiri"
    assert body["verification_status"] in ("confirmed", "corrected")
    assert body["model_version"] == MANUAL_MODEL_VERSION


def test_endpoint_rejects_an_unsupported_species_with_422(species_repo, prediction_repo, image_store):
    from fastapi.testclient import TestClient

    client = TestClient(_app(species_repo, prediction_repo, image_store))
    response = client.post(
        "/api/v1/fish/manual",
        files={"file": ("ikan.jpg", jpeg_bytes(), "image/jpeg")},
        data={"species_id": "species_shark"},
    )
    assert response.status_code == 422


def test_manual_entry_never_calls_the_cv_service(species_repo, prediction_repo, image_store):
    cv = FakeCVClient(None)
    from fastapi.testclient import TestClient
    from apps.main_api.main import create_main_app

    client = TestClient(
        create_main_app(
            deps=AppDependencies(
                cv_client=cv, species_repo=species_repo, prediction_repo=prediction_repo,
                image_store=image_store, embedder=object(),
            )
        )
    )
    client.post(
        "/api/v1/fish/manual",
        files={"file": ("ikan.jpg", jpeg_bytes(), "image/jpeg")},
        data={"species_id": "species_nila"},
    )
    # The whole point of this path is that it works while CV is down.
    assert cv.calls == 0
