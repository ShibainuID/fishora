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

    Supports encode/decode like a real tokenizer, including the
    add_special_tokens/skip_special_tokens switches, so chunking and
    ingestion can be tested without downloading the E5 model.
    """

    def __init__(self):
        self._index: dict[str, int] = {}
        self._words: list[str] = []

    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]:
        ids = []
        for word in text.split():
            if word not in self._index:
                self._index[word] = len(self._words)
                self._words.append(word)
            ids.append(self._index[word])
        return ids

    def decode(self, ids: list[int], *, skip_special_tokens: bool = True) -> str:
        return " ".join(self._words[token_id] for token_id in ids)


class SpecialTokenTokenizer:
    """A BERT-style fake whose DEFAULT encode wraps text in [CLS]/[SEP] ids
    and whose DEFAULT decode renders them as text, exactly like a real HF
    tokenizer. Chunking must pass add_special_tokens=False on encode and
    skip_special_tokens=True on decode; otherwise special-token text leaks
    into emitted chunks.
    """

    CLS_ID = 0
    SEP_ID = 1
    CLS = "[CLS]"
    SEP = "[SEP]"

    def __init__(self):
        self._index: dict[str, int] = {self.CLS: self.CLS_ID, self.SEP: self.SEP_ID}
        self._words: list[str] = [self.CLS, self.SEP]

    def encode(self, text: str, *, add_special_tokens: bool = True) -> list[int]:
        ids = []
        for word in text.split():
            if word not in self._index:
                self._index[word] = len(self._words)
                self._words.append(word)
            ids.append(self._index[word])
        if add_special_tokens:
            return [self.CLS_ID] + ids + [self.SEP_ID]
        return ids

    def decode(self, ids: list[int], *, skip_special_tokens: bool = False) -> str:
        words = [
            self._words[token_id]
            for token_id in ids
            if not (skip_special_tokens and token_id in (self.CLS_ID, self.SEP_ID))
        ]
        return " ".join(words)


class FakeEmbedder:
    """Deterministic 768-dimensional L2-normalized embedder with a whitespace
    tokenizer. Knobs let tests simulate contract violations: wrong dimension,
    unnormalized/non-finite vectors, short batches, or a different model."""

    model_name = "intfloat/multilingual-e5-base"
    dimension = 768

    def __init__(
        self,
        *,
        dimension: int = 768,
        normalized: bool = True,
        non_finite: bool = False,
        short_batch: bool = False,
        model_name: str = "intfloat/multilingual-e5-base",
        tokenizer: WhitespaceTokenizer | None = None,
    ):
        self.dimension = dimension
        self.normalized = normalized
        self.non_finite = non_finite
        self.short_batch = short_batch
        self.model_name = model_name
        self.tokenizer = tokenizer or WhitespaceTokenizer()
        self.passage_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    def _vector(self, index: int) -> list[float]:
        if not self.normalized:
            return [0.001 * (index + 1)] * self.dimension
        unit = 1.0 / (self.dimension ** 0.5)
        vector = [unit] * self.dimension
        if self.non_finite:
            vector[0] = float("nan")
        return vector

    def embed_passages(self, texts):
        self.passage_calls.append(list(texts))
        count = len(texts) - 1 if self.short_batch and texts else len(texts)
        return [self._vector(index) for index in range(count)]

    def embed_query(self, text):
        self.query_calls.append(text)
        return self._vector(0)


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