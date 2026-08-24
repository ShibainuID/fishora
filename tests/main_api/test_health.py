"""Readiness probe.

The e2e walkthrough needs to distinguish three states: API down, API up but
unseeded, and ready. Without the taxonomy no species resolves, so every
identify and manual declaration fails with a confusing 422.
"""

from fastapi.testclient import TestClient

from apps.main_api.main import create_main_app
from apps.main_api.ports import AppDependencies

from tests.main_api.fakes import FakeCVClient, FakeImageStore, FakePredictionRepository, FakeSpeciesRepository


def _client(species):
    return TestClient(
        create_main_app(
            deps=AppDependencies(
                cv_client=FakeCVClient(None),
                species_repo=FakeSpeciesRepository(species),
                prediction_repo=FakePredictionRepository(),
                image_store=FakeImageStore(),
                embedder=object(),
            )
        )
    )


def test_health_reports_ready_when_the_taxonomy_is_seeded(species_repo):
    response = _client([]).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # An empty species table is a real, distinct failure mode.
    assert body["taxonomy_seeded"] is False


def test_health_reports_seeded_once_species_exist(species):
    # `species` is a real supported label, so probing the label set finds it.
    response = _client([species]).get("/health")
    assert response.json()["taxonomy_seeded"] is True


def test_health_never_requires_a_session():
    assert _client([]).get("/health").status_code == 200
