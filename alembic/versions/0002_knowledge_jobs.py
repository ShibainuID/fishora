"""knowledge_jobs for background langgraph

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
        "knowledge_jobs",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column("prediction_id", sa.String(length=120), nullable=False),
        sa.Column("species_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expert_outputs", postgresql.JSONB(), nullable=True),
        sa.Column("critic_feedback", sa.Text(), nullable=True),
        sa.Column("final_card", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE", name="fk_knowledge_jobs_prediction_id"),
        sa.ForeignKeyConstraint(["species_id"], ["fish_species.id"], name="fk_knowledge_jobs_species_id"),
        sa.CheckConstraint("status IN ('processing', 'completed', 'failed')", name="ck_knowledge_jobs_status"),
    )
    op.create_index("ix_knowledge_jobs_status", "knowledge_jobs", ["status"])
    op.create_index("ix_knowledge_jobs_prediction_id", "knowledge_jobs", ["prediction_id"])
    op.create_index("ix_knowledge_jobs_species_id", "knowledge_jobs", ["species_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_jobs_species_id", table_name="knowledge_jobs")
    op.drop_index("ix_knowledge_jobs_prediction_id", table_name="knowledge_jobs")
    op.drop_index("ix_knowledge_jobs_status", table_name="knowledge_jobs")
    op.drop_table("knowledge_jobs")
