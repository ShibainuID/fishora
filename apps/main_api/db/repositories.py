import csv
from pathlib import Path
from typing import Callable, Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from apps.main_api.contracts import KnowledgeChunkWrite, KnowledgeSourceWrite, TaxonomySeed
from apps.main_api.db.models import FishSpecies, KnowledgeChunk, KnowledgeSource
from apps.main_api.services.embeddings import E5_MODEL_NAME

# Fixed bigint key ('Fish') for the transaction advisory lock: all Fishora
# ingests serialize on it, so concurrent mixed-model ingests cannot both pass.
FISHORA_INGEST_ADVISORY_LOCK = 0x46697368

TAXONOMY_STATUS_BY_LABEL = {
    "bandeng": "VERIFIED_TAXONOMY",
    "gelama_bunga": "VERIFIED_TAXONOMY",
    "gembolo": "TAXONOMY_REVIEW_REQUIRED",
    "gulamah": "VERIFIED_TAXONOMY",
    "kembung": "VERIFIED_TAXONOMY",
    "kuniran": "VERIFIED_TAXONOMY",
    "mujair": "VERIFIED_TAXONOMY",
    "nila": "VERIFIED_TAXONOMY",
    "senangin": "VERIFIED_TAXONOMY",
    "tenggiri": "MEDIUM_CONFIDENCE_LABEL_AMBIGUITY",
    "tuna": "MIXED_TAXONOMY",
}

def load_taxonomy_csv(path: Path) -> list[TaxonomySeed]:
    """Read the taxonomy CSV; only empty scientific_name/notes cells become None.

    Non-empty cells are preserved verbatim (no stripping). Rejects unknown
    normalized labels and any file whose normalized label set is not exactly
    the eleven supported labels.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows: list[TaxonomySeed] = []
        for row in reader:
            normalized_label = row["normalized_label"]
            if normalized_label not in TAXONOMY_STATUS_BY_LABEL:
                raise ValueError(f"unsupported normalized_label {normalized_label!r} in {path}")
            rows.append(
                TaxonomySeed(
                    raw_folder=row["raw_folder"],
                    raw_label=row["raw_label"],
                    normalized_label=normalized_label,
                    scientific_name=row["scientific_name"].strip() or None,
                    common_name_id=row["common_name_id"],
                    taxonomic_rank=row["taxonomic_rank"],
                    confidence=row["confidence"],
                    source=row["source"],
                    notes=row["notes"] or None,
                    taxonomy_status=TAXONOMY_STATUS_BY_LABEL[normalized_label],
                )
            )
    labels = {row.normalized_label for row in rows}
    if labels != set(TAXONOMY_STATUS_BY_LABEL):
        raise ValueError(
            f"taxonomy CSV normalized labels must be exactly the {len(TAXONOMY_STATUS_BY_LABEL)} "
            f"supported labels, got {sorted(labels)}"
        )
    if len(rows) != len(TAXONOMY_STATUS_BY_LABEL):
        raise ValueError(
            f"taxonomy CSV must contain exactly {len(TAXONOMY_STATUS_BY_LABEL)} rows, "
            f"one per supported label, got {len(rows)}"
        )
    return rows


def seed_taxonomy(session: Session, path: Path) -> int:
    """Upsert the eleven FishSpecies rows; returns the number of rows written.

    Does not commit; the caller owns the transaction.
    """
    written = 0
    for seed in load_taxonomy_csv(path):
        values = {
            "normalized_label": seed.normalized_label,
            "common_name_id": seed.common_name_id,
            "scientific_name": seed.scientific_name,
            "taxonomic_rank": seed.taxonomic_rank,
            "taxonomy_status": seed.taxonomy_status,
            "notes": seed.notes,
        }
        species = session.get(FishSpecies, f"species_{seed.normalized_label}")
        if species is None:
            session.add(FishSpecies(id=f"species_{seed.normalized_label}", **values))
            written += 1
        elif any(getattr(species, field) != value for field, value in values.items()):
            for field, value in values.items():
                setattr(species, field, value)
            written += 1
    return written


class SqlKnowledgeRepository:
    """Transactional store for approved sources/chunks (pgvector)."""

    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def embedding_models_in_store(self) -> set[str]:
        with self._session_factory() as session:
            return set(session.scalars(select(KnowledgeChunk.embedding_model).distinct()))

    def insert_verified(
        self,
        sources: Sequence[KnowledgeSourceWrite],
        chunks: Sequence[KnowledgeChunkWrite],
    ) -> int:
        """Upsert verified sources/chunks in one transaction, all or nothing.

        Under a Postgres transaction advisory lock the existing embedding
        models and verified chunk ids are re-checked inside this same write
        transaction before any upsert: another embedding model or an existing
        verified chunk missing from the incoming manifest (stale partial
        corpus) raises and rolls everything back, and two concurrent ingests
        cannot both pass a mixed-model check. Sources are flushed before
        chunks are added: the mappers declare no relationship(), so the unit
        of work has no cross-mapper ordering and would otherwise insert
        chunks first (alphabetical mapper order).
        """
        if not chunks:
            return 0
        # The whole incoming batch must use exactly the E5 model: a single
        # batch mixing two models would otherwise commit mixed vectors into
        # an empty store by passing a first-chunk-only check.
        incoming_models = {chunk.embedding_model for chunk in chunks}
        if incoming_models != {E5_MODEL_NAME}:
            raise ValueError(
                "incoming chunk batch must use exactly one embedding model "
                f"({E5_MODEL_NAME}), got {sorted(incoming_models)}"
            )
        with self._session_factory() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": FISHORA_INGEST_ADVISORY_LOCK},
            )
            existing_models = set(session.scalars(select(KnowledgeChunk.embedding_model).distinct()))
            if existing_models and existing_models != {E5_MODEL_NAME}:
                raise ValueError(
                    "knowledge store already contains another embedding model "
                    f"({sorted(existing_models)}); refusing to mix with {E5_MODEL_NAME}"
                )
            existing_ids = set(
                session.scalars(
                    select(KnowledgeChunk.id).where(KnowledgeChunk.verification_status == "verified")
                )
            )
            incoming_ids = {chunk.id for chunk in chunks}
            if not existing_ids <= incoming_ids:
                raise ValueError(
                    "existing verified chunks are not a subset of the incoming "
                    f"approved manifest: {sorted(existing_ids - incoming_ids)}"
                )
            for source in sources:
                row = session.get(KnowledgeSource, source.id)
                if row is None:
                    session.add(
                        KnowledgeSource(
                            id=source.id,
                            title=source.title,
                            source_type=source.source_type,
                            url=source.url,
                            publisher=source.publisher,
                            reviewed_at=source.reviewed_at,
                            verification_status=source.verification_status,
                        )
                    )
                else:
                    row.title = source.title
                    row.source_type = source.source_type
                    row.url = source.url
                    row.publisher = source.publisher
                    row.reviewed_at = source.reviewed_at
                    row.verification_status = source.verification_status
            session.flush()
            for chunk in chunks:
                row = session.get(KnowledgeChunk, chunk.id)
                if row is None:
                    session.add(
                        KnowledgeChunk(
                            id=chunk.id,
                            species_id=chunk.species_id,
                            source_id=chunk.source_id,
                            category=chunk.category,
                            content=chunk.content,
                            embedding=chunk.embedding,
                            embedding_model=chunk.embedding_model,
                            verification_status=chunk.verification_status,
                        )
                    )
                else:
                    row.species_id = chunk.species_id
                    row.source_id = chunk.source_id
                    row.category = chunk.category
                    row.content = chunk.content
                    row.embedding = chunk.embedding
                    row.embedding_model = chunk.embedding_model
                    row.verification_status = chunk.verification_status
            session.commit()
        return len(chunks)