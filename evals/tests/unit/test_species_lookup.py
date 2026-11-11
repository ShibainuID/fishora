"""A catch outside the trained species: name lookup and listing the species."""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from apps.main_api.config import MainSettings
from apps.main_api.errors import InvalidUnlistedSpecies
from apps.main_api.services import species_lookup
from evals.corpus import species_records
from evals.fakes import InMemorySpeciesRepository

pytestmark = pytest.mark.unit

FISHBASE = "https://www.fishbase.se/summary/Siganus-canaliculatus"
WIKI = "https://id.wikipedia.org/wiki/Baronang"


def _settings() -> MainSettings:
    return MainSettings(_env_file=None, database_url="postgresql+psycopg://t@localhost/t",
                        openrouter_api_key=SecretStr("test-key"))


class _Response:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _post(candidates, annotations):
    def post(url, json=None, headers=None, timeout=None):
        return _Response({"choices": [{"message": {
            "content": __import__("json").dumps({"candidates": candidates}), "annotations": annotations}}]})
    return post


def _cite(url, content):
    return {"type": "url_citation", "url_citation": {"url": url, "title": "T", "content": content}}


def test_lookup_keeps_only_names_a_source_ties_to_the_local_name():
    candidates = [
        {"scientific_name": "Siganus canaliculatus", "english_name": "White-spotted spinefoot", "rank": "species", "url": FISHBASE},
        {"scientific_name": "Siganus guttatus", "english_name": None, "rank": "species", "url": WIKI},  # not in the excerpt
        {"scientific_name": "Siganus javus", "rank": "species", "url": "https://blog.example/x"},      # not a search result
        {"scientific_name": "Siganus canaliculatus", "rank": "species", "url": WIKI},                  # duplicate name
    ]
    annotations = [
        _cite(FISHBASE, "Siganus canaliculatus. Common names: baronang (Indonesia), white-spotted spinefoot."),
        _cite(WIKI, "Baronang adalah ikan dari genus Siganus; contohnya Siganus canaliculatus."),
    ]
    matches = species_lookup.lookup("ikan baronang", _settings(), post=_post(candidates, annotations))
    assert [m.scientific_name for m in matches] == ["Siganus canaliculatus"]
    assert matches[0].url == FISHBASE and matches[0].existing_species_id is None


def test_lookup_flags_a_species_fishora_already_supports():
    repo = InMemorySpeciesRepository(species_records())
    kembung = next(s for s in species_records() if s.normalized_label == "kembung")
    url = "https://www.fishbase.se/summary/Rastrelliger-kanagurta"
    matches = species_lookup.lookup(
        "banyar", _settings(), repo,
        post=_post([{"scientific_name": kembung.scientific_name, "rank": "species", "url": url}],
                   [_cite(url, f"{kembung.scientific_name}: local names kembung, banyar.")]))
    assert matches[0].existing_species_id == kembung.id


@pytest.mark.parametrize("name", ["", "   ", "x" * 61, "baronang; drop table", "<script>"])
def test_names_that_are_not_plain_names_are_refused(name):
    with pytest.raises(InvalidUnlistedSpecies):
        species_lookup.clean_name(name)


def test_label_drops_the_word_ikan_and_joins_words():
    assert species_lookup.label_for("Ikan Baronang") == "baronang"
    assert species_lookup.label_for("kakap merah") == "kakap_merah"
    assert species_lookup.label_for("Ikan") == "ikan"


def test_register_adds_a_new_species_for_review():
    repo = InMemorySpeciesRepository(species_records())
    record = species_lookup.register(repo, "Ikan Baronang", scientific_name="Siganus canaliculatus",
                                     taxonomic_rank="species", source_url=FISHBASE, operator_id="op_rian")
    assert record.id == "species_baronang" and record.common_name_id == "Baronang"
    assert record.taxonomy_status == "TAXONOMY_REVIEW_REQUIRED"
    assert record.scientific_name == "Siganus canaliculatus" and FISHBASE in record.notes
    assert repo.get_by_id("species_baronang") == record
    # Listing the same fish again reuses it.
    assert species_lookup.register(repo, "baronang") == record


def test_register_without_a_scientific_name():
    record = species_lookup.register(InMemorySpeciesRepository([]), "kakap merah", taxonomic_rank="species")
    assert record.scientific_name is None and record.taxonomic_rank == "unknown"
    assert "no source" in record.notes


def test_register_reuses_a_known_species_by_label_or_scientific_name():
    repo = InMemorySpeciesRepository(species_records())
    kembung = repo.get_by_normalized_label("kembung")
    assert species_lookup.register(repo, "ikan kembung") == kembung
    assert species_lookup.register(repo, "banyar", scientific_name=kembung.scientific_name) == kembung
    assert repo.get_by_normalized_label("banyar") is None


def test_register_refuses_a_scientific_name_that_is_not_latin():
    with pytest.raises(InvalidUnlistedSpecies):
        species_lookup.register(InMemorySpeciesRepository([]), "baronang", scientific_name="<b>x</b>")


def _app():
    from apps.main_api.main import create_main_app
    from apps.main_api.ports import AppDependencies
    from evals.fakes import FixedCVClient, InMemoryImageStore, InMemoryPredictionRepository

    deps = AppDependencies(cv_client=FixedCVClient("nila"), species_repo=InMemorySpeciesRepository(species_records()),
                           prediction_repo=InMemoryPredictionRepository(), image_store=InMemoryImageStore(),
                           embedder=type("E5Stub", (), {"model_name": "intfloat/multilingual-e5-base"})())
    return create_main_app(deps=deps), deps


def test_unlisted_catch_is_declared_under_a_new_species():
    from evals.tests.conftest import png_bytes, sign_in

    app, deps = _app()
    with TestClient(app) as client:
        sign_in(client)
        response = client.post("/api/v1/fish/unlisted", files={"file": ("f.png", png_bytes(), "image/png")},
                               data={"local_name": "Ikan Baronang", "scientific_name": "Siganus canaliculatus",
                                     "taxonomic_rank": "species", "source_url": FISHBASE})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verified_species_id"] == "species_baronang" and body["normalized_label"] == "baronang"
    assert body["model_version"] == "manual-entry"
    assert deps.species_repo.get_by_id("species_baronang").taxonomy_status == "TAXONOMY_REVIEW_REQUIRED"


def test_a_bad_photo_adds_no_species():
    from evals.tests.conftest import sign_in

    app, deps = _app()
    with TestClient(app) as client:
        sign_in(client)
        response = client.post("/api/v1/fish/unlisted", files={"file": ("f.png", b"not an image", "image/png")},
                               data={"local_name": "baronang"})
    assert response.status_code in (400, 413, 415, 422)
    assert deps.species_repo.get_by_normalized_label("baronang") is None


def test_lookup_is_unavailable_without_openrouter_and_needs_an_operator():
    from evals.tests.conftest import sign_in

    app, _ = _app()
    with TestClient(app) as client:
        assert client.post("/api/v1/fish/lookup-species", json={"local_name": "baronang"}).status_code == 401
        sign_in(client)
        response = client.post("/api/v1/fish/lookup-species", json={"local_name": "baronang"})
    assert response.status_code == 503
    assert json.loads(response.text)["detail"] == "species lookup is unavailable"
