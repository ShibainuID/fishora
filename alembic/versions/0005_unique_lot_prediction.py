"""one auction lot per prediction

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # HANDOFF 11 models Prediction 1 -> 0..1 AuctionLot, but only an index
    # backed prediction_id, so one confirmed catch could be listed twice.
    op.create_unique_constraint("uq_lots_prediction_id", "lots", ["prediction_id"])
    # The unique constraint's own index serves every lookup the old one did.
    op.drop_index("ix_lots_prediction_id", table_name="lots")


def downgrade() -> None:
    op.create_index("ix_lots_prediction_id", "lots", ["prediction_id"])
    op.drop_constraint("uq_lots_prediction_id", "lots", type_="unique")
