from fastapi import APIRouter, Request
from pydantic import BaseModel

from apps.main_api.services.generation import KnowledgeCard
from apps.main_api.services.lots import LotService

router = APIRouter(prefix="/api/v1/discover")


class DiscoverResponse(BaseModel):
    public_slug: str
    species_id: str
    card: KnowledgeCard


@router.get("/{public_slug}", response_model=DiscoverResponse)
def discover(public_slug: str, request: Request):
    deps = request.app.state.deps
    lot = LotService(prediction_repo=deps.prediction_repo, lot_repo=deps.lot_repo).get_by_slug(public_slug)
    if not lot.knowledge_snapshot:
        from apps.main_api.errors import LotNotFound

        raise LotNotFound(public_slug)
    return DiscoverResponse(
        public_slug=lot.public_slug,
        species_id=lot.species_id,
        card=KnowledgeCard.model_validate(lot.knowledge_snapshot),
    )
