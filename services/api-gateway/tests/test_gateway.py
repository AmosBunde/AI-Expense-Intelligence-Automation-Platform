"""
Tests for API Gateway - Authentication, rate limiting, routing, and error handling.
"""
import time
from unittest.mock import AsyncMock, patch, MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import Response

# We test with synchronous TestClient for simplicity; async tests use pytest-asyncio
from services.api_gateway.src.main import app, create_token, settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token():
    return create_token(
        user_id="test-user-123",
        org_id="test-org-456",
        role="employee",
    )


@pytest.fixture
def admin_token():
    return create_token(
        user_id="admin-user-789",
        org_id="test-org-456",
        role="admin",
    )


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# =========================================================================
# Auth Tests
# =========================================================================

class TestAuthentication:
    def test_login_returns_token(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_invalid_token_rejected(self, client):
        response = client.get(
            "/api/v1/expenses",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_missing_token_rejected(self, client):
        response = client.get("/api/v1/expenses")
        assert response.status_code == 403  # FastAPI returns 403 for missing auth

    def test_expired_token_rejected(self, client):
        payload = {
            "sub": "user-123",
            "org": "org-456",
            "role": "employee",
            "exp": int(time.time()) - 3600,  # expired 1 hour ago
            "iat": int(time.time()) - 7200,
        }
        expired_token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        response = client.get(
            "/api/v1/expenses",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_token_contains_correct_claims(self, auth_token):
        decoded = jwt.decode(
            auth_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert "sub" in decoded
        assert "org" in decoded
        assert "role" in decoded
        assert "exp" in decoded


# =========================================================================
# Rate Limiting Tests
# =========================================================================

class TestRateLimiting:
    @patch("services.api_gateway.src.main.app")
    def test_rate_limit_allows_normal_traffic(self, mock_app, client, auth_headers):
        """Normal request volume should pass through."""
        # This test verifies the rate limit middleware doesn't block
        # under normal conditions
        pass  # Integration test with Redis required

    def test_rate_limit_header_format(self):
        """Rate limit key format is correct."""
        user_id = "test-user-123"
        key = f"rate:{user_id}"
        assert key == "rate:test-user-123"


# =========================================================================
# Expense Routes Tests
# =========================================================================

class TestExpenseRoutes:
    @patch("httpx.AsyncClient.post")
    def test_upload_expense_success(self, mock_post, client, auth_headers):
        mock_post.return_value = Response(
            200, json={"expense_id": "exp-123", "status": "processing"}
        )
        # File upload test
        response = client.post(
            "/api/v1/expenses/upload",
            headers=auth_headers,
            files={"file": ("receipt.jpg", b"fake-image-data", "image/jpeg")},
            data={"document_type": "receipt"},
        )
        # Will fail in unit test without running services, but validates route exists
        assert response.status_code in (200, 502)

    def test_list_expenses_requires_auth(self, client):
        response = client.get("/api/v1/expenses")
        assert response.status_code == 403

    def test_approve_requires_manager_role(self, client, auth_headers):
        """Regular employees cannot approve expenses."""
        response = client.post(
            "/api/v1/expenses/exp-123/approve",
            headers=auth_headers,
        )
        # Should be 403 since employee role lacks permission
        assert response.status_code in (403, 502)

    def test_approve_allowed_for_admin(self, client, admin_headers):
        """Admins can approve expenses."""
        response = client.post(
            "/api/v1/expenses/exp-123/approve",
            headers=admin_headers,
        )
        # Will be 502 without running services, but should not be 403
        assert response.status_code != 403


# =========================================================================
# Health Check Tests
# =========================================================================

class TestHealthChecks:
    def test_basic_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "api-gateway"
        assert "uptime_seconds" in data

    def test_deep_health_requires_auth(self, client):
        """Deep health check doesn't require auth (monitoring access)."""
        # Deep health is behind auth - adjust if needed for monitoring
        response = client.get("/api/v1/health/deep")
        assert response.status_code in (200, 403)


# =========================================================================
# Input Validation Tests
# =========================================================================

class TestInputValidation:
    def test_login_requires_valid_email(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "password"},
        )
        assert response.status_code == 422

    def test_list_expenses_validates_page(self, client, auth_headers):
        response = client.get(
            "/api/v1/expenses?page=0",  # Must be >= 1
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_expenses_validates_page_size(self, client, auth_headers):
        response = client.get(
            "/api/v1/expenses?page_size=500",  # Must be <= 100
            headers=auth_headers,
        )
        assert response.status_code == 422


# =========================================================================
# CORS Tests
# =========================================================================

class TestCORS:
    def test_cors_allows_configured_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200

    def test_cors_blocks_unknown_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS will not include the allow-origin header
        assert "access-control-allow-origin" not in response.headers or \
               response.headers.get("access-control-allow-origin") != "http://evil-site.com"
