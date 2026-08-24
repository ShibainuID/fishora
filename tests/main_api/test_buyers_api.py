from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from apps.main_api.contracts import LandingPointRecord, LotRecord, PredictionRecord
from apps.main_api.main import create_main_app
from apps.main_api.ports import AppDependencies
from tests.main_api.fakes import (
    FakeCVClient,
    FakeEmbedder,
    FakeImageStore,
    FakeLandingPointRepository,
    FakeLotRepository,
    FakePreferenceRepository,
    FakePredictionRepository,
    FakeSpeciesRepository,
)

NOW = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)


def _lot(lot_id: str, landing_point_id: str, price: Decimal = Decimal("68000")) -> LotRecord:
    return LotRecord(
        id=lot_id,
        prediction_id="pred_ok",
            operator_id="op_rian",
        species_id="species_tenggiri",
        landing_point_id=landing_point_id,
        quantity_kg=Decimal("24"),
        size_category="L",
        starting_price_per_kg=price,
        status="active",
        auction_starts_at=NOW,
        auction_ends_at=NOW + timedelta(hours=4),
        public_slug=lot_id,
        knowledge_snapshot={
            "commercial_uses": ["digoreng"],
            "characteristics": ["gurih"],
        },
    )


def _client():
    app = create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(),
            species_repo=FakeSpeciesRepository([]),
            prediction_repo=FakePredictionRepository({
                "pred_ok": PredictionRecord(
                    id="pred_ok", image_reference="x.jpg", predicted_species_id="species_tenggiri",
                    confidence=0.9, top_candidates=[], model_version="v1",
                    verification_status="confirmed", verified_species_id="species_tenggiri",
                )
            }),
            image_store=FakeImageStore(),
            embedder=FakeEmbedder(),
            lot_repo=FakeLotRepository({
                "lot_near": _lot("lot_near", "lp_near", Decimal("68000")),
                "lot_far": _lot("lot_far", "lp_far", Decimal("50000")),
                "lot_pricey": _lot("lot_pricey", "lp_near", Decimal("120000")),
            }),
            landing_point_repo=FakeLandingPointRepository([
                LandingPointRecord(id="lp_near", name="near", latitude=0.0, longitude=0.0),
                LandingPointRecord(id="lp_far", name="far", latitude=2.0, longitude=0.0),
            ]),
            preference_repo=FakePreferenceRepository(),
        )
    )
    return TestClient(app)


def _login(client: TestClient) -> None:
    assert client.post("/api/v1/auth/login", json={"username": "dewi", "password": "demo"}).status_code == 200


PREFS = {
    "business_type": "rumah_makan",
    "intended_uses": ["digoreng"],
    "characteristics": ["gurih"],
    "max_price_per_kg": "80000",
    "min_quantity_kg": "10",
    "latitude": 0.0,
    "longitude": 0.0,
}


def test_missing_profile_is_200_with_flag_not_404():
    client = _client()
    _login(client)
    response = client.get("/api/v1/buyers/buyer_dewi/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["profile_missing"] is True


def test_recommendations_are_ordered_and_carry_reasons():
    client = _client()
    _login(client)
    saved = client.put("/api/v1/buyers/buyer_dewi/preferences", json=PREFS)
    assert saved.status_code == 200
    response = client.get("/api/v1/buyers/buyer_dewi/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["profile_missing"] is False
    ids = [item["lot"]["id"] for item in body["items"]]
    assert "lot_far" not in ids
    assert ids[0] == "lot_near"
    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)
    reasons = body["items"][0]["reasons"]
    assert {row["criterion"] for row in reasons} == {
        "intended_use", "characteristics", "price", "volume", "distance",
    }
    assert all("met" in row and "detail" in row for row in reasons)
