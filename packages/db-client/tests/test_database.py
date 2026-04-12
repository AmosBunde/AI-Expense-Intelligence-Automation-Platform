"""Tests for db-client ORM models and DatabaseClient."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import (
    Base,
    DatabaseClient,
    ExpenseORM,
    FraudAnalysisORM,
    OrganizationORM,
    PolicyCheckORM,
    PolicyDocumentChunkORM,
    PolicyORM,
    UserORM,
)


# ---------------------------------------------------------------------------
# Fixtures — use aiosqlite for fast in-process tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as sess:
        yield sess


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def user_id():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# ORM Model Tests
# ---------------------------------------------------------------------------

class TestOrganizationORM:
    async def test_create_organization(self, session: AsyncSession, org_id):
        org = OrganizationORM(id=org_id, name="Acme Corp", settings={"currency": "USD"})
        session.add(org)
        await session.commit()

        result = await session.get(OrganizationORM, org_id)
        assert result is not None
        assert result.name == "Acme Corp"
        assert result.settings == {"currency": "USD"}

    async def test_organization_defaults(self, session: AsyncSession):
        org = OrganizationORM(id=uuid.uuid4(), name="Test Org")
        session.add(org)
        await session.commit()
        assert org.name == "Test Org"


class TestUserORM:
    async def test_create_user(self, session: AsyncSession, org_id, user_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        session.add(org)
        await session.flush()

        user = UserORM(
            id=user_id,
            organization_id=org_id,
            email="alice@acme.com",
            hashed_password="hashed_pw",
            full_name="Alice Smith",
            role="admin",
            department="Engineering",
        )
        session.add(user)
        await session.commit()

        result = await session.get(UserORM, user_id)
        assert result is not None
        assert result.email == "alice@acme.com"
        assert result.full_name == "Alice Smith"
        assert result.role == "admin"
        assert result.is_active is True

    async def test_user_email_unique(self, session: AsyncSession, org_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        session.add(org)
        await session.flush()

        user1 = UserORM(
            id=uuid.uuid4(),
            organization_id=org_id,
            email="dup@acme.com",
            hashed_password="pw",
            full_name="User One",
        )
        user2 = UserORM(
            id=uuid.uuid4(),
            organization_id=org_id,
            email="dup@acme.com",
            hashed_password="pw",
            full_name="User Two",
        )
        session.add(user1)
        await session.flush()
        session.add(user2)
        with pytest.raises(Exception):
            await session.flush()


class TestExpenseORM:
    async def test_create_expense(self, session: AsyncSession, org_id, user_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        user = UserORM(
            id=user_id,
            organization_id=org_id,
            email="bob@acme.com",
            hashed_password="pw",
            full_name="Bob Jones",
        )
        session.add_all([org, user])
        await session.flush()

        expense_id = uuid.uuid4()
        expense = ExpenseORM(
            id=expense_id,
            user_id=user_id,
            organization_id=org_id,
            document_type="receipt",
            merchant_name="Coffee Shop",
            amount=Decimal("12.50"),
            currency="USD",
            notes="Team lunch",
        )
        session.add(expense)
        await session.commit()

        result = await session.get(ExpenseORM, expense_id)
        assert result is not None
        assert result.merchant_name == "Coffee Shop"
        assert result.amount == Decimal("12.50")
        assert result.notes == "Team lunch"
        assert result.currency == "USD"

    async def test_expense_with_extraction_data(self, session: AsyncSession, org_id, user_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        user = UserORM(
            id=user_id,
            organization_id=org_id,
            email="carol@acme.com",
            hashed_password="pw",
            full_name="Carol",
        )
        session.add_all([org, user])
        await session.flush()

        expense_id = uuid.uuid4()
        extraction = {"raw_text": "Receipt from Store", "confidence": 0.95}
        line_items = [{"description": "Widget", "quantity": 2, "unit_price": "5.00", "total": "10.00"}]
        expense = ExpenseORM(
            id=expense_id,
            user_id=user_id,
            organization_id=org_id,
            document_type="invoice",
            extraction_data=extraction,
            line_items=line_items,
            amount=Decimal("10.00"),
        )
        session.add(expense)
        await session.commit()

        result = await session.get(ExpenseORM, expense_id)
        assert result.extraction_data["confidence"] == 0.95
        assert len(result.line_items) == 1


class TestPolicyORM:
    async def test_create_policy(self, session: AsyncSession, org_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        session.add(org)
        await session.flush()

        policy_id = uuid.uuid4()
        policy = PolicyORM(
            id=policy_id,
            organization_id=org_id,
            name="Meal Limit",
            description="Max $50 per meal",
            rules={"max_amount": 50, "category": "meals"},
            is_active=True,
            priority=1,
        )
        session.add(policy)
        await session.commit()

        result = await session.get(PolicyORM, policy_id)
        assert result.name == "Meal Limit"
        assert result.rules["max_amount"] == 50
        assert result.is_active is True


class TestPolicyCheckORM:
    async def test_create_policy_check(self, session: AsyncSession, org_id, user_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        user = UserORM(
            id=user_id,
            organization_id=org_id,
            email="dave@acme.com",
            hashed_password="pw",
            full_name="Dave",
        )
        session.add_all([org, user])
        await session.flush()

        expense_id = uuid.uuid4()
        expense = ExpenseORM(
            id=expense_id,
            user_id=user_id,
            organization_id=org_id,
            document_type="receipt",
            amount=Decimal("75.00"),
        )
        session.add(expense)
        await session.flush()

        check_id = uuid.uuid4()
        check = PolicyCheckORM(
            id=check_id,
            expense_id=expense_id,
            is_compliant=False,
            violations=[{"type": "over_limit", "description": "Exceeded $50 meal limit"}],
            recommended_action="require_review",
            auto_approved=False,
            notes="Flagged for manager review",
        )
        session.add(check)
        await session.commit()

        result = await session.get(PolicyCheckORM, check_id)
        assert result.is_compliant is False
        assert len(result.violations) == 1
        assert result.recommended_action == "require_review"


class TestFraudAnalysisORM:
    async def test_create_fraud_analysis(self, session: AsyncSession, org_id, user_id):
        org = OrganizationORM(id=org_id, name="Acme Corp")
        user = UserORM(
            id=user_id,
            organization_id=org_id,
            email="eve@acme.com",
            hashed_password="pw",
            full_name="Eve",
        )
        session.add_all([org, user])
        await session.flush()

        expense_id = uuid.uuid4()
        expense = ExpenseORM(
            id=expense_id,
            user_id=user_id,
            organization_id=org_id,
            document_type="receipt",
            amount=Decimal("999.99"),
        )
        session.add(expense)
        await session.flush()

        analysis_id = uuid.uuid4()
        analysis = FraudAnalysisORM(
            id=analysis_id,
            expense_id=expense_id,
            risk_level="high",
            risk_score=0.85,
            indicators=["unusual_amount", "new_vendor"],
            explanation="Amount is unusually high for this category",
        )
        session.add(analysis)
        await session.commit()

        result = await session.get(FraudAnalysisORM, analysis_id)
        assert result.risk_level == "high"
        assert result.risk_score == 0.85
        assert "unusual_amount" in result.indicators


# ---------------------------------------------------------------------------
# Table structure tests
# ---------------------------------------------------------------------------

class TestTableStructure:
    async def test_all_tables_created(self, engine):
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        expected = {
            "organizations", "users", "expenses", "policies",
            "policy_checks", "fraud_analyses", "policy_document_chunks",
        }
        assert expected.issubset(set(table_names))

    async def test_expense_indexes_defined(self):
        """Verify that the expected indexes are declared on ExpenseORM."""
        index_names = {idx.name for idx in ExpenseORM.__table__.indexes}
        assert "ix_expenses_user_status" in index_names
        assert "ix_expenses_org_date" in index_names
        assert "ix_expenses_category" in index_names
        assert "ix_expenses_created" in index_names


# ---------------------------------------------------------------------------
# DatabaseClient tests
# ---------------------------------------------------------------------------

class TestDatabaseClient:
    async def test_init_and_close(self):
        client = DatabaseClient("sqlite+aiosqlite://", pool_size=None, max_overflow=None)
        assert client.engine is not None
        assert client.async_session is not None
        await client.close()

    async def test_get_session_commit(self):
        client = DatabaseClient("sqlite+aiosqlite://", pool_size=None, max_overflow=None)
        # Create tables first
        async with client.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async for session in client.get_session():
            org = OrganizationORM(id=uuid.uuid4(), name="Session Test Org")
            session.add(org)

        # Verify committed — open a new session and query
        async for session in client.get_session():
            result = await session.execute(
                select(OrganizationORM).where(OrganizationORM.name == "Session Test Org")
            )
            assert result.scalars().first() is not None

        await client.close()

    async def test_get_session_rollback_on_error(self):
        client = DatabaseClient("sqlite+aiosqlite://", pool_size=None, max_overflow=None)
        async with client.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        org_id = uuid.uuid4()
        with pytest.raises(ValueError):
            async for session in client.get_session():
                session.add(OrganizationORM(id=org_id, name="Rollback Test"))
                raise ValueError("Simulated error")

        # Verify rolled back
        async for session in client.get_session():
            result = await session.get(OrganizationORM, org_id)
            assert result is None

        await client.close()
