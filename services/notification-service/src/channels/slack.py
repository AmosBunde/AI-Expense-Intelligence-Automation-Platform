"""Slack incoming-webhook channel. No-op (delivered=false) when unconfigured."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("notification-service.slack")


async def send_slack(subject: str, message: str, metadata: dict) -> tuple[bool, str]:
    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook:
        logger.info("Slack webhook not configured; would post subject=%r", subject)
        return False, "slack-not-configured"

    fields = [f"*{k}:* {v}" for k, v in metadata.items()]
    payload = {"text": "\n".join([f"*{subject}*", message, *fields])}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook, json=payload)
        if resp.status_code == 200:
            return True, "sent"
        return False, f"slack-status-{resp.status_code}"
    except httpx.HTTPError as exc:
        logger.error("Slack post failed: %s", exc)
        return False, f"slack-error: {exc}"
