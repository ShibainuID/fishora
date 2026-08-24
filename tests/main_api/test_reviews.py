"""Commercial-buyer reviews (PRD 8.5).

Two rules carry the weight here. Governance first: a review is a market signal,
never verified knowledge (PRD 4.4, 8.2), so it is stored and served apart from
the knowledge card. Second, the product requirement that a review written
against one lot surfaces on every auction for that species, including lots from
a different fisher group, since a buyer's experience of Tenggiri is about the
species and not about who landed it.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from apps.main_api.contracts import LotRecord, PredictionRecord
from apps.main_api.main import create_main_app
from apps.main_api.ports import AppDependencies

from tests.main_api.fakes import (
    FakeCVClient,
    FakeImageStore,
    FakeLotRepository,
    FakePredictionRepository,
    FakeReviewRepository,
    FakeSpeciesRepository,
)
from tests.main_api.test_lots_api import _login, _lot, _verified


def _client(lots=None, reviews=None):
    lot_repo = lots or FakeLotRepository({"lot_1": _lot()})
    review_repo = reviews or FakeReviewRepository()
    app = create_main_app(
        deps=AppDependencies(
            cv_client=FakeCVClient(None),
            species_repo=FakeSpeciesRepository([]),
            prediction_repo=FakePredictionRepository({"pred_ok": _verified()}),
            image_store=FakeImageStore(),
            embedder=object(),
            lot_repo=lot_repo,
            review_repo=review_repo,
        )
    )
    return TestClient(app), review_repo


def test_a_buyer_can_review_a_lot_they_were_allocated():
    lots = FakeLotRepository({"lot_1": _lot(status="allocated", allocated_buyer_id="buyer_dewi")})
    client, repo = _client(lots)
    _login(client, "dewi")

    response = client.post(
        "/api/v1/lots/lot_1/review",
        json={
            "actual_use": "digoreng",
            "processing_suitability": 4,
            "substitute_acceptance": True,
            "comment": "Tekstur padat, cocok untuk gorengan.",
        },
    )
    assert response.status_code == 200
    assert len(repo.all()) == 1


def test_a_buyer_cannot_review_a_lot_they_did_not_win():
    lots = FakeLotRepository({"lot_1": _lot(status="allocated", allocated_buyer_id="buyer_other")})
    client, repo = _client(lots)
    _login(client, "dewi")

    response = client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": 4},
    )
    # A review is post-use feedback (PRD 8.5). Someone who never received the
    # catch has nothing to report, and letting them post would poison the signal.
    assert response.status_code == 403
    assert repo.all() == []


def test_a_lot_still_open_cannot_be_reviewed():
    lots = FakeLotRepository({"lot_1": _lot(status="active")})
    client, repo = _client(lots)
    _login(client, "dewi")

    response = client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": 4},
    )
    assert response.status_code == 409
    assert repo.all() == []


def test_reviews_surface_on_every_lot_of_the_same_species():
    """The product requirement: one buyer's experience of a species travels to
    every auction for it, even lots landed by a different fisher group."""
    reviewed = _lot(status="allocated", allocated_buyer_id="buyer_dewi")
    other_fisher = _lot(
        id="lot_2",
        public_slug="tenggiri-lot2",
        operator_id="op_other",
        seller_fisher_group="KUB Bahari Jaya",
    )
    lots = FakeLotRepository({"lot_1": reviewed, "lot_2": other_fisher})
    client, _ = _client(lots)

    _login(client, "dewi")
    client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": 5},
    )

    # Same species, different lot, different fisher group.
    listed = client.get("/api/v1/lots/lot_2/reviews")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["actual_use"] == "digoreng"


def test_reviews_do_not_leak_across_species():
    reviewed = _lot(status="allocated", allocated_buyer_id="buyer_dewi")
    different_species = _lot(
        id="lot_3", public_slug="kembung-lot3", species_id="species_kembung"
    )
    lots = FakeLotRepository({"lot_1": reviewed, "lot_3": different_species})
    client, _ = _client(lots)

    _login(client, "dewi")
    client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": 5},
    )

    assert client.get("/api/v1/lots/lot_3/reviews").json() == []


def test_reviews_are_public_so_a_browsing_buyer_sees_them():
    lots = FakeLotRepository({"lot_1": _lot()})
    client, _ = _client(lots)
    # Reading is unauthenticated, like the marketplace listing itself.
    assert client.get("/api/v1/lots/lot_1/reviews").status_code == 200


def test_posting_a_review_requires_a_session():
    client, repo = _client(
        FakeLotRepository({"lot_1": _lot(status="allocated", allocated_buyer_id="buyer_dewi")})
    )
    response = client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": 4},
    )
    assert response.status_code == 401
    assert repo.all() == []


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_processing_suitability_is_bounded(rating):
    lots = FakeLotRepository({"lot_1": _lot(status="allocated", allocated_buyer_id="buyer_dewi")})
    client, _ = _client(lots)
    _login(client, "dewi")
    response = client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": rating},
    )
    assert response.status_code == 422


def test_review_response_never_carries_verified_knowledge_fields():
    """PRD 4.4: market signals and verified knowledge stay separate. A review
    payload must not carry taxonomy or sources, or a client could render it as
    though it were curated."""
    lots = FakeLotRepository({"lot_1": _lot(status="allocated", allocated_buyer_id="buyer_dewi")})
    client, _ = _client(lots)
    _login(client, "dewi")
    client.post(
        "/api/v1/lots/lot_1/review",
        json={"actual_use": "digoreng", "processing_suitability": 4},
    )
    row = client.get("/api/v1/lots/lot_1/reviews").json()[0]
    for forbidden in ("taxonomy_status", "sources", "scientific_name", "limitations"):
        assert forbidden not in row


def test_lot_response_carries_the_seller_fisher_group():
    """PRD 8.3.1 lists Seller / Fisher Group among the required lot fields. It is
    how a fisher stays visible in a flow an operator publishes on their behalf."""
    lots = FakeLotRepository({"lot_1": _lot(seller_fisher_group="KUB Mina Sejahtera")})
    client, _ = _client(lots)
    body = client.get("/api/v1/lots/lot_1").json()
    assert body["seller_fisher_group"] == "KUB Mina Sejahtera"
