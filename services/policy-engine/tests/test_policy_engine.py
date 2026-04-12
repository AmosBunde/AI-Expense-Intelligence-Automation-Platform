"""
Tests for Policy Engine - Rule evaluation, compliance checking, auto-approval.
"""
import pytest
from fastapi.testclient import TestClient

from services.policy_engine.src.main import (
    app,
    RuleEvaluator,
    PolicyRule,
    DEFAULT_RULES,
)


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# Rule Evaluator Unit Tests
# =========================================================================

class TestAmountLimitRule:
    def test_under_limit_passes(self):
        rule = PolicyRule(
            id="test-limit",
            name="Test",
            description="",
            condition_type="amount_limit",
            parameters={"max_amount": 100.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 50.0})
        assert result is None  # No violation

    def test_over_limit_fails(self):
        rule = PolicyRule(
            id="test-limit",
            name="Meal Limit",
            description="",
            condition_type="amount_limit",
            parameters={"max_amount": 75.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 150.0})
        assert result is not None
        assert result["violation_type"] == "over_limit"
        assert "150" in result["actual_value"]
        assert "75" in result["threshold_value"]

    def test_exact_limit_passes(self):
        rule = PolicyRule(
            id="test-limit",
            name="Test",
            description="",
            condition_type="amount_limit",
            parameters={"max_amount": 100.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 100.0})
        assert result is None  # Exact limit is OK

    def test_no_amount_passes(self):
        rule = PolicyRule(
            id="test-limit",
            name="Test",
            description="",
            condition_type="amount_limit",
            parameters={"max_amount": 100.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": None})
        assert result is None


class TestReceiptRequiredRule:
    def test_over_threshold_without_receipt_fails(self):
        rule = PolicyRule(
            id="receipt-req",
            name="Receipt Required",
            description="",
            condition_type="receipt_required",
            parameters={"threshold": 25.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 50.0, "file_key": None})
        assert result is not None
        assert result["violation_type"] == "missing_receipt"

    def test_over_threshold_with_receipt_passes(self):
        rule = PolicyRule(
            id="receipt-req",
            name="Receipt Required",
            description="",
            condition_type="receipt_required",
            parameters={"threshold": 25.0},
        )
        result = RuleEvaluator.evaluate(
            rule, {"amount": 50.0, "file_key": "s3://receipts/123.jpg"}
        )
        assert result is None

    def test_under_threshold_without_receipt_passes(self):
        rule = PolicyRule(
            id="receipt-req",
            name="Receipt Required",
            description="",
            condition_type="receipt_required",
            parameters={"threshold": 25.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 10.0, "file_key": None})
        assert result is None


class TestWeekendCheck:
    def test_weekday_passes(self):
        rule = PolicyRule(
            id="weekend",
            name="Weekend Check",
            description="",
            condition_type="weekend_check",
        )
        result = RuleEvaluator.evaluate(
            rule, {"transaction_date": "2026-04-13"}  # Monday
        )
        assert result is None

    def test_saturday_fails(self):
        rule = PolicyRule(
            id="weekend",
            name="Weekend Check",
            description="",
            condition_type="weekend_check",
        )
        result = RuleEvaluator.evaluate(
            rule, {"transaction_date": "2026-04-11"}  # Saturday
        )
        assert result is not None
        assert result["violation_type"] == "weekend_expense"

    def test_sunday_fails(self):
        rule = PolicyRule(
            id="weekend",
            name="Weekend Check",
            description="",
            condition_type="weekend_check",
        )
        result = RuleEvaluator.evaluate(
            rule, {"transaction_date": "2026-04-12"}  # Sunday
        )
        assert result is not None

    def test_no_date_passes(self):
        rule = PolicyRule(
            id="weekend",
            name="Weekend Check",
            description="",
            condition_type="weekend_check",
        )
        result = RuleEvaluator.evaluate(rule, {"transaction_date": None})
        assert result is None


class TestAutoApproveRule:
    def test_small_expense_auto_approved(self):
        rule = PolicyRule(
            id="auto-small",
            name="Auto Approve",
            description="",
            condition_type="auto_approve",
            parameters={"max_amount": 50.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 25.0})
        assert result is not None
        assert result.get("_auto_approve") is True

    def test_large_expense_not_auto_approved(self):
        rule = PolicyRule(
            id="auto-small",
            name="Auto Approve",
            description="",
            condition_type="auto_approve",
            parameters={"max_amount": 50.0},
        )
        result = RuleEvaluator.evaluate(rule, {"amount": 100.0})
        assert result is None


class TestFraudRiskRule:
    def test_high_risk_blocked(self):
        rule = PolicyRule(
            id="fraud-block",
            name="Fraud Block",
            description="",
            condition_type="fraud_risk_check",
            parameters={"block_levels": ["high", "critical"]},
        )
        result = RuleEvaluator.evaluate(
            rule, {"fraud_analysis": {"risk_level": "high"}}
        )
        assert result is not None
        assert result["severity"] == "critical"

    def test_low_risk_passes(self):
        rule = PolicyRule(
            id="fraud-block",
            name="Fraud Block",
            description="",
            condition_type="fraud_risk_check",
            parameters={"block_levels": ["high", "critical"]},
        )
        result = RuleEvaluator.evaluate(
            rule, {"fraud_analysis": {"risk_level": "low"}}
        )
        assert result is None


# =========================================================================
# Policy Check API Tests
# =========================================================================

class TestPolicyCheckEndpoint:
    def test_compliant_expense(self, client):
        response = client.post("/check", json={
            "expense_id": "exp-123",
            "organization_id": "org-456",
            "amount": 15.0,
            "category": "meals",
            "merchant_name": "Cafe",
            "transaction_date": "2026-04-13",  # Monday
            "file_key": "s3://receipts/123.jpg",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_compliant"] is True
        assert data["auto_approved"] is True  # Under $50 with receipt

    def test_over_limit_flagged(self, client):
        response = client.post("/check", json={
            "expense_id": "exp-456",
            "organization_id": "org-456",
            "amount": 200.0,
            "category": "meals",
            "merchant_name": "Fancy Restaurant",
            "transaction_date": "2026-04-13",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["is_compliant"] is False
        assert any(v["violation_type"] == "over_limit" for v in data["violations"])

    def test_fraud_risk_rejected(self, client):
        response = client.post("/check", json={
            "expense_id": "exp-789",
            "organization_id": "org-456",
            "amount": 500.0,
            "category": "equipment",
            "fraud_analysis": {"risk_level": "critical"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["recommended_action"] == "reject"

    def test_rules_evaluated_count(self, client):
        response = client.post("/check", json={
            "expense_id": "exp-999",
            "organization_id": "org-456",
            "amount": 30.0,
            "category": "meals",
        })
        data = response.json()
        assert data["rules_evaluated"] > 0


# =========================================================================
# Policy CRUD Tests
# =========================================================================

class TestPolicyCRUD:
    def test_list_policies(self, client):
        response = client.get("/policies?organization_id=org-123")
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert data["total"] > 0

    def test_create_policy(self, client):
        response = client.post("/policies", json={
            "organization_id": "org-123",
            "name": "Custom Rule",
            "description": "Test policy",
            "rules": {"condition": "amount > 1000"},
        })
        assert response.status_code == 200
        assert "id" in response.json()


# =========================================================================
# Default Rules Integrity Tests
# =========================================================================

class TestDefaultRules:
    def test_all_default_rules_have_ids(self):
        for rule in DEFAULT_RULES:
            assert rule.id, f"Rule missing id: {rule.name}"

    def test_all_default_rules_have_valid_condition_type(self):
        valid_types = {
            "amount_limit", "receipt_required", "auto_approve",
            "weekend_check", "duplicate_check", "fraud_risk_check",
        }
        for rule in DEFAULT_RULES:
            assert rule.condition_type in valid_types, \
                f"Invalid condition_type: {rule.condition_type}"

    def test_no_duplicate_rule_ids(self):
        ids = [r.id for r in DEFAULT_RULES]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs found"


# =========================================================================
# Health Check
# =========================================================================

class TestPolicyEngineHealth:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "policy-engine"
