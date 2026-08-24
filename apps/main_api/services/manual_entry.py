import uuid
from dataclasses import dataclass
from typing import Literal

from apps.common.image import validate_image_bytes
from apps.main_api.errors import UnsupportedSpecies

# Marks the record as an operator declaration, not a model output. The audit
# trail must never imply the classifier agreed when it was never called.
MANUAL_MODEL_VERSION = "manual-entry"


@dataclass(frozen=True)
class ManualEntryResult:
    prediction_id: str
    model_version: str
    verified_species_id: str
    normalized_label: str
    verification_status: Literal["confirmed", "corrected"]


class ManualEntryService:
    """Creates a verified prediction from an operator's own species call.

    Exists so a CV outage cannot strand a crate of fish: the operator names the
    species, the catch is still publishable, and the record shows a human made
    the call. Validation and species resolution both run before any image or
    prediction row is written.
    """

    def __init__(self, species_repo, prediction_repo, image_store, max_image_bytes: int):
        self._species_repo = species_repo
        self._prediction_repo = prediction_repo
        self._image_store = image_store
        self._max_image_bytes = max_image_bytes

    def declare(
        self, image_bytes: bytes, *, filename: str, content_type: str, species_id: str
    ) -> ManualEntryResult:
        validate_image_bytes(image_bytes, content_type, self._max_image_bytes)

        species = self._species_repo.get_by_id(species_id)
        if species is None:
            raise UnsupportedSpecies(species_id)

        prediction_id = uuid.uuid4().hex
        image_reference = self._image_store.save(prediction_id, image_bytes, content_type)
        try:
            self._prediction_repo.create(
                prediction_id=prediction_id,
                image_reference=image_reference,
                predicted_species_id=species.id,
                confidence=0.0,
                top_candidates=[],
                model_version=MANUAL_MODEL_VERSION,
            )
            record = self._prediction_repo.verify(prediction_id, species.id, "confirmed")
        except Exception:
            # Compensation: drop the image saved for this attempt only.
            self._image_store.delete(image_reference)
            raise

        return ManualEntryResult(
            prediction_id=record.id,
            model_version=record.model_version,
            verified_species_id=record.verified_species_id,
            normalized_label=species.normalized_label,
            verification_status=record.verification_status,
        )
