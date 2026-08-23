"""Task 6: real pgvector retrieval integration.

Proves wrong-species/unverified-chunk/source-unverified/model-mismatch
exclusion and cosine ordering against a real PostgreSQL/pgvector store, using
hand-normalized synthetic vectors; the local E5 model is not required.
"""

import math
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from apps.main_api.contracts import KnowledgeChunkWrite, KnowledgeSourceWrite
from apps.main_api.db.models import KnowledgeChunk, KnowledgeSource
from apps.main_api.db.repositories import SqlKnowledgeRepository, seed_taxonomy
from apps.main_api.services.embeddings import E5_MODEL_NAME
from apps.main_api.services.retrieval import VerifiedRetriever

from tests.main_api.fakes import FakeEmbedder

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_CSV = REPO_ROOT / "artifacts" / "Dataset" / "fishora_dataset" / "metadata" / "taxonomy.csv"

UNIT = 1.0 / (768 ** 0.5)
QUERY_VECTOR = [UNIT] * 768


@pytest.fixture
def session_factory_(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        seed_taxonomy(session, TAXONOMY_CSV)
        session.commit()
    return factory


def _clean_all_knowledge(session):
    """Empty the knowledge tables so insert_verified's global subset check
    never sees leftovers from another test."""
    session.execute(delete(KnowledgeChunk))
    session.execute(delete(KnowledgeSource))
    session.commit()


def _emb(k):
    """Normalized 768-d vector whose cosine distance to QUERY_VECTOR strictly
    increases with k (k=0 is exactly the unit vector)."""
    raw = [UNIT + k] + [UNIT] * 767
    norm = math.sqrt(sum(value * value for value in raw))
    return [value / norm for value in raw]


def _source(source_id, verification_status="verified"):
    return KnowledgeSourceWrite(
        id=source_id, title=f"IT source {source_id}", source_type="test",
        url=f"https://example.test/{source_id}", publisher="it",
        reviewed_at=datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc),
        verification_status=verification_status,
    )


def _chunk(chunk_id, source_id, category, content, embedding, *,
           species_id="species_bandeng", verification_status="verified",
           embedding_model=E5_MODEL_NAME):
    return KnowledgeChunkWrite(
        id=chunk_id, species_id=species_id, source_id=source_id, category=category,
        content=content, embedding=embedding, embedding_model=embedding_model,
        verification_status=verification_status,
    )


def _insert_direct(session_factory_, source, chunk):
    """Insert a source/chunk row bypassing the ingest model checks, for
    wrong-species / unverified / wrong-model rows the store would refuse."""
    with session_factory_() as session:
        session.add(KnowledgeSource(
            id=source.id, title=source.title, source_type=source.source_type,
            url=source.url, publisher=source.publisher, reviewed_at=source.reviewed_at,
            verification_status=source.verification_status))
        session.flush()
        session.add(KnowledgeChunk(
            id=chunk.id, species_id=chunk.species_id, source_id=chunk.source_id,
            category=chunk.category, content=chunk.content, embedding=chunk.embedding,
            embedding_model=chunk.embedding_model, verification_status=chunk.verification_status))
        session.commit()


@pytest.mark.integration
def test_pgvector_search_excludes_wrong_species_and_unverified_rows(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    with session_factory_() as session:
        _clean_all_knowledge(session)

    repo.insert_verified(
        [_source("it_src_v")],
        [_chunk("it_c_near", "it_src_v", "identity", "bandeng identity", _emb(0)),
         _chunk("it_c_mid", "it_src_v", "taste_texture", "bandeng taste", _emb(1))],
    )
    # Rows that would win on pure distance but must never be returned:
    _insert_direct(session_factory_, _source("it_src_tuna"),
                   _chunk("it_c_tuna", "it_src_tuna", "identity", "tuna identity", _emb(0),
                          species_id="species_tuna"))
    _insert_direct(session_factory_, _source("it_src_candidate"),
                   _chunk("it_c_candidate", "it_src_candidate", "identity", "candidate chunk", _emb(0),
                          verification_status="candidate"))
    _insert_direct(session_factory_, _source("it_src_wrong_model"),
                   _chunk("it_c_wrong_model", "it_src_wrong_model", "identity", "other model", _emb(0),
                          embedding_model="some/other-model"))
    _insert_direct(session_factory_, _source("it_src_unverified", verification_status="candidate"),
                   _chunk("it_c_bad_source", "it_src_unverified", "identity",
                          "chunk under unverified source", _emb(0)))

    result = repo.search_verified("species_bandeng", QUERY_VECTOR, E5_MODEL_NAME, limit=10)

    assert [row.chunk_id for row in result] == ["it_c_near", "it_c_mid"]
    assert all(row.species_id == "species_bandeng" for row in result)
    assert all(row.chunk_verification_status == "verified" for row in result)
    assert all(row.source_verification_status == "verified" for row in result)
    with session_factory_() as session:
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_pgvector_search_orders_by_cosine_distance_then_chunk_id(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    with session_factory_() as session:
        _clean_all_knowledge(session)
    # Inserted out of distance order on purpose.
    repo.insert_verified(
        [_source("it_src_order")],
        [_chunk("it_c_far", "it_src_order", "identity", "far", _emb(2)),
         _chunk("it_c_near", "it_src_order", "identity", "near", _emb(0)),
         _chunk("it_c_mid", "it_src_order", "identity", "mid", _emb(1))],
    )

    result = repo.search_verified("species_bandeng", QUERY_VECTOR, E5_MODEL_NAME, limit=10)

    assert [row.chunk_id for row in result] == ["it_c_near", "it_c_mid", "it_c_far"]
    assert result[0].distance < result[1].distance < result[2].distance
    with session_factory_() as session:
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_pgvector_retriever_category_diversity_and_six_chunk_bound(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    with session_factory_() as session:
        _clean_all_knowledge(session)
    repo.insert_verified(
        [_source("it_src_bandeng")],
        [_chunk("it_c_id", "it_src_bandeng", "identity", "id", _emb(9)),
         _chunk("it_c_pc", "it_src_bandeng", "physical_characteristics", "pc", _emb(1)),
         _chunk("it_c_tt", "it_src_bandeng", "taste_texture", "tt", _emb(2)),
         _chunk("it_c_pm", "it_src_bandeng", "processing_methods", "pm", _emb(3)),
         _chunk("it_c_cu", "it_src_bandeng", "commercial_uses", "cu", _emb(4)),
         _chunk("it_c_sub", "it_src_bandeng", "substitutes", "sub", _emb(5))],
    )

    result = VerifiedRetriever(repo, FakeEmbedder()).retrieve(
        "species_bandeng", "kartu pengetahuan bandeng")

    assert [chunk.category for chunk in result] == [
        "identity", "physical_characteristics", "taste_texture",
        "processing_methods", "commercial_uses", "substitutes"]
    assert len(result) == 6
    assert all(chunk.species_id == "species_bandeng" for chunk in result)
    assert all(chunk.chunk_verification_status == "verified" for chunk in result)
    assert all(chunk.source_verification_status == "verified" for chunk in result)
    assert all(chunk.source_id == "it_src_bandeng" for chunk in result)
    with session_factory_() as session:
        _clean_all_knowledge(session)