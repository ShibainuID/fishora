import math

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from apps.main_api.contracts import (
    BidRecord,
    BuyerPreferenceRecord,
    LandingPointRecord,
    LotRecord,
    PredictionRecord,
    RetrievedChunk,
    SpeciesRecord,
)
from apps.main_api.errors import BidOutbid, LotClosed, LotNotAllocatable, LotNotFound
from apps.main_api.services.embeddings import E5_MODEL_NAME


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return 1.0 - dot / (left_norm * right_norm)


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


class FakeLotRepository:
    """In-memory lots used by publication and bidding tests."""

    def __init__(self, lots: dict[str, LotRecord] | None = None):
        self._lots = dict(lots or {})
        self._bids: dict[str, list[BidRecord]] = {}

    def create(self, lot: LotRecord) -> LotRecord:
        self._lots[lot.id] = lot
        return lot

    def get(self, lot_id: str) -> LotRecord | None:
        return self._lots.get(lot_id)

    def get_by_slug(self, public_slug: str) -> LotRecord | None:
        return next((lot for lot in self._lots.values() if lot.public_slug == public_slug), None)

    def all(self) -> list[LotRecord]:
        return list(self._lots.values())

    def highest(self, lot_id: str) -> Decimal | None:
        bids = self._bids.get(lot_id) or []
        if not bids:
            return None
        return max(bid.amount_per_kg for bid in bids)

    def list_bids(self, lot_id: str) -> list[BidRecord]:
        bids = list(self._bids.get(lot_id) or [])
        bids.sort(key=lambda bid: bid.created_at, reverse=True)
        return bids

    def place_bid(
        self,
        lot_id: str,
        buyer_id: str,
        amount_per_kg: Decimal,
        now: datetime | None = None,
    ) -> BidRecord:
        lot = self.get(lot_id)
        if lot is None:
            raise LotNotFound(lot_id)
        clock = now or datetime.now(timezone.utc)
        if lot.status != "active" or clock >= lot.auction_ends_at:
            if lot.status == "active":
                lot.status = "closed"
            raise LotClosed(lot_id)
        highest = self.highest(lot_id)
        if highest is not None:
            if amount_per_kg <= highest:
                raise BidOutbid(highest)
        elif amount_per_kg < lot.starting_price_per_kg:
            raise BidOutbid(lot.starting_price_per_kg)
        bid = BidRecord(
            id=uuid4().hex,
            lot_id=lot_id,
            buyer_id=buyer_id,
            amount_per_kg=amount_per_kg,
            created_at=clock,
        )
        self._bids.setdefault(lot_id, []).append(bid)
        return bid

    def allocate(self, lot_id: str, now: datetime | None = None) -> LotRecord:
        lot = self.get(lot_id)
        if lot is None:
            raise LotNotFound(lot_id)
        clock = now or datetime.now(timezone.utc)
        if lot.status == "allocated":
            return lot
        if lot.status == "active" and clock >= lot.auction_ends_at:
            lot.status = "closed"
        if lot.status != "closed":
            raise LotNotAllocatable(lot_id, "allocation requires a closed lot")
        bids = self._bids.get(lot_id) or []
        if not bids:
            raise LotNotAllocatable(lot_id, "closed lot has no bids")
        winner = max(bids, key=lambda bid: (bid.amount_per_kg, -bid.created_at.timestamp()))
        lot.allocated_buyer_id = winner.buyer_id
        lot.status = "allocated"
        return lot


class FakeLandingPointRepository:
    def __init__(self, points: list[LandingPointRecord] | None = None):
        self._by_id = {point.id: point for point in (points or [])}

    def get(self, landing_point_id: str) -> LandingPointRecord | None:
        return self._by_id.get(landing_point_id)

    def all(self) -> list[LandingPointRecord]:
        return list(self._by_id.values())


class FakePreferenceRepository:
    def __init__(self, rows: dict[str, BuyerPreferenceRecord] | None = None):
        self._rows = dict(rows or {})

    def get(self, buyer_id: str) -> BuyerPreferenceRecord | None:
        return self._rows.get(buyer_id)

    def upsert(self, record: BuyerPreferenceRecord) -> BuyerPreferenceRecord:
        self._rows[record.buyer_id] = record
        return record


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


class FakeRetriever:
    """Records every retrieval key; the knowledge endpoint may only ever pass
    the stored verified species id."""

    def __init__(self, results=None):
        self.results = list(results or [])
        self.species_ids: list[str] = []
        self.queries: list[str] = []

    def retrieve(self, species_id, query):
        self.species_ids.append(species_id)
        self.queries.append(query)
        return list(self.results)


class FakeOpenCodeClient:
    """Stands in for OpenCodeGoClient: returns canned JSON or raises a canned
    error, and counts calls so the no-LLM empty-evidence path is provable."""

    def __init__(self, response="{}", error=None):
        self.response = response
        self.error = error
        self.calls = 0
        self.seen: list[tuple] = []

    def generate(self, system_prompt, evidence, species):
        self.calls += 1
        self.seen.append((system_prompt, evidence, species))
        if self.error is not None:
            raise self.error
        return self.response


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
    """In-memory knowledge store enforcing the insert_verified contract:
    rejects mixed embedding models and stale partial manifests (existing
    verified chunks must be a subset of the incoming approved chunks), and
    upserts sources/chunks so re-ingest is idempotent."""

    def __init__(self, embedding_models: set[str] | None = None):
        self._embedding_models = set(embedding_models or [])
        self._chunks_by_id: dict = {}
        self.sources: list = []
        self.chunks: list = []
        self.search_calls: list[tuple] = []

    def embedding_models_in_store(self):
        return set(self._embedding_models)

    def insert_verified(self, sources, chunks):
        incoming_models = {chunk.embedding_model for chunk in chunks}
        if incoming_models != {E5_MODEL_NAME}:
            raise ValueError(
                "incoming chunk batch must use exactly one embedding model "
                f"({E5_MODEL_NAME}), got {sorted(incoming_models)}"
            )
        if self._embedding_models and self._embedding_models != {E5_MODEL_NAME}:
            raise ValueError(
                "knowledge store already contains another embedding model "
                f"({sorted(self._embedding_models)}); refusing to mix with {E5_MODEL_NAME}"
            )
        existing = set(self._chunks_by_id)
        incoming = {chunk.id for chunk in chunks}
        if not existing <= incoming:
            raise ValueError(
                "existing verified chunks are not a subset of the incoming "
                f"approved manifest: {sorted(existing - incoming)}"
            )
        for source in sources:
            self.sources = [row for row in self.sources if row.id != source.id] + [source]
        for chunk in chunks:
            self.chunks = [row for row in self.chunks if row.id != chunk.id] + [chunk]
            self._chunks_by_id[chunk.id] = chunk
        self._embedding_models.add(E5_MODEL_NAME)
        return len(chunks)

    def search_verified(self, species_id, query_vector, embedding_model, limit):
        """Nearest verified chunks of one species, mirroring the SQL filters:
        exact species, verified chunk, verified joined source, exact embedding
        model. Sorted by (cosine distance, chunk id) for determinism."""
        self.search_calls.append((species_id, query_vector, embedding_model, limit))
        rows = []
        for chunk in self.chunks:
            if (chunk.species_id != species_id
                    or chunk.verification_status != "verified"
                    or chunk.embedding_model != embedding_model):
                continue
            source = next((s for s in self.sources if s.id == chunk.source_id), None)
            if source is None or source.verification_status != "verified":
                continue
            rows.append(RetrievedChunk(
                chunk_id=chunk.id,
                species_id=chunk.species_id,
                source_id=chunk.source_id,
                category=chunk.category,
                content=chunk.content,
                distance=_cosine_distance(chunk.embedding, query_vector),
                chunk_verification_status=chunk.verification_status,
                source_verification_status=source.verification_status,
                source_title=source.title,
                source_publisher=source.publisher,
                source_url=source.url,
                source_type=source.source_type,
                source_reviewed_at=source.reviewed_at,
            ))
        rows.sort(key=lambda row: (row.distance, row.chunk_id))
        return rows[:limit]