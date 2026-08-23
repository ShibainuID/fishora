"""Local E5 embeddings for Fishora knowledge retrieval and ingestion.

Vectors come from the local ``sentence-transformers`` model cache; no remote
embedding endpoint is ever called. The model is loaded lazily on the first
embed/tokenizer access and kept for the lifetime of the embedder instance, so
importing this module or constructing the embedder downloads nothing. The
dependency is a production install; the import is guarded so unrelated
imports and tests stay importable without the (torch-heavy) library.
"""

from __future__ import annotations

from typing import Sequence

try:  # production dependency; absent only in minimal test environments
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - exercised only in minimal environments
    SentenceTransformer = None  # type: ignore[assignment]

E5_MODEL_NAME = "intfloat/multilingual-e5-base"
E5_DIMENSION = 768


class E5QueryPassageFormatter:
    """E5 prompting: queries carry ``query: `` and passages ``passage: ``."""

    def query(self, text: str) -> str:
        return f"query: {text}"

    def passage(self, text: str) -> str:
        return f"passage: {text}"


class LocalE5Embedder:
    """768-dimensional normalized E5 vectors from the local model cache."""

    model_name = E5_MODEL_NAME
    dimension = E5_DIMENSION
    _formatter = E5QueryPassageFormatter()

    def __init__(self, model_name: str = E5_MODEL_NAME, device: str | None = None):
        if model_name != E5_MODEL_NAME:
            raise ValueError("Fishora ingestion and query embeddings require intfloat/multilingual-e5-base")
        self._device = device
        self._model = None  # loaded lazily on first use, once per instance

    def _load(self):
        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers is not installed; install the fishora production dependencies"
            )
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self._device)
        return self._model

    @property
    def tokenizer(self):
        """Real tokenizer (encode/decode) of the loaded model, for chunking."""
        return self._load().tokenizer

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        values = self._load().encode(
            [self._formatter.passage(text) for text in texts],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [row.astype("float32").tolist() for row in values]

    def embed_query(self, text: str) -> list[float]:
        value = self._load().encode(
            [self._formatter.query(text)],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        return value.astype("float32").tolist()