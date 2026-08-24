from decimal import Decimal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from apps.main_api.api.lots import LotResponse, _lot_response
from apps.main_api.contracts import BuyerPreferenceRecord
from apps.main_api.errors import Forbidden
from apps.main_api.services.lots import LotService
from apps.main_api.services.matching import recommend
from apps.main_api.services.session import current_user

router = APIRouter(prefix="/api/v1/buyers")


class PreferenceRequest(BaseModel):
    business_type: str
    intended_uses: list[str]
    characteristics: list[str]
    max_price_per_kg: Decimal | None = None
    min_quantity_kg: Decimal | None = None
    latitude: float
    longitude: float


class PreferenceResponse(PreferenceRequest):
    buyer_id: str


class MatchReasonResponse(BaseModel):
    criterion: str
    met: bool
    detail: str
    value: str | None = None


class RecommendationItem(BaseModel):
    lot: LotResponse
    score: float
    reasons: list[MatchReasonResponse]


class RecommendationsResponse(BaseModel):
    items: list[RecommendationItem]
    profile_missing: bool = False


@router.put("/{buyer_id}/preferences", response_model=PreferenceResponse)
def put_preferences(buyer_id: str, payload: PreferenceRequest, request: Request):
    user = current_user(request)
    if user.id != buyer_id:
        raise Forbidden("cannot write another buyer's preferences")
    record = BuyerPreferenceRecord(buyer_id=buyer_id, **payload.model_dump())
    saved = request.app.state.deps.preference_repo.upsert(record)
    return PreferenceResponse(buyer_id=saved.buyer_id, **payload.model_dump())


@router.get("/{buyer_id}/recommendations", response_model=RecommendationsResponse)
def get_recommendations(buyer_id: str, request: Request):
    user = current_user(request)
    if user.id != buyer_id:
        raise Forbidden("cannot read another buyer's recommendations")
    deps = request.app.state.deps
    prefs = deps.preference_repo.get(buyer_id)
    if prefs is None:
        return RecommendationsResponse(items=[], profile_missing=True)

    lot_service = LotService(
        prediction_repo=deps.prediction_repo,
        lot_repo=deps.lot_repo,
        landing_point_repo=deps.landing_point_repo,
    )
    lots = lot_service.list_lots(status="active")
    points = {point.id: point for point in deps.landing_point_repo.all()} if deps.landing_point_repo else {}
    ranked = recommend(lots, prefs, points)
    items = [
        RecommendationItem(
            lot=_lot_response(lot_service, lot),
            score=result.score,
            reasons=[MatchReasonResponse(
                criterion=reason.criterion, met=reason.met, detail=reason.detail, value=reason.value
            ) for reason in result.reasons],
        )
        for lot, result in ranked
    ]
    return RecommendationsResponse(items=items, profile_missing=False)
