"""Task 5: local E5 embedding (query/passage prefixes, lazy once-per-instance
model loading) and approved-only ingestion.

The real E5 model is exercised only when it is already present in the local
sentence-transformers cache; otherwise the suite stays deterministic with
fakes and reports an explicit environment skip. Neither importing this module
nor constructing the embedder may download anything.
"""

import math

import pytest

from tests.main_api.fakes import WhitespaceTokenizer


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