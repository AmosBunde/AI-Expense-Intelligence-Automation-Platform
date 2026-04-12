"""
API Gateway - Central entry point for the Expense Intelligence Platform.
Handles authentication, rate limiting, request routing, and response aggregation.
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Annotated

import httpx
import jwt
import redis.asyncio as redis
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

START_TIME = time.time()


# =============================================================================
# Configuration
# =============================================================================

class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    expense_processor_url: str = os.getenv("EXPENSE_PROCESSOR_URL", "http://localhost:8002")
    ai_engine_url: str = os.getenv("AI_ENGINE_URL", "http://localhost:8001")
    policy_engine_url: str = os.getenv("POLICY_ENGINE_URL", "http://localhost:8003")
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    s3_bucket: str = os.getenv("S3_BUCKET", "expense-documents")
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")


settings = Settings()


# =============================================================================
# Lifespan & Dependencies
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.redis.close()
    await app.state.http_client.aclose()


app = FastAPI(
    title="AI Expense Intelligence Platform",
    description="API Gateway for expense processing, AI analysis, and policy enforcement",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# =============================================================================
# Auth & Middleware
# =============================================================================

class TokenPayload(BaseModel):
    sub: str  # user_id
    org: str  # organization_id
    role: str
    exp: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def create_token(user_id: str, org_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "org": org_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> TokenPayload:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def rate_limit(user: TokenPayload = Depends(get_current_user)):
    """Sliding window rate limiter using Redis."""
    r = app.state.redis
    key = f"rate:{user.sub}"
    now = time.time()
    window_start = now - 60

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, 120)
    results = await pipe.execute()
    request_count = results[2]

    if request_count > settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return user


# =============================================================================
# Routes: Auth
# =============================================================================

@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(request: LoginRequest):
    """Authenticate and receive a JWT token."""
    # In production: validate against database with bcrypt
    # Stub for demonstration
    token = create_token(
        user_id=str(uuid.uuid4()),
        org_id=str(uuid.uuid4()),
        role="employee",
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


# =============================================================================
# Routes: Expenses
# =============================================================================

class ExpenseUploadResponse(BaseModel):
    expense_id: str
    status: str
    message: str


@app.post(
    "/api/v1/expenses/upload",
    response_model=ExpenseUploadResponse,
    tags=["expenses"],
)
async def upload_expense(
    file: UploadFile = File(...),
    document_type: str = Query(default="receipt"),
    user: TokenPayload = Depends(rate_limit),
):
    """Upload a receipt/invoice for AI processing."""
    # 1. Upload file to S3
    file_key = f"{user.org}/{user.sub}/{uuid.uuid4()}/{file.filename}"
    file_content = await file.read()

    # 2. Forward to expense processor
    client: httpx.AsyncClient = app.state.http_client
    response = await client.post(
        f"{settings.expense_processor_url}/process",
        json={
            "file_key": file_key,
            "document_type": document_type,
            "user_id": user.sub,
            "organization_id": user.org,
            "file_content_b64": __import__("base64").b64encode(file_content).decode(),
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Expense processor unavailable")

    data = response.json()
    return ExpenseUploadResponse(
        expense_id=data["expense_id"],
        status="processing",
        message="Expense submitted for AI extraction and policy check",
    )


@app.get("/api/v1/expenses", tags=["expenses"])
async def list_expenses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = None,
    category: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user: TokenPayload = Depends(rate_limit),
):
    """List expenses with filtering and pagination."""
    # Forward to expense processor which handles DB queries
    client: httpx.AsyncClient = app.state.http_client
    params = {
        "page": page,
        "page_size": page_size,
        "user_id": user.sub,
        "organization_id": user.org,
    }
    if status_filter:
        params["status"] = status_filter
    if category:
        params["category"] = category

    response = await client.get(
        f"{settings.expense_processor_url}/expenses", params=params
    )
    return response.json()


@app.get("/api/v1/expenses/{expense_id}", tags=["expenses"])
async def get_expense(expense_id: str, user: TokenPayload = Depends(rate_limit)):
    """Get full expense details including AI analysis."""
    client: httpx.AsyncClient = app.state.http_client
    response = await client.get(
        f"{settings.expense_processor_url}/expenses/{expense_id}",
        params={"user_id": user.sub},
    )
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Expense not found")
    return response.json()


@app.post("/api/v1/expenses/{expense_id}/approve", tags=["expenses"])
async def approve_expense(expense_id: str, user: TokenPayload = Depends(rate_limit)):
    """Manually approve a flagged expense (manager/admin only)."""
    if user.role not in ("manager", "admin", "finance"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    client: httpx.AsyncClient = app.state.http_client
    response = await client.post(
        f"{settings.expense_processor_url}/expenses/{expense_id}/approve",
        json={"approved_by": user.sub},
    )
    return response.json()


# =============================================================================
# Routes: AI Analysis
# =============================================================================

@app.post("/api/v1/ai/analyze", tags=["ai"])
async def analyze_expense(
    expense_id: str,
    user: TokenPayload = Depends(rate_limit),
):
    """Trigger AI analysis (fraud detection, categorization) for an expense."""
    client: httpx.AsyncClient = app.state.http_client
    response = await client.post(
        f"{settings.ai_engine_url}/analyze",
        json={"expense_id": expense_id, "organization_id": user.org},
    )
    return response.json()


@app.post("/api/v1/ai/chat", tags=["ai"])
async def chat_with_ai(
    message: str,
    expense_id: str | None = None,
    user: TokenPayload = Depends(rate_limit),
):
    """Chat with the AI agent about expenses, policies, or spend patterns."""
    client: httpx.AsyncClient = app.state.http_client
    response = await client.post(
        f"{settings.ai_engine_url}/chat",
        json={
            "message": message,
            "user_id": user.sub,
            "organization_id": user.org,
            "expense_id": expense_id,
        },
    )
    return response.json()


# =============================================================================
# Routes: Dashboard / Analytics
# =============================================================================

@app.get("/api/v1/analytics/spend-summary", tags=["analytics"])
async def get_spend_summary(
    period: str = Query(default="month", regex="^(week|month|quarter|year)$"),
    user: TokenPayload = Depends(rate_limit),
):
    """Get aggregated spend summary for dashboards."""
    client: httpx.AsyncClient = app.state.http_client
    response = await client.get(
        f"{settings.expense_processor_url}/analytics/summary",
        params={"organization_id": user.org, "period": period},
    )
    return response.json()


@app.get("/api/v1/analytics/anomalies", tags=["analytics"])
async def get_anomalies(user: TokenPayload = Depends(rate_limit)):
    """Get flagged anomalies and fraud alerts."""
    client: httpx.AsyncClient = app.state.http_client
    response = await client.get(
        f"{settings.ai_engine_url}/anomalies",
        params={"organization_id": user.org},
    )
    return response.json()


# =============================================================================
# Routes: Policies
# =============================================================================

@app.get("/api/v1/policies", tags=["policies"])
async def list_policies(user: TokenPayload = Depends(rate_limit)):
    """List active company expense policies."""
    client: httpx.AsyncClient = app.state.http_client
    response = await client.get(
        f"{settings.policy_engine_url}/policies",
        params={"organization_id": user.org},
    )
    return response.json()


@app.post("/api/v1/policies", tags=["policies"])
async def create_policy(policy: dict, user: TokenPayload = Depends(rate_limit)):
    """Create a new expense policy (admin only)."""
    if user.role not in ("admin", "finance"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    client: httpx.AsyncClient = app.state.http_client
    response = await client.post(
        f"{settings.policy_engine_url}/policies",
        json={**policy, "organization_id": user.org},
    )
    return response.json()


# =============================================================================
# Routes: Batch Operations
# =============================================================================

@app.post("/api/v1/batch/process", tags=["batch"])
async def trigger_batch(
    file: UploadFile = File(...),
    user: TokenPayload = Depends(rate_limit),
):
    """Upload CSV/Excel batch of transactions for processing."""
    if user.role not in ("admin", "finance"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    content = await file.read()
    # Queue batch job via Celery
    from packages.queue_client.tasks import process_batch
    task = process_batch.delay(
        file_content_b64=__import__("base64").b64encode(content).decode(),
        filename=file.filename,
        organization_id=user.org,
        user_id=user.sub,
    )
    return {"batch_id": task.id, "status": "queued"}


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }


@app.get("/api/v1/health/deep", tags=["system"])
async def deep_health():
    """Check all downstream service health."""
    client: httpx.AsyncClient = app.state.http_client
    deps = {}
    for name, url in [
        ("expense-processor", settings.expense_processor_url),
        ("ai-engine", settings.ai_engine_url),
        ("policy-engine", settings.policy_engine_url),
    ]:
        try:
            r = await client.get(f"{url}/health", timeout=5.0)
            deps[name] = "healthy" if r.status_code == 200 else "degraded"
        except Exception:
            deps[name] = "unhealthy"

    try:
        await app.state.redis.ping()
        deps["redis"] = "healthy"
    except Exception:
        deps["redis"] = "unhealthy"

    overall = "ok" if all(v == "healthy" for v in deps.values()) else "degraded"
    return {"status": overall, "dependencies": deps}
