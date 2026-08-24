from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from apps.main_api.services.reviews import ReviewService
from apps.main_api.services.session import require_role

router = APIRouter(prefix="/api/v1/lots")


class ReviewRequest(BaseModel):
    actual_use: str = Field(min_length=1, max_length=120)
    processing_suitability: int = Field(ge=1, le=5)
    substitute_acceptance: bool | None = None
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    """Deliberately carries no taxonomy, sources or scientific name: a review is
    a market signal and must never be renderable as verified knowledge."""

    id: str
    lot_id: str
    species_id: str
    buyer_id: str
    actual_use: str
    processing_suitability: int
    substitute_acceptance: bool | None = None
    comment: str | None = None
    created_at: datetime | None = None


def _service(request: Request) -> ReviewService:
    deps = request.app.state.deps
    return ReviewService(lot_repo=deps.lot_repo, review_repo=deps.review_repo)


@router.post("/{lot_id}/review", response_model=ReviewResponse)
def submit_review(lot_id: str, payload: ReviewRequest, request: Request):
    buyer = require_role(request, "buyer")
    review = _service(request).submit(
        lot_id=lot_id,
        buyer_id=buyer.id,
        actual_use=payload.actual_use,
        processing_suitability=payload.processing_suitability,
        substitute_acceptance=payload.substitute_acceptance,
        comment=payload.comment,
    )
    return ReviewResponse(**vars(review))


@router.get("/{lot_id}/reviews", response_model=list[ReviewResponse])
def list_reviews(lot_id: str, request: Request):
    """Public, like the marketplace listing. Returns every review for this
    lot's species, so a buyer sees other buyers' experience of the same fish
    even when a different fisher group landed it."""
    reviews = _service(request).list_for_lot(lot_id)
    return [ReviewResponse(**vars(row)) for row in reviews]
