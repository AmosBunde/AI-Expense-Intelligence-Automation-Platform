#!/usr/bin/env bash
# =============================================================================
# create_github_issues.sh
# Creates all 35 GitHub issues for the AI Expense Intelligence Platform
# with milestones, labels, and assignment to AmosBunde.
#
# Prerequisites:
#   1. GitHub CLI installed: https://cli.github.com
#   2. Authenticated: gh auth login
#   3. Run from anywhere (repo is hardcoded)
#
# Usage:
#   chmod +x create_github_issues.sh
#   ./create_github_issues.sh
# =============================================================================

set -euo pipefail

REPO="AmosBunde/AI-Expense-Intelligence-Automation-Platform"
ASSIGNEE="AmosBunde"

echo "=============================================="
echo " AI Expense Intelligence & Automation Platform"
echo " GitHub Issue Generator"
echo "=============================================="
echo " Repo:     $REPO"
echo " Assignee: $ASSIGNEE"
echo "=============================================="
echo ""

if ! gh auth status &>/dev/null; then
  echo "ERROR: GitHub CLI not authenticated. Run: gh auth login"
  exit 1
fi

# ---- Step 1: Labels ----
echo ">>> [1/4] Creating 19 labels..."

create_label() { gh label create "$1" --color "$2" --force --repo "$REPO" 2>/dev/null || true; }

create_label "infrastructure" "d73a4a"
create_label "backend" "0075ca"
create_label "frontend" "7057ff"
create_label "ai" "e99695"
create_label "security" "b60205"
create_label "testing" "0e8a16"
create_label "documentation" "0075ca"
create_label "devops" "006b75"
create_label "tooling" "5319e7"
create_label "performance" "fbca04"
create_label "priority:critical" "b60205"
create_label "priority:high" "d93f0b"
create_label "priority:medium" "fbca04"
create_label "milestone:1-foundation" "c2e0c6"
create_label "milestone:2-core-services" "bfdadc"
create_label "milestone:3-ai-engine" "d4c5f9"
create_label "milestone:4-policy-engine" "fef2c0"
create_label "milestone:5-dashboard" "f9d0c4"
create_label "milestone:6-integration" "e6e6e6"

echo "    Done."
echo ""

# ---- Step 2: Milestones ----
echo ">>> [2/4] Creating 6 milestones..."

create_ms() {
  gh api "repos/$REPO/milestones" --method POST \
    -f title="$1" -f description="$2" -f state="open" 2>/dev/null \
    && echo "    Created: $1" \
    || echo "    Exists:  $1"
}

create_ms "M1: Foundation & Infrastructure" "Project scaffolding, Docker, shared packages, CI/CD (Issues #1-#6)"
create_ms "M2: Core Services" "API Gateway, Expense Processor: OCR, normalization, pipeline (Issues #7-#12)"
create_ms "M3: AI Engine" "LangGraph agents, RAG pgvector, fraud detection, chat agent (Issues #13-#17)"
create_ms "M4: Policy Engine" "Rule evaluation, default rules, auto-approval, CRUD (Issues #18-#20)"
create_ms "M5: Dashboard UI" "React + TypeScript: expenses, analytics, AI chat, policy admin (Issues #21-#25)"
create_ms "M6: Integration & Production" "Tests, Docker, K8s, Terraform, docs (Issues #26-#35)"

echo ""

# ---- Step 3: Issues ----
echo ">>> [3/4] Creating 35 issues..."
echo ""

N=0
issue() {
  local title="$1" body="$2" labels="$3" ms="$4"
  N=$((N + 1))
  printf "  [%2d/35] %s\n" "$N" "$title"
  gh issue create --repo "$REPO" --title "$title" --body "$body" \
    --label "$labels" --assignee "$ASSIGNEE" --milestone "$ms" 2>&1 | grep -o 'https://.*' || true
  sleep 2
}

# ======================== M1 ========================

issue "Project scaffolding and monorepo setup" \
"## Description
Initialize the monorepo with service directories, shared packages, configuration files, and developer tooling.

## Acceptance Criteria
- [ ] Directory structure: 7 services, 3 packages, infra, docs, scripts
- [ ] Root \`pyproject.toml\` with ruff, mypy, pytest settings
- [ ] \`.gitignore\`, \`.editorconfig\`, \`.env.example\`
- [ ] All \`__init__.py\` files in place
- [ ] README with architecture overview and local setup guide

## Branch: \`feat/issue-1-scaffolding\`" \
"infrastructure,priority:critical,milestone:1-foundation" \
"M1: Foundation & Infrastructure"

issue "Docker infrastructure (PostgreSQL + pgvector, Redis, MinIO)" \
"## Description
Docker Compose for local infra: PostgreSQL 16 + pgvector, Redis 7, MinIO, pgAdmin.

**Depends on:** #1

## Acceptance Criteria
- [ ] \`docker-compose.infra.yml\` with health checks
- [ ] pgvector extension auto-enabled via \`init.sql\`
- [ ] MinIO with pre-created \`expense-documents\` bucket
- [ ] Persistent volumes for all data stores

## Branch: \`feat/issue-2-docker-infra\`" \
"infrastructure,priority:critical,milestone:1-foundation" \
"M1: Foundation & Infrastructure"

issue "Shared types package (Pydantic domain models)" \
"## Description
\`packages/shared-types\`: Pydantic v2 models, enums, domain types.

**Depends on:** #1

## Acceptance Criteria
- [ ] 8 enums: ExpenseStatus, DocumentType, ExpenseCategory, FraudRiskLevel, PolicyViolationType, ApprovalAction
- [ ] Core models: Expense, ExpenseExtraction, LineItem, PolicyCheckResult, PolicyViolation, FraudAnalysis
- [ ] API models: PaginatedResponse, SpendSummary, HealthCheck
- [ ] Unit tests for validation and serialization

## Branch: \`feat/issue-3-shared-types\`" \
"backend,priority:critical,milestone:1-foundation" \
"M1: Foundation & Infrastructure"

issue "Database client (SQLAlchemy ORM + Alembic migrations)" \
"## Description
\`packages/db-client\`: async ORM, connection pooling, pgvector, Alembic.

**Depends on:** #2, #3

## Acceptance Criteria
- [ ] 7 ORM models with proper indexes and pgvector Vector(1536) column
- [ ] DatabaseClient with async session, pool_size=20, max_overflow=10
- [ ] Alembic initial migration
- [ ] Tests for connection and model creation

## Branch: \`feat/issue-4-db-client\`" \
"backend,priority:critical,milestone:1-foundation" \
"M1: Foundation & Infrastructure"

issue "Queue client (Celery task definitions)" \
"## Description
\`packages/queue-client\`: Celery app, tasks, routing, Beat schedules.

**Depends on:** #2

## Acceptance Criteria
- [ ] 4 tasks: process_single, process_batch, generate_report, send_notification
- [ ] Routing to dedicated queues, retry with exponential backoff
- [ ] Beat: daily reconciliation, weekly summary

## Branch: \`feat/issue-5-queue-client\`" \
"backend,priority:high,milestone:1-foundation" \
"M1: Foundation & Infrastructure"

issue "CI/CD pipeline (GitHub Actions)" \
"## Description
Lint, test, build, deploy workflow.

**Depends on:** #1

## Acceptance Criteria
- [ ] Ruff lint + format check
- [ ] pytest with PostgreSQL + Redis service containers
- [ ] Frontend: type-check, test, build
- [ ] Docker matrix build (5 services)
- [ ] 70% coverage minimum
- [ ] Deploy gated on main branch

## Branch: \`feat/issue-6-cicd\`" \
"infrastructure,devops,priority:high,milestone:1-foundation" \
"M1: Foundation & Infrastructure"

# ======================== M2 ========================

issue "API Gateway - JWT authentication" \
"## Description
JWT auth with login, token validation, user context extraction.

**Depends on:** #3, #4

## Acceptance Criteria
- [ ] POST /api/v1/auth/login returns JWT (sub, org, role, exp)
- [ ] get_current_user dependency validates Bearer token
- [ ] 401 for expired/invalid tokens, 403 for missing
- [ ] Configurable expiration via JWT_EXPIRATION_MINUTES

## Branch: \`feat/issue-7-gateway-auth\`" \
"backend,security,priority:critical,milestone:2-core-services" \
"M2: Core Services"

issue "API Gateway - Redis sliding window rate limiting" \
"## Description
Per-user rate limiting with Redis sorted sets.

**Depends on:** #7

## Acceptance Criteria
- [ ] ZSET-based sliding window per user
- [ ] Configurable RATE_LIMIT_PER_MINUTE (default 60)
- [ ] Returns 429 when exceeded
- [ ] Pipeline-based atomic Redis calls

## Branch: \`feat/issue-8-rate-limiting\`" \
"backend,security,priority:high,milestone:2-core-services" \
"M2: Core Services"

issue "API Gateway - Full request routing and CORS" \
"## Description
All API routes proxying to downstream services.

**Depends on:** #7

## Acceptance Criteria
- [ ] 13 endpoints: upload, list, detail, approve, analyze, chat, analytics, anomalies, policies, batch, health, deep-health
- [ ] Role-gated: approve (manager+), batch (admin/finance), policies POST (admin/finance)
- [ ] CORS with configurable origins
- [ ] 502 handling for downstream failures
- [ ] Input validation (page>=1, page_size<=100)

## Branch: \`feat/issue-9-gateway-routes\`" \
"backend,priority:critical,milestone:2-core-services" \
"M2: Core Services"

issue "Expense Processor - OCR and text extraction" \
"## Description
Document ingestion: Tesseract OCR, PDF extraction, CSV parsing.

**Depends on:** #3

## Acceptance Criteria
- [ ] Tesseract OCR for JPEG/PNG receipts
- [ ] PDF text extraction with pdf2image fallback
- [ ] CSV/text direct parsing for bank statements
- [ ] Graceful fallback without Tesseract
- [ ] Tests per document type

## Branch: \`feat/issue-10-ocr\`" \
"backend,ai,priority:critical,milestone:2-core-services" \
"M2: Core Services"

issue "Expense Processor - Field normalization" \
"## Description
Currency, date, amount normalization.

**Depends on:** #10

## Acceptance Criteria
- [ ] Currency: \$→USD, €→EUR, £→GBP, ¥→JPY + uppercase
- [ ] Amount: 2 decimal rounding, null for invalid
- [ ] Date: ISO, US, EU, natural language formats
- [ ] Tests for all edge cases

## Branch: \`feat/issue-11-normalization\`" \
"backend,priority:high,milestone:2-core-services" \
"M2: Core Services"

issue "Expense Processor - Processing pipeline orchestration" \
"## Description
Full pipeline: decode → OCR → AI extract → normalize → policy check → persist.

**Depends on:** #10, #11

## Acceptance Criteria
- [ ] POST /process orchestrates full pipeline
- [ ] Calls AI Engine /analyze + Policy Engine /check
- [ ] Determines status: approved, flagged, categorized
- [ ] Persists expense, policy_check, fraud_analysis
- [ ] List, detail, approve, analytics endpoints

## Branch: \`feat/issue-12-pipeline\`" \
"backend,priority:critical,milestone:2-core-services" \
"M2: Core Services"

# ======================== M3 ========================

issue "AI Engine - LangGraph analysis pipeline" \
"## Description
4-node StateGraph: extract → retrieve policies → fraud analysis → categorize.

**Depends on:** #3, #4

## Acceptance Criteria
- [ ] ExpenseAgentState TypedDict with 7 fields
- [ ] 4 async nodes: extract_fields, retrieve_policies, fraud_analysis, categorize
- [ ] Conditional edge: skip fraud for < \$100
- [ ] Graph compiles, POST /analyze invokes it
- [ ] Tests for graph structure and nodes

## Branch: \`feat/issue-13-langgraph-pipeline\`" \
"backend,ai,priority:critical,milestone:3-ai-engine" \
"M3: AI Engine"

issue "AI Engine - LLM prompts (extraction + fraud + chat)" \
"## Description
GPT-4o prompts for structured JSON extraction and fraud detection.

**Depends on:** #13

## Acceptance Criteria
- [ ] EXTRACTION_PROMPT: all fields as JSON
- [ ] FRAUD_ANALYSIS_PROMPT: 8 indicators, risk_score 0-1
- [ ] CHAT_SYSTEM_PROMPT: tool descriptions + {policy_context}
- [ ] JSON-only output enforcement
- [ ] Sample receipt prompt testing

## Branch: \`feat/issue-14-prompts\`" \
"ai,priority:critical,milestone:3-ai-engine" \
"M3: AI Engine"

issue "AI Engine - RAG pipeline with pgvector" \
"## Description
Policy document RAG: chunk, embed, store, retrieve with org isolation.

**Depends on:** #4, #13

## Acceptance Criteria
- [ ] 512-token chunks, 64-token overlap, preserve tables
- [ ] text-embedding-3-small (1536 dims)
- [ ] Cosine search filtered by organization_id
- [ ] Top-8 with 2x over-fetch and reranking
- [ ] Policy ingestion script

## Branch: \`feat/issue-15-rag-pipeline\`" \
"backend,ai,priority:high,milestone:3-ai-engine" \
"M3: AI Engine"

issue "AI Engine - Chat agent with tool routing" \
"## Description
LangGraph chat graph with tool-calling for spend queries.

**Depends on:** #13

## Acceptance Criteria
- [ ] query_spend_patterns + search_similar_expenses tools
- [ ] agent → tools → agent loop via bind_tools + ToolNode
- [ ] POST /chat endpoint
- [ ] Natural language responses with tool data

## Branch: \`feat/issue-16-chat-agent\`" \
"backend,ai,priority:high,milestone:3-ai-engine" \
"M3: AI Engine"

issue "AI Engine - Fraud detection tools" \
"## Description
Agent tools for fraud pattern detection.

**Depends on:** #13

## Acceptance Criteria
- [ ] detect_fraud_patterns tool
- [ ] Duplicate, round-number, weekend, split transaction detection
- [ ] Historical z-score comparison
- [ ] Risk score 0.0-1.0, GET /anomalies endpoint
- [ ] Tests per indicator

## Branch: \`feat/issue-17-fraud-tools\`" \
"backend,ai,priority:high,milestone:3-ai-engine" \
"M3: AI Engine"

# ======================== M4 ========================

issue "Policy Engine - Rule evaluation framework" \
"## Description
Pluggable evaluators with static method dispatch.

**Depends on:** #3

## Acceptance Criteria
- [ ] PolicyRule model with condition_type + parameters
- [ ] RuleEvaluator with 6 evaluators
- [ ] Category filtering (null = all)
- [ ] Returns None (compliant) or violation dict
- [ ] Tests for every evaluator

## Branch: \`feat/issue-18-rule-framework\`" \
"backend,priority:critical,milestone:4-policy-engine" \
"M4: Policy Engine"

issue "Policy Engine - Default rules and auto-approval" \
"## Description
7 default rules + compliance decision logic.

**Depends on:** #18

## Acceptance Criteria
- [ ] Rules: meal \$75, travel \$2000, receipt >\$25, auto-approve <\$50, weekend, duplicate, fraud block
- [ ] Action priority: reject > escalate > require_review > auto_approve
- [ ] POST /check returns PolicyCheckResponse
- [ ] GET /policies, POST /policies endpoints

## Branch: \`feat/issue-19-default-rules\`" \
"backend,priority:high,milestone:4-policy-engine" \
"M4: Policy Engine"

issue "Policy Engine - Organization-specific rules CRUD" \
"## Description
Custom rules per org in PostgreSQL.

**Depends on:** #18, #4

## Acceptance Criteria
- [ ] GET, POST, PUT, DELETE for org rules
- [ ] Custom rules merged with defaults at evaluation
- [ ] Priority ordering for conflicts
- [ ] Tests for CRUD + merging

## Branch: \`feat/issue-20-policy-crud\`" \
"backend,priority:medium,milestone:4-policy-engine" \
"M4: Policy Engine"

# ======================== M5 ========================

issue "Dashboard UI - React + TypeScript + Vite setup" \
"## Description
Frontend scaffold with routing, state, and API client.

**Depends on:** #1

## Acceptance Criteria
- [ ] Vite + React 18 + TypeScript + Tailwind
- [ ] TanStack Router + Query, Zustand
- [ ] Axios with JWT interceptor
- [ ] Layout: sidebar + header + content
- [ ] Login page, pnpm build succeeds

## Branch: \`feat/issue-21-dashboard-setup\`" \
"frontend,priority:critical,milestone:5-dashboard" \
"M5: Dashboard UI"

issue "Dashboard UI - Expense views (list, detail, upload)" \
"## Description
Expense management CRUD views.

**Depends on:** #21

## Acceptance Criteria
- [ ] List with filtering (status, category, date) + pagination
- [ ] Detail view: extraction, fraud, policy, approval actions
- [ ] Upload: drag-and-drop, document type selector
- [ ] Loading/error/empty states, responsive design

## Branch: \`feat/issue-22-expense-views\`" \
"frontend,priority:critical,milestone:5-dashboard" \
"M5: Dashboard UI"

issue "Dashboard UI - Analytics dashboard (Recharts)" \
"## Description
Spend visualizations with KPI cards and charts.

**Depends on:** #21

## Acceptance Criteria
- [ ] KPI cards: total spend, flagged, auto-approved, avg time
- [ ] Donut chart by category, area chart monthly trend
- [ ] Top merchants bar chart, anomaly alerts panel
- [ ] Period selector + department filter

## Branch: \`feat/issue-23-analytics\`" \
"frontend,priority:high,milestone:5-dashboard" \
"M5: Dashboard UI"

issue "Dashboard UI - AI chat interface" \
"## Description
Conversational AI panel for expense queries.

**Depends on:** #21, #16

## Acceptance Criteria
- [ ] Chat drawer/page with message bubbles + markdown
- [ ] Typing indicator, tool usage badges
- [ ] Expense context linking
- [ ] Session chat history in Zustand

## Branch: \`feat/issue-24-ai-chat-ui\`" \
"frontend,ai,priority:medium,milestone:5-dashboard" \
"M5: Dashboard UI"

issue "Dashboard UI - Policy admin interface" \
"## Description
Admin UI for policy CRUD with role gating.

**Depends on:** #21, #20

## Acceptance Criteria
- [ ] Policy list with active toggle
- [ ] Create/edit forms with rule builder
- [ ] Rule preview against sample expense
- [ ] admin/finance role gate

## Branch: \`feat/issue-25-policy-admin\`" \
"frontend,priority:medium,milestone:5-dashboard" \
"M5: Dashboard UI"

# ======================== M6 ========================

issue "Notification service (email, Slack, webhook)" \
"## Description
Async notification delivery via Celery.

**Depends on:** #5

## Acceptance Criteria
- [ ] Email (SMTP) + Slack (webhook) channels
- [ ] 4 templates: approved, flagged, rejected, batch_complete
- [ ] Celery async delivery with status tracking
- [ ] Tests for template rendering

## Branch: \`feat/issue-26-notifications\`" \
"backend,priority:medium,milestone:6-integration" \
"M6: Integration & Production"

issue "Batch processor (CSV/Excel)" \
"## Description
Batch transaction processing via Celery workers.

**Depends on:** #5, #12

## Acceptance Criteria
- [ ] CSV + Excel parsing
- [ ] Row-by-row Celery task queuing
- [ ] Progress tracking + error aggregation
- [ ] Completion notification

## Branch: \`feat/issue-27-batch-processor\`" \
"backend,priority:medium,milestone:6-integration" \
"M6: Integration & Production"

issue "Integration tests (end-to-end pipeline)" \
"## Description
Full lifecycle tests across all services.

**Depends on:** #12, #13, #19

## Acceptance Criteria
- [ ] Service health checks (all 4 backends + deep health)
- [ ] Upload→extract→analyze→approve pipeline
- [ ] Fraud detection→flag→review pipeline
- [ ] Batch upload→process→summary pipeline
- [ ] Chat query with tool routing
- [ ] Auth flow: login→token→protected routes
- [ ] Policy: auto-approve, flag, reject scenarios
- [ ] 70%+ coverage, --run-integration marker

## Branch: \`feat/issue-28-integration-tests\`" \
"testing,priority:critical,milestone:6-integration" \
"M6: Integration & Production"

issue "Load testing with Locust" \
"## Description
Scalability validation: 100 users, <500ms p95.

**Depends on:** #28

## Acceptance Criteria
- [ ] ExpenseUser + FinanceAdmin user classes
- [ ] Targets: 100 concurrent, 50 uploads/s, 1000 reads/s
- [ ] Named endpoints for clean reports
- [ ] Latency percentiles and bottleneck docs

## Branch: \`feat/issue-29-load-testing\`" \
"testing,performance,priority:high,milestone:6-integration" \
"M6: Integration & Production"

issue "Production Dockerfiles and Docker Compose" \
"## Description
Finalized multi-stage Dockerfiles + production compose.

**Depends on:** #28

## Acceptance Criteria
- [ ] 5 Dockerfiles with HEALTHCHECK
- [ ] docker-compose.yml: all services + infra + Celery
- [ ] Nginx: SPA routing + API proxy + caching
- [ ] All images build: docker compose build

## Branch: \`feat/issue-30-docker-prod\`" \
"infrastructure,devops,priority:critical,milestone:6-integration" \
"M6: Integration & Production"

issue "Kubernetes manifests (Kustomize)" \
"## Description
K8s base + prod overlay with HPA and Ingress.

**Depends on:** #30

## Acceptance Criteria
- [ ] Namespace, Deployments, Services, ConfigMap, HPA, Ingress
- [ ] Prod overlay: 3+ replicas, increased resources
- [ ] Readiness + liveness probes
- [ ] kubectl kustomize validates

## Branch: \`feat/issue-31-kubernetes\`" \
"infrastructure,devops,priority:high,milestone:6-integration" \
"M6: Integration & Production"

issue "Terraform AWS infrastructure" \
"## Description
VPC, Aurora PostgreSQL, ElastiCache Redis, S3, ECS, ALB, Secrets Manager.

**Depends on:** #30

## Acceptance Criteria
- [ ] VPC: 3 AZs, public/private subnets, NAT
- [ ] RDS: Aurora PG 16 Serverless v2, Multi-AZ
- [ ] ElastiCache: Redis 7, 2 nodes, encryption
- [ ] S3: versioned, lifecycle (IA 90d, Glacier 365d)
- [ ] ECS + ALB + Secrets Manager
- [ ] terraform validate passes

## Branch: \`feat/issue-32-terraform\`" \
"infrastructure,devops,priority:high,milestone:6-integration" \
"M6: Integration & Production"

issue "Architecture documentation (C4, sequences, ADRs)" \
"## Description
Complete docs: Mermaid diagrams + 4 ADRs.

## Acceptance Criteria
- [ ] C4 Level 1/2/3 diagrams
- [ ] 3 sequence diagrams (upload, batch, chat)
- [ ] AWS deployment diagram
- [ ] ADR-001 to ADR-004

## Branch: \`feat/issue-33-documentation\`" \
"documentation,priority:high,milestone:6-integration" \
"M6: Integration & Production"

issue "Seed data and demo script" \
"## Description
Sample data for development and demos.

**Depends on:** #4

## Acceptance Criteria
- [ ] 1 org, 5 users, 7 policies, 50+ expenses
- [ ] Policy document chunks with embeddings
- [ ] Dry run (default) + --insert flag

## Branch: \`feat/issue-34-seed-data\`" \
"tooling,priority:medium,milestone:6-integration" \
"M6: Integration & Production"

issue "Claude Code implementation skill" \
"## Description
.claude/skills/expense-platform/SKILL.md for guided implementation.

## Acceptance Criteria
- [ ] Project overview + repo structure
- [ ] Issue-by-issue commands with branch names
- [ ] Git conventions, test commands, deploy verification

## Branch: \`feat/issue-35-skill\`" \
"tooling,priority:medium,milestone:6-integration" \
"M6: Integration & Production"

# ---- Step 4: Summary ----
echo ""
echo "=============================================="
echo " COMPLETE: $N issues created"
echo "=============================================="
echo ""
echo " Repo: https://github.com/$REPO"
echo " All assigned to: $ASSIGNEE"
echo ""
echo " M1: Foundation (#1-#6)    M4: Policy Engine (#18-#20)"
echo " M2: Core Services (#7-#12) M5: Dashboard (#21-#25)"
echo " M3: AI Engine (#13-#17)   M6: Production (#26-#35)"
echo ""
echo " View:  https://github.com/$REPO/issues"
echo " Start: git checkout -b feat/issue-1-scaffolding"
echo "=============================================="
