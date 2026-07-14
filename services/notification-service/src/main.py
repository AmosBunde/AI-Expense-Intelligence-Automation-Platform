"""
Notification Service - delivers expense workflow notifications.

Channels: email (SMTP) and Slack (incoming webhook). Unconfigured channels
degrade to a logged no-op with delivered=false — callers are never failed
because notifications are best-effort, but delivery status is always honest.
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .channels.email import send_email
from .channels.slack import send_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

START_TIME = time.time()

app = FastAPI(
    title="Notification Service",
    description="Email/Slack delivery for expense workflow events",
    version="1.0.0",
)


class NotifyRequest(BaseModel):
    channel: str = Field(pattern="^(email|slack)$")
    recipient: str = ""  # email address; ignored for slack (webhook is fixed)
    subject: str = "Expense update"
    message: str
    metadata: dict = Field(default_factory=dict)


class NotifyResponse(BaseModel):
    channel: str
    delivered: bool
    detail: str


@app.post("/notify", response_model=NotifyResponse)
async def notify(req: NotifyRequest) -> NotifyResponse:
    if req.channel == "email":
        delivered, detail = send_email(req.recipient, req.subject, req.message)
    else:
        delivered, detail = await send_slack(req.subject, req.message, req.metadata)

    if not delivered:
        logger.warning("notification not delivered channel=%s detail=%s", req.channel, detail)
    return NotifyResponse(channel=req.channel, delivered=delivered, detail=detail)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "notification-service",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }
