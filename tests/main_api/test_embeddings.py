"""Task 5: local E5 embedding (query/passage prefixes, lazy once-per-instance
model loading) and approved-only ingestion.

The real E5 model is exercised only when it is already present in the local
sentence-transformers cache; otherwise the suite stays deterministic with
fakes and reports an explicit environment skip. Neither importing this module
nor constructing the embedder may download anything.
"""

import math

import pytest

from tests.main_api.fakes import FakeEmbedder, FakeKnowledgeRepository, WhitespaceTokenizer


def test_e5_embedder_uses_distinct_shared_prefixes_and_dimension(monkeypatch):
    from apps.main_api.services.embeddings import E5QueryPassageFormatter

    formatter = E5QueryPassageFormatter()
    assert formatter.query("ciri ikan") == "query: ciri ikan"
    assert formatter.passage("Ciri ikan") == "passage: Ciri ikan"


def test_local_e5_embedder_rejects_other_models():
    from apps.main_api.services.embeddings import LocalE5Embedder

    with pytest.raises(ValueError, match="intfloat/multilingual-e5-base"):
        LocalE5Embedder(model_name="some/other-model")


def test_local_e5_embedder_construction_is_lazy(monkeypatch):
    """Constructing the embedder never loads (or downloads) the model."""
    from apps.main_api.services.embeddings import LocalE5Embedder

    def boom(*args, **kwargs):
        raise AssertionError("model must not load at construction time")

    monkeypatch.setattr("apps.main_api.services.embeddings.SentenceTransformer", boom)
    LocalE5Embedder()


def test_local_e5_embedder_loads_model_once_per_instance(monkeypatch):
    """The model loads on first use, exactly once, and prefixes are applied."""
    import numpy as np

    from apps.main_api.services.embeddings import LocalE5Embedder

    class FakeSentenceTransformer:
        instances = 0

        def __init__(self, *args, **kwargs):
            type(self).instances += 1
            self.tokenizer = WhitespaceTokenizer()

        def encode(self, sentences, **kwargs):
            return [np.full(768, 0.01 * index, dtype="float32") for index in range(len(sentences))]

    fake = FakeSentenceTransformer
    monkeypatch.setattr("apps.main_api.services.embeddings.SentenceTransformer", fake)
    embedder = LocalE5Embedder()
    passages = embedder.embed_passages(["Ciri ikan", "Bandeng presto"])
    query = embedder.embed_query("ciri ikan")
    assert fake.instances == 1
    assert len(passages) == 2
    assert all(len(vector) == 768 for vector in passages)
    assert len(query) == 768
    assert embedder.embed_passages(["lagi"]) is not None  # still the same loaded instance


def test_local_e5_embedder_prefixes_and_float32_output(monkeypatch):
    import numpy as np

    from apps.main_api.services.embeddings import LocalE5Embedder

    class FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            self.tokenizer = WhitespaceTokenizer()
            self.sentences = []

        def encode(self, sentences, **kwargs):
            self.sentences.extend(sentences)
            return [np.full(768, 0.01, dtype="float32") for _ in sentences]

    fake = FakeSentenceTransformer()
    monkeypatch.setattr("apps.main_api.services.embeddings.SentenceTransformer", lambda *a, **k: fake)
    embedder = LocalE5Embedder()
    embedder.embed_passages(["Ciri ikan"])
    embedder.embed_query("ciri ikan")
    assert fake.sentences == ["passage: Ciri ikan", "query: ciri ikan"]


def test_real_e5_model_dimension_and_normalization_if_cached():
    """Genuine environment skip (not a passing fake) when E5 is not cached locally."""
    pytest.importorskip("sentence_transformers", reason="sentence-transformers is not installed")
    from sentence_transformers import SentenceTransformer

    from apps.main_api.services.embeddings import E5_MODEL_NAME, LocalE5Embedder

    try:
        SentenceTransformer(E5_MODEL_NAME, local_files_only=True)
    except Exception as error:
        pytest.skip(f"intfloat/multilingual-e5-base is not in the local sentence-transformers cache: {error}")

    embedder = LocalE5Embedder()
    for vector in [*embedder.embed_passages(["Ciri ikan bandeng"]), embedder.embed_query("ciri ikan bandeng")]:
        assert len(vector) == 768
        norm = math.sqrt(sum(value * value for value in vector))
        assert math.isclose(norm, 1.0, rel_tol=1e-3), "E5 vectors must be normalized"


# --- approved-only ingestion ----------------------------------------------


def _ingest(approved_dir, approval_manifest, species_repo, knowledge_repo, embedder, approval_key="test-key"):
    from apps.main_api.services.ingestion import ingest_approved_corpus

    return ingest_approved_corpus(
        approved_dir, approval_manifest, species_repo, knowledge_repo, embedder, approval_key
    )


def test_ingestion_rejects_unapproved_directory(unapproved_dir, approval_manifest, species_repo, fake_knowledge_repo, fake_embedder):
    with pytest.raises(ValueError, match="candidate-only"):
        _ingest(unapproved_dir, approval_manifest, species_repo, fake_knowledge_repo, fake_embedder)


def test_ingestion_rejects_missing_approval_manifest(tmp_path, unapproved_dir, species_repo, fake_knowledge_repo, fake_embedder):
    with pytest.raises(FileNotFoundError, match="approval manifest"):
        _ingest(unapproved_dir, tmp_path / "missing.json", species_repo, fake_knowledge_repo, fake_embedder)


def test_ingestion_requires_approval_hmac_key(approved_corpus, species_repo, fake_knowledge_repo, fake_embedder):
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="approval key"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, fake_embedder, approval_key=None)


def test_ingestion_rejects_wrong_approval_key(approved_corpus, species_repo, fake_knowledge_repo, fake_embedder):
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="signature"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, fake_embedder, approval_key="wrong-key")


def test_ingestion_rejects_unknown_species_label(approved_corpus, fake_knowledge_repo, fake_embedder):
    from tests.main_api.fakes import FakeSpeciesRepository

    approved_dir, manifest = approved_corpus
    empty_repo = FakeSpeciesRepository([])
    with pytest.raises(ValueError, match="species"):
        _ingest(approved_dir, manifest, empty_repo, fake_knowledge_repo, fake_embedder)


def test_ingestion_refuses_store_with_another_embedding_model(approved_corpus, species_repo, fake_embedder):
    approved_dir, manifest = approved_corpus
    mixed_repo = FakeKnowledgeRepository(embedding_models={"some/other-model"})
    with pytest.raises(ValueError, match="embedding model"):
        _ingest(approved_dir, manifest, species_repo, mixed_repo, fake_embedder)
    assert mixed_repo.sources == [] and mixed_repo.chunks == []


def test_ingestion_rejects_wrong_embedding_dimension(approved_corpus, species_repo, fake_knowledge_repo):
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="768"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, FakeEmbedder(dimension=767))
    assert fake_knowledge_repo.sources == [] and fake_knowledge_repo.chunks == []


def test_ingestion_requires_exact_e5_model_name(approved_corpus, species_repo, fake_knowledge_repo):
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="intfloat/multilingual-e5-base"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo,
                FakeEmbedder(model_name="some/other-model"))
    assert fake_knowledge_repo.sources == [] and fake_knowledge_repo.chunks == []


def test_ingestion_rejects_embedding_batch_length_mismatch(approved_corpus, species_repo, fake_knowledge_repo):
    """A short embedder batch must fail loudly, never silently zip-truncate."""
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="vectors"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, FakeEmbedder(short_batch=True))
    assert fake_knowledge_repo.sources == [] and fake_knowledge_repo.chunks == []


def test_ingestion_rejects_unnormalized_vectors(approved_corpus, species_repo, fake_knowledge_repo):
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="normalized"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, FakeEmbedder(normalized=False))
    assert fake_knowledge_repo.sources == [] and fake_knowledge_repo.chunks == []


def test_ingestion_rejects_non_finite_vectors(approved_corpus, species_repo, fake_knowledge_repo):
    approved_dir, manifest = approved_corpus
    with pytest.raises(ValueError, match="finite"):
        _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, FakeEmbedder(non_finite=True))
    assert fake_knowledge_repo.sources == [] and fake_knowledge_repo.chunks == []


def test_ingestion_persists_verified_chunks_with_e5_embeddings(approved_corpus, species_repo, fake_knowledge_repo, fake_embedder):
    approved_dir, manifest = approved_corpus
    count = _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, fake_embedder)
    assert count == 2
    assert {source.id for source in fake_knowledge_repo.sources} == {
        "fishbase_chanos_chanos", "marinade_4962",
    }
    assert all(source.verification_status == "verified" for source in fake_knowledge_repo.sources)
    assert all(source.reviewed_at is not None for source in fake_knowledge_repo.sources)
    assert [chunk.id for chunk in fake_knowledge_repo.chunks] == [
        "chunk_bandeng_identity_001", "chunk_bandeng_processing_001",
    ]
    assert all(chunk.species_id == "species_bandeng" for chunk in fake_knowledge_repo.chunks)
    assert all(chunk.verification_status == "verified" for chunk in fake_knowledge_repo.chunks)
    assert all(len(chunk.embedding) == 768 for chunk in fake_knowledge_repo.chunks)
    assert all(chunk.embedding_model == "intfloat/multilingual-e5-base" for chunk in fake_knowledge_repo.chunks)


def test_ingestion_reingest_is_idempotent(approved_corpus, species_repo, fake_knowledge_repo, fake_embedder):
    approved_dir, manifest = approved_corpus
    first = _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, fake_embedder)
    second = _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, fake_embedder)
    assert first == second == 2
    assert len(fake_knowledge_repo.chunks) == 2, "identical re-ingest must upsert, not duplicate"
    assert len(fake_knowledge_repo.sources) == 2


def test_ingestion_accepts_additive_full_manifests(tmp_path, species_repo, fake_knowledge_repo, fake_embedder):
    from tests.main_api.test_corpus import approve_test_corpus

    small_dir, small_manifest = approve_test_corpus(tmp_path / "small", include_processing=False)
    assert _ingest(small_dir, small_manifest, species_repo, fake_knowledge_repo, fake_embedder) == 1
    full_dir, full_manifest = approve_test_corpus(tmp_path / "full")
    assert _ingest(full_dir, full_manifest, species_repo, fake_knowledge_repo, fake_embedder) == 2
    assert [chunk.id for chunk in fake_knowledge_repo.chunks] == [
        "chunk_bandeng_identity_001", "chunk_bandeng_processing_001",
    ]


def test_ingestion_rejects_stale_partial_manifest(tmp_path, species_repo, fake_knowledge_repo, fake_embedder):
    from tests.main_api.test_corpus import approve_test_corpus

    full_dir, full_manifest = approve_test_corpus(tmp_path / "full")
    _ingest(full_dir, full_manifest, species_repo, fake_knowledge_repo, fake_embedder)
    small_dir, small_manifest = approve_test_corpus(tmp_path / "small", include_processing=False)
    with pytest.raises(ValueError, match="subset"):
        _ingest(small_dir, small_manifest, species_repo, fake_knowledge_repo, fake_embedder)
    assert len(fake_knowledge_repo.chunks) == 2, "rejected manifest must not change the store"


def test_ingestion_splits_long_approved_sections(approved_corpus_long, species_repo, fake_knowledge_repo, fake_embedder):
    approved_dir, manifest = approved_corpus_long
    count = _ingest(approved_dir, manifest, species_repo, fake_knowledge_repo, fake_embedder)
    assert count == 4  # identity stays whole; 1620-token processing section splits into 3
    split_ids = [chunk.id for chunk in fake_knowledge_repo.chunks
                 if chunk.id.startswith("chunk_bandeng_processing_001")]
    split_chunks = [chunk for chunk in fake_knowledge_repo.chunks if chunk.id.startswith("chunk_bandeng_processing_001")]
    assert split_ids == ["chunk_bandeng_processing_001", "chunk_bandeng_processing_001__2",
                         "chunk_bandeng_processing_001__3"]
    tokenizer = WhitespaceTokenizer()
    for chunk in fake_knowledge_repo.chunks:
        assert chunk.category in {"identity", "processing_methods"}
        assert chunk.species_id == "species_bandeng"
        assert len(tokenizer.encode(chunk.content)) <= 600
    for previous, following in zip(split_chunks, split_chunks[1:]):
        assert tokenizer.encode(following.content)[:50] == tokenizer.encode(previous.content)[-50:]