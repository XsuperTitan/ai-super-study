"""create study history records

Revision ID: 20260603_0001
Revises: 
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260603_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "study_history_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("history_id", sa.String(length=64), nullable=False),
        sa.Column("anonymous_id", sa.String(length=96), nullable=False),
        sa.Column("source_content", sa.Text(), nullable=False),
        sa.Column("source_preview", sa.String(length=255), nullable=False),
        sa.Column("quiz_json", sa.JSON(), nullable=False),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("anonymous_id", "history_id", name="uq_history_anonymous_history"),
    )
    op.create_index("ix_study_history_records_anonymous_id", "study_history_records", ["anonymous_id"])
    op.create_index("ix_study_history_records_history_id", "study_history_records", ["history_id"])


def downgrade() -> None:
    op.drop_index("ix_study_history_records_history_id", table_name="study_history_records")
    op.drop_index("ix_study_history_records_anonymous_id", table_name="study_history_records")
    op.drop_table("study_history_records")
