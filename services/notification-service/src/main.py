"""
Notification Service - delivers expense workflow notifications.

Channels: email (SMTP) and Slack (incoming webhook). Unconfigured channels
degrade to a logged no-op with delivered=false — callers are never failed
because notifications are best-effort, but delivery status is always honest.
"""
from __future__ import annotations

import logging
import os
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
