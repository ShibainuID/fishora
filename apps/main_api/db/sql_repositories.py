from typing import Callable, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.main_api.contracts import PredictionRecord, SpeciesRecord
from apps.main_api.db.models import FishSpecies, Prediction
from apps.main_api.errors import PredictionNotFound


class SqlSpeciesRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def get_by_normalized_label(self, label: str) -> SpeciesRecord | None:
        with self._session_factory() as session:
            row = session.scalar(select(FishSpecies).where(FishSpecies.normalized_label == label))
            return self._to_record(row)

    def get_by_id(self, species_id: str) -> SpeciesRecord | None:
        with self._session_factory() as session:
            return self._to_record(session.get(FishSpecies, species_id))

    @staticmethod
    def _to_record(row: FishSpecies | None) -> SpeciesRecord | None:
        if row is None:
            return None
        return SpeciesRecord(
            id=row.id,
            normalized_label=row.normalized_label,
            common_name_id=row.common_name_id,
            scientific_name=row.scientific_name,
            taxonomic_rank=row.taxonomic_rank,
            taxonomy_status=row.taxonomy_status,
            notes=row.notes,
        )


class SqlPredictionRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def create(
        self,
        prediction_id: str,
        image_reference: str,
        predicted_species_id: str,
        confidence: float,
        top_candidates: list[dict[str, object]],
        model_version: str,
    ) -> PredictionRecord:
        row = Prediction(
            id=prediction_id,
            image_reference=image_reference,
            predicted_species_id=predicted_species_id,
            confidence=confidence,
            top_candidates=top_candidates,
            model_version=model_version,
            verification_status="pending",
        )
        with self._session_factory() as session:
            session.add(row)
            session.commit()
        return self._to_record(row)

    def get(self, prediction_id: str) -> PredictionRecord | None:
        with self._session_factory() as session:
            return self._to_record(session.get(Prediction, prediction_id))

    def verify(
        self,
        prediction_id: str,
        verified_species_id: str,
        verification_status: Literal["confirmed", "corrected"],
    ) -> PredictionRecord:
        with self._session_factory() as session:
            row = session.get(Prediction, prediction_id)
            if row is None:
                raise PredictionNotFound(prediction_id)
            row.verification_status = verification_status
            row.verified_species_id = verified_species_id
            session.commit()
        return self._to_record(row)

    @staticmethod
    def _to_record(row: Prediction | None) -> PredictionRecord | None:
        if row is None:
            return None
        return PredictionRecord(
            id=row.id,
            image_reference=row.image_reference,
            predicted_species_id=row.predicted_species_id,
            confidence=row.confidence,
            top_candidates=row.top_candidates,
            model_version=row.model_version,
            verification_status=row.verification_status,
            verified_species_id=row.verified_species_id,
        )