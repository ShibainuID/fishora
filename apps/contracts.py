from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CVCandidate(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class CVPredictionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_version: str
    status: Literal["confident_prediction", "low_confidence_human_verification_required"]
    prediction: CVCandidate
    top_candidates: list[CVCandidate] = Field(min_length=3, max_length=3)
    threshold: float = Field(ge=0.0, le=1.0)


class ImageValidationError(Exception):
    """Shared trust-boundary error raised before either service invokes inference."""

    def __init__(self, status_code: Literal[400, 413, 415], message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message