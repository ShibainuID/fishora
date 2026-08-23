"""Task 7: verification-gated knowledge endpoint.

Only the stored verified_species_id may drive retrieval; pending predictions
are rejected with 409 before any retrieval or generation happens.
"""

import json

from fastapi.testclient import TestClient


def test_pending_prediction_returns_409_and_verified_identity_is_the_only_retrieval_key(
        main_app, fake_retriever, seeded_prediction_repo):
    client = TestClient(main_app)
    pending = client.get("/api/v1/predictions/pred_confirm/knowledge")
    assert pending.status_code == 409
    assert fake_retriever.species_ids == []  # no retrieval before verification

    seeded_prediction_repo.verify("pred_correct", "species_gembolo", "corrected")
    response = client.get("/api/v1/predictions/pred_correct/knowledge")
    assert response.status_code == 200
    assert fake_retriever.species_ids[-1] == "species_gembolo"


def test_missing_prediction_returns_404(main_app, fake_retriever):
    response = TestClient(main_app).get("/api/v1/predictions/pred_missing/knowledge")
    assert response.status_code == 404
    assert fake_retriever.species_ids == []


def test_caller_species_query_parameter_is_ignored(main_app, fake_retriever, seeded_prediction_repo):
    # The route resolves identity from the stored verified_species_id only; a
    # caller-supplied ?species_id= must never become the retrieval key.
    seeded_prediction_repo.verify("pred_confirm", "species_gembolo", "corrected")
    response = TestClient(main_app).get(
        "/api/v1/predictions/pred_confirm/knowledge?species_id=species_tuna")
    assert response.status_code == 200
    assert fake_retriever.species_ids[-1] == "species_gembolo"


def test_verified_prediction_returns_enriched_card_with_taxonomy_guardrails(
        main_app, fake_retriever, fake_generator, seeded_prediction_repo, evidence):
    seeded_prediction_repo.verify("pred_correct", "species_gembolo", "corrected")
    fake_retriever.results = list(evidence)
    fake_generator.response = json.dumps({
        "common_name": "gembolo palsu",
        "scientific_name": "Rastrelliger faughni",
        "taxonomy_status": "MODEL_ATTEMPT",
        "physical_characteristics": "Badan ramping.",
        "taste": None,
        "texture": None,
        "processing_methods": ["digoreng"],
        "commercial_uses": [],
        "similar_or_substitute_species": [],
        "potential_buyer_segments": [],
        "limitations": [],
        "sources": [{"source_id": "source-1"}],
    })

    response = TestClient(main_app).get("/api/v1/predictions/pred_correct/knowledge")

    assert response.status_code == 200
    body = response.json()
    assert body["prediction_id"] == "pred_correct"
    assert body["species_id"] == "species_gembolo"
    card = body["card"]
    assert card["common_name"] == "common_gembolo"  # relational, not generated
    assert card["scientific_name"] is None  # gembolo guardrail
    assert card["taxonomy_status"] == "TAXONOMY_REVIEW_REQUIRED"
    assert card["physical_characteristics"] == "Badan ramping."
    assert card["processing_methods"] == ["digoreng"]
    assert card["limitations"]  # ambiguity limitation appended
    (source,) = card["sources"]
    assert source["source_id"] == "source-1"
    assert source["title"] == evidence[0].source_title  # server-side enrichment
    assert source["url"] == evidence[0].source_url
    assert source["publisher"] == evidence[0].source_publisher
    assert source["source_type"] == evidence[0].source_type
    assert source["verification_status"] == "verified"
    assert fake_generator.calls == 1
    assert fake_retriever.queries[0] == (
        "Buat kartu pengetahuan bahasa Indonesia untuk common_gembolo: "
        "identitas, ciri fisik, rasa dan tekstur, cara pengolahan, "
        "penggunaan komersial, dan spesies pengganti."
    )


def test_empty_evidence_returns_unavailable_card_without_calling_opencode(
        main_app, fake_retriever, fake_generator, seeded_prediction_repo):
    seeded_prediction_repo.verify("pred_confirm", "species_tuna", "confirmed")
    response = TestClient(main_app).get("/api/v1/predictions/pred_confirm/knowledge")
    assert response.status_code == 200
    card = response.json()["card"]
    assert card["sources"] == []
    assert card["processing_methods"] == []
    assert "Informasi belum tersedia" in card["limitations"]
    assert card["scientific_name"] == "Thunnus spp."  # tuna guardrail still applies
    assert fake_generator.calls == 0  # no OpenCode call for empty evidence
    assert fake_retriever.species_ids == ["species_tuna"]


def test_opencode_timeout_maps_to_502_without_leaking_details(
        main_app, fake_retriever, fake_generator, seeded_prediction_repo, evidence):
    from apps.main_api.errors import OpenCodeUnavailable

    seeded_prediction_repo.verify("pred_correct", "species_tuna", "corrected")
    fake_retriever.results = list(evidence)
    fake_generator.error = OpenCodeUnavailable("timeout", [chunk.chunk_id for chunk in evidence])

    response = TestClient(main_app).get("/api/v1/predictions/pred_correct/knowledge")

    assert response.status_code == 502
    body = response.json()
    assert set(body) == {"detail", "retrieved_chunk_ids"}  # fixed shape, no credentials/URLs/headers
    assert body["detail"] == "knowledge generation is temporarily unavailable"
    assert body["retrieved_chunk_ids"] == ["chunk-1", "chunk-2"]