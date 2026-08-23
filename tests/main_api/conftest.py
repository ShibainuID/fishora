import pytest

from apps.contracts import CVCandidate, CVPredictionEnvelope
from apps.main_api.contracts import PredictionRecord, SpeciesRecord
from apps.main_api.ports import AppDependencies

from tests.main_api.fakes import FakeCVClient, FakeImageStore, FakePredictionRepository, FakeSpeciesRepository

SUPPORTED_LABELS = [
    "bandeng", "gelama_bunga", "gembolo", "gulamah", "kembung", "kuniran",
    "mujair", "nila", "senangin", "tenggiri", "tuna",
]


def _species(label: str) -> SpeciesRecord:
    return SpeciesRecord(
        id=f"species_{label}",
        normalized_label=label,
        common_name_id=f"common_{label}",
        scientific_name=None,
        taxonomic_rank="species",
        taxonomy_status="VERIFIED_TAXONOMY",
        notes=None,
    )


@pytest.fixture
def species_repo():
    return FakeSpeciesRepository([_species(label) for label in SUPPORTED_LABELS])


@pytest.fixture
def prediction_repo():
    """Empty prediction repository: identification tests assert nothing persists on failure."""
    return FakePredictionRepository()


@pytest.fixture
def seeded_prediction_repo():
    """Pre-seeded prediction repository: verification tests mutate these rows."""
    return FakePredictionRepository(
        {
            "pred_confirm": PredictionRecord(
                id="pred_confirm", image_reference="images/pred_confirm.jpg",
                predicted_species_id="species_tuna", confidence=0.71,
                top_candidates=[{"species_id": "species_tuna", "normalized_label": "tuna", "confidence": 0.71}],
                model_version="test-model-1", verification_status="pending",
            ),
            "pred_correct": PredictionRecord(
                id="pred_correct", image_reference="images/pred_correct.jpg",
                predicted_species_id="species_tuna", confidence=0.71,
                top_candidates=[{"species_id": "species_tuna", "normalized_label": "tuna", "confidence": 0.71}],
                model_version="test-model-1", verification_status="pending",
            ),
        }
    )


@pytest.fixture
def image_store():
    return FakeImageStore()


@pytest.fixture
def cv_result():
    return CVPredictionEnvelope(
        model_version="test-model-1",
        status="confident_prediction",
        prediction=CVCandidate(label="tuna", confidence=0.71),
        top_candidates=[
            CVCandidate(label="tuna", confidence=0.71),
            CVCandidate(label="tenggiri", confidence=0.18),
            CVCandidate(label="gembolo", confidence=0.08),
        ],
        threshold=0.80,
    )


@pytest.fixture
def cv_low_confidence(cv_result):
    return cv_result.model_copy(update={"status": "low_confidence_human_verification_required"})


@pytest.fixture
def cv_unsupported_label():
    return CVPredictionEnvelope(
        model_version="test-model-1",
        status="confident_prediction",
        prediction=CVCandidate(label="shark", confidence=0.71),
        top_candidates=[
            CVCandidate(label="shark", confidence=0.71),
            CVCandidate(label="tuna", confidence=0.18),
            CVCandidate(label="tenggiri", confidence=0.08),
        ],
        threshold=0.80,
    )


@pytest.fixture
def main_app(seeded_prediction_repo, species_repo, image_store, cv_result):
    from apps.main_api.main import create_main_app

    return create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(cv_result),
            species_repo=species_repo,
            prediction_repo=seeded_prediction_repo,
            image_store=image_store,
        )
    )