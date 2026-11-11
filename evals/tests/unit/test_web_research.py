"""Web research for empty card fields: only verified, cited, allow-listed claims survive."""

import json

import pytest
from pydantic import SecretStr

from apps.main_api.config import MainSettings
from apps.main_api.contracts import KnowledgeJobRecord, SpeciesRecord
from apps.main_api.services import web_research
from evals.fakes import InMemoryJobRepository, InMemorySpeciesRepository

pytestmark = pytest.mark.unit

SPECIES = SpeciesRecord("species_kembung", "kembung", "Kembung", "Rastrelliger kanagurta", "species",
                        "VERIFIED_TAXONOMY", None)
FAO = "https://www.fao.org/fishery/kembung"
BLOG = "https://some-food-blog.example/kembung"


def _settings(**over) -> MainSettings:
    return MainSettings(_env_file=None, database_url="postgresql+psycopg://t@localhost/t",
                        openrouter_api_key=SecretStr("test-key"), **over)


class _Response:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _post(claims, annotations, sent=None):
    def post(url, json=None, headers=None, timeout=None):
        if sent is not None:
            sent.append(json)
        return _Response({
            "choices": [{"message": {"content": __import__("json").dumps({"claims": claims}),
                                     "annotations": annotations}}],
            "usage": {"cost": 0.0074, "server_tool_use_details": {"web_search_requests": 1}},
        })
    return post


def _cite(url, content):
    return {"type": "url_citation", "url_citation": {"url": url, "title": "T", "content": content}}


class _Judge:
    """Labels every claim it is shown as supported."""

    def invoke(self, prompt):
        payload = json.loads(prompt.rsplit("\n", 1)[1])
        return json.dumps({"verdicts": [{"id": c["id"], "reason": "ok", "label": "supported"}
                                        for c in payload["claims"]]})


def test_keeps_only_cited_allowlisted_and_checked_claims():
    claims = [
        {"field": "taste", "text": "Its flesh tastes mild.", "url": FAO},
        {"field": "taste", "text": "Its flesh is sweet.", "url": BLOG},          # off the allow-list
        {"field": "texture", "text": "Firm flesh.", "url": "https://fao.org/x"},  # not a search result
        {"field": "texture", "text": "Fat content is 12 percent.", "url": FAO},   # number not in excerpt
        {"field": "commercial_uses", "text": "Canned.", "url": FAO},              # field not requested
    ]
    annotations = [_cite(FAO, "Kembung flesh tastes mild and is firm; fat 5 percent."), _cite(BLOG, "sweet")]
    sent = []
    out = web_research.research(SPECIES, ["taste", "texture"], _settings(), _Judge(), post=_post(claims, annotations, sent))

    assert [f["text"] for f in out["findings"]] == ["Its flesh tastes mild."]
    assert out["findings"][0]["url"] == FAO
    assert out["checked"] == 2 and out["rejected"] == 3
    tool = sent[0]["tools"][0]
    assert tool["type"] == "openrouter:web_search"
    assert "fao.org" in tool["parameters"]["allowed_domains"]


def test_enabled_only_on_openrouter_with_a_key():
    assert web_research.enabled(_settings())
    assert not web_research.enabled(_settings(web_research_enabled=False))
    assert not web_research.enabled(_settings(llm_provider="opencode_go"))
    assert not web_research.enabled(MainSettings(_env_file=None, database_url="postgresql+psycopg://t@localhost/t"))
    assert not web_research.enabled(None)


def test_gaps_lists_the_empty_card_fields():
    card = {"taste": "Mild.", "texture": None, "processing_methods": [], "commercial_uses": ["Canned"],
            "physical_characteristics": "Silver.", "similar_or_substitute_species": [], "potential_buyer_segments": []}
    assert web_research.gaps(card) == ["texture", "processing_methods", "potential_buyer_segments",
                                       "similar_or_substitute_species"]
    assert web_research.gaps(None) == []


def test_run_for_job_stores_findings_in_the_trace_not_the_card(monkeypatch):
    jobs = InMemoryJobRepository()
    card = {"taste": None, "texture": "Firm.", "physical_characteristics": "Silver.", "processing_methods": ["Smoked"],
            "commercial_uses": ["Markets"], "similar_or_substitute_species": ["Gembolo"], "potential_buyer_segments": ["Traders"]}
    jobs.rows["j1"] = KnowledgeJobRecord(id="j1", prediction_id="p1", species_id=SPECIES.id, status="completed",
                                         final_card=card, trace={"pipeline": "x"})
    monkeypatch.setattr(web_research, "research", lambda *a, **k: {"findings": [
        {"field": "taste", "text": "Mild.", "url": FAO, "title": "T"}]})
    web_research.run_for_job("j1", jobs, InMemorySpeciesRepository([SPECIES]), _settings(), _Judge())

    job = jobs.get("j1")
    assert job.final_card == card
    assert job.trace["pipeline"] == "x"
    assert job.trace["web_research"]["status"] == "done"
    assert job.trace["web_research"]["fields"] == ["taste"]
    assert job.trace["web_research"]["findings"][0]["url"] == FAO


def test_run_for_job_records_a_failed_search(monkeypatch):
    jobs = InMemoryJobRepository()
    jobs.rows["j1"] = KnowledgeJobRecord(id="j1", prediction_id="p1", species_id=SPECIES.id, status="completed",
                                         final_card={"taste": None})

    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(web_research, "research", boom)
    web_research.run_for_job("j1", jobs, InMemorySpeciesRepository([SPECIES]), _settings(), _Judge())
    assert jobs.get("j1").trace["web_research"]["status"] == "failed"


def test_knowledge_endpoint_returns_web_leads_beside_the_card_not_in_it():
    from fastapi.testclient import TestClient

    from apps.main_api.main import create_main_app
    from apps.main_api.ports import AppDependencies
    from evals.corpus import species_records
    from evals.fakes import FixedCVClient, InMemoryImageStore, InMemoryPredictionRepository
    from evals.tests.conftest import sign_in

    jobs = InMemoryJobRepository()
    card = {"common_name": "Kembung", "scientific_name": "Rastrelliger kanagurta", "taxonomy_status": "VERIFIED_TAXONOMY",
            "physical_characteristics": None, "taste": None, "texture": None, "processing_methods": [],
            "commercial_uses": [], "similar_or_substitute_species": [], "potential_buyer_segments": [],
            "limitations": [], "sources": []}
    lead = {"field": "taste", "text": "Mild.", "url": FAO, "title": "T"}
    jobs.rows["p1"] = KnowledgeJobRecord(id="p1", prediction_id="p1", species_id="species_kembung", status="completed",
                                         final_card=card, trace={"web_research": {"status": "done", "fields": ["taste"],
                                                                                  "findings": [lead], "cost_usd": 0.007}})
    deps = AppDependencies(cv_client=FixedCVClient("kembung"), species_repo=InMemorySpeciesRepository(species_records()),
                           prediction_repo=InMemoryPredictionRepository(), image_store=InMemoryImageStore(),
                           embedder=type("E5Stub", (), {"model_name": "intfloat/multilingual-e5-base"})(), job_repo=jobs)
    with TestClient(create_main_app(deps=deps)) as client:
        sign_in(client)
        body = client.get("/api/v1/predictions/p1/knowledge").json()

    assert body["web_research"] == {"status": "done", "fields": ["taste"], "findings": [lead]}
    assert "Mild." not in json.dumps(body["card"])
