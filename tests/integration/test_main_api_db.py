import pytest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from apps.main_api.contracts import KnowledgeChunkWrite, KnowledgeSourceWrite
from apps.main_api.db.models import KnowledgeChunk, KnowledgeSource, Prediction
from apps.main_api.db.repositories import SqlKnowledgeRepository, seed_taxonomy
from apps.main_api.db.sql_repositories import SqlPredictionRepository, SqlSpeciesRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_CSV = REPO_ROOT / "artifacts" / "Dataset" / "fishora_dataset" / "metadata" / "taxonomy.csv"


@pytest.fixture
def session_factory_(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        seed_taxonomy(session, TAXONOMY_CSV)
        session.commit()
    return factory


@pytest.mark.integration
def test_sql_species_repository_maps_label_and_id(session_factory_):
    repo = SqlSpeciesRepository(session_factory_)
    tuna = repo.get_by_normalized_label("tuna")
    assert tuna is not None
    assert tuna.id == "species_tuna"
    assert repo.get_by_id("species_tuna").normalized_label == "tuna"
    assert repo.get_by_normalized_label("shark") is None
    assert repo.get_by_id("species_shark") is None


@pytest.mark.integration
def test_sql_prediction_repository_create_get_verify_roundtrip(session_factory_):
    repo = SqlPredictionRepository(session_factory_)
    prediction_id = "it_pred_tuna_1"
    with session_factory_() as session:
        session.execute(delete(Prediction).where(Prediction.id == prediction_id))
        session.commit()

    created = repo.create(
        prediction_id,
        "images/it_pred_tuna_1.jpg",
        "species_tuna",
        0.71,
        [
            {"species_id": "species_tuna", "normalized_label": "tuna", "confidence": 0.71},
            {"species_id": "species_tenggiri", "normalized_label": "tenggiri", "confidence": 0.18},
        ],
        "test-model-1",
    )
    assert created.verification_status == "pending"
    assert created.verified_species_id is None

    fetched = repo.get(prediction_id)
    assert fetched is not None
    assert fetched.predicted_species_id == "species_tuna"
    assert fetched.confidence == 0.71
    assert fetched.top_candidates[0]["normalized_label"] == "tuna"

    confirmed = repo.verify(prediction_id, "species_tuna", "confirmed")
    assert confirmed.verification_status == "confirmed"
    assert confirmed.verified_species_id == "species_tuna"
    assert confirmed.predicted_species_id == "species_tuna"  # predicted identity immutable

    corrected = repo.verify(prediction_id, "species_gembolo", "corrected")
    assert corrected.verification_status == "corrected"
    assert corrected.verified_species_id == "species_gembolo"
    assert corrected.predicted_species_id == "species_tuna"

    assert repo.get(prediction_id).verification_status == "corrected"  # persisted state via get()
    assert repo.get("it_pred_missing") is None

    with session_factory_() as session:
        session.delete(session.get(Prediction, prediction_id))
        session.commit()



def _clean_all_knowledge(session):
    """Empty the knowledge tables so insert_verified's global subset check
    never sees leftovers from another test."""
    session.execute(delete(KnowledgeChunk))
    session.execute(delete(KnowledgeSource))
    session.commit()


def _source(source_id, title="IT source"):
    return KnowledgeSourceWrite(id=source_id, title=title, source_type="test",
                                url="https://example.test", publisher="it",
                                reviewed_at=datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc),
                                verification_status="verified")


def _chunk(chunk_id, source_id, content, model="intfloat/multilingual-e5-base", fill=0.1):
    return KnowledgeChunkWrite(id=chunk_id, species_id="species_bandeng", source_id=source_id,
                               category="identity", content=content, embedding=[fill] * 768,
                               embedding_model=model, verification_status="verified")


@pytest.mark.integration
def test_sql_knowledge_repository_inserts_verified_rows_transactionally(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    source_id = "it_source_bandeng_1"
    with session_factory_() as session:
        _clean_all_knowledge(session)

    count = repo.insert_verified(
        [_source(source_id)],
        [_chunk("it_chunk_bandeng_1", source_id, "IT chunk one"),
         _chunk("it_chunk_bandeng_2", source_id, "IT chunk two", fill=0.2)],
    )
    assert count == 2
    with session_factory_() as session:
        source = session.get(KnowledgeSource, source_id)
        assert source is not None and source.verification_status == "verified"
        assert source.reviewed_at == datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc)
        rows = session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)).all()
        assert {row.id for row in rows} == {"it_chunk_bandeng_1", "it_chunk_bandeng_2"}
        assert all(row.embedding_model == "intfloat/multilingual-e5-base" for row in rows)
        assert all(len(row.embedding) == 768 for row in rows)
        assert all(row.verification_status == "verified" for row in rows)

    # Upsert path: the same source id updates; chunks are overwritten in
    # place by an additive full manifest.
    repo.insert_verified(
        [_source(source_id, title="IT source v2")],
        [_chunk("it_chunk_bandeng_1", source_id, "IT chunk one"),
         _chunk("it_chunk_bandeng_2", source_id, "IT chunk two", fill=0.2),
         _chunk("it_chunk_bandeng_3", source_id, "IT chunk three", fill=0.3)],
    )
    with session_factory_() as session:
        assert session.get(KnowledgeSource, source_id).title == "IT source v2"
        assert len(session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)).all()) == 3
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_sql_knowledge_repository_rolls_back_all_rows_on_write_failure(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    source_id = "it_source_rollback_1"
    with session_factory_() as session:
        _clean_all_knowledge(session)

    with pytest.raises(Exception, match="dimension"):
        repo.insert_verified(
            [_source(source_id)],
            [KnowledgeChunkWrite(id="it_chunk_rollback_1", species_id="species_bandeng", source_id=source_id,
                                 category="identity", content="bad vector", embedding=[0.1] * 767,
                                 embedding_model="intfloat/multilingual-e5-base", verification_status="verified")],
        )
    with session_factory_() as session:
        assert session.get(KnowledgeSource, source_id) is None, "source must roll back with the failed chunk"
        assert session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)).all() == []


@pytest.mark.integration
def test_sql_knowledge_repository_rejects_mixed_embedding_models(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    with session_factory_() as session:
        _clean_all_knowledge(session)
    assert repo.embedding_models_in_store() == set()
    repo.insert_verified(
        [_source("it_source_models_1")],
        [_chunk("it_chunk_models_1", "it_source_models_1", "a")],
    )
    assert repo.embedding_models_in_store() == {"intfloat/multilingual-e5-base"}
    with pytest.raises(ValueError, match="embedding model"):
        repo.insert_verified(
            [_source("it_source_models_2")],
            [_chunk("it_chunk_models_2", "it_source_models_2", "b", model="some/other-model")],
        )
    assert repo.embedding_models_in_store() == {"intfloat/multilingual-e5-base"}
    with session_factory_() as session:
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_sql_knowledge_repository_reingest_is_idempotent(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    source_id = "it_source_reingest_1"
    with session_factory_() as session:
        _clean_all_knowledge(session)
    payload = ([_source(source_id)], [_chunk("it_chunk_reingest_1", source_id, "v1"),
                                      _chunk("it_chunk_reingest_2", source_id, "v2")])
    assert repo.insert_verified(*payload) == 2
    assert repo.insert_verified(*payload) == 2  # identical re-ingest: no error, no duplicates
    with session_factory_() as session:
        rows = session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)).all()
        assert len(rows) == 2
        assert {row.content for row in rows} == {"v1", "v2"}
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_sql_knowledge_repository_rejects_stale_partial_manifest(session_factory_):
    repo = SqlKnowledgeRepository(session_factory_)
    with session_factory_() as session:
        _clean_all_knowledge(session)
    repo.insert_verified(
        [_source("it_source_stale_1")],
        [_chunk("it_chunk_stale_1", "it_source_stale_1", "a"),
         _chunk("it_chunk_stale_2", "it_source_stale_1", "b")],
    )
    with pytest.raises(ValueError, match="subset"):
        repo.insert_verified(
            [_source("it_source_stale_1")],
            [_chunk("it_chunk_stale_1", "it_source_stale_1", "a")],
        )
    with session_factory_() as session:
        rows = session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id == "it_source_stale_1")).all()
        assert len(rows) == 2, "rejected partial manifest must not remove or update rows"
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_sql_knowledge_repository_serializes_concurrent_mixed_model_ingests(session_factory_):
    """Two ingests racing with different models: the advisory xact lock
    serializes them, so exactly one succeeds and the other is refused."""
    import threading

    with session_factory_() as session:
        _clean_all_knowledge(session)
    results: list[str] = []
    barrier = threading.Barrier(2)

    def run(source_id, model):
        repo = SqlKnowledgeRepository(session_factory_)
        try:
            barrier.wait()
            repo.insert_verified([_source(source_id)], [_chunk(f"{source_id}_c", source_id, "x", model=model)])
            results.append("ok")
        except ValueError as error:
            results.append(f"err:{error}")

    threads = [
        threading.Thread(target=run, args=("it_conc_a", "intfloat/multilingual-e5-base")),
        threading.Thread(target=run, args=("it_conc_b", "some/other-model")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(results) == 2
    assert sum(result == "ok" for result in results) == 1
    assert sum(result.startswith("err:") for result in results) == 1
    assert any("embedding model" in result for result in results if result.startswith("err:"))
    with session_factory_() as session:
        _clean_all_knowledge(session)


@pytest.mark.integration
def test_cli_ingest_persists_verified_chunks_after_commit(tmp_path, session_factory_, monkeypatch, capsys):
    """Real end-to-end CLI ingest; explicit environment skip without the E5 model.

    The operator CLI embeds with the real local model, so this test runs only
    when sentence-transformers and the cached E5 model are actually present.
    """
    pytest.importorskip("sentence_transformers", reason="sentence-transformers is not installed")
    from sentence_transformers import SentenceTransformer

    try:
        SentenceTransformer("intfloat/multilingual-e5-base", local_files_only=True)
    except Exception as error:
        pytest.skip(f"intfloat/multilingual-e5-base is not cached locally: {error}")

    from tests.main_api.test_corpus import approve_test_corpus

    approved_dir, manifest_path = approve_test_corpus(tmp_path, approval_key="cli-it-key")
    with session_factory_() as session:
        _clean_all_knowledge(session)

    from scripts.corpus_pipeline import main

    monkeypatch.setenv("FISHORA_CORPUS_APPROVAL_KEY", "cli-it-key")
    from apps.main_api.config import MainSettings

    monkeypatch.setenv("FISHORA_DATABASE_URL", MainSettings().database_url)
    result = main(["ingest", "--approved-dir", str(approved_dir),
                   "--approval-manifest", str(manifest_path),
                   "--embedding-model", "intfloat/multilingual-e5-base"])
    assert result == 2
    assert "ingested 2 verified chunks" in capsys.readouterr().out
    with session_factory_() as session:
        sources = session.scalars(select(KnowledgeSource).where(KnowledgeSource.id.in_(
            ["fishbase_chanos_chanos", "marinade_4962"]))).all()
        assert {source.id for source in sources} == {"fishbase_chanos_chanos", "marinade_4962"}
        assert all(source.verification_status == "verified" for source in sources)
        chunks = session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source_id.in_(
            ["fishbase_chanos_chanos", "marinade_4962"]))).all()
        assert {chunk.id for chunk in chunks} == {"chunk_bandeng_identity_001", "chunk_bandeng_processing_001"}
        assert all(chunk.embedding_model == "intfloat/multilingual-e5-base" for chunk in chunks)
        assert all(len(chunk.embedding) == 768 for chunk in chunks)
        _clean_all_knowledge(session)
