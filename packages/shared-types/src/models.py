"""
Shared domain models for the Expense Intelligence Platform.
All services import from this package to ensure type consistency.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Enums
# =============================================================================

class ExpenseStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    CATEGORIZED = "categorized"
    POLICY_CHECKED = "policy_checked"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"
    PAID = "paid"


class DocumentType(str, Enum):
    RECEIPT = "receipt"
    INVOICE = "invoice"
    BANK_STATEMENT = "bank_statement"
    CREDIT_CARD = "credit_card"
    MANUAL_ENTRY = "manual_entry"


class ExpenseCategory(str, Enum):
    TRAVEL = "travel"
    MEALS = "meals"
    OFFICE_SUPPLIES = "office_supplies"
    SOFTWARE = "software"
    MARKETING = "marketing"
    UTILITIES = "utilities"
    RENT = "rent"
    PROFESSIONAL_SERVICES = "professional_services"
    EQUIPMENT = "equipment"
    INSURANCE = "insurance"
    TRAINING = "training"
    ENTERTAINMENT = "entertainment"
    SHIPPING = "shipping"
    MISCELLANEOUS = "miscellaneous"


class FraudRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyViolationType(str, Enum):
    OVER_LIMIT = "over_limit"
    MISSING_RECEIPT = "missing_receipt"
    DUPLICATE_EXPENSE = "duplicate_expense"
    POLICY_BREACH = "policy_breach"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    UNAPPROVED_VENDOR = "unapproved_vendor"
    WEEKEND_EXPENSE = "weekend_expense"
    SPLIT_EXPENSE = "split_expense"


class ApprovalAction(str, Enum):
    AUTO_APPROVE = "auto_approve"
    REQUIRE_REVIEW = "require_review"
    ESCALATE = "escalate"
    REJECT = "reject"


# =============================================================================
# Core Domain Models
# =============================================================================

class ExtractedField(BaseModel):
    """A single field extracted from a document by the LLM."""
    model_config = ConfigDict(from_attributes=True)

    field_name: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[list[float]] = None  # [x1, y1, x2, y2] normalized


class LineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    description: str
    quantity: float = 1.0
    unit_price: Decimal
    total: Decimal


class ExpenseExtraction(BaseModel):
    """Result of LLM extraction from a document."""
    model_config = ConfigDict(from_attributes=True)

    merchant_name: Optional[str] = None
    merchant_address: Optional[str] = None
    transaction_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    tax_amount: Optional[Decimal] = None
    tip_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    category: Optional[ExpenseCategory] = None
    category_confidence: float = 0.0
    raw_fields: list[ExtractedField] = Field(default_factory=list)


class PolicyViolation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    violation_type: PolicyViolationType
    severity: FraudRiskLevel
    description: str
    policy_reference: str  # e.g., "Policy 3.2.1 - Meal Limit"
    threshold_value: Optional[str] = None
    actual_value: Optional[str] = None


class PolicyCheckResult(BaseModel):
    """Result of checking an expense against company policies."""
    model_config = ConfigDict(from_attributes=True)

    expense_id: uuid.UUID
    is_compliant: bool
    violations: list[PolicyViolation] = Field(default_factory=list)
    recommended_action: ApprovalAction
    auto_approved: bool = False
    notes: str = ""


class FraudAnalysis(BaseModel):
    """AI-generated fraud analysis for an expense."""
    model_config = ConfigDict(from_attributes=True)

    expense_id: uuid.UUID
    risk_level: FraudRiskLevel
    risk_score: float = Field(ge=0.0, le=1.0)
    indicators: list[str] = Field(default_factory=list)
    explanation: str = ""
    similar_expenses: list[uuid.UUID] = Field(default_factory=list)


class ExpenseCreate(BaseModel):
    """Input model for creating a new expense."""
    model_config = ConfigDict(from_attributes=True)

    document_type: DocumentType
    file_key: Optional[str] = None  # S3 key for uploaded document
    raw_text: Optional[str] = None  # For manual or pre-extracted text
    metadata: dict = Field(default_factory=dict)


class Expense(BaseModel):
    """Full expense record as stored in the database."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    organization_id: uuid.UUID
    status: ExpenseStatus = ExpenseStatus.PENDING
    document_type: DocumentType
    file_key: Optional[str] = None
    extraction: Optional[ExpenseExtraction] = None
    category: Optional[ExpenseCategory] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    merchant_name: Optional[str] = None
    transaction_date: Optional[datetime] = None
    policy_check: Optional[PolicyCheckResult] = None
    fraud_analysis: Optional[FraudAnalysis] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# API Response Models
# =============================================================================

class PaginatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False


class SpendSummary(BaseModel):
    """Aggregated spend data for dashboards."""
    model_config = ConfigDict(from_attributes=True)

    period: str  # e.g., "2026-Q1"
    total_spend: Decimal
    by_category: dict[str, Decimal] = Field(default_factory=dict)
    by_department: dict[str, Decimal] = Field(default_factory=dict)
    top_merchants: list[dict] = Field(default_factory=list)
    flagged_count: int = 0
    auto_approved_count: int = 0
    avg_processing_time_seconds: float = 0.0


class HealthCheck(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = "ok"
    service: str
    version: str
    uptime_seconds: float
    dependencies: dict[str, str] = Field(default_factory=dict)
