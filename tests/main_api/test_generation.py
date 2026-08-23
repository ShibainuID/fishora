"""Task 7: strict OpenCode Go generation, citations, and taxonomy guardrails.

The OpenCodeGoClient tests stub the OpenAI constructor and Responses resource:
no real paid API request is ever made, and no user credential is read.
KnowledgeGenerator tests (added alongside the generator) use a
FakeOpenCodeClient end to end.
"""

import httpx
import json
import openai
import pytest

from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.errors import InvalidGeneratedKnowledge, OpenCodeUnavailable
from apps.main_api.services.generation import (
    GeneratedKnowledgeCard,
    OpenCodeGoClient,
    SYSTEM_PROMPT,
    KnowledgeGenerator,
)


def valid_json_for(label, forbidden_name):
    return json.dumps({
        "common_name": label,
        "scientific_name": forbidden_name,
        "taxonomy_status": "MODEL_ATTEMPT",
        "physical_characteristics": None,
        "taste": None,
        "texture": None,
        "processing_methods": [],
        "commercial_uses": [],
        "similar_or_substitute_species": [],
        "potential_buyer_segments": [],
        "limitations": [],
        "sources": [{"source_id": "source-1"}],
    })


# ---------------------------------------------------------------- generator


def test_no_verified_evidence_returns_empty_state_without_calling_opencode(species, fake_retriever, fake_generator):
    card = KnowledgeGenerator(fake_generator).generate(species, [])
    assert card.processing_methods == []
    assert card.sources == []
    assert "Informasi belum tersedia" in card.limitations
    assert fake_generator.calls == 0


def test_citation_must_reference_a_retrieved_source(species, evidence, fake_generator):
    fake_generator.response = '{"common_name":"bandeng","scientific_name":"Chanos chanos","taxonomy_status":"VERIFIED_TAXONOMY","physical_characteristics":null,"taste":null,"texture":null,"processing_methods":[],"commercial_uses":[],"similar_or_substitute_species":[],"potential_buyer_segments":[],"limitations":[],"sources":[{"source_id":"source-not-retrieved"}]}'
    try:
        KnowledgeGenerator(fake_generator).generate(species, evidence)
    except InvalidGeneratedKnowledge as error:
        assert "source-not-retrieved" in str(error)
    else:
        raise AssertionError("unretrieved citations must be rejected")


def test_invalid_json_and_opencode_timeout_become_retriable_generation_failures(species, evidence, fake_generator):
    fake_generator.response = "{"
    try:
        KnowledgeGenerator(fake_generator).generate(species, evidence)
    except InvalidGeneratedKnowledge:
        pass
    else:
        raise AssertionError("invalid JSON must be rejected")

    fake_generator.error = OpenCodeUnavailable("timeout", [chunk.chunk_id for chunk in evidence])
    try:
        KnowledgeGenerator(fake_generator).generate(species, evidence)
    except OpenCodeUnavailable:
        pass
    else:
        raise AssertionError("OpenCode failure must be propagated for HTTP 502 mapping")


def test_taxonomy_guardrails_override_model_attempts_to_narrow_tuna_or_name_gembolo(species_records, evidence, fake_generator):
    for label, forbidden_name, required_name in [
        ("tuna", "Thunnus albacares", "Thunnus spp."),
        ("gembolo", "Rastrelliger faughni", None),
        ("tenggiri", "Scomberomorus guttatus", "Scomberomorus commerson"),
    ]:
        fake_generator.response = valid_json_for(label, forbidden_name)
        card = KnowledgeGenerator(fake_generator).generate(species_records[label], evidence)
        assert card.scientific_name == required_name
        assert card.taxonomy_status == species_records[label].taxonomy_status
        assert card.common_name == species_records[label].common_name_id
        assert card.limitations


def test_relational_identity_overrides_generated_names_for_any_species(species, evidence, fake_generator):
    fake_generator.response = valid_json_for("bandeng", "Chanos chanos")
    card = KnowledgeGenerator(fake_generator).generate(species, evidence)
    assert card.common_name == species.common_name_id
    assert card.scientific_name is None  # relational value, not the generated one
    assert card.taxonomy_status == species.taxonomy_status


def test_generated_json_with_extra_fields_is_rejected(species, evidence, fake_generator):
    payload = json.loads(valid_json_for("bandeng", "Chanos chanos"))
    payload["invented_field"] = "x"
    fake_generator.response = json.dumps(payload)
    with pytest.raises(InvalidGeneratedKnowledge, match="schema"):
        KnowledgeGenerator(fake_generator).generate(species, evidence)


def test_generated_json_missing_required_field_is_rejected(species, evidence, fake_generator):
    payload = json.loads(valid_json_for("bandeng", "Chanos chanos"))
    del payload["processing_methods"]
    fake_generator.response = json.dumps(payload)
    with pytest.raises(InvalidGeneratedKnowledge, match="schema"):
        KnowledgeGenerator(fake_generator).generate(species, evidence)


def test_generated_json_with_non_list_field_is_rejected(species, evidence, fake_generator):
    payload = json.loads(valid_json_for("bandeng", "Chanos chanos"))
    payload["commercial_uses"] = "bukan daftar"
    fake_generator.response = json.dumps(payload)
    with pytest.raises(InvalidGeneratedKnowledge, match="schema"):
        KnowledgeGenerator(fake_generator).generate(species, evidence)


def test_empty_citations_with_evidence_are_rejected(species, evidence, fake_generator):
    payload = json.loads(valid_json_for("bandeng", "Chanos chanos"))
    payload["sources"] = []
    fake_generator.response = json.dumps(payload)
    with pytest.raises(InvalidGeneratedKnowledge, match="source"):
        KnowledgeGenerator(fake_generator).generate(species, evidence)


def test_sources_are_enriched_from_retrieved_evidence_never_from_generated_text(species, evidence, fake_generator):
    fake_generator.response = valid_json_for("bandeng", "Chanos chanos")
    card = KnowledgeGenerator(fake_generator).generate(species, evidence)
    (source,) = card.sources
    assert source.source_id == "source-1"
    assert source.title == "FishBase: Chanos chanos"
    assert source.url == "https://fishbase.example/chanos"
    assert source.publisher == "FishBase"
    assert source.source_type == "fishbase"
    assert source.reviewed_at == evidence[0].source_reviewed_at
    assert source.verification_status == "verified"


# ----------------------------------------------------------- opencode client


def _opencode_settings(api_key="test-key"):
    from types import SimpleNamespace

    from pydantic import SecretStr

    return SimpleNamespace(
        opencode_go_base_url="https://opencode.ai/zen/go/v1",
        opencode_go_api_key=SecretStr(api_key),
        opencode_go_model="gpt-5.6-luna",
        opencode_go_timeout_seconds=60.0,
    )


def _chunk(source_id="source-1", chunk_id="chunk-1"):
    return RetrievedChunk(
        chunk_id=chunk_id, species_id="species_bandeng", source_id=source_id,
        category="identity", content="Bandeng adalah ikan susu (Chanos chanos).",
        distance=0.1, chunk_verification_status="verified",
        source_verification_status="verified", source_title="FishBase: Chanos chanos",
        source_publisher="FishBase", source_url="https://fishbase.example/chanos",
        source_type="fishbase", source_reviewed_at=None,
    )


class _StubResponsesResource:
    def __init__(self, output_text="{}", error=None):
        self.calls = 0
        self.kwargs = None
        self._output_text = output_text
        self._error = error

    def create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        if self._error is not None:
            raise self._error
        return _StubResponse(self._output_text)


class _StubResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class _StubOpenAIClient:
    def __init__(self, responses):
        self.responses = responses
        self.kwargs = None


def _stub_openai_factory(stub):
    def factory(**kwargs):
        stub.kwargs = kwargs
        return stub
    return factory


def _species():
    return SpeciesRecord(
        id="species_bandeng", normalized_label="bandeng", common_name_id="common_bandeng",
        scientific_name=None, taxonomic_rank="species", taxonomy_status="VERIFIED_TAXONOMY",
        notes=None,
    )


def test_opencode_client_rejects_blank_api_key(monkeypatch):
    monkeypatch.setattr("apps.main_api.services.generation.OpenAI", _stub_openai_factory(_StubOpenAIClient(_StubResponsesResource())))
    with pytest.raises(ValueError, match="OPENCODE_GO_API_KEY"):
        OpenCodeGoClient(_opencode_settings(api_key=""))


def test_opencode_client_calls_responses_create_exactly_once_with_strict_schema(monkeypatch):
    responses = _StubResponsesResource(output_text='{"common_name":"bandeng"}')
    stub = _StubOpenAIClient(responses)
    monkeypatch.setattr("apps.main_api.services.generation.OpenAI", _stub_openai_factory(stub))

    output = OpenCodeGoClient(_opencode_settings()).generate(SYSTEM_PROMPT, [_chunk()], _species())

    assert output == '{"common_name":"bandeng"}'
    assert responses.calls == 1  # exactly one paid call per generation
    assert stub.kwargs["base_url"] == "https://opencode.ai/zen/go/v1"
    assert stub.kwargs["api_key"] == "test-key"  # SecretStr.get_secret_value(), never the SecretStr
    assert stub.kwargs["timeout"] == 60.0
    assert responses.kwargs["model"] == "gpt-5.6-luna"
    assert responses.kwargs["instructions"] == SYSTEM_PROMPT
    payload = responses.kwargs["input"]
    assert "common_bandeng" in payload and "source_id: source-1" in payload and "Chanos chanos" in payload
    text_format = responses.kwargs["text"]["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["strict"] is True
    schema = text_format["schema"]
    assert schema["additionalProperties"] is False
    assert set(GeneratedKnowledgeCard.model_fields) <= set(schema["properties"])
    assert "chat" not in responses.kwargs  # Responses API, never chat.completions


def test_opencode_client_timeout_and_connection_errors_map_to_opencode_unavailable(monkeypatch):
    request = httpx.Request("POST", "https://opencode.ai/zen/go/v1/responses")
    for error in (openai.APITimeoutError(request=request), openai.APIConnectionError(request=request)):
        responses = _StubResponsesResource(error=error)
        stub = _StubOpenAIClient(responses)
        monkeypatch.setattr("apps.main_api.services.generation.OpenAI", _stub_openai_factory(stub))
        with pytest.raises(OpenCodeUnavailable) as excinfo:
            OpenCodeGoClient(_opencode_settings()).generate(SYSTEM_PROMPT, [_chunk()], _species())
        assert excinfo.value.retrieved_chunk_ids == ["chunk-1"]