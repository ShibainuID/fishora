from dataclasses import dataclass
from typing import Callable, Literal, Protocol, Sequence

from sqlalchemy.orm import Session

from apps.contracts import CVPredictionEnvelope
from apps.main_api.contracts import (
    KnowledgeChunkWrite,
    KnowledgeSourceWrite,
    PredictionRecord,
    SpeciesRecord,
)


class CVClient(Protocol):
    def predict(self, image_bytes: bytes, *, filename: str, content_type: str) -> CVPredictionEnvelope: ...


class ImageStore(Protocol):
    def save(self, prediction_id: str, image_bytes: bytes, content_type: str) -> str: ...
    def delete(self, image_reference: str) -> None: ...


class SpeciesRepository(Protocol):
    def get_by_normalized_label(self, label: str) -> SpeciesRecord | None: ...
    def get_by_id(self, species_id: str) -> SpeciesRecord | None: ...


class Tokenizer(Protocol):
    """A real tokenizer (encode/decode), not a bare token counter."""

    def encode(self, text: str) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...


class Embedder(Protocol):
    model_name: str
    tokenizer: Tokenizer

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class KnowledgeRepository(Protocol):
    """Transactional store for approved sources/chunks (one commit, all or nothing)."""

    def embedding_models_in_store(self) -> set[str]: ...
    def insert_verified(
        self,
        sources: Sequence[KnowledgeSourceWrite],
        chunks: Sequence[KnowledgeChunkWrite],
    ) -> int: ...


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