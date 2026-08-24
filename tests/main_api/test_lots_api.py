from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from apps.main_api.contracts import LotRecord, PredictionRecord
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


NOW = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)


def _verified() -> PredictionRecord:
    return PredictionRecord(
        id="pred_ok",
        image_reference="images/ok.jpg",
        predicted_species_id="species_kembung",
        confidence=0.91,
        top_candidates=[],
        model_version="v1",
        verification_status="confirmed",
        verified_species_id="species_tenggiri",
    )


def _lot(**overrides) -> LotRecord:
    row = dict(
        id="lot_1",
        prediction_id="pred_ok",
        operator_id="op_rian",
        species_id="species_tenggiri",
        landing_point_id="lp_muara_angke",
        quantity_kg=Decimal("24"),
        size_category="L",
        starting_price_per_kg=Decimal("68000"),
        status="active",
        auction_starts_at=NOW,
        auction_ends_at=NOW + timedelta(hours=4),
        public_slug="tenggiri-lot1",
    )
    row.update(overrides)
    return LotRecord(**row)


def _client(lot_repo=None, prediction_repo=None):
    predictions = prediction_repo or FakePredictionRepository({"pred_ok": _verified()})
    lots = lot_repo or FakeLotRepository()
    app = create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(),
            species_repo=FakeSpeciesRepository([]),
            prediction_repo=predictions,
            image_store=FakeImageStore(),
            embedder=FakeEmbedder(),
            lot_repo=lots,
        )
    )
    return TestClient(app), lots


def _login(client: TestClient, username: str = "dewi") -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "demo"})
    assert response.status_code == 200


def test_bid_at_or_below_highest_is_409_with_current_highest():
    client, lots = _client(FakeLotRepository({"lot_1": _lot()}))
    _login(client, "dewi")
    first = client.post("/api/v1/lots/lot_1/bids", json={"amount_per_kg": "70000"})
    assert first.status_code == 200
    blocked = client.post("/api/v1/lots/lot_1/bids", json={"amount_per_kg": "70000"})
    assert blocked.status_code == 409
    body = blocked.json()
    assert body["detail"] == "bid must exceed current highest"
    assert Decimal(body["current_highest_per_kg"]) == Decimal("70000")
    below = client.post("/api/v1/lots/lot_1/bids", json={"amount_per_kg": "69000"})
    assert below.status_code == 409
    assert Decimal(below.json()["current_highest_per_kg"]) == Decimal("70000")


def test_bid_on_closed_lot_is_409():
    client, _ = _client(FakeLotRepository({"lot_1": _lot(status="closed")}))
    _login(client, "dewi")
    response = client.post("/api/v1/lots/lot_1/bids", json={"amount_per_kg": "70000"})
    assert response.status_code == 409
    assert "closed" in response.json()["detail"]


def test_operator_can_close_an_active_lot_then_allocate():
    lots = FakeLotRepository({"lot_1": _lot()})
    client, _ = _client(lots)
    _login(client, "dewi")
    assert client.post("/api/v1/lots/lot_1/bids", json={"amount_per_kg": "70000"}).status_code == 200
    _login(client, "rian")
    closed = client.post("/api/v1/lots/lot_1/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    allocated = client.post("/api/v1/lots/lot_1/allocate")
    assert allocated.status_code == 200
    assert allocated.json()["allocated_buyer_id"] == "buyer_dewi"


def test_buyer_cannot_close_a_lot():
    lots = FakeLotRepository({"lot_1": _lot()})
    client, _ = _client(lots)
    _login(client, "dewi")
    response = client.post("/api/v1/lots/lot_1/close")
    assert response.status_code == 403


def test_allocate_requires_closed_lot_and_is_idempotent():
    lots = FakeLotRepository({"lot_1": _lot()})
    client, _ = _client(lots)
    _login(client, "dewi")
    client.post("/api/v1/lots/lot_1/bids", json={"amount_per_kg": "70000"})
    _login(client, "rian")
    too_early = client.post("/api/v1/lots/lot_1/allocate")
    assert too_early.status_code == 409

    lots.get("lot_1").status = "closed"
    first = client.post("/api/v1/lots/lot_1/allocate")
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "allocated"
    assert body["allocated_buyer_id"] == "buyer_dewi"

    second = client.post("/api/v1/lots/lot_1/allocate")
    assert second.status_code == 200
    assert second.json()["allocated_buyer_id"] == "buyer_dewi"
    assert lots.get("lot_1").status == "allocated"


def test_list_lots_filters_species_price_quantity_status():
    lots = FakeLotRepository({
        "lot_a": _lot(id="lot_a", species_id="species_tenggiri", starting_price_per_kg=Decimal("68000"), quantity_kg=Decimal("24")),
        "lot_b": _lot(id="lot_b", species_id="species_tuna", starting_price_per_kg=Decimal("90000"), quantity_kg=Decimal("10"), public_slug="tuna-lotb"),
        "lot_c": _lot(id="lot_c", species_id="species_tenggiri", status="closed", public_slug="tenggiri-lotc"),
    })
    client, _ = _client(lots)
    tenggiri = client.get("/api/v1/lots", params={"species_id": "species_tenggiri", "status": "active"})
    assert {row["id"] for row in tenggiri.json()} == {"lot_a"}
    cheap = client.get("/api/v1/lots", params={"max_price": "70000"})
    assert {row["id"] for row in cheap.json()} == {"lot_a", "lot_c"}
    bulky = client.get("/api/v1/lots", params={"min_quantity": "20"})
    assert {row["id"] for row in bulky.json()} == {"lot_a", "lot_c"}
    assert cheap.json()[0]["serviceability_radius_km"] == 100.0
