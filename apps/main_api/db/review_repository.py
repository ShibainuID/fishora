import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.main_api.contracts import ReviewRecord
from apps.main_api.db.models import CommercialBuyerReview


class SqlReviewRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def create(self, review: ReviewRecord) -> ReviewRecord:
        row = CommercialBuyerReview(
            id=review.id or uuid.uuid4().hex,
            lot_id=review.lot_id,
            species_id=review.species_id,
            buyer_id=review.buyer_id,
            actual_use=review.actual_use,
            processing_suitability=review.processing_suitability,
            substitute_acceptance=review.substitute_acceptance,
            comment=review.comment,
        )
        with self._session_factory() as session:
            session.add(row)
            session.commit()
            return self._to_record(row)

    def list_for_species(self, species_id: str) -> list[ReviewRecord]:
        # Keyed on species, not lot: a buyer's experience of a fish applies to
        # every auction for it, whichever fisher group landed the catch.
        with self._session_factory() as session:
            rows = session.scalars(
                select(CommercialBuyerReview)
                .where(CommercialBuyerReview.species_id == species_id)
                .order_by(CommercialBuyerReview.created_at.desc())
            ).all()
            return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: CommercialBuyerReview) -> ReviewRecord:
        return ReviewRecord(
            id=row.id,
            lot_id=row.lot_id,
            species_id=row.species_id,
            buyer_id=row.buyer_id,
            actual_use=row.actual_use,
            processing_suitability=row.processing_suitability,
            substitute_acceptance=row.substitute_acceptance,
            comment=row.comment,
            created_at=row.created_at,
        )
