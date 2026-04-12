---
name: expense-platform
description: Skill for implementing the AI Expense Intelligence Platform. Use this skill when working on any issue related to the expense platform project, including backend services (API Gateway, AI Engine, Expense Processor, Policy Engine), frontend dashboard, infrastructure (Docker, K8s, Terraform), testing, or documentation. Trigger on mentions of expense processing, receipt extraction, fraud detection, policy evaluation, spend analytics, LangGraph agents, or any reference to the expense-intelligence-platform repository.
---

# AI Expense Intelligence Platform - Implementation Skill

## Project Overview

A microservices-based platform that uses AI (LangGraph + GPT-4o + RAG) to categorize, analyze, and automate business expense workflows. Services communicate via HTTP. PostgreSQL with pgvector for storage and RAG. Redis for caching and task queues. React dashboard for UI.

## Repository Structure

```
expense-intelligence-platform/
├── services/
│   ├── api-gateway/          # FastAPI - Auth, routing, rate limiting
│   ├── expense-processor/    # FastAPI - OCR, extraction, normalization
│   ├── ai-engine/            # FastAPI + LangGraph - Agents, RAG, fraud
│   ├── policy-engine/        # FastAPI - Rule evaluation, auto-approval
│   ├── dashboard-ui/         # React + TypeScript - Analytics UI
│   ├── notification-service/ # Notification delivery
│   └── batch-processor/      # Celery workers
├── packages/
│   ├── shared-types/         # Pydantic models
│   ├── db-client/            # SQLAlchemy ORM
│   └── queue-client/         # Celery tasks
├── infrastructure/
│   ├── docker/               # Dockerfiles + Compose
│   ├── k8s/                  # Kustomize manifests
│   └── terraform/            # AWS IaC
├── docs/                     # Architecture docs
└── scripts/                  # Dev utilities
```

## Implementation Workflow

For each issue, follow this sequence:
1. Create a feature branch from `develop`
2. Implement the code changes
3. Write/update tests
4. Run tests locally
5. Commit with conventional commit message
6. Push and create PR

## Git Conventions

- Branch naming: `feat/issue-{number}-{short-description}`
- Commit messages: `feat(service): description (#issue)`
- Types: `feat`, `fix`, `test`, `docs`, `infra`, `refactor`

---

## Issue Implementation Commands

### Issue #1: Project Scaffolding

```bash
# Initialize repo
git init expense-intelligence-platform
cd expense-intelligence-platform
git checkout -b feat/issue-1-scaffolding

# Create all directories
mkdir -p services/{api-gateway,expense-processor,ai-engine,policy-engine,dashboard-ui,notification-service,batch-processor}/{src,tests}
mkdir -p packages/{shared-types,db-client,queue-client}/src
mkdir -p infrastructure/{docker,k8s/{base,overlays/{dev,staging,prod}},terraform/{modules/{ecs,rds,redis,s3,vpc},environments/{dev,prod}}}
mkdir -p docs/{architecture,api,deployment,adr}
mkdir -p scripts .github/{workflows,ISSUE_TEMPLATE}
mkdir -p .claude/skills/expense-platform

# Create __init__.py files
find services packages -type d -name src -exec touch {}/__init__.py \;
find services -type d -name tests -exec touch {}/__init__.py \;

# Create root configs
# (Copy pyproject.toml, .gitignore, .editorconfig, ruff.toml from templates)

git add -A
git commit -m "feat: project scaffolding and monorepo structure (#1)"
```

### Issue #2: Docker Infrastructure

```bash
git checkout -b feat/issue-2-docker-infra develop

# Files to create:
# - infrastructure/docker/docker-compose.infra.yml
# - infrastructure/docker/init.sql

# Verify infrastructure starts
docker compose -f infrastructure/docker/docker-compose.infra.yml up -d
docker compose -f infrastructure/docker/docker-compose.infra.yml ps
# All services should show "healthy"

# Verify pgvector
docker exec expense-postgres psql -U expense_user -d expense_db -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"

git add -A
git commit -m "infra: Docker Compose for PostgreSQL+pgvector, Redis, MinIO (#2)"
```

### Issue #3: Shared Types Package

```bash
git checkout -b feat/issue-3-shared-types develop

# Files to create:
# - packages/shared-types/src/models.py
# - packages/shared-types/src/__init__.py
# - packages/shared-types/pyproject.toml
# - packages/shared-types/tests/test_models.py

# Run tests
cd packages/shared-types
pytest tests/ -v
cd ../..

git add -A
git commit -m "feat(shared-types): Pydantic domain models and enums (#3)"
```

### Issue #4: Database Client Package

```bash
git checkout -b feat/issue-4-db-client develop

# Files to create:
# - packages/db-client/src/database.py
# - packages/db-client/src/__init__.py
# - packages/db-client/pyproject.toml
# - packages/db-client/alembic.ini
# - packages/db-client/alembic/env.py
# - packages/db-client/alembic/versions/001_initial.py
# - packages/db-client/tests/test_database.py

# Run migration
docker compose -f infrastructure/docker/docker-compose.infra.yml up -d postgres
cd packages/db-client
alembic upgrade head
cd ../..

# Run tests
pytest packages/db-client/tests/ -v

git add -A
git commit -m "feat(db-client): SQLAlchemy ORM models, migrations, connection pooling (#4)"
```

### Issue #5: Queue Client Package

```bash
git checkout -b feat/issue-5-queue-client develop

# Files to create:
# - packages/queue-client/src/tasks.py
# - packages/queue-client/src/__init__.py
# - packages/queue-client/pyproject.toml
# - packages/queue-client/tests/test_tasks.py

pytest packages/queue-client/tests/ -v

git add -A
git commit -m "feat(queue-client): Celery task definitions with routing and retry (#5)"
```

### Issue #6: CI/CD Pipeline

```bash
git checkout -b feat/issue-6-cicd develop

# Files to create:
# - .github/workflows/ci.yml
# - .github/ISSUE_TEMPLATE/bug_report.md
# - .github/ISSUE_TEMPLATE/feature_request.md
# - .github/pull_request_template.md

git add -A
git commit -m "infra: GitHub Actions CI/CD pipeline (#6)"
```

### Issue #7: API Gateway - Authentication

```bash
git checkout -b feat/issue-7-gateway-auth develop

# Files to create/update:
# - services/api-gateway/src/main.py (auth section)
# - services/api-gateway/src/middleware/auth.py
# - services/api-gateway/tests/test_auth.py
# - services/api-gateway/pyproject.toml

pytest services/api-gateway/tests/test_auth.py -v

git add -A
git commit -m "feat(api-gateway): JWT authentication and token management (#7)"
```

### Issue #8: API Gateway - Rate Limiting

```bash
git checkout -b feat/issue-8-rate-limiting develop

# Files to create/update:
# - services/api-gateway/src/middleware/rate_limiter.py
# - services/api-gateway/tests/test_rate_limiting.py

# Integration test (requires Redis)
docker compose -f infrastructure/docker/docker-compose.infra.yml up -d redis
pytest services/api-gateway/tests/test_rate_limiting.py -v

git add -A
git commit -m "feat(api-gateway): Redis sliding window rate limiting (#8)"
```

### Issue #9: API Gateway - Full Routing

```bash
git checkout -b feat/issue-9-gateway-routes develop

# Update: services/api-gateway/src/main.py (all routes)
# Create: services/api-gateway/tests/test_gateway.py

pytest services/api-gateway/tests/ -v

git add -A
git commit -m "feat(api-gateway): complete request routing to all downstream services (#9)"
```

### Issue #10-12: Expense Processor (OCR + Normalize + Pipeline)

```bash
git checkout -b feat/issue-10-12-expense-processor develop

# Files to create:
# - services/expense-processor/src/main.py
# - services/expense-processor/src/extractors/ocr.py
# - services/expense-processor/src/normalizers/fields.py
# - services/expense-processor/pyproject.toml
# - services/expense-processor/tests/test_processor.py
# - services/expense-processor/tests/test_normalizer.py
# - services/expense-processor/tests/test_ocr.py

pytest services/expense-processor/tests/ -v

git add -A
git commit -m "feat(expense-processor): OCR extraction, normalization, processing pipeline (#10, #11, #12)"
```

### Issue #13-14: AI Engine - LangGraph + Prompts

```bash
git checkout -b feat/issue-13-14-ai-engine-core develop

# Files to create:
# - services/ai-engine/src/main.py
# - services/ai-engine/src/agent/graph.py
# - services/ai-engine/src/agent/state.py
# - services/ai-engine/src/prompts/extraction.py
# - services/ai-engine/src/prompts/fraud.py
# - services/ai-engine/src/prompts/chat.py
# - services/ai-engine/pyproject.toml
# - services/ai-engine/tests/test_ai_engine.py
# - services/ai-engine/tests/test_graph.py
# - services/ai-engine/tests/test_prompts.py

pytest services/ai-engine/tests/ -v

git add -A
git commit -m "feat(ai-engine): LangGraph analysis pipeline with extraction and fraud prompts (#13, #14)"
```

### Issue #15: AI Engine - RAG Pipeline

```bash
git checkout -b feat/issue-15-rag-pipeline develop

# Files to create:
# - services/ai-engine/src/rag/retriever.py
# - services/ai-engine/src/rag/ingest.py
# - services/ai-engine/src/rag/embeddings.py
# - services/ai-engine/tests/test_rag.py

pytest services/ai-engine/tests/test_rag.py -v

git add -A
git commit -m "feat(ai-engine): RAG pipeline with pgvector retrieval and policy ingestion (#15)"
```

### Issue #16-17: AI Engine - Chat Agent + Fraud Tools

```bash
git checkout -b feat/issue-16-17-chat-fraud develop

# Files to create:
# - services/ai-engine/src/agent/chat_graph.py
# - services/ai-engine/src/tools/spend_query.py
# - services/ai-engine/src/tools/fraud_detection.py
# - services/ai-engine/src/tools/similarity_search.py
# - services/ai-engine/tests/test_chat.py
# - services/ai-engine/tests/test_tools.py

pytest services/ai-engine/tests/ -v

git add -A
git commit -m "feat(ai-engine): chat agent with tool routing and fraud detection tools (#16, #17)"
```

### Issue #18-20: Policy Engine (Complete)

```bash
git checkout -b feat/issue-18-20-policy-engine develop

# Files to create:
# - services/policy-engine/src/main.py
# - services/policy-engine/src/rules/evaluators.py
# - services/policy-engine/src/rules/defaults.py
# - services/policy-engine/pyproject.toml
# - services/policy-engine/tests/test_policy_engine.py
# - services/policy-engine/tests/test_evaluators.py

pytest services/policy-engine/tests/ -v

git add -A
git commit -m "feat(policy-engine): rule evaluation framework with default rules and CRUD (#18, #19, #20)"
```

### Issue #21-25: Dashboard UI (Complete)

```bash
git checkout -b feat/issue-21-25-dashboard develop

cd services/dashboard-ui

# Initialize React project
pnpm create vite . --template react-ts
pnpm add @tanstack/react-query @tanstack/react-router zustand axios recharts
pnpm add -D tailwindcss postcss autoprefixer @types/react @types/react-dom vitest

# Create all component files
# (See dashboard-ui/src/ for full file list)

pnpm build
pnpm test -- --run

cd ../..

git add -A
git commit -m "feat(dashboard): React UI with expense views, analytics, AI chat, policy admin (#21-#25)"
```

### Issue #26-27: Notification + Batch Processing

```bash
git checkout -b feat/issue-26-27-notifications-batch develop

# Files to create:
# - services/notification-service/src/main.py
# - services/notification-service/src/channels/email.py
# - services/notification-service/src/channels/slack.py
# - services/notification-service/src/templates/
# - services/batch-processor/src/main.py
# - services/batch-processor/src/workers/csv_processor.py

git add -A
git commit -m "feat: notification service and batch processor (#26, #27)"
```

### Issue #28-29: Integration + Load Tests

```bash
git checkout -b feat/issue-28-29-testing develop

# Files to create:
# - tests/integration/test_full_pipeline.py
# - tests/integration/test_batch_flow.py
# - tests/integration/conftest.py
# - tests/load/locustfile.py

# Run integration tests
docker compose -f infrastructure/docker/docker-compose.infra.yml up -d
pytest tests/integration/ -v --run-integration

# Run load tests
locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 60s --host=http://localhost:8000

git add -A
git commit -m "test: integration tests and Locust load testing (#28, #29)"
```

### Issue #30-32: Production Infrastructure

```bash
git checkout -b feat/issue-30-32-prod-infra develop

# Files to create:
# - All Dockerfiles (finalize)
# - docker-compose.yml (production)
# - infrastructure/k8s/base/*.yaml
# - infrastructure/k8s/overlays/{dev,staging,prod}/*.yaml
# - infrastructure/terraform/modules/**/*.tf
# - infrastructure/terraform/environments/**/*.tf

# Verify Docker builds
docker compose build

# Verify K8s manifests
kubectl kustomize infrastructure/k8s/overlays/dev/

git add -A
git commit -m "infra: production Dockerfiles, Kubernetes manifests, Terraform modules (#30, #31, #32)"
```

### Issue #33-35: Documentation + Seed + Skill

```bash
git checkout -b feat/issue-33-35-docs develop

# Files to create:
# - docs/architecture/ARCHITECTURE.md (C4 + sequence diagrams)
# - docs/adr/001-microservices.md
# - docs/adr/002-langgraph.md
# - docs/adr/003-pgvector.md
# - docs/adr/004-rule-engine.md
# - scripts/seed_data.py
# - .claude/skills/expense-platform/SKILL.md

python scripts/seed_data.py

git add -A
git commit -m "docs: architecture diagrams, ADRs, seed data, implementation skill (#33, #34, #35)"
```

---

## Testing Commands Reference

```bash
# Run all tests
pytest services/ packages/ -v --cov=services --cov=packages --cov-report=html

# Run specific service tests
pytest services/api-gateway/tests/ -v
pytest services/ai-engine/tests/ -v
pytest services/expense-processor/tests/ -v
pytest services/policy-engine/tests/ -v

# Run with markers
pytest -m "not integration" -v          # Skip integration tests
pytest -m "integration" -v               # Only integration tests

# Linting
ruff check services/ packages/
ruff format services/ packages/

# Type checking
mypy services/ packages/ --ignore-missing-imports

# Frontend
cd services/dashboard-ui && pnpm test -- --run && pnpm build
```

## Deployment Verification

```bash
# Local Docker
docker compose up --build -d
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health/deep

# Kubernetes
kubectl get pods -n expense-platform
kubectl logs -f deployment/api-gateway -n expense-platform

# Smoke tests
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```
