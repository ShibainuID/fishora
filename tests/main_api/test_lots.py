from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from apps.main_api.contracts import PredictionRecord
from apps.main_api.errors import InvalidLot, PredictionNotVerified
from apps.main_api.services.lots import LotService
from tests.main_api.fakes import FakeLotRepository, FakePredictionRepository


def _pending() -> PredictionRecord:
    return PredictionRecord(
        id="pred_pending",
        image_reference="images/pending.jpg",
        predicted_species_id="species_tenggiri",
        confidence=0.91,
        top_candidates=[],
        model_version="v1",
        verification_status="pending",
    )


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


def _service(records: dict[str, PredictionRecord]) -> LotService:
    return LotService(
        prediction_repo=FakePredictionRepository(records),
        lot_repo=FakeLotRepository(),
    )


def _publish(service: LotService, **overrides):
    kwargs = {
        "prediction_id": "pred_ok",
        "operator_id": "op_1",
        "quantity_kg": Decimal("24"),
        "starting_price_per_kg": Decimal("68000"),
        "size_category": "L",
        "landing_point_id": "lp_muara_angke",
        "now": datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc),
    }
    kwargs.update(overrides)
    return service.publish(**kwargs)


def test_publish_from_pending_prediction_raises():
    service = _service({"pred_pending": _pending()})
    with pytest.raises(PredictionNotVerified):
        _publish(service, prediction_id="pred_pending")


def test_publish_copies_verified_species_not_caller_argument():
    service = _service({"pred_ok": _verified()})
    lot = _publish(service)
    assert lot.species_id == "species_tenggiri"
    assert lot.species_id != "species_kembung"


def test_zero_or_negative_quantity_and_price_are_rejected():
    service = _service({"pred_ok": _verified()})
    with pytest.raises(InvalidLot):
        _publish(service, quantity_kg=Decimal("0"))
    with pytest.raises(InvalidLot):
        _publish(service, quantity_kg=Decimal("-1"))
    with pytest.raises(InvalidLot):
        _publish(service, starting_price_per_kg=Decimal("0"))
    with pytest.raises(InvalidLot):
        _publish(service, starting_price_per_kg=Decimal("-10"))


def test_published_lot_has_server_id_and_active_status():
    service = _service({"pred_ok": _verified()})
    lot = _publish(service)
    assert lot.id
    assert lot.status == "active"
    assert lot.auction_ends_at - lot.auction_starts_at == timedelta(hours=4)
