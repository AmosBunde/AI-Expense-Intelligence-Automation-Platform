"""Tests for shared domain models."""
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.models import (
    ApprovalAction,
    DocumentType,
    Expense,
    ExpenseCategory,
    ExpenseCreate,
    ExpenseExtraction,
    ExpenseStatus,
    ExtractedField,
    FraudAnalysis,
    FraudRiskLevel,
    HealthCheck,
    LineItem,
    PaginatedResponse,
    PolicyCheckResult,
    PolicyViolation,
    PolicyViolationType,
    SpendSummary,
)


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    def test_expense_status_members(self):
        assert ExpenseStatus.PENDING == "pending"
        assert ExpenseStatus.PROCESSING == "processing"
        assert ExpenseStatus.EXTRACTED == "extracted"
        assert ExpenseStatus.CATEGORIZED == "categorized"
        assert ExpenseStatus.POLICY_CHECKED == "policy_checked"
        assert ExpenseStatus.APPROVED == "approved"
        assert ExpenseStatus.FLAGGED == "flagged"
        assert ExpenseStatus.REJECTED == "rejected"
        assert ExpenseStatus.PAID == "paid"
        assert len(ExpenseStatus) == 9

    def test_document_type_members(self):
        assert DocumentType.RECEIPT == "receipt"
        assert DocumentType.INVOICE == "invoice"
        assert DocumentType.BANK_STATEMENT == "bank_statement"
        assert DocumentType.CREDIT_CARD == "credit_card"
        assert DocumentType.MANUAL_ENTRY == "manual_entry"
        assert len(DocumentType) == 5

    def test_expense_category_members(self):
        expected = {
            "travel", "meals", "office_supplies", "software", "marketing",
            "utilities", "rent", "professional_services", "equipment",
            "insurance", "training", "entertainment", "shipping", "miscellaneous",
        }
        assert {c.value for c in ExpenseCategory} == expected
        assert len(ExpenseCategory) == 14

    def test_fraud_risk_level_members(self):
        assert FraudRiskLevel.LOW == "low"
        assert FraudRiskLevel.MEDIUM == "medium"
        assert FraudRiskLevel.HIGH == "high"
        assert FraudRiskLevel.CRITICAL == "critical"
        assert len(FraudRiskLevel) == 4

    def test_policy_violation_type_members(self):
        expected = {
            "over_limit", "missing_receipt", "duplicate_expense",
            "policy_breach", "suspicious_pattern", "unapproved_vendor",
            "weekend_expense", "split_expense",
        }
        assert {v.value for v in PolicyViolationType} == expected
        assert len(PolicyViolationType) == 8

    def test_approval_action_members(self):
        assert ApprovalAction.AUTO_APPROVE == "auto_approve"
        assert ApprovalAction.REQUIRE_REVIEW == "require_review"
        assert ApprovalAction.ESCALATE == "escalate"
        assert ApprovalAction.REJECT == "reject"
        assert len(ApprovalAction) == 4


# =============================================================================
# Model Creation Tests
# =============================================================================

class TestModelCreation:
    def test_extracted_field(self):
        field = ExtractedField(
            field_name="total",
            value="42.50",
            confidence=0.95,
        )
        assert field.field_name == "total"
        assert field.confidence == 0.95
        assert field.bounding_box is None

    def test_extracted_field_with_bounding_box(self):
        field = ExtractedField(
            field_name="date",
            value="2026-01-15",
            confidence=0.8,
            bounding_box=[0.1, 0.2, 0.3, 0.4],
        )
        assert field.bounding_box == [0.1, 0.2, 0.3, 0.4]

    def test_line_item(self):
        item = LineItem(
            description="Widget",
            quantity=3.0,
            unit_price=Decimal("10.00"),
            total=Decimal("30.00"),
        )
        assert item.description == "Widget"
        assert item.total == Decimal("30.00")

    def test_expense_extraction(self):
        extraction = ExpenseExtraction(
            merchant_name="Acme Corp",
            amount=Decimal("150.00"),
            currency="USD",
            category=ExpenseCategory.OFFICE_SUPPLIES,
            category_confidence=0.92,
        )
        assert extraction.merchant_name == "Acme Corp"
        assert extraction.amount == Decimal("150.00")
        assert extraction.line_items == []

    def test_expense_extraction_with_line_items(self):
        extraction = ExpenseExtraction(
            merchant_name="Store",
            amount=Decimal("50.00"),
            line_items=[
                LineItem(
                    description="Item A",
                    unit_price=Decimal("25.00"),
                    total=Decimal("25.00"),
                ),
                LineItem(
                    description="Item B",
                    unit_price=Decimal("25.00"),
                    total=Decimal("25.00"),
                ),
            ],
        )
        assert len(extraction.line_items) == 2

    def test_policy_violation(self):
        violation = PolicyViolation(
            violation_type=PolicyViolationType.OVER_LIMIT,
            severity=FraudRiskLevel.MEDIUM,
            description="Meal exceeds $75 limit",
            policy_reference="Policy 3.2.1 - Meal Limit",
            threshold_value="75.00",
            actual_value="120.00",
        )
        assert violation.violation_type == PolicyViolationType.OVER_LIMIT

    def test_policy_check_result(self):
        eid = uuid.uuid4()
        result = PolicyCheckResult(
            expense_id=eid,
            is_compliant=False,
            violations=[
                PolicyViolation(
                    violation_type=PolicyViolationType.OVER_LIMIT,
                    severity=FraudRiskLevel.LOW,
                    description="Over limit",
                    policy_reference="Policy 1.0",
                ),
            ],
            recommended_action=ApprovalAction.REQUIRE_REVIEW,
        )
        assert result.expense_id == eid
        assert not result.is_compliant
        assert len(result.violations) == 1

    def test_fraud_analysis(self):
        eid = uuid.uuid4()
        analysis = FraudAnalysis(
            expense_id=eid,
            risk_level=FraudRiskLevel.HIGH,
            risk_score=0.85,
            indicators=["duplicate_amount", "weekend_submission"],
            explanation="Multiple indicators of suspicious activity",
        )
        assert analysis.risk_score == 0.85
        assert len(analysis.indicators) == 2

    def test_expense_create(self):
        expense = ExpenseCreate(
            document_type=DocumentType.RECEIPT,
            file_key="uploads/receipt_001.pdf",
            metadata={"source": "mobile_app"},
        )
        assert expense.document_type == DocumentType.RECEIPT
        assert expense.file_key == "uploads/receipt_001.pdf"

    def test_expense_full(self):
        uid = uuid.uuid4()
        oid = uuid.uuid4()
        expense = Expense(
            user_id=uid,
            organization_id=oid,
            document_type=DocumentType.INVOICE,
            status=ExpenseStatus.EXTRACTED,
            amount=Decimal("500.00"),
            merchant_name="Vendor Inc",
        )
        assert expense.user_id == uid
        assert expense.status == ExpenseStatus.EXTRACTED
        assert expense.id is not None
        assert isinstance(expense.created_at, datetime)

    def test_paginated_response(self):
        resp = PaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            total=50,
            page=1,
            page_size=20,
            has_next=True,
        )
        assert resp.total == 50
        assert resp.has_next is True

    def test_spend_summary(self):
        summary = SpendSummary(
            period="2026-Q1",
            total_spend=Decimal("50000.00"),
            by_category={"travel": Decimal("15000.00")},
            flagged_count=5,
            auto_approved_count=120,
        )
        assert summary.period == "2026-Q1"
        assert summary.total_spend == Decimal("50000.00")

    def test_health_check(self):
        hc = HealthCheck(
            service="expense-api",
            version="0.1.0",
            uptime_seconds=3600.5,
            dependencies={"postgres": "ok", "redis": "ok"},
        )
        assert hc.status == "ok"
        assert hc.dependencies["postgres"] == "ok"


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    def test_confidence_too_high(self):
        with pytest.raises(ValidationError):
            ExtractedField(
                field_name="total",
                value="42.50",
                confidence=1.5,
            )

    def test_confidence_too_low(self):
        with pytest.raises(ValidationError):
            ExtractedField(
                field_name="total",
                value="42.50",
                confidence=-0.1,
            )

    def test_risk_score_too_high(self):
        with pytest.raises(ValidationError):
            FraudAnalysis(
                expense_id=uuid.uuid4(),
                risk_level=FraudRiskLevel.LOW,
                risk_score=1.5,
                explanation="test",
            )

    def test_risk_score_too_low(self):
        with pytest.raises(ValidationError):
            FraudAnalysis(
                expense_id=uuid.uuid4(),
                risk_level=FraudRiskLevel.LOW,
                risk_score=-0.1,
                explanation="test",
            )

    def test_invalid_expense_status(self):
        with pytest.raises(ValidationError):
            Expense(
                user_id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                document_type=DocumentType.RECEIPT,
                status="invalid_status",
            )

    def test_invalid_document_type(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(document_type="not_a_type")

    def test_confidence_boundary_zero(self):
        field = ExtractedField(field_name="x", value="v", confidence=0.0)
        assert field.confidence == 0.0

    def test_confidence_boundary_one(self):
        field = ExtractedField(field_name="x", value="v", confidence=1.0)
        assert field.confidence == 1.0


# =============================================================================
# JSON Serialization Round-Trip Tests
# =============================================================================

class TestJsonRoundTrip:
    def test_extracted_field_roundtrip(self):
        original = ExtractedField(
            field_name="amount",
            value="99.99",
            confidence=0.97,
            bounding_box=[0.1, 0.2, 0.5, 0.6],
        )
        json_str = original.model_dump_json()
        restored = ExtractedField.model_validate_json(json_str)
        assert restored == original

    def test_expense_extraction_roundtrip(self):
        original = ExpenseExtraction(
            merchant_name="Coffee Shop",
            amount=Decimal("5.50"),
            transaction_date=datetime(2026, 1, 15, 10, 30),
            line_items=[
                LineItem(
                    description="Latte",
                    quantity=1.0,
                    unit_price=Decimal("5.50"),
                    total=Decimal("5.50"),
                ),
            ],
            category=ExpenseCategory.MEALS,
            category_confidence=0.99,
        )
        json_str = original.model_dump_json()
        restored = ExpenseExtraction.model_validate_json(json_str)
        assert restored.merchant_name == original.merchant_name
        assert restored.amount == original.amount
        assert len(restored.line_items) == 1

    def test_expense_roundtrip(self):
        uid = uuid.uuid4()
        oid = uuid.uuid4()
        original = Expense(
            user_id=uid,
            organization_id=oid,
            document_type=DocumentType.RECEIPT,
            status=ExpenseStatus.APPROVED,
            amount=Decimal("250.00"),
            merchant_name="Office Depot",
            category=ExpenseCategory.OFFICE_SUPPLIES,
            tags=["q1", "office"],
        )
        json_str = original.model_dump_json()
        restored = Expense.model_validate_json(json_str)
        assert restored.user_id == uid
        assert restored.status == ExpenseStatus.APPROVED
        assert restored.tags == ["q1", "office"]

    def test_policy_check_result_roundtrip(self):
        eid = uuid.uuid4()
        original = PolicyCheckResult(
            expense_id=eid,
            is_compliant=False,
            violations=[
                PolicyViolation(
                    violation_type=PolicyViolationType.MISSING_RECEIPT,
                    severity=FraudRiskLevel.MEDIUM,
                    description="No receipt attached",
                    policy_reference="Policy 2.1",
                ),
            ],
            recommended_action=ApprovalAction.REQUIRE_REVIEW,
            notes="Needs manager approval",
        )
        json_str = original.model_dump_json()
        restored = PolicyCheckResult.model_validate_json(json_str)
        assert restored.expense_id == eid
        assert len(restored.violations) == 1
        assert restored.violations[0].violation_type == PolicyViolationType.MISSING_RECEIPT

    def test_fraud_analysis_roundtrip(self):
        eid = uuid.uuid4()
        similar = [uuid.uuid4(), uuid.uuid4()]
        original = FraudAnalysis(
            expense_id=eid,
            risk_level=FraudRiskLevel.CRITICAL,
            risk_score=0.95,
            indicators=["amount_anomaly", "velocity_check"],
            explanation="Unusually high amount",
            similar_expenses=similar,
        )
        json_str = original.model_dump_json()
        restored = FraudAnalysis.model_validate_json(json_str)
        assert restored.expense_id == eid
        assert restored.similar_expenses == similar

    def test_health_check_roundtrip(self):
        original = HealthCheck(
            service="api",
            version="1.0.0",
            uptime_seconds=7200.0,
            dependencies={"db": "ok"},
        )
        json_str = original.model_dump_json()
        restored = HealthCheck.model_validate_json(json_str)
        assert restored == original
