import json

from fastapi.testclient import TestClient

from apps.main_api.errors import OpenCodeUnavailable
from apps.main_api.main import create_main_app
from apps.main_api.ports import AppDependencies
from apps.main_api.services.generation import KnowledgeGenerator
from tests.main_api.conftest import _species
from tests.main_api.fakes import (
    FakeCVClient,
    FakeEmbedder,
    FakeImageStore,
    FakeLotRepository,
    FakeOpenCodeClient,
    FakePredictionRepository,
    FakeRetriever,
    FakeSpeciesRepository,
)
from tests.main_api.test_lots_api import _verified


COMMERCIAL_LEAKS = (
    "starting_price", "amount_per_kg", "buyer_id", "buyer_dewi", "quantity_kg",
    "operator_id", "op_rian", "68000", "allocated",
)


def _client(retriever, generator, lots=None, predictions=None):
    app = create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(),
            species_repo=FakeSpeciesRepository([_species("tenggiri")]),
            prediction_repo=predictions or FakePredictionRepository({"pred_ok": _verified()}),
            image_store=FakeImageStore(),
            embedder=FakeEmbedder(),
            lot_repo=lots or FakeLotRepository(),
            retriever=retriever,
            generator=KnowledgeGenerator(generator),
        )
    )
    return TestClient(app), app


def test_snapshot_is_written_at_publish_and_discover_never_calls_the_llm(evidence):
    retriever = FakeRetriever(evidence)
    generator = FakeOpenCodeClient(json.dumps({
        "common_name": "ignored",
        "scientific_name": None,
        "taxonomy_status": "VERIFIED_TAXONOMY",
        "physical_characteristics": "Tubuh memanjang.",
        "taste": "gurih",
        "texture": "padat",
        "processing_methods": ["digoreng"],
        "commercial_uses": ["fillet"],
        "similar_or_substitute_species": ["kembung"],
        "potential_buyer_segments": ["rumah makan"],
        "limitations": [],
        "sources": [{"source_id": "source-1"}],
    }))
    lots = FakeLotRepository()
    client, app = _client(retriever, generator, lots)
    client.post("/api/v1/auth/login", json={"username": "rian", "password": "demo"})
    published = client.post("/api/v1/lots", json={
        "prediction_id": "pred_ok",
        "quantity_kg": "24",
        "starting_price_per_kg": "68000",
        "size_category": "L",
        "landing_point_id": "lp_muara_angke",
    })
    assert published.status_code == 200
    body = published.json()
    lot = lots.get(body["id"])
    assert lot.knowledge_snapshot is not None
    assert lot.knowledge_snapshot["physical_characteristics"] == "Tubuh memanjang."
    assert generator.calls == 1

    generator.error = OpenCodeUnavailable("llm is down", ["chunk-1"])
    app.state.deps.generator = KnowledgeGenerator(generator)
    discover = client.get(f"/api/v1/discover/{body['public_slug']}")
    assert discover.status_code == 200
    payload = discover.json()
    assert payload["public_slug"] == body["public_slug"]
    assert payload["species_id"] == "species_tenggiri"
    assert payload["card"]["physical_characteristics"] == "Tubuh memanjang."
    blob = json.dumps(payload)
    for leak in COMMERCIAL_LEAKS:
        assert leak not in blob
    assert generator.calls == 1  # discover did not generate again

    knowledge = client.get("/api/v1/predictions/pred_ok/knowledge")
    assert knowledge.status_code == 502


def test_unknown_discover_slug_is_404(evidence):
    client, _ = _client(FakeRetriever(evidence), FakeOpenCodeClient("{}"))
    response = client.get("/api/v1/discover/does-not-exist")
    assert response.status_code == 404
