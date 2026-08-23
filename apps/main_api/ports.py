from dataclasses import dataclass
from typing import Callable, Literal, Protocol

from sqlalchemy.orm import Session

from apps.contracts import CVPredictionEnvelope
from apps.main_api.contracts import PredictionRecord, SpeciesRecord


class CVClient(Protocol):
    def predict(self, image_bytes: bytes, *, filename: str, content_type: str) -> CVPredictionEnvelope: ...


class ImageStore(Protocol):
    def save(self, prediction_id: str, image_bytes: bytes, content_type: str) -> str: ...
    def delete(self, image_reference: str) -> None: ...


class SpeciesRepository(Protocol):
    def get_by_normalized_label(self, label: str) -> SpeciesRecord | None: ...
    def get_by_id(self, species_id: str) -> SpeciesRecord | None: ...


class PredictionRepository(Protocol):
    def create(
        self,
        prediction_id: str,
        image_reference: str,
        predicted_species_id: str,
        confidence: float,
        top_candidates: list[dict[str, object]],
        model_version: str,
    ) -> PredictionRecord: ...

    def get(self, prediction_id: str) -> PredictionRecord | None: ...

    def verify(
        self,
        prediction_id: str,
        verified_species_id: str,
        verification_status: Literal["confirmed", "corrected"],
    ) -> PredictionRecord: ...

    def all(self) -> list[PredictionRecord]: ...


@dataclass
class AppDependencies:
    """Small concrete bundle of ports for the main API.

    Production wiring happens lazily in the app lifespan; tests inject fakes
    through the bundle instead of a nine-argument factory signature.
    """

    session_factory: Callable[[], Session] | None = None
    cv_client: CVClient | None = None
    species_repo: SpeciesRepository | None = None
    prediction_repo: PredictionRepository | None = None
    image_store: ImageStore | None = None