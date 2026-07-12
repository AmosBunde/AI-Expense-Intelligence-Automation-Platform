# AI Expense Intelligence & Automation Platform

[![CI/CD Pipeline](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/ci.yml)
[![Release Images](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/release.yml/badge.svg)](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![React 18](https://img.shields.io/badge/react-18-61dafb)

> An AI-powered system that categorizes, analyzes, and automates business spend workflows. Ingests receipts, invoices, and transaction data. Extracts structured fields via LLM. Enriches with company policies via RAG. Agents flag anomalies, detect fraud, and suggest actions. Automates approvals and categorization. Dashboards show spend insights. Supports real-time inference and batch processing.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Service Ports](#service-ports)
- [Local Development Setup](#local-development-setup)
- [Cloud Deployment](#cloud-deployment)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [Documentation](#documentation)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Gateway (FastAPI)                        │
│              Auth · Rate Limiting · Request Routing                 │
└──────────┬──────────────┬──────────────┬───────────────┬───────────┘
           │              │              │               │
    ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐
    │   Expense   │ │    AI    │ │   Policy    │ │  Dashboard │
    │  Processor  │ │  Engine  │ │   Engine    │ │     UI     │
    │             │ │          │ │             │ │   (React)  │
    │ Extract     │ │ LangGraph│ │ Rules Eval  │ │            │
    │ Normalize   │ │ RAG      │ │ Auto-Approve│ │ Analytics  │
    │ Classify    │ │ Agents   │ │ Fraud Flags │ │ Reports    │
    └──────┬──────┘ └────┬─────┘ └──────┬──────┘ └────────────┘
           │              │              │
    ┌──────▼──────────────▼──────────────▼───────────────────────┐
    │                    Shared Infrastructure                    │
    │  PostgreSQL · Redis · S3/MinIO · Celery/Bull · pgvector    │
    └────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Gateway | Python 3.12, FastAPI, Pydantic v2 |
| AI Engine | LangGraph, LangChain, OpenAI API, pgvector |
| Expense Processor | Python, Tesseract OCR, pdf2image |
| Policy Engine | Python, rule-engine, custom DSL |
| Dashboard | React 18, TypeScript, Recharts, TanStack Query |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Queue | Celery (Redis broker) |
| Storage | AWS S3 / MinIO (local) |
| Containerization | Docker, Docker Compose |
| Orchestration | Kubernetes / AWS ECS |
| IaC | Terraform |
| CI/CD | GitHub Actions |

## Project Structure

```
expense-intelligence-platform/
├── services/
│   ├── api-gateway/          # Request routing, auth, rate limiting
│   ├── expense-processor/    # Document ingestion, OCR, field extraction
│   ├── ai-engine/            # LangGraph agents, RAG, LLM inference
│   ├── policy-engine/        # Company policy rules, auto-approval
│   ├── dashboard-ui/         # React frontend with analytics
│   ├── notification-service/ # Email, Slack, webhook notifications
│   └── batch-processor/      # Scheduled batch jobs, reconciliation
├── packages/
│   ├── shared-types/         # Pydantic models, TypeScript types
│   ├── db-client/            # Database connection, migrations
│   └── queue-client/         # Celery task definitions
├── infrastructure/
│   ├── docker/               # Dockerfiles, compose files
│   ├── k8s/                  # Kubernetes manifests (Kustomize)
│   └── terraform/            # AWS infrastructure as code
├── migrations/               # Alembic database migrations
├── docs/                     # Architecture docs, ADRs, API specs
├── scripts/                  # Dev tooling, seed data, utilities
├── .github/                  # CI/CD workflows, issue templates
└── .claude/skills/           # Claude Code implementation skill
```

## Service Ports

| Service | Port (local) | Swagger docs | Container image |
|---------|-------------|--------------|-----------------|
| API Gateway | 8000 | `http://localhost:8000/docs` | `ghcr.io/amosbunde/expense-api-gateway` |
| AI Engine | 8001 | `http://localhost:8001/docs` | `ghcr.io/amosbunde/expense-ai-engine` |
| Expense Processor | 8002 | `http://localhost:8002/docs` | `ghcr.io/amosbunde/expense-expense-processor` |
| Policy Engine | 8003 | `http://localhost:8003/docs` | `ghcr.io/amosbunde/expense-policy-engine` |
| Notification Service | 8004 | `http://localhost:8004/docs` | — (shares policy-engine image) |
| Batch Processor | 8005 | `http://localhost:8005/docs` | — (shares expense-processor image) |
| Dashboard UI | 5173 (dev) / 80 (container) | — | `ghcr.io/amosbunde/expense-dashboard-ui` |
| PostgreSQL (pgvector) | 5432 | — | `pgvector/pgvector:pg16` |
| Redis | 6379 | — | `redis:7-alpine` |
| MinIO | 9000 (API) / 9001 (console) | — | `minio/minio` |

Images are published to GHCR by the [Release Images workflow](.github/workflows/release.yml) on every push to `main` (tagged `latest` + commit SHA) and on `v*.*.*` tags (semver).

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+ and pnpm
- Docker and Docker Compose v2
- Git

### Step 1: Clone and Configure

```bash
git clone https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform.git
cd AI-Expense-Intelligence-Automation-Platform

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY
# Optional: AWS credentials (falls back to MinIO locally)
```

### Step 2: Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, MinIO, and pgvector
docker compose -f infrastructure/docker/docker-compose.infra.yml up -d

# Wait for services to be healthy
docker compose -f infrastructure/docker/docker-compose.infra.yml ps
```

### Step 3: Initialize Database

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install shared packages
pip install -e packages/db-client
pip install -e packages/shared-types
pip install -e packages/queue-client

# Run migrations
cd packages/db-client
alembic upgrade head
cd ../..

# Seed sample data
python scripts/seed_data.py
```

### Step 4: Start Backend Services

```bash
# Terminal 1: API Gateway
cd services/api-gateway
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8000

# Terminal 2: AI Engine
cd services/ai-engine
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8001

# Terminal 3: Expense Processor
cd services/expense-processor
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8002

# Terminal 4: Policy Engine
cd services/policy-engine
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8003

# Terminal 5: Celery Workers
celery -A packages.queue_client.app worker --loglevel=info
```

### Step 5: Start Frontend

```bash
cd services/dashboard-ui
pnpm install
pnpm dev  # Starts on http://localhost:5173
```

### Step 6: One-Command Start (Alternative)

```bash
# Start everything with Docker Compose
docker compose up --build

# Services available at:
# - API Gateway:  http://localhost:8000
# - Dashboard:    http://localhost:5173
# - MinIO:        http://localhost:9001
# - pgAdmin:      http://localhost:5050
```

### Running Tests

```bash
# All backend tests
pytest --cov=services --cov-report=html

# Specific service
pytest services/ai-engine/tests/ -v

# Frontend tests
cd services/dashboard-ui && pnpm test

# Integration tests (requires running infrastructure)
pytest tests/integration/ -v --run-integration

# Load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## Cloud Deployment

> **Start here:** the step-by-step [Deployment Guide](docs/deployment/DEPLOYMENT.md) covers the release/image flow, required secrets, database migrations, smoke tests, rollback, and a production readiness checklist. The sections below are quick references per target.

### Option A: Docker + AWS ECS (Recommended for Production)

```bash
# 1. Build and push images
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1
export ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Build all services
for service in api-gateway expense-processor ai-engine policy-engine dashboard-ui; do
  docker build -t $ECR_REGISTRY/expense-$service:latest \
    -f infrastructure/docker/Dockerfile.$service .
  docker push $ECR_REGISTRY/expense-$service:latest
done

# 2. Provision infrastructure with Terraform
cd infrastructure/terraform/environments/prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 3. Deploy services
# ECS services are configured via Terraform and auto-deploy from ECR
```

### Option B: Docker + GCP Cloud Run

```bash
# 1. Authenticate
gcloud auth configure-docker

# 2. Build and push
export PROJECT_ID=$(gcloud config get-value project)
for service in api-gateway expense-processor ai-engine policy-engine dashboard-ui; do
  docker build -t gcr.io/$PROJECT_ID/expense-$service:latest \
    -f infrastructure/docker/Dockerfile.$service .
  docker push gcr.io/$PROJECT_ID/expense-$service:latest
done

# 3. Deploy each service
for service in api-gateway expense-processor ai-engine policy-engine; do
  gcloud run deploy expense-$service \
    --image gcr.io/$PROJECT_ID/expense-$service:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=$DATABASE_URL,REDIS_URL=$REDIS_URL"
done
```

### Option C: Kubernetes (AWS EKS / GKE)

```bash
# 1. Create cluster (EKS example)
eksctl create cluster --name expense-platform --region us-east-1 \
  --nodegroup-name workers --node-type t3.large --nodes 3

# 2. Apply base manifests
kubectl apply -k infrastructure/k8s/base/

# 3. Apply environment overlay
kubectl apply -k infrastructure/k8s/overlays/prod/

# 4. Verify
kubectl get pods -n expense-platform
kubectl get svc -n expense-platform
```

### Option D: Docker Compose on a Single VM

```bash
# For staging/demo environments
ssh user@your-server
git clone https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform.git
cd AI-Expense-Intelligence-Automation-Platform

cp .env.example .env.prod   # fill in real secrets — startup fails if any are missing

# Pin IMAGE_TAG to a commit SHA for reproducible deploys (latest is dev-only)
IMAGE_TAG=<commit-sha> docker compose \
  -f infrastructure/docker/docker-compose.prod.yml \
  --env-file .env.prod up -d
```

The production compose file pulls prebuilt GHCR images, publishes only the gateway (`:8000`) and dashboard (`:80`), and keeps Postgres/Redis/MinIO internal. Put a TLS terminator (Caddy, nginx, or a cloud LB) in front.

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key for LLM | Yes |
| `S3_BUCKET` | S3 bucket for document storage | Yes |
| `S3_ENDPOINT` | S3 endpoint (MinIO for local) | Local only |
| `JWT_SECRET` | JWT signing secret | Yes |
| `CELERY_BROKER_URL` | Celery broker URL | Yes |
| `SMTP_HOST` | Email server host | Optional |
| `SLACK_WEBHOOK_URL` | Slack notification URL | Optional |

---

## Contributing

1. Open (or pick) a GitHub issue describing the change.
2. Branch from `main`: `<type>/issue-<number>-<short-description>` — types: `feat`, `fix`, `test`, `docs`, `infra`, `refactor`, `ci`.
3. Commit using conventional messages referencing the issue: `feat(api-gateway): add refresh tokens (#42)`.
4. Ensure `ruff check`, `pytest`, and (for UI changes) `pnpm test` pass locally — CI runs the same gates on the PR.
5. Open a PR against `main` with a problem statement, what changed, and how it was verified. PRs are squash-merged.

## Documentation

- [Deployment Guide & Production Readiness Checklist](docs/deployment/DEPLOYMENT.md)
- [Architecture Overview](docs/architecture/ARCHITECTURE.md) and [ADRs](docs/adr/)
- [Git Issues & Implementation Plan](docs/ISSUES.md)
- Interactive API docs: each FastAPI service serves Swagger UI at `/docs` and OpenAPI JSON at `/openapi.json` (see [Service Ports](#service-ports))

## License

MIT
