from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, Field

from apps.main_api.services.identification import IdentificationService
from apps.main_api.services.verification import VerificationService

router = APIRouter(prefix="/api/v1/fish")


class VerifyRequest(BaseModel):
    prediction_id: str
    verified_species_id: str


class SpeciesCandidate(BaseModel):
    species_id: str
    normalized_label: str
    confidence: float = Field(ge=0.0, le=1.0)


class IdentificationResponse(BaseModel):
    prediction_id: str
    model_version: str
    status: Literal["confident_prediction", "low_confidence_human_verification_required"]
    prediction: SpeciesCandidate
    top_candidates: list[SpeciesCandidate]
    threshold: float
    verification_status: Literal["pending"]


class VerificationResponse(BaseModel):
    prediction_id: str
    predicted_species_id: str
    verified_species_id: str
    verification_status: Literal["confirmed", "corrected"]


@router.post("/identify", response_model=IdentificationResponse)
async def identify(request: Request, file: UploadFile = File(...)):
    deps = request.app.state.deps
    settings = request.app.state.settings
    service = IdentificationService(
        cv_client=deps.cv_client,
        species_repo=deps.species_repo,
        prediction_repo=deps.prediction_repo,
        image_store=deps.image_store,
        max_image_bytes=settings.cv_max_image_bytes,
    )
    result = service.identify(
        await file.read(),
        filename=file.filename or "image",
        content_type=file.content_type,
    )
    return IdentificationResponse(
        prediction_id=result.prediction_id,
        model_version=result.model_version,
        status=result.status,
        prediction=SpeciesCandidate(**asdict(result.prediction)),
        top_candidates=[SpeciesCandidate(**asdict(candidate)) for candidate in result.top_candidates],
        threshold=result.threshold,
        verification_status=result.verification_status,
    )


@router.post("/verify", response_model=VerificationResponse)
async def verify(payload: VerifyRequest, request: Request):
    deps = request.app.state.deps
    result = VerificationService(
        species_repo=deps.species_repo,
        prediction_repo=deps.prediction_repo,
    ).verify(payload.prediction_id, payload.verified_species_id)
    return VerificationResponse(
        prediction_id=result.prediction_id,
        predicted_species_id=result.predicted_species_id,
        verified_species_id=result.verified_species_id,
        verification_status=result.verification_status,
    )