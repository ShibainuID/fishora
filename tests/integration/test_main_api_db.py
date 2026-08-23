import pytest
from pathlib import Path
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from apps.main_api.db.models import Prediction
from apps.main_api.db.repositories import seed_taxonomy
from apps.main_api.db.sql_repositories import SqlPredictionRepository, SqlSpeciesRepository

TAXONOMY_CSV = Path("/home/athilla/Documents/IF_ITB/Lomba/COMPFEST/AIC-2026/artifacts/Dataset/fishora_dataset/metadata/taxonomy.csv")


@pytest.fixture
def session_factory_(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        seed_taxonomy(session, TAXONOMY_CSV)
        session.commit()
    return factory


@pytest.mark.integration
def test_sql_species_repository_maps_label_and_id(session_factory_):
    repo = SqlSpeciesRepository(session_factory_)
    tuna = repo.get_by_normalized_label("tuna")
    assert tuna is not None
    assert tuna.id == "species_tuna"
    assert repo.get_by_id("species_tuna").normalized_label == "tuna"
    assert repo.get_by_normalized_label("shark") is None
    assert repo.get_by_id("species_shark") is None


@pytest.mark.integration
def test_sql_prediction_repository_create_get_verify_roundtrip(session_factory_):
    repo = SqlPredictionRepository(session_factory_)
    prediction_id = "it_pred_tuna_1"
    with session_factory_() as session:
        session.execute(delete(Prediction).where(Prediction.id == prediction_id))
        session.commit()

    created = repo.create(
        prediction_id,
        "images/it_pred_tuna_1.jpg",
        "species_tuna",
        0.71,
        [
            {"species_id": "species_tuna", "normalized_label": "tuna", "confidence": 0.71},
            {"species_id": "species_tenggiri", "normalized_label": "tenggiri", "confidence": 0.18},
        ],
        "test-model-1",
    )
    assert created.verification_status == "pending"
    assert created.verified_species_id is None

    fetched = repo.get(prediction_id)
    assert fetched is not None
    assert fetched.predicted_species_id == "species_tuna"
    assert fetched.confidence == 0.71
    assert fetched.top_candidates[0]["normalized_label"] == "tuna"

    confirmed = repo.verify(prediction_id, "species_tuna", "confirmed")
    assert confirmed.verification_status == "confirmed"
    assert confirmed.verified_species_id == "species_tuna"
    assert confirmed.predicted_species_id == "species_tuna"  # predicted identity immutable

    corrected = repo.verify(prediction_id, "species_gembolo", "corrected")
    assert corrected.verification_status == "corrected"
    assert corrected.verified_species_id == "species_gembolo"
    assert corrected.predicted_species_id == "species_tuna"

    assert repo.get(prediction_id).verification_status == "corrected"  # persisted state via get()
    assert repo.get("it_pred_missing") is None

    with session_factory_() as session:
        session.delete(session.get(Prediction, prediction_id))
        session.commit()