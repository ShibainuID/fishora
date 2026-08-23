"""Task 6: verified, species-scoped, category-diverse retrieval (unit tests).

The fake knowledge repository and fake embedder stay in-memory; only
VerifiedRetriever behavior is under test here. Real pgvector behavior
(exclusion of wrong-species/unverified/wrong-model rows, cosine ordering) is
covered in tests/integration/test_pgvector_retrieval.py.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from apps.main_api.contracts import KnowledgeChunkWrite, KnowledgeSourceWrite
from apps.main_api.services.embeddings import E5_MODEL_NAME

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
UNIT = 1.0 / (768 ** 0.5)


def _source(source_id, verification_status="verified"):
    return KnowledgeSourceWrite(
        id=source_id, title=f"Source {source_id}", source_type="test",
        url=f"https://example.test/{source_id}", publisher="it",
        reviewed_at=datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc),
        verification_status=verification_status,
    )


def _chunk(chunk_id, source_id, category, content, embedding=None, *,
           species_id="species_bandeng", verification_status="verified",
           embedding_model=E5_MODEL_NAME):
    return KnowledgeChunkWrite(
        id=chunk_id, species_id=species_id, source_id=source_id, category=category,
        content=content, embedding=embedding if embedding is not None else [UNIT] * 768,
        embedding_model=embedding_model, verification_status=verification_status,
    )


def _emb(k):
    """Normalized 768-d vector whose cosine distance to the unit query vector
    strictly increases with k (k=0 is exactly the unit vector)."""
    raw = [UNIT + k] + [UNIT] * 767
    norm = sum(value * value for value in raw) ** 0.5
    return [value / norm for value in raw]


def _seed(repo, chunks, sources=None):
    """Insert chunks plus one verified source per distinct source id."""
    if sources is None:
        sources = []
        seen = set()
        for chunk in chunks:
            if chunk.source_id not in seen:
                seen.add(chunk.source_id)
                sources.append(_source(chunk.source_id))
    repo.insert_verified(sources, list(chunks))


def test_retrieval_filters_species_and_both_verification_statuses(fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    _seed(fake_knowledge_repo, [
        _chunk("c_bandeng_id", "s_bandeng", "identity", "Bandeng is the milkfish."),
        _chunk("c_bandeng_candidate", "s_bandeng", "taste_texture", "unverified chunk",
               verification_status="candidate"),
        _chunk("c_bandeng_bad_source", "s_bad_source", "taste_texture",
               "chunk under an unverified source"),
        _chunk("c_tuna_id", "s_tuna", "identity", "Tuna identity", species_id="species_tuna"),
    ], sources=[_source("s_bandeng"),
                _source("s_bad_source", verification_status="candidate"),
                _source("s_tuna")])

    result = VerifiedRetriever(fake_knowledge_repo, fake_embedder).retrieve(
        "species_bandeng", "ciri fisik bandeng")

    assert [chunk.chunk_id for chunk in result] == ["c_bandeng_id"]
    assert all(chunk.species_id == "species_bandeng" for chunk in result)
    assert all(chunk.chunk_verification_status == "verified" for chunk in result)
    assert all(chunk.source_verification_status == "verified" for chunk in result)


def test_retrieval_selects_one_best_chunk_per_available_category_before_filling_by_distance(
        fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    # The only identity chunk is the globally farthest; every other chunk is
    # nearer. Category-first selection must still surface identity first.
    _seed(fake_knowledge_repo, [
        _chunk("c_id", "s_bandeng", "identity", "id", embedding=_emb(9)),
        _chunk("c_pc", "s_bandeng", "physical_characteristics", "pc", embedding=_emb(1)),
        _chunk("c_tt", "s_bandeng", "taste_texture", "tt", embedding=_emb(2)),
        _chunk("c_pm", "s_bandeng", "processing_methods", "pm", embedding=_emb(3)),
        _chunk("c_cu", "s_bandeng", "commercial_uses", "cu", embedding=_emb(4)),
        _chunk("c_sub", "s_bandeng", "substitutes", "sub", embedding=_emb(5)),
    ])

    result = VerifiedRetriever(fake_knowledge_repo, fake_embedder).retrieve(
        "species_bandeng", "kartu pengetahuan bandeng")
    categories = [chunk.category for chunk in result]

    assert categories == ["identity", "physical_characteristics", "taste_texture",
                          "processing_methods", "commercial_uses", "substitutes"]
    assert len(categories) <= 6
    assert len(categories) == len(set(categories))


def test_retrieval_rejects_negative_max_chunks(fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    retriever = VerifiedRetriever(fake_knowledge_repo, fake_embedder)
    with pytest.raises(ValueError, match="max_chunks"):
        retriever.retrieve("species_bandeng", "q", max_chunks=-1)


def test_retrieval_returns_empty_without_embedding_for_zero_max_chunks(
        fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    retriever = VerifiedRetriever(fake_knowledge_repo, fake_embedder)
    assert retriever.retrieve("species_bandeng", "q", max_chunks=0) == []
    assert fake_embedder.query_calls == []
    assert fake_knowledge_repo.search_calls == []


def test_retrieval_never_exceeds_max_chunks(fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    _seed(fake_knowledge_repo, [
        _chunk("c_id", "s_bandeng", "identity", "id", embedding=_emb(0)),
        _chunk("c_pc", "s_bandeng", "physical_characteristics", "pc", embedding=_emb(1)),
        _chunk("c_tt", "s_bandeng", "taste_texture", "tt", embedding=_emb(2)),
        _chunk("c_pm", "s_bandeng", "processing_methods", "pm", embedding=_emb(3)),
        _chunk("c_cu", "s_bandeng", "commercial_uses", "cu", embedding=_emb(4)),
        _chunk("c_sub", "s_bandeng", "substitutes", "sub", embedding=_emb(5)),
    ])

    result = VerifiedRetriever(fake_knowledge_repo, fake_embedder).retrieve(
        "species_bandeng", "q", max_chunks=3)

    assert len(result) == 3
    assert [chunk.category for chunk in result] == [
        "identity", "physical_characteristics", "taste_texture"]


def test_retrieval_fills_remaining_slots_with_nearest_unused_candidates(
        fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    _seed(fake_knowledge_repo, [
        _chunk("c_id", "s_bandeng", "identity", "id", embedding=_emb(0)),
        _chunk("c_pc", "s_bandeng", "physical_characteristics", "pc", embedding=_emb(4)),
        _chunk("c_tt", "s_bandeng", "taste_texture", "tt", embedding=_emb(5)),
        _chunk("c_pm", "s_bandeng", "processing_methods", "pm", embedding=_emb(6)),
        _chunk("c_cu", "s_bandeng", "commercial_uses", "cu", embedding=_emb(7)),
        _chunk("c_sub", "s_bandeng", "substitutes", "sub", embedding=_emb(8)),
        _chunk("c_id_near1", "s_bandeng", "identity", "id near 1", embedding=_emb(1)),
        _chunk("c_id_near2", "s_bandeng", "identity", "id near 2", embedding=_emb(2)),
    ])

    result = VerifiedRetriever(fake_knowledge_repo, fake_embedder).retrieve(
        "species_bandeng", "q", max_chunks=8)

    assert len(result) == 8
    assert [chunk.category for chunk in result] == [
        "identity", "physical_characteristics", "taste_texture",
        "processing_methods", "commercial_uses", "substitutes", "identity", "identity"]
    assert [chunk.chunk_id for chunk in result][6:] == ["c_id_near1", "c_id_near2"]


def test_retrieval_returns_fewer_than_max_when_evidence_is_missing(
        fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    _seed(fake_knowledge_repo, [_chunk("c_id", "s_bandeng", "identity", "id")])
    retriever = VerifiedRetriever(fake_knowledge_repo, fake_embedder)

    assert [chunk.chunk_id for chunk in retriever.retrieve("species_bandeng", "q")] == ["c_id"]
    assert retriever.retrieve("species_unknown", "q") == []


def test_retrieval_uses_embed_query_never_passage_embedding(fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    _seed(fake_knowledge_repo, [_chunk("c_id", "s_bandeng", "identity", "id")])
    VerifiedRetriever(fake_knowledge_repo, fake_embedder).retrieve(
        "species_bandeng", "ciri fisik bandeng")

    assert fake_embedder.query_calls == ["ciri fisik bandeng"]
    assert fake_embedder.passage_calls == []
    assert len(fake_knowledge_repo.search_calls) == 1
    species_id, _, embedding_model, limit = fake_knowledge_repo.search_calls[0]
    assert species_id == "species_bandeng"
    assert embedding_model == E5_MODEL_NAME
    assert limit == 6 * 6  # bounded fetch window for category diversification


def test_retrieved_chunk_carries_source_metadata_and_both_statuses(
        fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    reviewed_at = datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc)
    _seed(fake_knowledge_repo, [_chunk("c_id", "s_bandeng", "identity", "id")], sources=[
        KnowledgeSourceWrite(id="s_bandeng", title="Bandeng Encyclopedia", source_type="fishbase",
                             url="https://fishbase.example/chanos", publisher="FishBase",
                             reviewed_at=reviewed_at, verification_status="verified")])

    (chunk,) = VerifiedRetriever(fake_knowledge_repo, fake_embedder).retrieve(
        "species_bandeng", "q")

    assert chunk.chunk_id == "c_id"
    assert chunk.species_id == "species_bandeng"
    assert chunk.category == "identity"
    assert chunk.content == "id"
    assert chunk.distance == pytest.approx(0.0, abs=1e-12)
    assert chunk.chunk_verification_status == "verified"
    assert chunk.source_verification_status == "verified"
    assert chunk.source_id == "s_bandeng"
    assert chunk.source_title == "Bandeng Encyclopedia"
    assert chunk.source_publisher == "FishBase"
    assert chunk.source_url == "https://fishbase.example/chanos"
    assert chunk.source_type == "fishbase"
    assert chunk.source_reviewed_at == reviewed_at


def test_retrieval_is_deterministic_across_calls(fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    _seed(fake_knowledge_repo, [
        _chunk("c_id", "s_bandeng", "identity", "id", embedding=_emb(9)),
        _chunk("c_pc", "s_bandeng", "physical_characteristics", "pc", embedding=_emb(1)),
        _chunk("c_tt", "s_bandeng", "taste_texture", "tt", embedding=_emb(2)),
        _chunk("c_pm", "s_bandeng", "processing_methods", "pm", embedding=_emb(3)),
        _chunk("c_cu", "s_bandeng", "commercial_uses", "cu", embedding=_emb(4)),
        _chunk("c_sub", "s_bandeng", "substitutes", "sub", embedding=_emb(5)),
    ])
    retriever = VerifiedRetriever(fake_knowledge_repo, fake_embedder)

    first = [chunk.chunk_id for chunk in retriever.retrieve("species_bandeng", "q")]
    second = [chunk.chunk_id for chunk in retriever.retrieve("species_bandeng", "q")]

    assert first == second


def test_six_fixed_questions_recall_every_available_category(fake_knowledge_repo, fake_embedder):
    from apps.main_api.services.retrieval import VerifiedRetriever

    questions = json.loads((FIXTURES_DIR / "retrieval_questions.json").read_text(encoding="utf-8"))
    assert len(questions) == 6
    assert {q["category"] for q in questions} == {
        "identity", "physical_characteristics", "taste_texture",
        "processing_methods", "commercial_uses", "substitutes",
    }
    # One verified chunk per category, all far; six nearer identity fillers
    # would crowd every category out under plain distance order.
    chunks = [
        _chunk(f"c_{q['category']}", "s_bandeng", q["category"], q["question"], embedding=_emb(9))
        for q in questions
    ]
    chunks += [_chunk(f"c_filler_{k}", "s_bandeng", "identity", f"filler {k}", embedding=_emb(k))
               for k in range(1, 7)]
    _seed(fake_knowledge_repo, chunks)
    retriever = VerifiedRetriever(fake_knowledge_repo, fake_embedder)

    for question in questions:
        result = retriever.retrieve("species_bandeng", question["question"])
        categories = [chunk.category for chunk in result]
        assert question["category"] in categories, f"question {question['id']} lost its category"
        assert all(chunk.species_id == "species_bandeng" for chunk in result)
        assert all(chunk.chunk_verification_status == "verified" for chunk in result)
        assert all(chunk.source_verification_status == "verified" for chunk in result)

    assert len(retriever.retrieve("species_bandeng", questions[0]["question"])) == 6


class _BrokenEmbedder:
    """Embedder producing vectors the retriever must reject before any search."""

    model_name = E5_MODEL_NAME

    def __init__(self, vector):
        self._vector = vector

    def embed_query(self, text):
        return list(self._vector)


def test_retrieval_rejects_embedder_with_wrong_model_name(fake_knowledge_repo):
    # Task 6 deferred item: the query vector must come from exactly the
    # intfloat/multilingual-e5-base embedder, checked before embedding.
    from apps.main_api.services.retrieval import VerifiedRetriever

    from tests.main_api.fakes import FakeEmbedder

    wrong = FakeEmbedder(model_name="some/other-model")
    with pytest.raises(ValueError, match="embedder model"):
        VerifiedRetriever(fake_knowledge_repo, wrong).retrieve("species_bandeng", "q")
    assert wrong.query_calls == []
    assert fake_knowledge_repo.search_calls == []


def test_retrieval_rejects_malformed_query_vectors(fake_knowledge_repo):
    from apps.main_api.services.retrieval import VerifiedRetriever

    cases = [
        ([UNIT] * 767, "dimension"),
        ([float("nan")] * 768, "non-finite"),
        ([2.0] * 768, "normalized"),
    ]
    for vector, match in cases:
        retriever = VerifiedRetriever(fake_knowledge_repo, _BrokenEmbedder(vector))
        with pytest.raises(ValueError, match=match):
            retriever.retrieve("species_bandeng", "q")

    assert fake_knowledge_repo.search_calls == []