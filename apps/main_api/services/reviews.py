import uuid

from apps.main_api.contracts import ReviewRecord
from apps.main_api.errors import Forbidden, LotClosed, LotNotFound


class ReviewService:
    """Post-use feedback from the buyer who received the catch (PRD 8.5).

    Two gates: the lot must be allocated, and the reviewer must be the buyer it
    was allocated to. Feedback from anyone else is not experience, and a lot
    still under auction has not been used yet.
    """

    def __init__(self, lot_repo, review_repo):
        self._lot_repo = lot_repo
        self._review_repo = review_repo

    def submit(
        self,
        *,
        lot_id: str,
        buyer_id: str,
        actual_use: str,
        processing_suitability: int,
        substitute_acceptance: bool | None = None,
        comment: str | None = None,
    ) -> ReviewRecord:
        lot = self._lot_repo.get(lot_id)
        if lot is None:
            raise LotNotFound(lot_id)
        if lot.status != "allocated":
            raise LotClosed(lot_id)
        if lot.allocated_buyer_id != buyer_id:
            raise Forbidden("only the allocated buyer can review this lot")

        return self._review_repo.create(
            ReviewRecord(
                id=uuid.uuid4().hex,
                lot_id=lot.id,
                # Denormalised on purpose: reviews are read by species so one
                # buyer's experience reaches every auction for that fish.
                species_id=lot.species_id,
                buyer_id=buyer_id,
                actual_use=actual_use,
                processing_suitability=processing_suitability,
                substitute_acceptance=substitute_acceptance,
                comment=comment,
            )
        )

    def list_for_lot(self, lot_id: str) -> list[ReviewRecord]:
        lot = self._lot_repo.get(lot_id)
        if lot is None:
            raise LotNotFound(lot_id)
        return self._review_repo.list_for_species(lot.species_id)
