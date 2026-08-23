import json
from datetime import datetime, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.contracts import CVCandidate, CVPredictionEnvelope
from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.ports import AppDependencies
from apps.main_api.services.generation import KnowledgeGenerator
from tests.main_api.fakes import (
    FakeCVClient,
    FakeEmbedder,
    FakeImageStore,
    FakeKnowledgeRepository,
    FakeOpenCodeClient,
    FakePredictionRepository,
    FakeRetriever,
    FakeSpeciesRepository,
)


def _jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 16), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_upload_correct_and_generate_grounded_card():
    from apps.main_api.main import create_main_app

    species_repo = FakeSpeciesRepository([
        SpeciesRecord(
            id=f"species_{label}", normalized_label=label, common_name_id=label,
            scientific_name="Chanos chanos" if label == "bandeng" else None,
            taxonomic_rank="species", taxonomy_status="VERIFIED_TAXONOMY", notes=None,
        )
        for label in ("tuna", "tenggiri", "gembolo", "bandeng")
    ])
    cv_result = CVPredictionEnvelope(
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
    evidence = [RetrievedChunk(
        chunk_id="chunk-1", species_id="species_bandeng", source_id="source-1",
        category="identity", content="Bandeng adalah Chanos chanos.", distance=0.1,
        chunk_verification_status="verified", source_verification_status="verified",
        source_title="FishBase: Chanos chanos", source_publisher="FishBase",
        source_url="https://fishbase.example/chanos", source_type="fishbase",
        source_reviewed_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
    )]
    predictions = FakePredictionRepository()
    retriever = FakeRetriever(evidence)
    opencode = FakeOpenCodeClient(json.dumps({
        "common_name": "bandeng",
        "scientific_name": "Chanos chanos",
        "taxonomy_status": "VERIFIED_TAXONOMY",
        "physical_characteristics": "Tubuh memanjang dan berwarna keperakan.",
        "taste": "gurih",
        "texture": "lembut",
        "processing_methods": ["presto"],
        "commercial_uses": ["pangan"],
        "similar_or_substitute_species": [],
        "potential_buyer_segments": ["rumah tangga"],
        "limitations": [],
        "sources": [{"source_id": "source-1"}],
    }))
    app = create_main_app(deps=AppDependencies(
        cv_client=FakeCVClient(cv_result),
        species_repo=species_repo,
        prediction_repo=predictions,
        image_store=FakeImageStore(),
        embedder=FakeEmbedder(),
        knowledge_repo=FakeKnowledgeRepository(),
        retriever=retriever,
        generator=KnowledgeGenerator(opencode),
    ))

    with TestClient(app) as client:
        identified = client.post(
            "/api/v1/fish/identify",
            files={"file": ("fish.jpg", _jpeg_bytes(), "image/jpeg")},
        )
        assert identified.status_code == 200
        prediction_id = identified.json()["prediction_id"]
        assert client.get(f"/api/v1/predictions/{prediction_id}/knowledge").status_code == 409

        verified = client.post(
            "/api/v1/fish/verify",
            json={"prediction_id": prediction_id, "verified_species_id": "species_bandeng"},
        )
        assert verified.status_code == 200
        assert verified.json()["verification_status"] == "corrected"

        card = client.get(f"/api/v1/predictions/{prediction_id}/knowledge")

    record = predictions.get(prediction_id)
    assert record.predicted_species_id == "species_tuna"
    assert record.verified_species_id == "species_bandeng"
    assert retriever.species_ids == ["species_bandeng"]
    assert card.status_code == 200
    assert [source["source_id"] for source in card.json()["card"]["sources"]] == ["source-1"]
    assert opencode.calls == 1
