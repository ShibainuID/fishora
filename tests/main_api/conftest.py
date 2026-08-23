import json

import pytest

from apps.contracts import CVCandidate, CVPredictionEnvelope
from apps.main_api.contracts import PredictionRecord, SpeciesRecord
from apps.main_api.ports import AppDependencies

from tests.main_api.fakes import (
    FakeCVClient,
    FakeEmbedder,
    FakeImageStore,
    FakeKnowledgeRepository,
    FakePredictionRepository,
    FakeSpeciesRepository,
)

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
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def fake_knowledge_repo():
    return FakeKnowledgeRepository()


@pytest.fixture
def unapproved_dir(tmp_path):
    """Candidate-only records (no signed approval anywhere)."""
    from apps.main_api.services.corpus import collect_candidate_stages

    from tests.main_api.test_corpus import FISHBASE_SOURCE, MARINADE_SOURCE, STAGES, claim, write_offline_dir

    claims = [
        claim("claim_bandeng_identity_001", "fishbase_chanos_chanos", "identity",
              "Bandeng is the milkfish Chanos chanos, family Chanidae.",
              "Teleostei (teleosts) > Gonorynchiformes", "x"),
        claim("claim_bandeng_processing_001", "marinade_4962", "processing_methods",
              "Bandeng presto is pressure-cooked milkfish at UMKM scale.",
              "KARAKTERISTIK PROSES PENGOLAHAN BANDENG", "x"),
    ]
    stage_dir = write_offline_dir(tmp_path / "offline", [FISHBASE_SOURCE, MARINADE_SOURCE],
                                  {stage: [dict(c, stage=stage) for c in claims] for stage in STAGES})
    candidate_dir = tmp_path / "candidates"
    collect_candidate_stages(stage_dir, candidate_dir)
    return candidate_dir


@pytest.fixture
def approval_manifest(tmp_path, unapproved_dir):
    """A manifest naming the candidate files; no valid signature for them."""
    path = tmp_path / "approval.json"
    path.write_text(json.dumps({
        "manifest": {
            "reviewer": "operator",
            "approved_at": "2026-08-24T08:00:00+00:00",
            "approved_chunk_ids": ["chunk_bandeng_identity_001", "chunk_bandeng_processing_001"],
            "approved_source_ids": ["fishbase_chanos_chanos", "marinade_4962"],
        },
        "signature": "0" * 64,
    }), encoding="utf-8")
    return path


@pytest.fixture
def approved_corpus(tmp_path):
    """Throwaway approved corpus signed with a temporary HMAC key."""
    from tests.main_api.test_corpus import approve_test_corpus

    return approve_test_corpus(tmp_path)


@pytest.fixture
def approved_corpus_long(tmp_path):
    """Approved corpus whose processing section exceeds 600 tokens (must split)."""
    from tests.main_api.test_corpus import approve_test_corpus

    return approve_test_corpus(tmp_path, long_processing=True)


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