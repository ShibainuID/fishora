"""commercial buyer reviews and the seller fisher group

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PRD 8.3.1 requires Seller / Fisher Group on every lot. Nullable because
    # lots already published predate the column.
    op.add_column("lots", sa.Column("seller_fisher_group", sa.String(length=160), nullable=True))

    op.create_table(
        "commercial_buyer_reviews",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("lot_id", sa.String(length=120), sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("species_id", sa.String(length=80), sa.ForeignKey("fish_species.id"), nullable=False),
        sa.Column("buyer_id", sa.String(length=120), nullable=False),
        sa.Column("actual_use", sa.String(length=120), nullable=False),
        sa.Column("processing_suitability", sa.Integer(), nullable=False),
        sa.Column("substitute_acceptance", sa.Boolean(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("processing_suitability BETWEEN 1 AND 5", name="ck_reviews_suitability_range"),
        sa.UniqueConstraint("lot_id", "buyer_id", name="uq_reviews_lot_buyer"),
    )
    op.create_index("ix_commercial_buyer_reviews_lot_id", "commercial_buyer_reviews", ["lot_id"])
    op.create_index("ix_commercial_buyer_reviews_buyer_id", "commercial_buyer_reviews", ["buyer_id"])
    # Reviews are read by species, so one buyer's experience reaches every
    # auction for that fish regardless of which fisher group landed it.
    op.create_index(
        "ix_reviews_species_created_at",
        "commercial_buyer_reviews",
        ["species_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_species_created_at", table_name="commercial_buyer_reviews")
    op.drop_index("ix_commercial_buyer_reviews_buyer_id", table_name="commercial_buyer_reviews")
    op.drop_index("ix_commercial_buyer_reviews_lot_id", table_name="commercial_buyer_reviews")
    op.drop_table("commercial_buyer_reviews")
    op.drop_column("lots", "seller_fisher_group")
