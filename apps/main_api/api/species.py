from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/species")


class SpeciesResponse(BaseModel):
    """The taxonomy as the backend holds it.

    `notes` is deliberately absent: it carries reviewer commentary about why a
    name is uncertain, which is for the corpus reviewers rather than callers.
    """

    id: str
    normalized_label: str
    common_name_id: str
    scientific_name: str | None
    taxonomic_rank: str
    taxonomy_status: str


@router.get("", response_model=list[SpeciesResponse])
def list_species(request: Request):
    return [
        SpeciesResponse.model_validate(record, from_attributes=True)
        for record in request.app.state.deps.species_repo.list_all()
    ]


@router.get("/{species_id}", response_model=SpeciesResponse)
def get_species(species_id: str, request: Request):
    record = request.app.state.deps.species_repo.get_by_id(species_id)
    if record is None:
        # 404, not the 422 that UnsupportedSpecies carries: that one is for a
        # species id submitted with a write, this is a missing resource.
        raise HTTPException(status_code=404, detail="species not found")
    return SpeciesResponse.model_validate(record, from_attributes=True)
