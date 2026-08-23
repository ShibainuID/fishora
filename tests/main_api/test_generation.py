"""Task 7: strict OpenCode Go generation, citations, and taxonomy guardrails.

The OpenCodeGoClient tests stub the OpenAI constructor and Responses resource:
no real paid API request is ever made, and no user credential is read.
KnowledgeGenerator tests (added alongside the generator) use a
FakeOpenCodeClient end to end.
"""

import httpx
import openai
import pytest

from apps.main_api.contracts import RetrievedChunk, SpeciesRecord
from apps.main_api.errors import OpenCodeUnavailable
from apps.main_api.services.generation import (
    GeneratedKnowledgeCard,
    OpenCodeGoClient,
    SYSTEM_PROMPT,
)


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