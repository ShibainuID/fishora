"""commerce tables for lots, bids, preferences, landing points

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "landing_points",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
    )

    op.create_table(
        "lots",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("prediction_id", sa.String(length=120), nullable=False),
        sa.Column("operator_id", sa.String(length=120), nullable=False),
        sa.Column("species_id", sa.String(length=80), nullable=False),
        sa.Column("landing_point_id", sa.String(length=120), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("size_category", sa.String(length=1), nullable=False),
        sa.Column("starting_price_per_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("auction_starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("auction_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("knowledge_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("public_slug", sa.String(length=160), nullable=False),
        sa.Column("allocated_buyer_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], name="fk_lots_prediction_id"),
        sa.ForeignKeyConstraint(["species_id"], ["fish_species.id"], name="fk_lots_species_id"),
        sa.ForeignKeyConstraint(["landing_point_id"], ["landing_points.id"], name="fk_lots_landing_point_id"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'closed', 'allocated')",
            name="ck_lots_status",
        ),
        sa.CheckConstraint("quantity_kg > 0", name="ck_lots_quantity_positive"),
        sa.CheckConstraint("starting_price_per_kg > 0", name="ck_lots_price_positive"),
        sa.CheckConstraint("auction_ends_at > auction_starts_at", name="ck_lots_auction_window"),
        sa.CheckConstraint("size_category IN ('S', 'M', 'L')", name="ck_lots_size_category"),
        sa.UniqueConstraint("public_slug", name="uq_lots_public_slug"),
    )
    op.create_index("ix_lots_prediction_id", "lots", ["prediction_id"])
    op.create_index("ix_lots_operator_id", "lots", ["operator_id"])
    op.create_index("ix_lots_species_id", "lots", ["species_id"])

    op.create_table(
        "bids",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("lot_id", sa.String(length=120), nullable=False),
        sa.Column("buyer_id", sa.String(length=120), nullable=False),
        sa.Column("amount_per_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], name="fk_bids_lot_id"),
        sa.CheckConstraint("amount_per_kg > 0", name="ck_bids_amount_positive"),
    )
    op.create_index("ix_bids_buyer_id", "bids", ["buyer_id"])
    op.create_index(
        "ix_bids_lot_id_created_at",
        "bids",
        ["lot_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "buyer_preferences",
        sa.Column("buyer_id", sa.String(length=120), primary_key=True),
        sa.Column("business_type", sa.String(length=80), nullable=False),
        sa.Column("intended_uses", postgresql.JSONB(), nullable=False),
        sa.Column("characteristics", postgresql.JSONB(), nullable=False),
        sa.Column("max_price_per_kg", sa.Numeric(12, 2), nullable=True),
        sa.Column("min_quantity_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("buyer_preferences")
    op.drop_index("ix_bids_lot_id_created_at", table_name="bids")
    op.drop_index("ix_bids_buyer_id", table_name="bids")
    op.drop_table("bids")
    op.drop_index("ix_lots_species_id", table_name="lots")
    op.drop_index("ix_lots_operator_id", table_name="lots")
    op.drop_index("ix_lots_prediction_id", table_name="lots")
    op.drop_table("lots")
    op.drop_table("landing_points")
