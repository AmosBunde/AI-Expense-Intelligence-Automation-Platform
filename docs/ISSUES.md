# Git Issues - AI Expense Intelligence Platform

> Full implementation plan organized by milestones. Each issue includes scope, acceptance criteria, and dependencies.

---

## Milestone 1: Foundation & Infrastructure (Sprint 1-2)

### Issue #1: Project scaffolding and monorepo setup
**Labels:** `infrastructure`, `priority:critical`
**Assignee:** Lead Engineer

**Description:**
Initialize the monorepo with service directories, shared packages, configuration files, and developer tooling.

**Acceptance Criteria:**
- [ ] Directory structure matches architecture spec
- [ ] Root `pyproject.toml` with workspace config
- [ ] `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml`
- [ ] Ruff linter + formatter configuration
- [ ] Mypy type checking configuration
- [ ] All `__init__.py` files in place
- [ ] README with project overview

**Files:** Root configs, all `__init__.py`, `.github/` templates

---

### Issue #2: Docker infrastructure setup (PostgreSQL + pgvector, Redis, MinIO)
**Labels:** `infrastructure`, `priority:critical`
**Depends on:** #1

**Description:**
Create Docker Compose for local infrastructure: PostgreSQL 16 with pgvector extension, Redis 7, MinIO for S3-compatible storage, and pgAdmin.

**Acceptance Criteria:**
- [ ] `docker-compose.infra.yml` with health checks
- [ ] PostgreSQL starts with pgvector extension enabled
- [ ] Redis accessible on port 6379
- [ ] MinIO accessible with pre-created bucket
- [ ] pgAdmin accessible for DB management
- [ ] All volumes persist data across restarts

---

### Issue #3: Shared types package (Pydantic domain models)
**Labels:** `backend`, `priority:critical`
**Depends on:** #1

**Description:**
Create the `shared-types` package with all Pydantic v2 models, enums, and domain types used across services.

**Acceptance Criteria:**
- [ ] All enums: `ExpenseStatus`, `DocumentType`, `ExpenseCategory`, `FraudRiskLevel`, `PolicyViolationType`, `ApprovalAction`
- [ ] Core models: `Expense`, `ExpenseExtraction`, `LineItem`, `PolicyCheckResult`, `PolicyViolation`, `FraudAnalysis`
- [ ] API models: `PaginatedResponse`, `SpendSummary`, `HealthCheck`
- [ ] All models use `ConfigDict(from_attributes=True)` for ORM compat
- [ ] Unit tests for model validation and serialization

---

### Issue #4: Database client package (SQLAlchemy ORM + migrations)
**Labels:** `backend`, `priority:critical`
**Depends on:** #2, #3

**Description:**
Create the `db-client` package with SQLAlchemy async ORM models, connection pooling, and Alembic migration setup.

**Acceptance Criteria:**
- [ ] ORM models: `OrganizationORM`, `UserORM`, `ExpenseORM`, `PolicyORM`, `PolicyCheckORM`, `FraudAnalysisORM`, `PolicyDocumentChunkORM`
- [ ] Proper indexes on `expenses` table (user+status, org+date, category, created_at)
- [ ] `PolicyDocumentChunkORM` with pgvector `Vector(1536)` column
- [ ] `DatabaseClient` class with async session management and connection pooling
- [ ] Alembic setup with initial migration
- [ ] Tests for DB connection and model creation

---

### Issue #5: Queue client package (Celery task definitions)
**Labels:** `backend`, `priority:high`
**Depends on:** #2

**Description:**
Create the `queue-client` package with Celery app configuration, task definitions, and routing.

**Acceptance Criteria:**
- [ ] Celery app with Redis broker configuration
- [ ] Tasks: `process_single`, `process_batch`, `generate_report`, `send_notification`
- [ ] Task routing to dedicated queues
- [ ] Retry policies with exponential backoff
- [ ] Celery Beat schedule for periodic tasks (daily reconciliation, weekly summary)
- [ ] Tests for task serialization

---

### Issue #6: CI/CD pipeline (GitHub Actions)
**Labels:** `infrastructure`, `devops`, `priority:high`
**Depends on:** #1

**Description:**
Set up GitHub Actions workflow for linting, testing, building, and deployment.

**Acceptance Criteria:**
- [ ] Lint job: Ruff check + format
- [ ] Backend test job: pytest with PostgreSQL + Redis service containers
- [ ] Frontend test job: type-check + vitest + build
- [ ] Docker build job: matrix build all service images
- [ ] Coverage threshold: 70% minimum
- [ ] Deploy job: gated on main branch with environment approval

---

## Milestone 2: Core Services (Sprint 3-4)

### Issue #7: API Gateway - Authentication and JWT
**Labels:** `backend`, `security`, `priority:critical`
**Depends on:** #3, #4

**Description:**
Implement the API Gateway with JWT authentication, token creation/validation, and user context extraction.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/login` - returns JWT token
- [ ] JWT contains `sub` (user_id), `org` (org_id), `role`, `exp`
- [ ] `get_current_user` dependency extracts and validates JWT
- [ ] Expired tokens return 401
- [ ] Invalid tokens return 401
- [ ] Tests for all auth scenarios

---

### Issue #8: API Gateway - Rate limiting with Redis
**Labels:** `backend`, `security`, `priority:high`
**Depends on:** #7

**Description:**
Implement sliding window rate limiting using Redis sorted sets.

**Acceptance Criteria:**
- [ ] Sliding window counter per user
- [ ] Configurable limit via `RATE_LIMIT_PER_MINUTE` env var
- [ ] Returns 429 when limit exceeded
- [ ] Rate limit key expires automatically
- [ ] Integration test with Redis

---

### Issue #9: API Gateway - Request routing to downstream services
**Labels:** `backend`, `priority:critical`
**Depends on:** #7

**Description:**
Implement all API routes that proxy requests to downstream services with proper error handling.

**Acceptance Criteria:**
- [ ] `POST /api/v1/expenses/upload` - file upload to expense processor
- [ ] `GET /api/v1/expenses` - list with filtering and pagination
- [ ] `GET /api/v1/expenses/{id}` - single expense details
- [ ] `POST /api/v1/expenses/{id}/approve` - role-gated approval
- [ ] `POST /api/v1/ai/analyze` - trigger AI analysis
- [ ] `POST /api/v1/ai/chat` - conversational AI
- [ ] `GET /api/v1/analytics/spend-summary` - dashboard data
- [ ] `GET /api/v1/analytics/anomalies` - fraud alerts
- [ ] `GET/POST /api/v1/policies` - policy CRUD
- [ ] `POST /api/v1/batch/process` - batch upload
- [ ] `GET /health` and `GET /api/v1/health/deep`
- [ ] CORS configuration
- [ ] 502 error handling for downstream failures

---

### Issue #10: Expense Processor - OCR and text extraction
**Labels:** `backend`, `ai`, `priority:critical`
**Depends on:** #3

**Description:**
Implement document ingestion with OCR capabilities for receipts, invoices, and bank statements.

**Acceptance Criteria:**
- [ ] Tesseract OCR for image-based receipts
- [ ] PDF text extraction with pdf2image fallback
- [ ] CSV/text file direct parsing
- [ ] Graceful fallback when Tesseract is unavailable
- [ ] Base64 encoding for LLM vision processing fallback
- [ ] Tests for each document type

---

### Issue #11: Expense Processor - Field normalization
**Labels:** `backend`, `priority:high`
**Depends on:** #10

**Description:**
Implement field normalization for extracted expense data.

**Acceptance Criteria:**
- [ ] Currency symbol to ISO code mapping ($, €, £, ¥, KES)
- [ ] Amount rounding to 2 decimal places
- [ ] Date format normalization (US, EU, ISO, natural language)
- [ ] Null/missing field handling
- [ ] Unit tests for all normalization edge cases

---

### Issue #12: Expense Processor - Processing pipeline orchestration
**Labels:** `backend`, `priority:critical`
**Depends on:** #10, #11

**Description:**
Wire up the full processing pipeline: decode > OCR > AI extract > normalize > policy check > store.

**Acceptance Criteria:**
- [ ] `POST /process` endpoint orchestrates full pipeline
- [ ] Calls AI Engine for extraction + fraud analysis
- [ ] Calls Policy Engine for compliance check
- [ ] Determines final status based on fraud + policy results
- [ ] Database persistence of expense, policy check, and fraud analysis records
- [ ] Returns expense_id and status
- [ ] Integration tests for the full pipeline

---

## Milestone 3: AI Engine (Sprint 4-5)

### Issue #13: AI Engine - LangGraph analysis pipeline
**Labels:** `backend`, `ai`, `priority:critical`
**Depends on:** #3, #4

**Description:**
Build the LangGraph StateGraph for the expense analysis pipeline with nodes for extraction, RAG, fraud detection, and categorization.

**Acceptance Criteria:**
- [ ] `ExpenseAgentState` TypedDict with all required fields
- [ ] `extract_fields_node` - LLM extraction with structured JSON output
- [ ] `retrieve_policies_node` - RAG retrieval from pgvector
- [ ] `fraud_analysis_node` - LLM fraud assessment
- [ ] `categorize_node` - category refinement with policy context
- [ ] `should_analyze_fraud` conditional routing
- [ ] Graph compiles and runs end-to-end
- [ ] Tests for graph structure and node behavior

---

### Issue #14: AI Engine - LLM extraction prompts
**Labels:** `ai`, `priority:critical`
**Depends on:** #13

**Description:**
Design and implement extraction and fraud detection prompts for GPT-4o.

**Acceptance Criteria:**
- [ ] `EXTRACTION_PROMPT` extracts all required fields as JSON
- [ ] `FRAUD_ANALYSIS_PROMPT` checks all 8 indicator types
- [ ] `CHAT_SYSTEM_PROMPT` with tool descriptions and policy context
- [ ] Prompts enforce JSON-only output
- [ ] Prompts handle edge cases (missing fields, ambiguous data)
- [ ] Prompt testing with sample receipts

---

### Issue #15: AI Engine - RAG pipeline with pgvector
**Labels:** `backend`, `ai`, `priority:high`
**Depends on:** #4, #13

**Description:**
Implement RAG retrieval for company policy documents using pgvector.

**Acceptance Criteria:**
- [ ] Document chunking (512 tokens, 64 overlap)
- [ ] Embedding generation with OpenAI text-embedding-3-small
- [ ] `PolicyDocumentChunkORM` storage in pgvector
- [ ] Cosine similarity search filtered by organization_id
- [ ] Top-k retrieval with reranking
- [ ] Policy ingestion script for seeding
- [ ] Tests for retrieval relevance

---

### Issue #16: AI Engine - Chat agent with tools
**Labels:** `backend`, `ai`, `priority:high`
**Depends on:** #13

**Description:**
Build the conversational chat agent using LangGraph with tool-calling capabilities.

**Acceptance Criteria:**
- [ ] `query_spend_patterns` tool - aggregated spend queries
- [ ] `search_similar_expenses` tool - duplicate/similar expense search
- [ ] LangGraph chat graph with agent > tool > agent loop
- [ ] Tool routing based on LLM tool_calls
- [ ] Natural language responses with data from tools
- [ ] `POST /chat` endpoint
- [ ] Tests for tool routing and response generation

---

### Issue #17: AI Engine - Fraud detection tools
**Labels:** `backend`, `ai`, `priority:high`
**Depends on:** #13

**Description:**
Implement agent tools for fraud pattern detection.

**Acceptance Criteria:**
- [ ] `detect_fraud_patterns` tool definition
- [ ] `search_similar_expenses` for duplicate detection
- [ ] Round-number bias detection
- [ ] Weekend timing analysis
- [ ] Split transaction detection
- [ ] Historical pattern comparison
- [ ] Risk score calculation (0.0 - 1.0)
- [ ] Tests for each fraud indicator

---

## Milestone 4: Policy Engine (Sprint 5-6)

### Issue #18: Policy Engine - Rule evaluation framework
**Labels:** `backend`, `priority:critical`
**Depends on:** #3

**Description:**
Build the rule evaluation engine with pluggable evaluators.

**Acceptance Criteria:**
- [ ] `PolicyRule` model with condition_type, parameters, severity, action
- [ ] `RuleEvaluator` class with method dispatch
- [ ] Evaluators: amount_limit, receipt_required, auto_approve, weekend_check, duplicate_check, fraud_risk_check
- [ ] Rules filtered by category (null = applies to all)
- [ ] Tests for every evaluator with edge cases

---

### Issue #19: Policy Engine - Default rules and auto-approval
**Labels:** `backend`, `priority:high`
**Depends on:** #18

**Description:**
Define default policy rules and implement the auto-approval logic.

**Acceptance Criteria:**
- [ ] 7 default rules covering meals, travel, receipts, auto-approve, weekends, duplicates, fraud
- [ ] Auto-approval for small expenses (<$50 with receipt)
- [ ] Escalation for high-severity violations
- [ ] Rejection for critical fraud risk
- [ ] Action priority: reject > escalate > require_review > auto_approve
- [ ] `POST /check` endpoint
- [ ] Comprehensive tests for compliant, flagged, and rejected scenarios

---

### Issue #20: Policy Engine - Organization-specific rules (CRUD)
**Labels:** `backend`, `priority:medium`
**Depends on:** #18, #4

**Description:**
Support custom policy rules per organization stored in PostgreSQL.

**Acceptance Criteria:**
- [ ] `GET /policies` - list active rules for an org
- [ ] `POST /policies` - create new rule
- [ ] `PUT /policies/{id}` - update rule
- [ ] `DELETE /policies/{id}` - soft delete
- [ ] Rules loaded from DB merged with defaults
- [ ] Priority ordering for conflicting rules
- [ ] Tests for CRUD operations

---

## Milestone 5: Dashboard UI (Sprint 6-7)

### Issue #21: Dashboard UI - Project setup (React + TypeScript + Vite)
**Labels:** `frontend`, `priority:critical`
**Depends on:** #1

**Description:**
Initialize the React frontend with TypeScript, Vite, Tailwind CSS, and core dependencies.

**Acceptance Criteria:**
- [ ] Vite + React 18 + TypeScript setup
- [ ] Tailwind CSS configuration
- [ ] TanStack Router for routing
- [ ] TanStack Query for API state management
- [ ] Zustand for global state
- [ ] Axios HTTP client with JWT interceptor
- [ ] Layout component with sidebar navigation
- [ ] Login page

---

### Issue #22: Dashboard UI - Expense management views
**Labels:** `frontend`, `priority:critical`
**Depends on:** #21

**Description:**
Build expense list, detail, and upload views.

**Acceptance Criteria:**
- [ ] Expense list with filtering (status, category, date range)
- [ ] Pagination with page size selector
- [ ] Expense detail view with extraction data, fraud analysis, policy check
- [ ] Upload form with drag-and-drop file upload
- [ ] Real-time status updates
- [ ] Responsive design (mobile + desktop)

---

### Issue #23: Dashboard UI - Analytics dashboard
**Labels:** `frontend`, `priority:high`
**Depends on:** #21

**Description:**
Build the analytics dashboard with spend visualizations.

**Acceptance Criteria:**
- [ ] Spend summary cards (total, by period, trend)
- [ ] Category breakdown pie/donut chart (Recharts)
- [ ] Monthly spend trend line chart
- [ ] Top merchants bar chart
- [ ] Anomaly/fraud alerts panel
- [ ] Date range selector
- [ ] Department filter

---

### Issue #24: Dashboard UI - AI chat interface
**Labels:** `frontend`, `ai`, `priority:medium`
**Depends on:** #21, #16

**Description:**
Build chat UI for conversational AI expense queries.

**Acceptance Criteria:**
- [ ] Chat panel (slide-out or dedicated page)
- [ ] Message bubbles with markdown rendering
- [ ] Typing indicator during AI response
- [ ] Tool usage display (which tools the AI used)
- [ ] Expense context linking (chat about a specific expense)
- [ ] Chat history within session

---

### Issue #25: Dashboard UI - Policy management (admin)
**Labels:** `frontend`, `priority:medium`
**Depends on:** #21, #20

**Description:**
Build admin interface for managing expense policies.

**Acceptance Criteria:**
- [ ] Policy list with active/inactive toggle
- [ ] Policy creation form with rule builder
- [ ] Policy editing
- [ ] Rule preview (test against sample expense)
- [ ] Role-gated access (admin/finance only)

---

## Milestone 6: Integration & Production Readiness (Sprint 7-8)

### Issue #26: Notification service
**Labels:** `backend`, `priority:medium`
**Depends on:** #5

**Description:**
Implement notification delivery via email, Slack, and webhooks.

**Acceptance Criteria:**
- [ ] Email notifications via SMTP
- [ ] Slack webhook notifications
- [ ] Notification templates (approved, flagged, rejected, batch complete)
- [ ] Async delivery via Celery
- [ ] Delivery status tracking
- [ ] Tests for template rendering

---

### Issue #27: Batch processor implementation
**Labels:** `backend`, `priority:medium`
**Depends on:** #5, #12

**Description:**
Implement CSV/Excel batch transaction processing.

**Acceptance Criteria:**
- [ ] CSV parsing with header detection
- [ ] Excel (.xlsx) parsing
- [ ] Row-by-row processing via Celery tasks
- [ ] Progress tracking (processed/failed/total)
- [ ] Error collection and reporting
- [ ] Completion notification
- [ ] Tests for various CSV formats

---

### Issue #28: Integration tests (end-to-end pipeline)
**Labels:** `testing`, `priority:critical`
**Depends on:** #12, #13, #19

**Description:**
Write end-to-end integration tests covering the full expense lifecycle.

**Acceptance Criteria:**
- [ ] Test: Upload receipt > extract > analyze > policy check > approve
- [ ] Test: Upload receipt > extract > fraud detected > flag > manual review
- [ ] Test: Batch upload > process all > summary report
- [ ] Test: Chat query about spend patterns
- [ ] Test: Policy violation detection and escalation
- [ ] Tests run against real PostgreSQL + Redis (Docker)
- [ ] Minimum 70% coverage across all services

---

### Issue #29: Load testing with Locust
**Labels:** `testing`, `performance`, `priority:high`
**Depends on:** #28

**Description:**
Create load tests to validate scalability targets.

**Acceptance Criteria:**
- [ ] Locustfile with user scenarios (upload, list, chat, analytics)
- [ ] Target: 100 concurrent users, <500ms p95 latency
- [ ] Target: 50 expense uploads per second sustained
- [ ] Target: API Gateway handles 1000 req/s for reads
- [ ] Report with latency percentiles and throughput
- [ ] Identify bottlenecks and document tuning recommendations

---

### Issue #30: Production Docker Compose and Dockerfiles
**Labels:** `infrastructure`, `devops`, `priority:critical`
**Depends on:** #28

**Description:**
Finalize all Dockerfiles and production Docker Compose configuration.

**Acceptance Criteria:**
- [ ] Multi-stage builds for all services
- [ ] Non-root user in all containers
- [ ] Health checks on all containers
- [ ] Production compose with resource limits
- [ ] Secrets management via environment variables
- [ ] Logging configuration (JSON structured logs)
- [ ] All images build successfully

---

### Issue #31: Kubernetes manifests (Kustomize)
**Labels:** `infrastructure`, `devops`, `priority:high`
**Depends on:** #30

**Description:**
Create Kubernetes manifests using Kustomize for multi-environment deployment.

**Acceptance Criteria:**
- [ ] Base manifests: Deployments, Services, ConfigMaps, Secrets
- [ ] Dev overlay: single replica, debug logging
- [ ] Staging overlay: 2 replicas, staging config
- [ ] Prod overlay: autoscaling, resource limits, anti-affinity
- [ ] Namespace isolation
- [ ] Ingress configuration
- [ ] HPA for auto-scaling
- [ ] PDB for high availability

---

### Issue #32: Terraform infrastructure (AWS)
**Labels:** `infrastructure`, `devops`, `priority:high`
**Depends on:** #30

**Description:**
Create Terraform modules for AWS infrastructure provisioning.

**Acceptance Criteria:**
- [ ] VPC module: public/private subnets, NAT gateway
- [ ] ECS module: cluster, task definitions, services
- [ ] RDS module: PostgreSQL 16 with pgvector, Multi-AZ
- [ ] ElastiCache module: Redis cluster
- [ ] S3 module: versioned bucket with lifecycle policies
- [ ] ALB + CloudFront configuration
- [ ] Secrets Manager for API keys
- [ ] CloudWatch monitoring and alarms
- [ ] Dev and prod environment configurations

---

### Issue #33: Architecture documentation
**Labels:** `documentation`, `priority:high`
**Depends on:** All

**Description:**
Complete architecture documentation with C4 diagrams, sequence diagrams, and ADRs.

**Acceptance Criteria:**
- [ ] C4 Level 1: System Context diagram
- [ ] C4 Level 2: Container diagram
- [ ] C4 Level 3: Component diagram (AI Engine)
- [ ] Sequence diagram: Expense upload flow
- [ ] Sequence diagram: Batch processing flow
- [ ] Sequence diagram: AI chat flow
- [ ] Deployment architecture diagram
- [ ] ADR-001: Microservices vs monolith
- [ ] ADR-002: LangGraph for agent orchestration
- [ ] ADR-003: pgvector for RAG storage
- [ ] ADR-004: Rule-based policy engine
- [ ] API documentation (OpenAPI auto-generated)

---

### Issue #34: Seed data and demo script
**Labels:** `tooling`, `priority:medium`
**Depends on:** #4

**Description:**
Create seed data scripts for local development and demos.

**Acceptance Criteria:**
- [ ] Seed organizations and users (admin, manager, employee)
- [ ] Seed sample policy rules
- [ ] Seed 50+ sample expenses across all categories and statuses
- [ ] Seed policy document chunks with embeddings
- [ ] Demo script that walks through key flows
- [ ] `python scripts/seed_data.py` works cleanly

---

### Issue #35: Claude Code implementation skill
**Labels:** `tooling`, `priority:medium`
**Depends on:** All

**Description:**
Create a Claude Code skill for implementing all issues in this project.

**Acceptance Criteria:**
- [ ] SKILL.md with implementation workflow
- [ ] Issue-by-issue implementation commands
- [ ] Git commit conventions
- [ ] Testing commands per issue
- [ ] Deployment verification steps

---

## Issue Dependency Graph

```
#1 (Scaffolding)
├── #2 (Docker Infra) ──── #4 (DB Client) ──── #13 (AI LangGraph)
│                     │                    ├── #15 (RAG Pipeline)
│                     ├── #5 (Queue Client)├── #7 (Gateway Auth)
│                     │                    │
│                     └── #34 (Seed Data)  ├── #18 (Policy Rules)
│                                          │
├── #3 (Shared Types) ────────────────────┘
│
├── #6 (CI/CD)
│
└── #21 (Dashboard Setup)
     ├── #22 (Expense Views)
     ├── #23 (Analytics)
     ├── #24 (AI Chat)
     └── #25 (Policy Admin)

#10 (OCR) + #11 (Normalize) → #12 (Pipeline)
#13 + #14 (Prompts) + #15 + #16 (Chat) + #17 (Fraud) → AI Engine complete
#18 + #19 (Default Rules) + #20 (Custom Rules) → Policy Engine complete
#26 (Notifications) + #27 (Batch) → Integration layer
#28 (Integration Tests) + #29 (Load Tests) → Quality gate
#30 (Docker) + #31 (K8s) + #32 (Terraform) → Deployment ready
#33 (Docs) + #34 (Seed) + #35 (Skill) → Project complete
```
