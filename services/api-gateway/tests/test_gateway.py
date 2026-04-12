"""
Tests for API Gateway - Authentication, rate limiting, routing, and error handling.
"""
import time
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from src.main import app, create_token, settings


@pytest.fixture(autouse=True)
def _setup_app_state():
    """Provide a fake Redis and mock HTTP client for every test."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    app.state.redis = fake_redis
    app.state.http_client = mock_http
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


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
def manager_token():
    return create_token(
        user_id="mgr-user-555",
        org_id="test-org-456",
        role="manager",
    )


@pytest.fixture
def finance_token():
    return create_token(
        user_id="fin-user-666",
        org_id="test-org-456",
        role="finance",
    )


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def manager_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture
def finance_headers(finance_token):
    return {"Authorization": f"Bearer {finance_token}"}


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
        assert data["expires_in"] == settings.jwt_expiration_minutes * 60

    def test_login_token_is_valid_jwt(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@corp.com", "password": "secret"},
        )
        token = response.json()["access_token"]
        decoded = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert "sub" in decoded
        assert "org" in decoded
        assert "role" in decoded
        assert decoded["role"] == "employee"

    def test_invalid_token_rejected(self, client):
        response = client.get(
            "/api/v1/expenses",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_missing_token_rejected(self, client):
        response = client.get("/api/v1/expenses")
        assert response.status_code in (401, 403)  # Depends on FastAPI/Starlette version

    def test_expired_token_rejected(self, client):
        payload = {
            "sub": "user-123",
            "org": "org-456",
            "role": "employee",
            "exp": int(time.time()) - 3600,
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
        assert decoded["sub"] == "test-user-123"
        assert decoded["org"] == "test-org-456"
        assert decoded["role"] == "employee"
        assert "exp" in decoded


# =========================================================================
# Role-Based Access Control Tests
# =========================================================================


class TestRoleBasedAccess:
    def test_employee_cannot_approve(self, client, auth_headers):
        """Regular employees must not be able to approve expenses."""
        response = client.post(
            "/api/v1/expenses/exp-123/approve",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "permissions" in response.json()["detail"].lower()

    def test_manager_can_approve(self, client, manager_headers):
        app.state.http_client.post.return_value = httpx.Response(
            200, json={"expense_id": "exp-123", "status": "approved"}
        )
        response = client.post(
            "/api/v1/expenses/exp-123/approve",
            headers=manager_headers,
        )
        assert response.status_code == 200

    def test_admin_can_approve(self, client, admin_headers):
        app.state.http_client.post.return_value = httpx.Response(
            200, json={"expense_id": "exp-123", "status": "approved"}
        )
        response = client.post(
            "/api/v1/expenses/exp-123/approve",
            headers=admin_headers,
        )
        assert response.status_code == 200

    def test_finance_can_approve(self, client, finance_headers):
        app.state.http_client.post.return_value = httpx.Response(
            200, json={"expense_id": "exp-123", "status": "approved"}
        )
        response = client.post(
            "/api/v1/expenses/exp-123/approve",
            headers=finance_headers,
        )
        assert response.status_code == 200

    def test_employee_cannot_create_policy(self, client, auth_headers):
        response = client.post(
            "/api/v1/policies",
            headers=auth_headers,
            json={"name": "Travel Policy", "rules": []},
        )
        assert response.status_code == 403

    def test_admin_can_create_policy(self, client, admin_headers):
        app.state.http_client.post.return_value = httpx.Response(
            200, json={"policy_id": "pol-1", "name": "Travel Policy"}
        )
        response = client.post(
            "/api/v1/policies",
            headers=admin_headers,
            json={"name": "Travel Policy", "rules": []},
        )
        assert response.status_code == 200

    def test_employee_cannot_batch_process(self, client, auth_headers):
        response = client.post(
            "/api/v1/batch/process",
            headers=auth_headers,
            files={"file": ("batch.csv", b"col1,col2\n1,2", "text/csv")},
        )
        assert response.status_code == 403


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

    def test_login_requires_password(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 422

    def test_list_expenses_page_zero_rejected(self, client, auth_headers):
        response = client.get(
            "/api/v1/expenses?page=0",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_expenses_page_negative_rejected(self, client, auth_headers):
        response = client.get(
            "/api/v1/expenses?page=-1",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_expenses_page_size_too_large(self, client, auth_headers):
        response = client.get(
            "/api/v1/expenses?page_size=500",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_expenses_page_size_zero_rejected(self, client, auth_headers):
        response = client.get(
            "/api/v1/expenses?page_size=0",
            headers=auth_headers,
        )
        assert response.status_code == 422


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
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data

    def test_deep_health_checks_dependencies(self, client):
        """Deep health endpoint checks Redis and all downstream services."""
        # Mock downstream health checks
        app.state.http_client.get.return_value = httpx.Response(
            200, json={"status": "ok"}
        )
        response = client.get("/api/v1/health/deep")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        deps = data["dependencies"]
        assert "expense-processor" in deps
        assert "ai-engine" in deps
        assert "policy-engine" in deps
        assert "redis" in deps

    def test_deep_health_shows_degraded_on_failure(self, client):
        """If a downstream service is down, deep health reports degraded."""
        app.state.http_client.get.side_effect = httpx.ConnectError("connection refused")
        response = client.get("/api/v1/health/deep")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["expense-processor"] == "unhealthy"


# =========================================================================
# Expense Route Tests
# =========================================================================


class TestExpenseRoutes:
    def test_upload_expense(self, client, auth_headers):
        app.state.http_client.post.return_value = httpx.Response(
            200, json={"expense_id": "exp-abc", "status": "processing"}
        )
        response = client.post(
            "/api/v1/expenses/upload",
            headers=auth_headers,
            files={"file": ("receipt.jpg", b"fake-image-data", "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["expense_id"] == "exp-abc"
        assert data["status"] == "processing"

    def test_upload_expense_processor_down(self, client, auth_headers):
        app.state.http_client.post.return_value = httpx.Response(500, text="error")
        response = client.post(
            "/api/v1/expenses/upload",
            headers=auth_headers,
            files={"file": ("receipt.jpg", b"data", "image/jpeg")},
        )
        assert response.status_code == 502

    def test_list_expenses(self, client, auth_headers):
        app.state.http_client.get.return_value = httpx.Response(
            200, json={"items": [], "total": 0}
        )
        response = client.get("/api/v1/expenses", headers=auth_headers)
        assert response.status_code == 200

    def test_get_expense(self, client, auth_headers):
        app.state.http_client.get.return_value = httpx.Response(
            200, json={"expense_id": "exp-1", "amount": 42.50}
        )
        response = client.get("/api/v1/expenses/exp-1", headers=auth_headers)
        assert response.status_code == 200

    def test_get_expense_not_found(self, client, auth_headers):
        app.state.http_client.get.return_value = httpx.Response(404, text="not found")
        response = client.get("/api/v1/expenses/exp-missing", headers=auth_headers)
        assert response.status_code == 404


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
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_blocks_unknown_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") != "http://evil-site.com"
