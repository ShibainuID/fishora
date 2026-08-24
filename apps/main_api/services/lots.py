"""Verification-gated lot publication.

Species identity is copied from the prediction's stored verified_species_id.
Callers never supply a species id, mirroring KnowledgeService.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from apps.main_api.contracts import LotRecord
from apps.main_api.errors import InvalidLot, PredictionNotFound, PredictionNotVerified

DEFAULT_AUCTION_HOURS = 4
_POSITIVE_SIZES = {"S", "M", "L"}


class LotService:
    def __init__(self, prediction_repo, lot_repo, *, auction_hours: int = DEFAULT_AUCTION_HOURS):
        self._prediction_repo = prediction_repo
        self._lot_repo = lot_repo
        self._auction_hours = auction_hours

    def publish(
        self,
        *,
        prediction_id: str,
        operator_id: str,
        quantity_kg: Decimal,
        starting_price_per_kg: Decimal,
        size_category: str,
        landing_point_id: str,
        now: datetime | None = None,
    ) -> LotRecord:
        record = self._prediction_repo.get(prediction_id)
        if record is None:
            raise PredictionNotFound(prediction_id)
        if record.verification_status not in ("confirmed", "corrected") or record.verified_species_id is None:
            raise PredictionNotVerified(prediction_id)
        if quantity_kg <= 0 or starting_price_per_kg <= 0:
            raise InvalidLot("quantity and starting price must be greater than zero")
        if size_category not in _POSITIVE_SIZES:
            raise InvalidLot("size_category must be S, M, or L")

        starts = now or datetime.now(timezone.utc)
        lot_id = uuid4().hex
        label = record.verified_species_id.removeprefix("species_")
        lot = LotRecord(
            id=lot_id,
            prediction_id=record.id,
            operator_id=operator_id,
            species_id=record.verified_species_id,
            landing_point_id=landing_point_id,
            quantity_kg=quantity_kg,
            size_category=size_category,
            starting_price_per_kg=starting_price_per_kg,
            status="active",
            auction_starts_at=starts,
            auction_ends_at=starts + timedelta(hours=self._auction_hours),
            public_slug=f"{label}-{lot_id[:8]}",
        )
        return self._lot_repo.create(lot)
