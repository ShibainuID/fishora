from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apps.main_api.contracts import BuyerPreferenceRecord, LandingPointRecord, LotRecord
from apps.main_api.services.matching import WEIGHTS, match_lot, recommend


NOW = datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc)


def _lot(**overrides) -> LotRecord:
    row = dict(
        id="lot_1",
        prediction_id="pred_ok",
        operator_id="op_1",
        species_id="species_tenggiri",
        landing_point_id="lp_near",
        quantity_kg=Decimal("24"),
        size_category="L",
        starting_price_per_kg=Decimal("68000"),
        status="active",
        auction_starts_at=NOW,
        auction_ends_at=NOW + timedelta(hours=4),
        public_slug="tenggiri-lot1",
        knowledge_snapshot={
            "commercial_uses": ["digoreng", "fillet"],
            "characteristics": ["gurih", "padat"],
        },
    )
    row.update(overrides)
    return LotRecord(**row)


def _prefs(**overrides) -> BuyerPreferenceRecord:
    row = dict(
        buyer_id="buyer_dewi",
        business_type="rumah_makan",
        intended_uses=["digoreng"],
        characteristics=["gurih"],
        max_price_per_kg=Decimal("80000"),
        min_quantity_kg=Decimal("10"),
        latitude=0.0,
        longitude=0.0,
    )
    row.update(overrides)
    return BuyerPreferenceRecord(**row)


def _landing(lat: float = 0.0) -> LandingPointRecord:
    return LandingPointRecord(id="lp_near", name="near", latitude=lat, longitude=0.0)


def test_weights_sum_to_exactly_one():
    assert sum(WEIGHTS.values()) == 1.0
    assert set(WEIGHTS) == {"intended_use", "characteristics", "price", "volume", "distance"}


def test_perfect_match_scores_one():
    result = match_lot(_lot(), _prefs(), _landing())
    assert result.score == 1.0
    assert [reason.criterion for reason in result.reasons] == list(WEIGHTS)
    assert all(reason.met for reason in result.reasons)


def test_reasons_always_include_unmet_criteria():
    result = match_lot(
        _lot(knowledge_snapshot={"commercial_uses": ["asap"], "characteristics": ["tawar"]}),
        _prefs(),
        _landing(),
    )
    by_name = {reason.criterion: reason for reason in result.reasons}
    assert set(by_name) == set(WEIGHTS)
    assert by_name["intended_use"].met is False
    assert by_name["characteristics"].met is False
    assert by_name["price"].met is True
    assert result.score == 0.45


def test_score_is_deterministic_for_identical_input():
    lot, prefs, landing = _lot(), _prefs(), _landing()
    assert match_lot(lot, prefs, landing) == match_lot(lot, prefs, landing)


def test_no_preferences_yields_no_recommendation():
    assert recommend([_lot()], None, {"lp_near": _landing()}) == []
