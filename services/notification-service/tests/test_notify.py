"""Tests for the notification service: channels, fallbacks, honesty of status."""
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "notification-service"


def test_email_unconfigured_is_honest_noop():
    os.environ.pop("SMTP_HOST", None)
    resp = client.post(
        "/notify",
        json={"channel": "email", "recipient": "a@b.com", "message": "hi"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["delivered"] is False
    assert body["detail"] == "smtp-not-configured"


def test_slack_unconfigured_is_honest_noop():
    os.environ.pop("SLACK_WEBHOOK_URL", None)
    resp = client.post("/notify", json={"channel": "slack", "message": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {
        "channel": "slack",
        "delivered": False,
        "detail": "slack-not-configured",
    }


def test_unknown_channel_rejected():
    resp = client.post("/notify", json={"channel": "carrier-pigeon", "message": "hi"})
    assert resp.status_code == 422


def test_email_sends_when_configured():
    with patch.dict(os.environ, {"SMTP_HOST": "smtp.test"}), patch("src.channels.email.smtplib.SMTP") as smtp:
        resp = client.post(
            "/notify",
            json={
                "channel": "email",
                "recipient": "fin@corp.com",
                "subject": "Expense approved",
                "message": "exp-1 approved",
            },
        )
    assert resp.json()["delivered"] is True
    smtp.assert_called_once()
    sent = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert sent["To"] == "fin@corp.com"
    assert sent["Subject"] == "Expense approved"


def test_email_requires_recipient_when_configured():
    with patch.dict(os.environ, {"SMTP_HOST": "smtp.test"}):
        resp = client.post("/notify", json={"channel": "email", "message": "hi"})
    assert resp.json() == {"channel": "email", "delivered": False, "detail": "no-recipient"}
