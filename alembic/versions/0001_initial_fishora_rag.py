"""initial fishora rag schema

Revision ID: 0001
Revises:
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # vector extension must exist before knowledge_chunks.embedding is created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "fish_species",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("normalized_label", sa.String(length=80), nullable=False),
        sa.Column("common_name_id", sa.String(length=120), nullable=False),
        sa.Column("scientific_name", sa.String(length=160), nullable=True),
        sa.Column("taxonomic_rank", sa.String(length=40), nullable=False),
        sa.Column("taxonomy_status", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("normalized_label", name="uq_fish_species_normalized_label"),
    )
    op.create_index("ix_fish_species_normalized_label", "fish_species", ["normalized_label"])

    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "verification_status IN ('candidate', 'verified')",
            name="ck_knowledge_sources_verification_status",
        ),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("species_id", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("verification_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], name="fk_knowledge_chunks_source_id"),
        sa.ForeignKeyConstraint(["species_id"], ["fish_species.id"], name="fk_knowledge_chunks_species_id"),
        sa.CheckConstraint(
            "category IN ('identity', 'physical_characteristics', 'taste_texture', "
            "'processing_methods', 'commercial_uses', 'substitutes')",
            name="ck_knowledge_chunks_category",
        ),
        sa.CheckConstraint(
            "verification_status IN ('candidate', 'verified')",
            name="ck_knowledge_chunks_verification_status",
        ),
    )
    op.create_index("ix_knowledge_chunks_species_id", "knowledge_chunks", ["species_id"])
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("image_reference", sa.Text(), nullable=False),
        sa.Column("predicted_species_id", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("top_candidates", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("verification_status", sa.String(length=20), nullable=False),
        sa.Column("verified_species_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["predicted_species_id"], ["fish_species.id"], name="fk_predictions_predicted_species_id"),
        sa.ForeignKeyConstraint(["verified_species_id"], ["fish_species.id"], name="fk_predictions_verified_species_id"),
        sa.CheckConstraint(
            "verification_status IN ('pending', 'confirmed', 'corrected')",
            name="ck_predictions_verification_status",
        ),
    )
    op.create_index("ix_predictions_predicted_species_id", "predictions", ["predicted_species_id"])


def downgrade() -> None:
    op.drop_index("ix_predictions_predicted_species_id", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("ix_knowledge_chunks_source_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_species_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
    op.drop_index("ix_fish_species_normalized_label", table_name="fish_species")
    op.drop_table("fish_species")