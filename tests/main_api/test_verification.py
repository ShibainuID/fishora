from fastapi.testclient import TestClient


def test_confirm_preserves_predicted_identity_and_correct_changes_only_verified_identity(main_app, seeded_prediction_repo):
    client = TestClient(main_app)
    confirmed = client.post("/api/v1/fish/verify", json={"prediction_id": "pred_confirm", "verified_species_id": "species_tuna"})
    assert confirmed.status_code == 200
    assert confirmed.json()["verification_status"] == "confirmed"
    assert seeded_prediction_repo.get("pred_confirm").predicted_species_id == "species_tuna"
    assert seeded_prediction_repo.get("pred_confirm").verified_species_id == "species_tuna"
    assert seeded_prediction_repo.get("pred_confirm").confidence == 0.71  # history untouched

    corrected = client.post("/api/v1/fish/verify", json={"prediction_id": "pred_correct", "verified_species_id": "species_gembolo"})
    assert corrected.status_code == 200
    record = seeded_prediction_repo.get("pred_correct")
    assert corrected.json()["verification_status"] == "corrected"
    assert record.predicted_species_id == "species_tuna"
    assert record.verified_species_id == "species_gembolo"
    assert record.image_reference == "images/pred_correct.jpg"  # history untouched


def test_verify_missing_prediction_returns_404(main_app, seeded_prediction_repo):
    response = TestClient(main_app).post(
        "/api/v1/fish/verify", json={"prediction_id": "pred_missing", "verified_species_id": "species_tuna"}
    )
    assert response.status_code == 404
    assert seeded_prediction_repo.get("pred_missing") is None


def test_verify_unsupported_species_returns_422(main_app, seeded_prediction_repo):
    response = TestClient(main_app).post(
        "/api/v1/fish/verify", json={"prediction_id": "pred_confirm", "verified_species_id": "species_shark"}
    )
    assert response.status_code == 422
    record = seeded_prediction_repo.get("pred_confirm")
    assert record.verification_status == "pending"
    assert record.verified_species_id is None


def test_verify_ignores_caller_supplied_status_field(main_app, seeded_prediction_repo):
    # Status is derived server-side; a caller-supplied status must not be accepted.
    response = TestClient(main_app).post(
        "/api/v1/fish/verify",
        json={"prediction_id": "pred_confirm", "verified_species_id": "species_tuna", "status": "corrected"},
    )
    assert response.status_code == 200
    assert response.json()["verification_status"] == "confirmed"