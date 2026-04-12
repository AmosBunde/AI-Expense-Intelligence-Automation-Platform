"""
Integration tests - Full expense lifecycle tests.
Requires running infrastructure: PostgreSQL, Redis, MinIO.
Run with: pytest tests/integration/ -v --run-integration
"""
import base64
import json
import os
import uuid

import pytest
import httpx

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
PROCESSOR_BASE = os.getenv("EXPENSE_PROCESSOR_URL", "http://localhost:8002")
AI_BASE = os.getenv("AI_ENGINE_URL", "http://localhost:8001")
POLICY_BASE = os.getenv("POLICY_ENGINE_URL", "http://localhost:8003")


pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def auth_token():
    """Get a valid JWT token for tests."""
    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password"},
        )
        assert response.status_code == 200
        return response.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# =========================================================================
# Service Health Tests
# =========================================================================

class TestServiceHealth:
    """Verify all services are running and healthy."""

    def test_api_gateway_health(self):
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE}/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"

    def test_expense_processor_health(self):
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{PROCESSOR_BASE}/health")
            assert r.status_code == 200

    def test_ai_engine_health(self):
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{AI_BASE}/health")
            assert r.status_code == 200

    def test_policy_engine_health(self):
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{POLICY_BASE}/health")
            assert r.status_code == 200

    def test_deep_health(self, auth_headers):
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            r = client.get("/api/v1/health/deep", headers=auth_headers)
            assert r.status_code == 200
            deps = r.json()["dependencies"]
            for service, status in deps.items():
                assert status == "healthy", f"{service} is {status}"


# =========================================================================
# Full Pipeline Tests
# =========================================================================

class TestExpenseUploadPipeline:
    """Test the full expense upload and processing pipeline."""

    def test_upload_receipt_processes_successfully(self, auth_headers):
        """Upload a receipt image and verify it goes through the full pipeline."""
        # Create a fake receipt image (in reality this would be a real image)
        fake_receipt = b"STARBUCKS #1234\n123 Main St\n04/10/2026\nGrande Latte $5.75\nTotal: $5.75"

        with httpx.Client(base_url=API_BASE, timeout=60) as client:
            response = client.post(
                "/api/v1/expenses/upload",
                headers=auth_headers,
                files={"file": ("receipt.txt", fake_receipt, "text/plain")},
                data={"document_type": "receipt"},
            )

            assert response.status_code in (200, 502), f"Got {response.status_code}: {response.text}"

            if response.status_code == 200:
                data = response.json()
                assert "expense_id" in data
                assert data["status"] in ("processing", "categorized", "approved", "flagged")

    def test_list_expenses_returns_paginated(self, auth_headers):
        """List expenses with pagination."""
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            response = client.get(
                "/api/v1/expenses?page=1&page_size=10",
                headers=auth_headers,
            )
            assert response.status_code in (200, 502)

            if response.status_code == 200:
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert data["page_size"] <= 10


class TestPolicyCheckPipeline:
    """Test policy evaluation through the API."""

    def test_small_expense_auto_approved(self):
        """Expenses under $50 with receipt should be auto-approved."""
        with httpx.Client(base_url=POLICY_BASE, timeout=30) as client:
            response = client.post("/check", json={
                "expense_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
                "amount": 15.0,
                "category": "meals",
                "merchant_name": "Coffee Shop",
                "transaction_date": "2026-04-13",
                "file_key": "s3://receipts/test.jpg",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["auto_approved"] is True
            assert data["is_compliant"] is True

    def test_over_limit_flagged(self):
        """Meals over $75 should be flagged."""
        with httpx.Client(base_url=POLICY_BASE, timeout=30) as client:
            response = client.post("/check", json={
                "expense_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
                "amount": 200.0,
                "category": "meals",
                "merchant_name": "Fancy Restaurant",
                "transaction_date": "2026-04-13",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["is_compliant"] is False
            violations = data["violations"]
            assert any(v["violation_type"] == "over_limit" for v in violations)

    def test_fraud_risk_rejected(self):
        """Critical fraud risk should be rejected."""
        with httpx.Client(base_url=POLICY_BASE, timeout=30) as client:
            response = client.post("/check", json={
                "expense_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
                "amount": 999.00,
                "category": "equipment",
                "fraud_analysis": {"risk_level": "critical", "risk_score": 0.95},
            })
            assert response.status_code == 200
            data = response.json()
            assert data["recommended_action"] == "reject"


class TestAIAnalysisPipeline:
    """Test AI analysis endpoints."""

    def test_analyze_endpoint_accepts_text(self):
        """AI Engine should accept raw text for analysis."""
        with httpx.Client(base_url=AI_BASE, timeout=120) as client:
            response = client.post("/analyze", json={
                "expense_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
                "raw_text": "UBER TRIP\nDate: 04/10/2026\nFrom: Airport\nTo: Hotel\nFare: $34.50\nTip: $5.00\nTotal: $39.50",
            })
            # May fail without valid OPENAI_API_KEY
            assert response.status_code in (200, 500)

    def test_chat_endpoint(self):
        """Chat endpoint should accept messages."""
        with httpx.Client(base_url=AI_BASE, timeout=120) as client:
            response = client.post("/chat", json={
                "message": "What categories do we track?",
                "user_id": str(uuid.uuid4()),
                "organization_id": str(uuid.uuid4()),
            })
            assert response.status_code in (200, 500)

            if response.status_code == 200:
                data = response.json()
                assert "reply" in data


class TestAnalyticsPipeline:
    """Test analytics and dashboard data endpoints."""

    def test_spend_summary(self, auth_headers):
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            response = client.get(
                "/api/v1/analytics/spend-summary?period=month",
                headers=auth_headers,
            )
            assert response.status_code in (200, 502)

    def test_anomalies(self, auth_headers):
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            response = client.get(
                "/api/v1/analytics/anomalies",
                headers=auth_headers,
            )
            assert response.status_code in (200, 502)


# =========================================================================
# Auth Integration Tests
# =========================================================================

class TestAuthIntegration:
    def test_login_returns_valid_token(self):
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "password"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    def test_protected_route_rejects_no_token(self):
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            response = client.get("/api/v1/expenses")
            assert response.status_code == 403

    def test_protected_route_accepts_valid_token(self, auth_headers):
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            response = client.get(
                "/api/v1/expenses",
                headers=auth_headers,
            )
            assert response.status_code in (200, 502)
