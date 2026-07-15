"""
Policy Engine - Company expense policy evaluation, auto-approval, and compliance checking.
Uses a rule-based DSL with support for custom policy definitions per organization.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

START_TIME = time.time()

app = FastAPI(title="Policy Engine", version="1.0.0")

# ── Internal service-to-service authentication ───────────────────────────────
# Only the gateway and workers may call this service. When INTERNAL_API_TOKEN
# is set, every request except /health must present it in X-Internal-Token.
# Production refuses to start without a token (fail closed).
import hmac as _hmac

from fastapi.responses import JSONResponse as _JSONResponse

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")

if not INTERNAL_API_TOKEN and os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod"):
    raise RuntimeError(
        "Refusing to start: INTERNAL_API_TOKEN must be set in production "
        "(generate one with `openssl rand -hex 32`)."
    )


@app.middleware("http")
async def require_internal_token(request, call_next):
    if INTERNAL_API_TOKEN and request.url.path != "/health":
        provided = request.headers.get("X-Internal-Token", "")
        if not _hmac.compare_digest(provided.encode(), INTERNAL_API_TOKEN.encode()):
            return _JSONResponse(status_code=401, content={"detail": "Missing or invalid internal token"})
    return await call_next(request)



# =============================================================================
# Rule Definitions
# =============================================================================

class PolicyRule(BaseModel):
    """A single evaluatable policy rule."""
    id: str
    name: str
    description: str
    category: str | None = None  # null = applies to all categories
    condition_type: str  # amount_limit, receipt_required, duplicate_check, etc.
    parameters: dict[str, Any] = {}
    violation_severity: str = "medium"  # low, medium, high, critical
    action_on_violation: str = "require_review"  # auto_approve, require_review, escalate, reject
    is_active: bool = True


# Default policy rules (per-org rules loaded from DB in production)
DEFAULT_RULES: list[PolicyRule] = [
    PolicyRule(
        id="meal-limit",
        name="Meal Expense Limit",
        description="Meals must not exceed $75 per person",
        category="meals",
        condition_type="amount_limit",
        parameters={"max_amount": 75.0, "currency": "USD"},
        violation_severity="medium",
        action_on_violation="require_review",
    ),
    PolicyRule(
        id="travel-limit",
        name="Travel Expense Limit",
        description="Individual travel expenses must not exceed $2,000",
        category="travel",
        condition_type="amount_limit",
        parameters={"max_amount": 2000.0, "currency": "USD"},
        violation_severity="high",
        action_on_violation="escalate",
    ),
    PolicyRule(
        id="receipt-required",
        name="Receipt Required Over $25",
        description="All expenses over $25 must include a receipt",
        category=None,
        condition_type="receipt_required",
        parameters={"threshold": 25.0},
        violation_severity="medium",
        action_on_violation="require_review",
    ),
    PolicyRule(
        id="auto-approve-small",
        name="Auto-Approve Small Expenses",
        description="Expenses under $50 with receipt are auto-approved",
        category=None,
        condition_type="auto_approve",
        parameters={"max_amount": 50.0, "requires_receipt": True},
        violation_severity="low",
        action_on_violation="auto_approve",
    ),
    PolicyRule(
        id="weekend-flag",
        name="Weekend Expense Flag",
        description="Business expenses on weekends require justification",
        category=None,
        condition_type="weekend_check",
        parameters={},
        violation_severity="low",
        action_on_violation="require_review",
    ),
    PolicyRule(
        id="duplicate-check",
        name="Duplicate Expense Detection",
        description="Flag expenses with same merchant and similar amount within 7 days",
        category=None,
        condition_type="duplicate_check",
        parameters={"days_window": 7, "amount_tolerance_pct": 10},
        violation_severity="high",
        action_on_violation="escalate",
    ),
    PolicyRule(
        id="high-risk-fraud",
        name="High Risk Fraud Block",
        description="Automatically reject expenses flagged as high/critical fraud risk",
        category=None,
        condition_type="fraud_risk_check",
        parameters={"block_levels": ["high", "critical"]},
        violation_severity="critical",
        action_on_violation="reject",
    ),
]


# =============================================================================
# Rule Evaluators
# =============================================================================

class RuleEvaluator:
    """Evaluates a single policy rule against expense data."""

    @staticmethod
    def evaluate(rule: PolicyRule, expense_data: dict) -> dict | None:
        """Returns a violation dict if rule is violated, None if compliant."""
        evaluator_map = {
            "amount_limit": RuleEvaluator._check_amount_limit,
            "receipt_required": RuleEvaluator._check_receipt_required,
            "auto_approve": RuleEvaluator._check_auto_approve,
            "weekend_check": RuleEvaluator._check_weekend,
            "duplicate_check": RuleEvaluator._check_duplicate,
            "fraud_risk_check": RuleEvaluator._check_fraud_risk,
        }

        evaluator = evaluator_map.get(rule.condition_type)
        if not evaluator:
            return None

        return evaluator(rule, expense_data)

    @staticmethod
    def _check_amount_limit(rule: PolicyRule, data: dict) -> dict | None:
        amount = data.get("amount")
        if amount is None:
            return None
        max_amount = rule.parameters.get("max_amount", float("inf"))
        if float(amount) > max_amount:
            return {
                "violation_type": "over_limit",
                "severity": rule.violation_severity,
                "description": f"{rule.name}: ${amount} exceeds limit of ${max_amount}",
                "policy_reference": rule.id,
                "threshold_value": str(max_amount),
                "actual_value": str(amount),
            }
        return None

    @staticmethod
    def _check_receipt_required(rule: PolicyRule, data: dict) -> dict | None:
        amount = data.get("amount")
        has_receipt = data.get("file_key") is not None or data.get("has_receipt", False)
        threshold = rule.parameters.get("threshold", 25.0)
        if amount and float(amount) > threshold and not has_receipt:
            return {
                "violation_type": "missing_receipt",
                "severity": rule.violation_severity,
                "description": f"Receipt required for expenses over ${threshold}",
                "policy_reference": rule.id,
                "threshold_value": str(threshold),
                "actual_value": str(amount),
            }
        return None

    @staticmethod
    def _check_auto_approve(rule: PolicyRule, data: dict) -> dict | None:
        """Returns a special marker for auto-approval eligibility."""
        amount = data.get("amount")
        max_amount = rule.parameters.get("max_amount", 50.0)
        if amount and float(amount) <= max_amount:
            return {"_auto_approve": True}
        return None

    @staticmethod
    def _check_weekend(rule: PolicyRule, data: dict) -> dict | None:
        date_str = data.get("transaction_date")
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(str(date_str))
            if dt.weekday() >= 5:  # Saturday or Sunday
                return {
                    "violation_type": "weekend_expense",
                    "severity": rule.violation_severity,
                    "description": "Business expense submitted for a weekend date",
                    "policy_reference": rule.id,
                    "threshold_value": "weekday",
                    "actual_value": dt.strftime("%A"),
                }
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def _check_duplicate(rule: PolicyRule, data: dict) -> dict | None:
        # In production: query DB for similar recent expenses
        return None

    @staticmethod
    def _check_fraud_risk(rule: PolicyRule, data: dict) -> dict | None:
        # `fraud_analysis` may be present but explicitly null (expense not
        # yet analyzed) — `or {}` covers both missing and None
        fraud = data.get("fraud_analysis") or {}
        risk_level = fraud.get("risk_level", "low")
        block_levels = rule.parameters.get("block_levels", ["high", "critical"])
        if risk_level in block_levels:
            return {
                "violation_type": "suspicious_pattern",
                "severity": "critical",
                "description": f"AI fraud detection flagged as {risk_level} risk",
                "policy_reference": rule.id,
                "threshold_value": "low/medium",
                "actual_value": risk_level,
            }
        return None


# =============================================================================
# API Endpoints
# =============================================================================

class PolicyCheckRequest(BaseModel):
    expense_id: str
    organization_id: str
    amount: float | None = None
    category: str | None = None
    merchant_name: str | None = None
    transaction_date: str | None = None
    file_key: str | None = None
    fraud_analysis: dict | None = None


class PolicyCheckResponse(BaseModel):
    expense_id: str
    is_compliant: bool
    violations: list[dict]
    recommended_action: str
    auto_approved: bool
    rules_evaluated: int
    notes: str



# Decision audit: provided by packages/db-client (on PYTHONPATH in containers).
# Local test runs without it fall back to log-only records — auditing must
# never break the decision path either way.
try:
    from audit import record_decision
except ImportError:  # pragma: no cover - container images always have it
    import logging as _logging

    async def record_decision(**kwargs) -> bool:
        _logging.getLogger("decision-audit").info("audit-fallback %s", kwargs)
        return False


@app.post("/check", response_model=PolicyCheckResponse)
async def check_expense(request: PolicyCheckRequest):
    """Evaluate an expense against all active policies."""
    # In production: load org-specific rules from DB
    rules = [r for r in DEFAULT_RULES if r.is_active]

    # Filter rules by category
    applicable_rules = [
        r for r in rules
        if r.category is None or r.category == request.category
    ]

    violations = []
    auto_approve = False
    expense_data = request.model_dump()

    for rule in applicable_rules:
        result = RuleEvaluator.evaluate(rule, expense_data)
        if result:
            if result.get("_auto_approve"):
                auto_approve = True
            else:
                violations.append(result)

    # Determine recommended action
    if any(v.get("severity") == "critical" for v in violations):
        action = "reject"
        auto_approve = False
    elif any(v.get("severity") == "high" for v in violations):
        action = "escalate"
        auto_approve = False
    elif violations:
        action = "require_review"
        auto_approve = False
    elif auto_approve:
        action = "auto_approve"
    else:
        action = "require_review"

    await record_decision(
        expense_id=request.expense_id,
        organization_id=request.organization_id,
        decision_type="policy_verdict",
        decision=action,
        risk_level=(request.fraud_analysis or {}).get("risk_level"),
        rule_ids=[r.id for r in applicable_rules],
        details={
            "violations": violations,
            "auto_approved": auto_approve and len(violations) == 0,
            "amount": request.amount,
            "category": request.category,
        },
    )

    return PolicyCheckResponse(
        expense_id=request.expense_id,
        is_compliant=len(violations) == 0,
        violations=violations,
        recommended_action=action,
        auto_approved=auto_approve and len(violations) == 0,
        rules_evaluated=len(applicable_rules),
        notes=f"Evaluated {len(applicable_rules)} rules, found {len(violations)} violations",
    )


@app.get("/policies")
async def list_policies(organization_id: str):
    """List active policies for an organization."""
    return {
        "policies": [r.model_dump() for r in DEFAULT_RULES if r.is_active],
        "total": len([r for r in DEFAULT_RULES if r.is_active]),
    }


@app.post("/policies")
async def create_policy(policy: dict):
    """Create a new policy rule."""
    # In production: persist to DB
    return {"id": str(uuid.uuid4()), "status": "created", **policy}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "policy-engine",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }
