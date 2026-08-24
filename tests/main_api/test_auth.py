from fastapi.testclient import TestClient

from apps.main_api.contracts import PredictionRecord
from apps.main_api.main import create_main_app
from apps.main_api.ports import AppDependencies
from tests.main_api.fakes import (
    FakeCVClient,
    FakeEmbedder,
    FakeImageStore,
    FakeLotRepository,
    FakePredictionRepository,
    FakeSpeciesRepository,
)


def _client():
    app = create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(),
            species_repo=FakeSpeciesRepository([]),
            prediction_repo=FakePredictionRepository({
                "pred_ok": PredictionRecord(
                    id="pred_ok",
                    image_reference="images/ok.jpg",
                    predicted_species_id="species_tenggiri",
                    confidence=0.9,
                    top_candidates=[],
                    model_version="v1",
                    verification_status="confirmed",
                    verified_species_id="species_tenggiri",
                )
            }),
            image_store=FakeImageStore(),
            embedder=FakeEmbedder(),
            lot_repo=FakeLotRepository(),
        )
    )
    return TestClient(app)


PUBLISH = {
    "prediction_id": "pred_ok",
    "quantity_kg": "24",
    "starting_price_per_kg": "68000",
    "size_category": "L",
    "landing_point_id": "lp_muara_angke",
}


def test_login_sets_httponly_samesite_lax_cookie():
    response = _client().post("/api/v1/auth/login", json={"username": "rian", "password": "demo"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert response.json()["role"] == "operator"
    assert response.json()["name"] == "Rian Setiawan"


def test_unauthenticated_publish_is_401():
    response = _client().post("/api/v1/lots", json=PUBLISH)
    assert response.status_code == 401


def test_buyer_cannot_publish_a_lot():
    client = _client()
    client.post("/api/v1/auth/login", json={"username": "dewi", "password": "demo"})
    response = client.post("/api/v1/lots", json=PUBLISH)
    assert response.status_code == 403


def test_operator_cannot_publish_as_another_operator():
    client = _client()
    client.post("/api/v1/auth/login", json={"username": "rian", "password": "demo"})
    response = client.post("/api/v1/lots", json={**PUBLISH, "operator_id": "op_other"})
    assert response.status_code == 403
    ok = client.post("/api/v1/lots", json=PUBLISH)
    assert ok.status_code == 200
    assert ok.json()["operator_id"] == "op_rian"
