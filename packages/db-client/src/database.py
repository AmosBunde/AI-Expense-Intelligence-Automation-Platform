"""
Database client package - SQLAlchemy models, session management, and connection pooling.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator

from sqlalchemy import (
    Column, String, Text, Numeric, DateTime, Boolean, Integer, Float,
    ForeignKey, Enum as SAEnum, JSON, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector

from shared_types.models import (
    ExpenseStatus, DocumentType, ExpenseCategory, FraudRiskLevel
)


class Base(DeclarativeBase):
    pass


# =============================================================================
# ORM Models
# =============================================================================

class OrganizationORM(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("UserORM", back_populates="organization")
    policies = relationship("PolicyORM", back_populates="organization")
    expenses = relationship("ExpenseORM", back_populates="organization")


class UserORM(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="employee")  # employee, manager, admin, finance
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("OrganizationORM", back_populates="users")
    expenses = relationship("ExpenseORM", back_populates="user")


class ExpenseORM(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_user_status", "user_id", "status"),
        Index("ix_expenses_org_date", "organization_id", "transaction_date"),
        Index("ix_expenses_category", "category"),
        Index("ix_expenses_created", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    status = Column(SAEnum(ExpenseStatus), default=ExpenseStatus.PENDING, nullable=False)
    document_type = Column(SAEnum(DocumentType), nullable=False)
    file_key = Column(String(500))
    merchant_name = Column(String(255))
    merchant_address = Column(Text)
    transaction_date = Column(DateTime)
    amount = Column(Numeric(12, 2))
    currency = Column(String(3), default="USD")
    tax_amount = Column(Numeric(12, 2))
    tip_amount = Column(Numeric(12, 2))
    payment_method = Column(String(50))
    category = Column(SAEnum(ExpenseCategory))
    category_confidence = Column(Float, default=0.0)
    extraction_data = Column(JSONB, default={})
    line_items = Column(JSONB, default=[])
    tags = Column(ARRAY(String), default=[])
    notes = Column(Text, default="")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("UserORM", back_populates="expenses", foreign_keys=[user_id])
    organization = relationship("OrganizationORM", back_populates="expenses")
    policy_checks = relationship("PolicyCheckORM", back_populates="expense")
    fraud_analyses = relationship("FraudAnalysisORM", back_populates="expense")


class PolicyORM(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    rules = Column(JSONB, nullable=False)  # Structured rule definitions
    category = Column(SAEnum(ExpenseCategory), nullable=True)  # null = applies to all
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("OrganizationORM", back_populates="policies")


class PolicyCheckORM(Base):
    __tablename__ = "policy_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id"), nullable=False)
    is_compliant = Column(Boolean, nullable=False)
    violations = Column(JSONB, default=[])
    recommended_action = Column(String(50))
    auto_approved = Column(Boolean, default=False)
    notes = Column(Text, default="")
    checked_at = Column(DateTime, default=datetime.utcnow)

    expense = relationship("ExpenseORM", back_populates="policy_checks")


class FraudAnalysisORM(Base):
    __tablename__ = "fraud_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id"), nullable=False)
    risk_level = Column(SAEnum(FraudRiskLevel), nullable=False)
    risk_score = Column(Float, nullable=False)
    indicators = Column(JSONB, default=[])
    explanation = Column(Text, default="")
    similar_expense_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    expense = relationship("ExpenseORM", back_populates="fraud_analyses")


class PolicyDocumentChunkORM(Base):
    """Embedded policy document chunks for RAG retrieval."""
    __tablename__ = "policy_document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    document_name = Column(String(255), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# Database Session Management
# =============================================================================

class DatabaseClient:
    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 10):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False,
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        await self.engine.dispose()
