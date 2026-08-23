from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.main_api.db.base import Base


class FishSpecies(Base):
    __tablename__ = "fish_species"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    normalized_label: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    common_name_id: Mapped[str] = mapped_column(String(120), nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(String(160))
    taxonomic_rank: Mapped[str] = mapped_column(String(40), nullable=False)
    taxonomy_status: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint("verification_status IN ('candidate', 'verified')", name="ck_knowledge_sources_verification_status"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(160))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint(
            "category IN ('identity', 'physical_characteristics', 'taste_texture', "
            "'processing_methods', 'commercial_uses', 'substitutes')",
            name="ck_knowledge_chunks_category",
        ),
        CheckConstraint("verification_status IN ('candidate', 'verified')", name="ck_knowledge_chunks_verification_status"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    species_id: Mapped[str] = mapped_column(ForeignKey("fish_species.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("verification_status IN ('pending', 'confirmed', 'corrected')", name="ck_predictions_verification_status"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    image_reference: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_species_id: Mapped[str] = mapped_column(ForeignKey("fish_species.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    top_candidates: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    verified_species_id: Mapped[str | None] = mapped_column(ForeignKey("fish_species.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())