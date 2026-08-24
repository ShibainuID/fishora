import math

from apps.main_api.services.geo import (
    DEFAULT_SERVICEABILITY_RADIUS_KM,
    haversine_km,
    within_serviceability,
)


def _north_of_origin(km: float) -> float:
    return km / 6371.0 * (180.0 / math.pi)


def test_lot_at_99_5km_is_visible_and_100_5km_is_not():
    near = _north_of_origin(99.5)
    far = _north_of_origin(100.5)
    assert within_serviceability(0.0, 0.0, near, 0.0)
    assert not within_serviceability(0.0, 0.0, far, 0.0)


def test_exactly_100km_is_inclusive():
    exact = _north_of_origin(100.0)
    assert math.isclose(haversine_km(0.0, 0.0, exact, 0.0), 100.0, abs_tol=1e-9)
    assert within_serviceability(0.0, 0.0, exact, 0.0)


def test_radius_field_is_named_as_an_explicit_proxy_not_freshness():
    import inspect
    from apps.main_api.api import lots as lots_api
    from apps.main_api.services import geo

    source = inspect.getsource(geo) + inspect.getsource(lots_api)
    assert "serviceability_radius_km" in source
    assert "freshness_radius_km" not in source
    assert DEFAULT_SERVICEABILITY_RADIUS_KM == 100.0


def test_list_lots_hides_lots_outside_the_serviceability_radius():
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
        FakePredictionRepository,
        FakeSpeciesRepository,
    )

    now = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)
    near_lat = _north_of_origin(99.5)
    far_lat = _north_of_origin(100.5)
    points = FakeLandingPointRepository([
        LandingPointRecord(id="lp_near", name="near", latitude=near_lat, longitude=0.0),
        LandingPointRecord(id="lp_far", name="far", latitude=far_lat, longitude=0.0),
    ])

    def lot(lot_id: str, landing_point_id: str) -> LotRecord:
        return LotRecord(
            id=lot_id,
            prediction_id="pred_ok",
            operator_id="op_1",
            species_id="species_tenggiri",
            landing_point_id=landing_point_id,
            quantity_kg=Decimal("24"),
            size_category="L",
            starting_price_per_kg=Decimal("68000"),
            status="active",
            auction_starts_at=now,
            auction_ends_at=now + timedelta(hours=4),
            public_slug=lot_id,
        )

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
            lot_repo=FakeLotRepository({
                "lot_near": lot("lot_near", "lp_near"),
                "lot_far": lot("lot_far", "lp_far"),
            }),
            landing_point_repo=points,
        )
    )
    response = TestClient(app).get("/api/v1/lots", params={"buyer_lat": 0, "buyer_lon": 0})
    ids = {row["id"] for row in response.json()}
    assert ids == {"lot_near"}
    assert response.json()[0]["serviceability_radius_km"] == 100.0
    assert "freshness_radius_km" not in response.json()[0]
