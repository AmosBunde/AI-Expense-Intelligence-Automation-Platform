"""Internal service-to-service auth: token required for everything but /health."""
import pytest
from fastapi.testclient import TestClient

import src.main as main
from src.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def token_configured(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_TOKEN", "test-internal-secret")


def test_health_is_open_without_token(token_configured):
    assert client.get("/health").status_code == 200


def test_requests_without_token_rejected(token_configured):
    # Middleware runs before routing: even unknown paths must 401
    resp = client.get("/any/path")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing or invalid internal token"


def test_wrong_token_rejected(token_configured):
    resp = client.get("/any/path", headers={"X-Internal-Token": "wrong"})
    assert resp.status_code == 401


def test_valid_token_passes_middleware(token_configured):
    # 404 (not 401) proves the middleware admitted the request to routing
    resp = client.get("/definitely/not/a/route", headers={"X-Internal-Token": "test-internal-secret"})
    assert resp.status_code == 404


def test_open_when_no_token_configured(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_API_TOKEN", "")
    assert client.get("/definitely/not/a/route").status_code == 404


def test_outbound_calls_carry_internal_token(monkeypatch):
    # The processor is a caller too: its ai-engine/policy-engine requests
    # must attach the token or they 401 against hardened services
    monkeypatch.setenv("INTERNAL_API_TOKEN", "outbound-secret")
    assert main._internal_headers() == {"X-Internal-Token": "outbound-secret"}
    monkeypatch.delenv("INTERNAL_API_TOKEN")
    assert main._internal_headers() == {}
