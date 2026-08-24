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


def test_publish_honours_a_requested_auction_duration(prediction_repo, species_repo):
    """The operator picks 2h/4h/8h/24h in the UI. If the request cannot carry it,
    every lot silently runs for the default and the control is a lie."""
    from decimal import Decimal
    from datetime import timedelta

    from apps.main_api.contracts import PredictionRecord
    from apps.main_api.services.lots import LotService
    from tests.main_api.fakes import FakeLotRepository, FakePredictionRepository

    predictions = FakePredictionRepository({
        "pred_ok": PredictionRecord(
            id="pred_ok", image_reference="images/ok.jpg",
            predicted_species_id="species_tenggiri", confidence=0.9,
            top_candidates=[], model_version="v1",
            verification_status="confirmed", verified_species_id="species_tenggiri",
        )
    })
    service = LotService(prediction_repo=predictions, lot_repo=FakeLotRepository())

    lot = service.publish(
        prediction_id="pred_ok", operator_id="op_rian",
        quantity_kg=Decimal("24"), starting_price_per_kg=Decimal("68000"),
        size_category="L", landing_point_id="lp_muara_angke",
        auction_hours=8,
    )
    assert lot.auction_ends_at - lot.auction_starts_at == timedelta(hours=8)


def test_publish_rejects_an_out_of_range_auction_duration(prediction_repo, species_repo):
    from decimal import Decimal

    import pytest

    from apps.main_api.contracts import PredictionRecord
    from apps.main_api.services.lots import LotService
    from tests.main_api.fakes import FakeLotRepository, FakePredictionRepository

    predictions = FakePredictionRepository({
        "pred_ok": PredictionRecord(
            id="pred_ok", image_reference="images/ok.jpg",
            predicted_species_id="species_tenggiri", confidence=0.9,
            top_candidates=[], model_version="v1",
            verification_status="confirmed", verified_species_id="species_tenggiri",
        )
    })
    service = LotService(prediction_repo=predictions, lot_repo=FakeLotRepository())

    for hours in (0, -4, 999):
        with pytest.raises(ValueError):
            service.publish(
                prediction_id="pred_ok", operator_id="op_rian",
                quantity_kg=Decimal("24"), starting_price_per_kg=Decimal("68000"),
                size_category="L", landing_point_id="lp_muara_angke",
                auction_hours=hours,
            )


class _BrokenKnowledgeService:
    """Stands in for generation being down: no API key, or the LLM unreachable."""

    def get_for_prediction(self, prediction_id: str):
        raise RuntimeError("generation unavailable")


def test_publish_survives_an_unavailable_knowledge_service():
    service = LotService(
        prediction_repo=FakePredictionRepository({"pred_ok": _verified()}),
        lot_repo=FakeLotRepository(),
        knowledge_service=_BrokenKnowledgeService(),
    )

    lot = _publish(service)

    # The catch is landed and the auction has to open. Letting a knowledge
    # failure take publication down blocks the fisherman's actual business on a
    # service whose output the lot page already treats as optional.
    assert lot.status == "active"
    assert lot.knowledge_snapshot is None
