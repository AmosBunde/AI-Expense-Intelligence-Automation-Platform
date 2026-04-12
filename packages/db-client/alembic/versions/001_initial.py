"""Initial schema: organizations, users, expenses, policies, fraud, RAG chunks.

Revision ID: 001
Revises:
Create Date: 2026-04-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("settings", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="employee"),
        sa.Column("department", sa.String(100)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    expense_status = postgresql.ENUM(
        "pending", "processing", "extracted", "categorized",
        "policy_checked", "approved", "flagged", "rejected", "paid",
        name="expensestatus", create_type=True,
    )
    document_type = postgresql.ENUM(
        "receipt", "invoice", "bank_statement", "credit_card", "manual_entry",
        name="documenttype", create_type=True,
    )
    expense_category = postgresql.ENUM(
        "travel", "meals", "office_supplies", "software", "marketing",
        "utilities", "rent", "professional_services", "equipment",
        "insurance", "training", "entertainment", "shipping", "miscellaneous",
        name="expensecategory", create_type=True,
    )

    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("status", expense_status, nullable=False, server_default="pending"),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("file_key", sa.String(500)),
        sa.Column("merchant_name", sa.String(255)),
        sa.Column("merchant_address", sa.Text),
        sa.Column("transaction_date", sa.DateTime),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("tax_amount", sa.Numeric(12, 2)),
        sa.Column("tip_amount", sa.Numeric(12, 2)),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("category", expense_category),
        sa.Column("category_confidence", sa.Float, server_default="0.0"),
        sa.Column("extraction_data", postgresql.JSONB, server_default="{}"),
        sa.Column("line_items", postgresql.JSONB, server_default="[]"),
        sa.Column("tags", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("notes", sa.Text, server_default=""),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_expenses_user_status", "expenses", ["user_id", "status"])
    op.create_index("ix_expenses_org_date", "expenses", ["organization_id", "transaction_date"])
    op.create_index("ix_expenses_category", "expenses", ["category"])
    op.create_index("ix_expenses_created", "expenses", ["created_at"])

    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("rules", postgresql.JSONB, nullable=False),
        sa.Column("category", expense_category, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    fraud_risk_level = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="fraudrisklevel", create_type=True,
    )

    op.create_table(
        "policy_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "expense_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("expenses.id"),
            nullable=False,
        ),
        sa.Column("is_compliant", sa.Boolean, nullable=False),
        sa.Column("violations", postgresql.JSONB, server_default="[]"),
        sa.Column("recommended_action", sa.String(50)),
        sa.Column("auto_approved", sa.Boolean, server_default="false"),
        sa.Column("notes", sa.Text, server_default=""),
        sa.Column("checked_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "fraud_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "expense_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("expenses.id"),
            nullable=False,
        ),
        sa.Column("risk_level", fraud_risk_level, nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("indicators", postgresql.JSONB, server_default="[]"),
        sa.Column("explanation", sa.Text, server_default=""),
        sa.Column(
            "similar_expense_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default="{}",
        ),
        sa.Column("analyzed_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "policy_document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    # Add the vector column via raw SQL since alembic doesn't natively support pgvector
    op.execute(
        "ALTER TABLE policy_document_chunks "
        "ADD COLUMN IF NOT EXISTS embedding vector(1536)"
    )


def downgrade() -> None:
    op.drop_table("policy_document_chunks")
    op.drop_table("fraud_analyses")
    op.drop_table("policy_checks")
    op.drop_table("policies")
    op.drop_table("expenses")
    op.drop_table("users")
    op.drop_table("organizations")

    op.execute("DROP TYPE IF EXISTS fraudrisklevel")
    op.execute("DROP TYPE IF EXISTS expensecategory")
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS expensestatus")
    op.execute("DROP EXTENSION IF EXISTS vector")
