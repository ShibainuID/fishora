"""Verification-gated lot publication, listing, bidding, and allocation.

Species identity is copied from the prediction's stored verified_species_id.
Callers never supply a species id, mirroring KnowledgeService.
Bid races are serialised inside the lot repository (row lock).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from apps.main_api.contracts import BidRecord, LotRecord
from apps.main_api.errors import InvalidLot, LotNotFound, PredictionNotFound, PredictionNotVerified

DEFAULT_AUCTION_HOURS = 4
# A lot that never closes cannot be allocated, and one that closes instantly
# cannot be bid on, so the window is bounded rather than free-form.
MIN_AUCTION_HOURS = 1
MAX_AUCTION_HOURS = 72
_POSITIVE_SIZES = {"S", "M", "L"}


class LotService:
    def __init__(
        self,
        prediction_repo,
        lot_repo,
        *,
        auction_hours: int = DEFAULT_AUCTION_HOURS,
        landing_point_repo=None,
        knowledge_service=None,
    ):
        self._prediction_repo = prediction_repo
        self._lot_repo = lot_repo
        self._auction_hours = auction_hours
        self._landing_point_repo = landing_point_repo
        self._knowledge_service = knowledge_service

    def publish(
        self,
        *,
        prediction_id: str,
        operator_id: str,
        quantity_kg: Decimal,
        starting_price_per_kg: Decimal,
        size_category: str,
        landing_point_id: str,
        auction_hours: int | None = None,
        seller_fisher_group: str | None = None,
        now: datetime | None = None,
    ) -> LotRecord:
        hours = self._auction_hours if auction_hours is None else int(auction_hours)
        if not MIN_AUCTION_HOURS <= hours <= MAX_AUCTION_HOURS:
            raise ValueError(
                f"auction_hours must be between {MIN_AUCTION_HOURS} and {MAX_AUCTION_HOURS}"
            )
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
        snapshot = None
        if self._knowledge_service is not None:
            # Best effort. The catch is landed and the auction has to open; a
            # knowledge card that cannot be generated is a degraded listing, not
            # a reason to refuse publication. The lot page and the discover page
            # both already render without a snapshot.
            try:
                snapshot = self._knowledge_service.get_for_prediction(
                    prediction_id
                ).card.model_dump(mode="json")
            except Exception:
                snapshot = None
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
            auction_ends_at=starts + timedelta(hours=hours),
            public_slug=f"{label}-{lot_id[:8]}",
            knowledge_snapshot=snapshot,
            seller_fisher_group=seller_fisher_group,
        )
        return self._lot_repo.create(lot)

    def get(self, lot_id: str) -> LotRecord:
        lot = self._lot_repo.get(lot_id)
        if lot is None:
            raise LotNotFound(lot_id)
        return lot

    def get_by_slug(self, public_slug: str) -> LotRecord:
        lot = self._lot_repo.get_by_slug(public_slug)
        if lot is None:
            raise LotNotFound(public_slug)
        return lot

    def list_lots(
        self,
        *,
        species_id: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        min_quantity: Decimal | None = None,
        max_quantity: Decimal | None = None,
        status: str | None = None,
        operator_id: str | None = None,
        buyer_lat: float | None = None,
        buyer_lon: float | None = None,
        serviceability_radius_km: float | None = None,
    ) -> list[LotRecord]:
        lots = self._lot_repo.all()
        filtered = []
        for lot in lots:
            if species_id and lot.species_id != species_id:
                continue
            if status and lot.status != status:
                continue
            if operator_id and lot.operator_id != operator_id:
                continue
            if min_price is not None and lot.starting_price_per_kg < min_price:
                continue
            if max_price is not None and lot.starting_price_per_kg > max_price:
                continue
            if min_quantity is not None and lot.quantity_kg < min_quantity:
                continue
            if max_quantity is not None and lot.quantity_kg > max_quantity:
                continue
            if buyer_lat is not None and buyer_lon is not None and self._landing_point_repo is not None:
                from apps.main_api.services.geo import DEFAULT_SERVICEABILITY_RADIUS_KM, within_serviceability

                radius = (
                    serviceability_radius_km
                    if serviceability_radius_km is not None
                    else DEFAULT_SERVICEABILITY_RADIUS_KM
                )
                point = self._landing_point_repo.get(lot.landing_point_id)
                if point is None or not within_serviceability(
                    buyer_lat, buyer_lon, point.latitude, point.longitude, radius
                ):
                    continue
            filtered.append(lot)
        return filtered

    def place_bid(
        self,
        lot_id: str,
        buyer_id: str,
        amount_per_kg: Decimal,
        now: datetime | None = None,
    ) -> BidRecord:
        if amount_per_kg <= 0:
            raise InvalidLot("bid amount must be greater than zero")
        return self._lot_repo.place_bid(lot_id, buyer_id, amount_per_kg, now=now)

    def list_bids(self, lot_id: str) -> list[BidRecord]:
        self.get(lot_id)
        return self._lot_repo.list_bids(lot_id)

    def current_highest(self, lot_id: str) -> Decimal | None:
        return self._lot_repo.highest(lot_id)

    def close(self, lot_id: str) -> LotRecord:
        return self._lot_repo.close(lot_id)

    def allocate(self, lot_id: str, now: datetime | None = None) -> LotRecord:
        return self._lot_repo.allocate(lot_id, now=now)
