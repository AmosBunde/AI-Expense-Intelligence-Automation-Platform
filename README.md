# AI Expense Intelligence & Automation Platform

[![CI/CD Pipeline](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/ci.yml)
[![Release Images](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/release.yml/badge.svg)](https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![React 18](https://img.shields.io/badge/react-18-61dafb)

> An AI-powered system that categorizes, analyzes, and automates business spend workflows. Receipts and invoices are read by an LLM pipeline, checked against company policy via RAG, scored for fraud, and routed for approval — before anyone opens a spreadsheet.

**Quickstart:** `cp .env.example .env && make dev` → gateway on
[localhost:8000/docs](http://localhost:8000/docs), dashboard on
[localhost:5173](http://localhost:5173). All operational commands are in the
[Makefile](Makefile) — run `make` to list them.

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [The AI Engine](#the-ai-engine)
- [The Dashboard](#the-dashboard)
- [Security Model](#security-model)
- [Scalability](#scalability)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Service Ports](#service-ports)
- [Local Development Setup](#local-development-setup)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [Documentation](#documentation)

## How It Works

The life of one receipt, end to end:

1. **Upload.** An employee drops a receipt (image or PDF) into the dashboard.
   The API Gateway authenticates the JWT, enforces the per-user rate limit and
   the 10 MB / content-type upload rules, stores the file reference under the
   caller's organization, and forwards the payload to the Expense Processor.
2. **Extraction.** The Expense Processor runs OCR (Tesseract, with pdf2image
   for PDFs), then an LLM extraction pass turns raw text into structured
   fields — merchant, date, total, tax, currency, line items — and normalizes
   them (currency codes, date formats, merchant canonicalization).
3. **AI analysis.** The AI Engine's LangGraph pipeline picks up the expense:
   it categorizes it, retrieves the relevant company policy passages from
   pgvector (RAG), scores fraud signals (duplicate detection, amount outliers
   versus the org's history, vendor/time-pattern anomalies), and writes an
   explanation of its reasoning onto the expense record.
4. **Policy verdict.** The Policy Engine evaluates deterministic rules —
   amount thresholds, per-head meal limits, duplicate windows, auto-approval
   floors. Low-risk, under-limit expenses are **auto-approved** with no human
   involved; everything else is routed to a manager's queue with the AI
   reasoning and the exact rule that fired attached.
5. **Review & notify.** Managers approve or reject from the dashboard (RBAC
   enforced at the gateway); the Notification Service emails or Slacks the
   outcome. Batch CSV/Excel imports follow the same pipeline via Celery
   workers; nightly reconciliation runs in the batch processor.
6. **Ask questions.** At any point, anyone can ask the AI Analyst chat things
   like *"what did we spend on travel this quarter?"* or *"summarize our meal
   policy"* — a LangGraph chat agent answers using spend-query tools and
   RAG-grounded policy citations.

## Architecture

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

Design principles:

- **The gateway is the only public surface.** Every downstream service is
  reachable only on the internal network; auth, rate limiting, RBAC checks,
  and upload validation happen once, at the edge.
- **Services are stateless.** All state lives in PostgreSQL, Redis, and
  object storage, so any service can scale horizontally by adding replicas.
- **Deterministic rules decide; AI explains and flags.** Auto-approval is
  driven by the rule engine, not by LLM output — the AI contributes
  categorization, anomaly scores, and human-readable reasoning, and its
  scores feed *into* rules rather than replacing them.
- **Async where latency doesn't matter.** Single receipts process
  synchronously for fast feedback; batch imports and reconciliation go
  through Celery queues.

Deeper reading: [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) (C4 +
sequence diagrams) and the [ADRs](docs/adr/) covering the microservices
split, LangGraph, pgvector, and the rule engine.

## The AI Engine

Three cooperating pieces, all in `services/ai-engine/`:

- **Analysis pipeline** (`src/agent/graph.py`) — a LangGraph state machine:
  `extract → categorize → retrieve policy context → fraud scoring →
  compose verdict`. Each node is independently testable; prompts live in
  `src/prompts/` as versioned templates.
- **RAG over pgvector** (`src/rag/`) — company policy documents are chunked,
  embedded, and stored in PostgreSQL with the pgvector extension. Retrieval
  grounds both the analysis pipeline (policy-aware fraud reasoning) and the
  chat agent (answers cite their source passages). One database serves both
  relational and vector workloads — no separate vector store to operate.
- **Chat agent** (`src/agent/chat_graph.py` + `src/tools/`) — a
  tool-routing agent with three tools: spend aggregation queries, fraud/
  anomaly lookups, and policy similarity search. The agent decides which
  tools a question needs, calls them, and synthesizes a grounded answer.

## The Dashboard

**Meridian** (`services/dashboard-ui/`) is a Vite + React 18 + TypeScript
SPA — Swiss-typographic design, light/dark themes, mobile-first, zero
runtime dependencies beyond React.

| View | What you can do |
|---|---|
| Overview | Spend totals, auto-approval rate, monthly trend, category breakdown, live anomaly feed |
| Expenses | Filterable ledger → detail drawer with AI analysis, fraud score, policy verdict; managers approve flagged items in place |
| Upload | Drag-and-drop receipts with instant validation feedback |
| AI Analyst | Chat about spend, expenses, and policy with cited sources |
| Policies | Browse the rulebook; admins/finance create rules |

Role-gated actions (approve, create policy) are hidden for roles that lack
them — and enforced again server-side at the gateway, which is the
authority. In local dev the UI runs in labeled **demo mode** when the
backend is unreachable, so it's explorable standalone.

## Security Model

**Authentication & authorization**

- JWT bearer tokens (HS256) carrying `sub` (user), `org` (tenant), and
  `role` claims; every downstream query is scoped by the org claim.
- Credentials verify against bcrypt hashes configured via `AUTH_USERS`.
  Unknown-user and wrong-password failures are indistinguishable in both
  response *and timing* (dummy-hash verification), preventing account
  enumeration.
- RBAC at the gateway: approvals require `manager`/`admin`/`finance`;
  policy creation and batch imports require `admin`/`finance`.
- **Fail-closed posture:** in production the gateway refuses to start with
  a missing/default `JWT_SECRET`, and refuses logins entirely if
  `AUTH_USERS` is unconfigured. Demo login exists only when `ENVIRONMENT`
  is explicitly dev-like; an unset environment is treated as production.

**Abuse resistance**

- Per-user sliding-window rate limit (Redis) on all authenticated routes;
  separate per-IP fixed-window limit on the pre-auth login endpoint.
- Uploads capped (10 MB receipts / 50 MB batches) with content-type
  allowlists — enforced by reading at most `limit+1` bytes, never buffering
  unbounded input.
- Security headers from both the app and nginx (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store` on API
  responses, HSTS in production); CORS restricted to explicit methods and
  headers.

**Secrets & deployment hardening**

- No secrets in git: the prod compose file requires them from an env file
  (`${VAR:?}` fails startup if missing); Kubernetes reads them from an
  `app-secrets` Secret ([template](infrastructure/k8s/base/secrets.example.yaml)
  deliberately excluded from kustomize resources).
- Production containers publish only the gateway and dashboard ports;
  Postgres/Redis/MinIO are internal-only. Known accepted trade-off on the
  single-VM target: service-to-service traffic inside the Docker network is
  plaintext — put TLS at the edge and upgrade to K8s + mTLS (service mesh)
  if your threat model requires encrypted east-west traffic.

**Verification:** the gateway ships 42 tests including a dedicated security
suite (credential validation, fail-closed behavior, rate limits, header
presence, upload rejection). CI runs lint → tests → build on every PR.

## Scalability

| Layer | How it scales | Notes |
|---|---|---|
| API Gateway & services | Horizontally — stateless replicas behind the ingress/LB | K8s prod overlay runs 3 gateway / 3 AI-engine replicas |
| Peak absorption | HPA on the gateway (CPU 70% / mem 80%, 2→10 replicas) | `infrastructure/k8s/base/deployments.yaml` |
| Async work | Celery workers on Redis queues; batch imports and notifications never block request paths | Scale workers independently (5 replicas in prod overlay) |
| Database | PostgreSQL with connection pooling; pgvector indexes for ANN search | Add read replicas for analytics before sharding |
| Cache & rate limiting | Redis (LRU-capped in prod compose) | Move to Redis Cluster/ElastiCache when a single node saturates |
| LLM calls | The dominant latency + cost driver | Bounded by upload limits and rate limits; batch pipeline smooths spikes |

Known bottlenecks, in the order you'd hit them: (1) OpenAI API throughput —
mitigate with request batching and caching of repeated policy retrievals;
(2) single Postgres writer — read replicas, then partition expenses by org;
(3) synchronous receipt processing under burst load — shift extraction to
the Celery path once p95 upload latency matters. Load-test scaffolding lives
in `tests/load/locustfile.py` (`locust -f tests/load/locustfile.py`).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Gateway | Python 3.12, FastAPI, Pydantic v2, PyJWT, bcrypt |
| AI Engine | LangGraph, LangChain, OpenAI API, pgvector |
| Expense Processor | Python, Tesseract OCR, pdf2image |
| Policy Engine | Python, rule-engine, custom DSL |
| Dashboard | React 18, TypeScript, Vite, hand-rolled SVG charts |
| Database | PostgreSQL 16 + pgvector |
| Cache / queues | Redis 7, Celery |
| Storage | AWS S3 / MinIO (local) |
| Packaging | Docker multi-stage builds, GHCR images |
| Orchestration | Kubernetes (Kustomize) / AWS ECS |
| IaC | Terraform |
| CI/CD | GitHub Actions (CI on PRs, image publishing on main/tags) |

## Project Structure

```
expense-intelligence-platform/
├── services/
│   ├── api-gateway/          # Public edge: auth, RBAC, rate limits, routing
│   ├── expense-processor/    # OCR, LLM extraction, normalization
│   ├── ai-engine/            # LangGraph pipeline, RAG, chat agent, fraud tools
│   ├── policy-engine/        # Deterministic rules, auto-approval
│   ├── dashboard-ui/         # Meridian — React analytics dashboard
│   ├── notification-service/ # Email, Slack, webhook delivery
│   └── batch-processor/      # CSV imports, scheduled reconciliation
├── packages/
│   ├── shared-types/         # Pydantic domain models shared by services
│   ├── db-client/            # SQLAlchemy ORM, Alembic migrations, pooling
│   └── queue-client/         # Celery app + task definitions
├── infrastructure/
│   ├── docker/               # Dockerfiles, dev/infra/prod compose, nginx
│   ├── k8s/                  # Kustomize base + dev/staging/prod overlays
│   └── terraform/            # AWS VPC, RDS, ElastiCache, ECS modules
├── docs/                     # Architecture, ADRs, deployment guide
├── scripts/                  # Seed data, issue tooling
├── tests/                    # Cross-service integration + Locust load tests
├── Makefile                  # Single entrypoint: make help
└── .github/workflows/        # ci.yml (PR gate) + release.yml (GHCR publish)
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

Images are published to GHCR by the [Release Images workflow](.github/workflows/release.yml)
on every push to `main` (tagged `latest` + commit SHA) and on `v*.*.*` tags (semver).

---

## Local Development Setup

### Prerequisites

- Python 3.12+ · Node.js 20+ and pnpm · Docker + Compose v2 · Git

### The short way

```bash
git clone https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform.git
cd AI-Expense-Intelligence-Automation-Platform
cp .env.example .env        # set OPENAI_API_KEY; the rest has dev defaults
make dev                    # builds and starts everything
```

Gateway: <http://localhost:8000/docs> · Dashboard: <http://localhost:5173> ·
MinIO console: <http://localhost:9001>. In dev, any email/password signs in
(demo mode); the dashboard shows labeled sample data if a backend is down.

### The granular way (services on the host)

```bash
make infra                  # just Postgres + Redis + MinIO in Docker
python -m venv .venv && source .venv/bin/activate
pip install -e packages/shared-types -e packages/db-client -e packages/queue-client
make migrate && make seed

# each in its own terminal:
cd services/api-gateway        && pip install -e ".[dev]" && uvicorn src.main:app --reload --port 8000
cd services/ai-engine          && pip install -e ".[dev]" && uvicorn src.main:app --reload --port 8001
cd services/expense-processor  && pip install -e ".[dev]" && uvicorn src.main:app --reload --port 8002
cd services/policy-engine      && pip install -e ".[dev]" && uvicorn src.main:app --reload --port 8003
PYTHONPATH=packages/queue-client/src celery -A tasks:celery_app worker \
  --loglevel=info -Q expense_processing,batch_processing,reporting,notifications

cd services/dashboard-ui && pnpm install && pnpm dev
```

### Tests & quality gates

```bash
make test        # backend suites + dashboard type-check/tests/build
make lint        # ruff check + format check
make test-backend
make test-frontend
pytest tests/integration/ -v --run-integration   # needs `make infra`
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## Deployment

> **Start here:** the step-by-step [Deployment Guide](docs/deployment/DEPLOYMENT.md)
> covers the release/image flow, required secrets, database migrations, smoke
> tests, rollback, and a production readiness checklist.

### Option A: single VM with Docker Compose

```bash
ssh user@your-server
git clone https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform.git
cd AI-Expense-Intelligence-Automation-Platform
cp .env.example .env.prod      # fill in real secrets — startup fails if any are missing
make prod IMAGE_TAG=<commit-sha>
```

Pulls prebuilt GHCR images, publishes only the gateway (`:8000`) and
dashboard (`:80`), keeps infra internal. Put a TLS terminator (Caddy, nginx,
or a cloud LB) in front.

### Option B: Kubernetes (EKS / GKE)

```bash
# 1. Create the app-secrets Secret (see infrastructure/k8s/base/secrets.example.yaml)
# 2. Set your real host in base/deployments.yaml (ConfigMap + Ingress)
make k8s-dev        # or k8s-staging / k8s-prod
kubectl get pods -n expense-platform -w
```

Prod overlay: 3 gateway + 3 AI-engine replicas, HPA 2→10, nginx ingress with
cert-manager TLS. The dev overlay is the only one that permits demo login.

### Option C: AWS ECS via Terraform

```bash
cd infrastructure/terraform/environments/prod
terraform init && terraform plan -out=tfplan   # review: VPC, RDS, ElastiCache, ECS
terraform apply tfplan
```

---

## Environment Variables

Copy [.env.example](.env.example) and fill in. The important ones:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | LLM extraction, analysis, chat | Yes |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | PostgreSQL DSNs (async + sync) | Yes |
| `REDIS_URL`, `CELERY_BROKER_URL` | Cache / rate limits / queues | Yes |
| `JWT_SECRET` | Token signing — `openssl rand -hex 32`; prod refuses defaults | Yes |
| `AUTH_USERS` | JSON of bcrypt-hashed users; prod logins disabled without it | Prod |
| `ENVIRONMENT` | `production` enables fail-closed auth + HSTS | Prod |
| `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT` | Document storage (MinIO locally) | Yes |
| `MAX_UPLOAD_MB`, `LOGIN_RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_PER_MINUTE` | Abuse limits (sane defaults) | No |
| `SMTP_*`, `SLACK_WEBHOOK_URL` | Notification channels | No |

## Contributing

1. Open (or pick) a GitHub issue describing the change.
2. Branch from `main`: `<type>/issue-<number>-<short-description>` — types: `feat`, `fix`, `test`, `docs`, `infra`, `security`, `ci`, `refactor`.
3. Commit with conventional messages referencing the issue: `feat(api-gateway): add refresh tokens (#42)`.
4. Run `make lint test` locally — CI runs the same gates on the PR.
5. Open a PR against `main` with a problem statement, what changed, and how it was verified. PRs are squash-merged.

## Documentation

- [Deployment Guide & Production Readiness Checklist](docs/deployment/DEPLOYMENT.md)
- [Architecture Overview](docs/architecture/ARCHITECTURE.md) and [ADRs](docs/adr/)
- [Git Issues & Implementation Plan](docs/ISSUES.md)
- Interactive API docs: every FastAPI service serves Swagger UI at `/docs` and OpenAPI JSON at `/openapi.json`

## License

MIT
