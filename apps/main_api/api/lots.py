from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from apps.main_api.contracts import BidRecord, LotRecord
from apps.main_api.services.lots import LotService

# Named in the contract so Task 18 can keep the proxy explicit. Not freshness.
DEFAULT_SERVICEABILITY_RADIUS_KM = 100.0

router = APIRouter(prefix="/api/v1/lots")


class PublishLotRequest(BaseModel):
    prediction_id: str
    operator_id: str
    quantity_kg: Decimal = Field(gt=0)
    starting_price_per_kg: Decimal = Field(gt=0)
    size_category: Literal["S", "M", "L"]
    landing_point_id: str


class LotResponse(BaseModel):
    id: str
    prediction_id: str
    operator_id: str
    species_id: str
    landing_point_id: str
    quantity_kg: Decimal
    size_category: Literal["S", "M", "L"]
    starting_price_per_kg: Decimal
    status: Literal["draft", "active", "closed", "allocated"]
    auction_starts_at: datetime
    auction_ends_at: datetime
    public_slug: str
    allocated_buyer_id: str | None = None
    current_highest_per_kg: Decimal | None = None
    serviceability_radius_km: float = DEFAULT_SERVICEABILITY_RADIUS_KM


class PlaceBidRequest(BaseModel):
    buyer_id: str
    amount_per_kg: Decimal = Field(gt=0)


class BidResponse(BaseModel):
    id: str
    lot_id: str
    buyer_id: str
    amount_per_kg: Decimal
    created_at: datetime


class AllocateResponse(BaseModel):
    id: str
    status: Literal["allocated"]
    allocated_buyer_id: str
    current_highest_per_kg: Decimal | None = None


def _service(request: Request) -> LotService:
    deps = request.app.state.deps
    return LotService(
        prediction_repo=deps.prediction_repo,
        lot_repo=deps.lot_repo,
        landing_point_repo=deps.landing_point_repo,
        knowledge_service=None if deps.generator is None else None,
    )


def _lot_response(service: LotService, lot: LotRecord) -> LotResponse:
    return LotResponse(
        id=lot.id,
        prediction_id=lot.prediction_id,
        operator_id=lot.operator_id,
        species_id=lot.species_id,
        landing_point_id=lot.landing_point_id,
        quantity_kg=lot.quantity_kg,
        size_category=lot.size_category,
        starting_price_per_kg=lot.starting_price_per_kg,
        status=lot.status,
        auction_starts_at=lot.auction_starts_at,
        auction_ends_at=lot.auction_ends_at,
        public_slug=lot.public_slug,
        allocated_buyer_id=lot.allocated_buyer_id,
        current_highest_per_kg=service.current_highest(lot.id),
        serviceability_radius_km=DEFAULT_SERVICEABILITY_RADIUS_KM,
    )


def _bid_response(bid: BidRecord) -> BidResponse:
    return BidResponse(
        id=bid.id,
        lot_id=bid.lot_id,
        buyer_id=bid.buyer_id,
        amount_per_kg=bid.amount_per_kg,
        created_at=bid.created_at,
    )


@router.post("", response_model=LotResponse)
def publish_lot(payload: PublishLotRequest, request: Request):
    service = _service(request)
    lot = service.publish(
        prediction_id=payload.prediction_id,
        operator_id=payload.operator_id,
        quantity_kg=payload.quantity_kg,
        starting_price_per_kg=payload.starting_price_per_kg,
        size_category=payload.size_category,
        landing_point_id=payload.landing_point_id,
    )
    return _lot_response(service, lot)


@router.get("", response_model=list[LotResponse])
def list_lots(
    request: Request,
    species_id: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    min_quantity: Decimal | None = None,
    max_quantity: Decimal | None = None,
    status: str | None = None,
    buyer_lat: float | None = Query(default=None),
    buyer_lon: float | None = Query(default=None),
    serviceability_radius_km: float | None = Query(default=None),
):
    service = _service(request)
    lots = service.list_lots(
        species_id=species_id,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        status=status,
        buyer_lat=buyer_lat,
        buyer_lon=buyer_lon,
        serviceability_radius_km=serviceability_radius_km,
    )
    return [_lot_response(service, lot) for lot in lots]


@router.get("/{lot_id}", response_model=LotResponse)
def get_lot(lot_id: str, request: Request):
    service = _service(request)
    return _lot_response(service, service.get(lot_id))


@router.post("/{lot_id}/bids", response_model=BidResponse)
def place_bid(lot_id: str, payload: PlaceBidRequest, request: Request):
    service = _service(request)
    return _bid_response(service.place_bid(lot_id, payload.buyer_id, payload.amount_per_kg))


@router.get("/{lot_id}/bids", response_model=list[BidResponse])
def list_bids(lot_id: str, request: Request):
    service = _service(request)
    return [_bid_response(bid) for bid in service.list_bids(lot_id)]


@router.post("/{lot_id}/allocate", response_model=AllocateResponse)
def allocate_lot(lot_id: str, request: Request):
    service = _service(request)
    lot = service.allocate(lot_id)
    return AllocateResponse(
        id=lot.id,
        status="allocated",
        allocated_buyer_id=lot.allocated_buyer_id or "",
        current_highest_per_kg=service.current_highest(lot.id),
    )
