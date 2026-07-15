"""
Tests for gateway security hardening: credential validation, production
fail-fast, security headers, and upload size/type limits.
"""
import io
import json
from unittest.mock import AsyncMock

import bcrypt
import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

from src.main import app, create_token, settings


@pytest.fixture(autouse=True)
def _setup_app_state():
    app.state.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.state.http_client = AsyncMock(spec=httpx.AsyncClient)
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _auth_users_config() -> str:
    pw_hash = bcrypt.hashpw(b"correct horse", bcrypt.gensalt(rounds=4)).decode()
    return json.dumps(
        {
            "finance@corp.com": {
                "password_hash": pw_hash,
                "role": "finance",
                "org": "org-1",
                "user_id": "user-1",
            }
        }
    )


class TestCredentialValidation:
    def test_configured_user_with_correct_password_gets_token(self, client, monkeypatch):
        monkeypatch.setattr(settings, "auth_users", _auth_users_config())
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "finance@corp.com", "password": "correct horse"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_wrong_password_rejected(self, client, monkeypatch):
        monkeypatch.setattr(settings, "auth_users", _auth_users_config())
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "finance@corp.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_unknown_user_rejected_with_same_error(self, client, monkeypatch):
        monkeypatch.setattr(settings, "auth_users", _auth_users_config())
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@corp.com", "password": "correct horse"},
        )
        assert response.status_code == 401
        # Identical detail to the wrong-password case: no account enumeration
        assert response.json()["detail"] == "Invalid credentials"

    def test_production_without_auth_users_disables_login(self, client, monkeypatch):
        monkeypatch.setattr(settings, "auth_users", "")
        monkeypatch.setattr(settings, "environment", "production")
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "any@corp.com", "password": "anything"},
        )
        assert response.status_code == 503

    def test_dev_demo_mode_still_works_without_auth_users(self, client, monkeypatch):
        monkeypatch.setattr(settings, "auth_users", "")
        monkeypatch.setattr(settings, "environment", "development")
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "any@corp.com", "password": "anything"},
        )
        assert response.status_code == 200

    def test_unset_environment_fails_closed(self, client, monkeypatch):
        # An empty/unknown ENVIRONMENT must be treated as production,
        # not as permission for demo logins
        monkeypatch.setattr(settings, "auth_users", "")
        monkeypatch.setattr(settings, "environment", "")
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "any@corp.com", "password": "anything"},
        )
        assert response.status_code == 503

    def test_login_rate_limited_per_ip(self, monkeypatch):
        # All 5 requests must share one event loop (fakeredis connections are
        # loop-bound), so drive the ASGI app directly instead of TestClient
        import asyncio

        monkeypatch.setattr(settings, "login_rate_limit_per_minute", 3)

        async def run() -> list[int]:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                return [
                    (
                        await ac.post(
                            "/api/v1/auth/login",
                            json={"email": "any@corp.com", "password": "x"},
                        )
                    ).status_code
                    for _ in range(5)
                ]

        responses = asyncio.run(run())
        assert responses[:3] == [200, 200, 200]
        assert responses[3] == 429
        assert responses[4] == 429


class TestSecurityHeaders:
    def test_headers_present_on_api_responses(self, client):
        response = client.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"

    def test_api_responses_are_not_cacheable(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "any@corp.com", "password": "x"},
        )
        assert response.headers["Cache-Control"] == "no-store"


class TestUploadLimits:
    def _headers(self):
        token = create_token("u1", "o1", "employee")
        return {"Authorization": f"Bearer {token}"}

    def test_disallowed_content_type_rejected(self, client):
        response = client.post(
            "/api/v1/expenses/upload",
            headers=self._headers(),
            files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        )
        assert response.status_code == 415

    def test_oversized_file_rejected(self, client, monkeypatch):
        monkeypatch.setattr(settings, "max_upload_mb", 1)
        big = io.BytesIO(b"x" * (1024 * 1024 + 1))
        response = client.post(
            "/api/v1/expenses/upload",
            headers=self._headers(),
            files={"file": ("big.pdf", big, "application/pdf")},
        )
        assert response.status_code == 413

    def test_batch_requires_csv_or_excel(self, client):
        token = create_token("u1", "o1", "finance")
        response = client.post(
            "/api/v1/batch/process",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("data.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
        assert response.status_code == 415

    def test_batch_enqueues_by_task_name(self, client):
        from unittest.mock import MagicMock

        fake_celery = MagicMock()
        fake_celery.send_task.return_value = MagicMock(id="task-123")
        app.state.celery = fake_celery

        token = create_token("u1", "o1", "finance")
        response = client.post(
            "/api/v1/batch/process",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("data.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
        )
        assert response.status_code == 200
        assert response.json() == {"batch_id": "task-123", "status": "queued"}
        name, kwargs = (
            fake_celery.send_task.call_args.args[0],
            fake_celery.send_task.call_args.kwargs,
        )
        # Task name and queue must match the worker's task_routes
        assert name == "tasks.process_batch"
        assert kwargs["queue"] == "batch_processing"


class TestInternalHeaders:
    def test_header_attached_when_token_set(self, monkeypatch):
        from src.main import internal_headers

        monkeypatch.setenv("INTERNAL_API_TOKEN", "svc-secret")
        assert internal_headers() == {"X-Internal-Token": "svc-secret"}

    def test_no_header_when_unset(self, monkeypatch):
        from src.main import internal_headers

        monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)
        assert internal_headers() == {}


class TestAuditEndpoint:
    def _headers(self, role):
        return {"Authorization": f"Bearer {create_token('u1', 'org-1', role)}"}

    def test_employee_cannot_read_audit(self, client):
        resp = client.get("/api/v1/audit/exp-1", headers=self._headers("employee"))
        assert resp.status_code == 403

    def test_finance_reads_audit_records(self, client, monkeypatch):
        from unittest.mock import AsyncMock

        import src.main as main

        records = [{"decision_type": "policy_verdict", "decision": "auto_approve"}]
        monkeypatch.setattr(main, "fetch_decisions", AsyncMock(return_value=records))
        resp = client.get("/api/v1/audit/exp-1", headers=self._headers("finance"))
        assert resp.status_code == 200
        assert resp.json() == {"expense_id": "exp-1", "decisions": records}

    def test_unreachable_audit_store_is_503(self, client, monkeypatch):
        from unittest.mock import AsyncMock

        import src.main as main

        monkeypatch.setattr(main, "fetch_decisions", AsyncMock(side_effect=OSError("down")))
        resp = client.get("/api/v1/audit/exp-1", headers=self._headers("admin"))
        assert resp.status_code == 503


# NOTE: keep this class LAST — importlib.reload mutates src.main's
# module dict in place, which breaks endpoint tests that run after it.
class TestProductionFailFast:
    def test_dev_secret_rejected_in_production(self):
        # Re-import the module with production env + default secret
        import importlib
        import os

        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("JWT_SECRET", None)
        try:
            import src.main as main_module

            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                importlib.reload(main_module)
        finally:
            os.environ["ENVIRONMENT"] = "development"
            import src.main as main_module

            importlib.reload(main_module)
