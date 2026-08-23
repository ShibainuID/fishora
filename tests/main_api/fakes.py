from apps.main_api.contracts import PredictionRecord, SpeciesRecord


class FakeCVClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def predict(self, image_bytes, *, filename, content_type):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class FakeSpeciesRepository:
    def __init__(self, species: list[SpeciesRecord]):
        self._by_label = {s.normalized_label: s for s in species}
        self._by_id = {s.id: s for s in species}

    def get_by_normalized_label(self, label):
        return self._by_label.get(label)

    def get_by_id(self, species_id):
        return self._by_id.get(species_id)


class FakePredictionRepository:
    def __init__(self, records: dict[str, PredictionRecord] | None = None):
        self._records = dict(records or {})

    def create(self, prediction_id, image_reference, predicted_species_id, confidence, top_candidates, model_version):
        record = PredictionRecord(
            id=prediction_id,
            image_reference=image_reference,
            predicted_species_id=predicted_species_id,
            confidence=confidence,
            top_candidates=top_candidates,
            model_version=model_version,
            verification_status="pending",
        )
        self._records[prediction_id] = record
        return record

    def get(self, prediction_id):
        return self._records.get(prediction_id)

    def verify(self, prediction_id, verified_species_id, verification_status):
        record = self._records[prediction_id]  # service checks existence first
        record.verified_species_id = verified_species_id
        record.verification_status = verification_status
        return record

    def all(self):
        return list(self._records.values())


class FakeImageStore:
    def __init__(self):
        self.saved: list[str] = []
        self.deleted: list[str] = []

    def save(self, prediction_id, image_bytes, content_type):
        reference = f"images/{prediction_id}.jpg"
        self.saved.append(reference)
        return reference

    def delete(self, image_reference):
        self.deleted.append(image_reference)
        if image_reference in self.saved:
            self.saved.remove(image_reference)


class WhitespaceTokenizer:
    """Deterministic tokenizer: one token per whitespace-separated word.

    Supports encode/decode like a real tokenizer, so chunking and ingestion
    can be tested without downloading the E5 model.
    """

    def __init__(self):
        self._index: dict[str, int] = {}
        self._words: list[str] = []

    def encode(self, text: str) -> list[int]:
        ids = []
        for word in text.split():
            if word not in self._index:
                self._index[word] = len(self._words)
                self._words.append(word)
            ids.append(self._index[word])
        return ids

    def decode(self, ids: list[int]) -> str:
        return " ".join(self._words[token_id] for token_id in ids)


class FakeEmbedder:
    """Deterministic 768-dimensional embedder with a whitespace tokenizer."""

    model_name = "intfloat/multilingual-e5-base"
    dimension = 768

    def __init__(self, dimension: int = 768, tokenizer: WhitespaceTokenizer | None = None):
        self.dimension = dimension
        self.tokenizer = tokenizer or WhitespaceTokenizer()
        self.passage_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    def embed_passages(self, texts):
        self.passage_calls.append(list(texts))
        return [[(index + 1) * 0.001] * self.dimension for index in range(len(texts))]

    def embed_query(self, text):
        self.query_calls.append(text)
        return [0.5] * self.dimension


class FakeKnowledgeRepository:
    """In-memory knowledge store; records every verified write."""

    def __init__(self, embedding_models: set[str] | None = None):
        self._embedding_models = set(embedding_models or [])
        self.sources: list = []
        self.chunks: list = []

    def embedding_models_in_store(self):
        return set(self._embedding_models)

    def insert_verified(self, sources, chunks):
        self.sources.extend(sources)
        self.chunks.extend(chunks)
        return len(chunks)