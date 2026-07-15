"""Decision audit trail: append-only record of AI analyses and policy verdicts.

Revision ID: 002
Revises: 001
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_audit",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Plain text, no FK: audit records must outlive expense rows
        sa.Column("expense_id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("decision_type", sa.Text(), nullable=False),  # ai_analysis | policy_verdict
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=True),
        sa.Column("fraud_score", sa.Float(), nullable=True),
        sa.Column("rule_ids", postgresql.JSONB(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_decision_audit_expense", "decision_audit", ["expense_id"])
    op.create_index(
        "ix_decision_audit_org_time", "decision_audit", ["organization_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("decision_audit")
