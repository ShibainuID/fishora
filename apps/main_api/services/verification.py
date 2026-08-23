from dataclasses import dataclass
from typing import Literal

from apps.main_api.errors import PredictionNotFound, UnsupportedSpecies


@dataclass(frozen=True)
class VerificationResult:
    prediction_id: str
    predicted_species_id: str
    verified_species_id: str
    verification_status: Literal["confirmed", "corrected"]


class VerificationService:
    """Loads the stored prediction, validates the target species, and derives the status.

    Confirmed only when the verified species id equals the predicted one;
    any other supported species is a correction. The predicted identity and
    stored history are never modified.
    """

    def __init__(self, species_repo, prediction_repo):
        self._species_repo = species_repo
        self._prediction_repo = prediction_repo

    def verify(self, prediction_id: str, verified_species_id: str) -> VerificationResult:
        record = self._prediction_repo.get(prediction_id)
        if record is None:
            raise PredictionNotFound(prediction_id)
        if self._species_repo.get_by_id(verified_species_id) is None:
            raise UnsupportedSpecies(verified_species_id)

        status = "confirmed" if verified_species_id == record.predicted_species_id else "corrected"
        updated = self._prediction_repo.verify(prediction_id, verified_species_id, status)
        return VerificationResult(
            prediction_id=updated.id,
            predicted_species_id=updated.predicted_species_id,
            verified_species_id=updated.verified_species_id,
            verification_status=updated.verification_status,
        )