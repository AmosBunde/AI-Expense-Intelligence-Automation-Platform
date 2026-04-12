#!/usr/bin/env bash
# =============================================================================
# claude_run_all_issues.sh
#
# Runs Claude Code (`claude -p`) against each issue with full implementation
# prompts. Claude Code reads the skill, implements the code, runs tests,
# commits, pushes, and creates the PR.
#
# Prerequisites:
#   1. Claude Code CLI installed: npm install -g @anthropic-ai/claude-code
#   2. Inside the cloned repo with scaffold files already committed
#   3. GitHub CLI authenticated: gh auth login
#   4. Issues already created on GitHub (create_github_issues.sh)
#   5. .claude/skills/expense-platform/SKILL.md exists in repo
#
# Usage:
#   chmod +x scripts/claude_run_all_issues.sh
#   ./scripts/claude_run_all_issues.sh           # Run all issues
#   ./scripts/claude_run_all_issues.sh --from 7  # Resume from issue #7
#   ./scripts/claude_run_all_issues.sh --issue 13 # Run single issue #13
#
# Each issue:
#   1. Checks out develop, creates feature branch
#   2. Runs `claude -p "prompt"` with full implementation instructions
#   3. Claude Code implements, tests, commits
#   4. Script pushes, creates PR, merges
# =============================================================================

set -euo pipefail

REPO="AmosBunde/AI-Expense-Intelligence-Automation-Platform"
START_FROM=1
SINGLE_ISSUE=0

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --from) START_FROM="$2"; shift 2 ;;
    --issue) SINGLE_ISSUE="$2"; START_FROM="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# Colors
G='\033[0;32m'
C='\033[0;36m'
B='\033[1m'
N='\033[0m'

log()  { echo -e "${G}>>>${N} $1"; }
step() { echo -e "\n${C}${B}══════════════════════════════════════════════════${N}"; echo -e "${C}${B}  ISSUE #$1: $2${N}"; echo -e "${C}${B}══════════════════════════════════════════════════${N}\n"; }

# Helper: branch → implement → push → PR → merge
run_issue() {
  local num="$1"
  local branch="$2"
  local commit_msg="$3"
  local pr_title="$4"
  local prompt="$5"

  step "$num" "$pr_title"

  # 1. Create branch
  git checkout develop
  git pull origin develop
  git checkout -b "$branch" 2>/dev/null || git checkout "$branch"

  # 2. Run Claude Code with the prompt
  log "Running Claude Code..."
  claude -p "$prompt" --allowedTools "Bash(git*),Bash(pytest*),Bash(python*),Bash(mkdir*),Bash(cat*),Bash(touch*),Bash(cp*),Bash(find*),Bash(pip*),Bash(cd*),Bash(ls*),Bash(ruff*),Edit,Write"

  # 3. Stage and commit
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "$commit_msg"
    log "Committed: $commit_msg"
  else
    log "No changes to commit (Claude may have already committed)"
  fi

  # 4. Push
  git push -u origin "$branch"
  log "Pushed branch: $branch"

  # 5. Create PR
  gh pr create \
    --repo "$REPO" \
    --base develop \
    --head "$branch" \
    --title "$pr_title" \
    --body "Closes #$num - Implemented by Claude Code" \
    --assignee AmosBunde 2>/dev/null || log "PR may already exist"

  # 6. Auto-merge
  sleep 3
  gh pr merge --repo "$REPO" --squash --auto --delete-branch "$branch" 2>/dev/null || log "Auto-merge queued"

  # 7. Return to develop
  sleep 2
  git checkout develop
  git pull origin develop

  log "Issue #$num complete."

  # Exit if single issue mode
  if [[ "$SINGLE_ISSUE" -gt 0 ]]; then
    exit 0
  fi
}

echo -e "${B}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║  AI Expense Intelligence Platform                    ║"
echo "║  Claude Code Implementation Runner                   ║"
echo "║  Repo: $REPO               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${N}"

# Ensure we start clean
git checkout develop 2>/dev/null || git checkout -b develop
git pull origin develop 2>/dev/null || true

# =============================================================================
# ISSUE #1
# =============================================================================
if [[ "$START_FROM" -le 1 ]]; then
run_issue 1 "feat/issue-1-scaffolding" \
  "feat: project scaffolding and monorepo structure (#1)" \
  "Project scaffolding and monorepo setup" \
'Read the skill at .claude/skills/expense-platform/SKILL.md first.

You are implementing Issue #1: Project Scaffolding for the AI Expense Intelligence Platform.

Create the complete project directory structure:

services/
  api-gateway/src/ api-gateway/tests/
  expense-processor/src/ expense-processor/tests/
  ai-engine/src/ ai-engine/tests/
  policy-engine/src/ policy-engine/tests/
  dashboard-ui/src/
  notification-service/src/
  batch-processor/src/
packages/
  shared-types/src/
  db-client/src/
  queue-client/src/
infrastructure/docker/ infrastructure/k8s/base/ infrastructure/k8s/overlays/dev/ infrastructure/k8s/overlays/staging/ infrastructure/k8s/overlays/prod/
infrastructure/terraform/modules/ infrastructure/terraform/environments/dev/ infrastructure/terraform/environments/prod/
docs/architecture/ docs/api/ docs/deployment/ docs/adr/
scripts/
tests/integration/ tests/load/

Create __init__.py in every Python src/ and tests/ directory.

Create these root files if they do not exist:
- pyproject.toml with ruff, mypy, pytest config (target py312, 70% coverage minimum)
- .gitignore (Python, Node, Docker, Terraform, IDE, OS files)
- .env.example with all env vars (DATABASE_URL, REDIS_URL, OPENAI_API_KEY, JWT_SECRET, S3_BUCKET, etc.)
- README.md with architecture overview

Do NOT create service implementation files yet - only the structure.
Commit with message: "feat: project scaffolding and monorepo structure (#1)"'
fi

# =============================================================================
# ISSUE #2
# =============================================================================
if [[ "$START_FROM" -le 2 ]]; then
run_issue 2 "feat/issue-2-docker-infra" \
  "infra: Docker Compose for PostgreSQL+pgvector, Redis, MinIO (#2)" \
  "Docker infrastructure setup" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issue #2: Docker infrastructure for local development.

Create infrastructure/docker/docker-compose.infra.yml with:
- PostgreSQL 16 using image pgvector/pgvector:pg16
  - DB: expense_db, User: expense_user, Pass: expense_pass
  - Port 5432, health check with pg_isready, persistent volume
- Redis 7 Alpine
  - Port 6379, health check with redis-cli ping, persistent volume
- MinIO (latest)
  - Ports 9000 (API) + 9001 (console)
  - Root user/pass: minioadmin/minioadmin
  - Health check on /minio/health/live
- minio-init service that creates the expense-documents bucket using mc CLI
- pgAdmin on port 5050 (admin@expense.local / admin)

Create infrastructure/docker/init.sql:
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS pg_trgm;

Mount init.sql as /docker-entrypoint-initdb.d/init.sql in the postgres service.

Commit: "infra: Docker Compose for PostgreSQL+pgvector, Redis, MinIO (#2)"'
fi

# =============================================================================
# ISSUE #3
# =============================================================================
if [[ "$START_FROM" -le 3 ]]; then
run_issue 3 "feat/issue-3-shared-types" \
  "feat(shared-types): Pydantic domain models and enums (#3)" \
  "Shared types package" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issue #3: Shared types package at packages/shared-types/

Create packages/shared-types/src/models.py with ALL these Pydantic v2 models:

Enums:
- ExpenseStatus: pending, processing, extracted, categorized, policy_checked, approved, flagged, rejected, paid
- DocumentType: receipt, invoice, bank_statement, credit_card, manual_entry
- ExpenseCategory: travel, meals, office_supplies, software, marketing, utilities, rent, professional_services, equipment, insurance, training, entertainment, shipping, miscellaneous
- FraudRiskLevel: low, medium, high, critical
- PolicyViolationType: over_limit, missing_receipt, duplicate_expense, policy_breach, suspicious_pattern, unapproved_vendor, weekend_expense, split_expense
- ApprovalAction: auto_approve, require_review, escalate, reject

Models (all with ConfigDict(from_attributes=True)):
- ExtractedField: field_name, value, confidence (0-1), bounding_box optional
- LineItem: description, quantity, unit_price (Decimal), total (Decimal)
- ExpenseExtraction: merchant_name, merchant_address, transaction_date, amount (Decimal), currency, tax_amount, tip_amount, payment_method, line_items, category, category_confidence
- PolicyViolation: violation_type, severity, description, policy_reference, threshold_value, actual_value
- PolicyCheckResult: expense_id (UUID), is_compliant, violations list, recommended_action, auto_approved, notes
- FraudAnalysis: expense_id (UUID), risk_level, risk_score (0-1), indicators list, explanation, similar_expenses
- ExpenseCreate: document_type, file_key optional, raw_text optional, metadata dict
- Expense: full model with id, user_id, organization_id, status, all fields, timestamps
- PaginatedResponse: items, total, page, page_size, has_next
- SpendSummary: period, total_spend, by_category, by_department, top_merchants, flagged_count, auto_approved_count
- HealthCheck: status, service, version, uptime_seconds, dependencies

Create packages/shared-types/pyproject.toml with pydantic>=2.0 dependency.
Create packages/shared-types/tests/test_models.py with tests for:
- Enum membership
- Model creation with valid data
- Model validation (reject invalid confidence scores, negative amounts)
- JSON serialization round-trip

Run: pytest packages/shared-types/tests/ -v
Commit: "feat(shared-types): Pydantic domain models and enums (#3)"'
fi

# =============================================================================
# ISSUE #4
# =============================================================================
if [[ "$START_FROM" -le 4 ]]; then
run_issue 4 "feat/issue-4-db-client" \
  "feat(db-client): SQLAlchemy ORM models, migrations, connection pooling (#4)" \
  "Database client package" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issue #4: Database client at packages/db-client/

Create packages/db-client/src/database.py with:

ORM Models (SQLAlchemy 2.0 async, DeclarativeBase):
- OrganizationORM: id (UUID PK), name, settings (JSONB), created_at
- UserORM: id, organization_id FK, email (unique), hashed_password, full_name, role, department, is_active, created_at
- ExpenseORM: id, user_id FK, organization_id FK, status (enum), document_type (enum), file_key, merchant_name, merchant_address, transaction_date, amount (Numeric 12,2), currency, tax_amount, tip_amount, payment_method, category (enum), category_confidence (Float), extraction_data (JSONB), line_items (JSONB), tags (ARRAY String), notes, approved_by FK, approved_at, created_at, updated_at
  - Indexes: (user_id, status), (organization_id, transaction_date), (category), (created_at)
- PolicyORM: id, organization_id FK, name, description, rules (JSONB), category (nullable enum), is_active, priority, created_at
- PolicyCheckORM: id, expense_id FK, is_compliant, violations (JSONB), recommended_action, auto_approved, notes, checked_at
- FraudAnalysisORM: id, expense_id FK, risk_level (enum), risk_score (Float), indicators (JSONB), explanation, similar_expense_ids (ARRAY UUID), analyzed_at
- PolicyDocumentChunkORM: id, organization_id FK, document_name, chunk_text, chunk_index, embedding (Vector 1536 from pgvector), metadata (JSONB), created_at

DatabaseClient class:
- __init__(database_url, pool_size=20, max_overflow=10)
- Uses create_async_engine with pool_pre_ping=True
- async_sessionmaker with expire_on_commit=False
- get_session() async generator with commit/rollback
- init_db() creates pgvector extension and all tables
- close() disposes engine

Create packages/db-client/pyproject.toml.
Run any tests if possible.
Commit: "feat(db-client): SQLAlchemy ORM models, migrations, connection pooling (#4)"'
fi

# =============================================================================
# ISSUE #5
# =============================================================================
if [[ "$START_FROM" -le 5 ]]; then
run_issue 5 "feat/issue-5-queue-client" \
  "feat(queue-client): Celery tasks with routing and retry (#5)" \
  "Queue client package" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issue #5: Queue client at packages/queue-client/

Create packages/queue-client/src/tasks.py:
- Celery app with Redis broker from CELERY_BROKER_URL env var
- JSON serializer, UTC timezone, acks_late, prefetch=1
- Task routing: process_single→expense_processing queue, process_batch→batch_processing, generate_report→reporting, send_notification→notifications
- process_single(expense_id, file_key, organization_id): calls expense processor via httpx, max_retries=3 with exponential backoff
- process_batch(file_content_b64, filename, organization_id, user_id): parses CSV, queues individual tasks
- generate_report(organization_id, period, report_type): placeholder
- send_notification(channel, recipient, template, context): placeholder
- Beat schedule: daily reconciliation (86400s), weekly summary (604800s)

Create pyproject.toml.
Commit: "feat(queue-client): Celery tasks with routing and retry (#5)"'
fi

# =============================================================================
# ISSUE #6
# =============================================================================
if [[ "$START_FROM" -le 6 ]]; then
run_issue 6 "feat/issue-6-cicd" \
  "infra: GitHub Actions CI/CD pipeline (#6)" \
  "CI/CD pipeline" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issue #6: GitHub Actions CI/CD.

Create .github/workflows/ci.yml:
- Trigger: push to main/develop, PR to main
- Job 1 "lint": Python 3.12, ruff check + ruff format --check on services/ packages/
- Job 2 "test-backend" (needs lint): PostgreSQL pgvector:pg16 + Redis 7 service containers, install all Python deps, run pytest on each service with coverage, --cov-fail-under=70
- Job 3 "test-frontend" (needs lint): Node 20, pnpm install/type-check/test/build in services/dashboard-ui
- Job 4 "docker-build" (needs test-backend + test-frontend, only main): matrix strategy building 5 service images with docker/build-push-action, GHA cache
- Job 5 "deploy" (needs docker-build, only main): placeholder with environment approval

Create .github/ISSUE_TEMPLATE/feature.md issue template.
Create .github/pull_request_template.md.
Commit: "infra: GitHub Actions CI/CD pipeline (#6)"'
fi

# =============================================================================
# ISSUES #7-9: API Gateway
# =============================================================================
if [[ "$START_FROM" -le 7 ]]; then
run_issue "7" "feat/issue-7-9-api-gateway" \
  "feat(api-gateway): JWT auth, Redis rate limiting, full request routing (#7, #8, #9)" \
  "API Gateway: auth + rate limiting + routing" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #7, #8, #9: Complete API Gateway at services/api-gateway/

Create services/api-gateway/src/main.py with FastAPI app:

AUTHENTICATION (#7):
- Settings model reading from env vars
- create_token(user_id, org_id, role) using PyJWT
- POST /api/v1/auth/login accepting email+password, returning JWT
- get_current_user dependency: validates Bearer token, returns TokenPayload(sub, org, role, exp)
- 401 for expired/invalid tokens

RATE LIMITING (#8):
- rate_limit dependency using Redis sorted sets (ZSET)
- Sliding window: ZREMRANGEBYSCORE + ZADD + ZCARD in pipeline
- Configurable RATE_LIMIT_PER_MINUTE, returns 429 when exceeded
- Key format: rate:{user_id}, expires after 120s

ROUTING (#9) - all routes use rate_limit dependency:
- POST /api/v1/expenses/upload: file upload, forwards to expense processor
- GET /api/v1/expenses: list with page, page_size, status, category filters
- GET /api/v1/expenses/{id}: single expense
- POST /api/v1/expenses/{id}/approve: role-gated (manager/admin/finance)
- POST /api/v1/ai/analyze: forward to AI engine
- POST /api/v1/ai/chat: forward to AI engine
- GET /api/v1/analytics/spend-summary: with period param
- GET /api/v1/analytics/anomalies: forward to AI engine
- GET /api/v1/policies + POST /api/v1/policies: policy CRUD (POST admin-only)
- POST /api/v1/batch/process: batch upload (admin/finance only)
- GET /health: basic health
- GET /api/v1/health/deep: checks all downstream services + Redis

CORS middleware with configurable origins. httpx.AsyncClient in lifespan.

Create services/api-gateway/tests/test_gateway.py with tests for:
- Login returns token
- Invalid/expired/missing token handling
- Role-based access control (employee cannot approve)
- Input validation (page=0 rejected, page_size=500 rejected)
- Health check response
- CORS headers

Create services/api-gateway/pyproject.toml.
Run: pytest services/api-gateway/tests/ -v
Commit: "feat(api-gateway): JWT auth, Redis rate limiting, full request routing (#7, #8, #9)"'
fi

# =============================================================================
# ISSUES #10-12: Expense Processor
# =============================================================================
if [[ "$START_FROM" -le 10 ]]; then
run_issue "10" "feat/issue-10-12-expense-processor" \
  "feat(expense-processor): OCR extraction, normalization, processing pipeline (#10, #11, #12)" \
  "Expense Processor: OCR + normalization + pipeline" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #10, #11, #12: Complete Expense Processor at services/expense-processor/

Create services/expense-processor/src/main.py:

OCR & TEXT EXTRACTION (#10):
- extract_text_from_document(file_bytes, document_type) async function
- For receipt/invoice: try pytesseract on PIL Image, fallback to base64 string
- For bank_statement: decode UTF-8, fallback for binary
- Graceful handling of missing Tesseract

NORMALIZATION (#11):
- normalize_extraction(raw_extraction) function
- Currency: $ → USD, € → EUR, £ → GBP, ¥ → JPY, uppercase all
- Amount: round to 2 decimals, None for invalid strings
- Date: try ISO, US (MM/DD/YYYY), EU (DD/MM/YYYY), natural (April 10, 2026)

PIPELINE (#12):
- POST /process endpoint:
  1. Decode base64 file content
  2. OCR text extraction
  3. POST to AI Engine /analyze (raw_text, org_id)
  4. Normalize the extraction result
  5. POST to Policy Engine /check (expense data + fraud result)
  6. Determine status: flagged if high/critical fraud or non-compliant, approved if auto_approved, else categorized
  7. Return {expense_id, status, extraction}

- GET /expenses: list with user_id, org_id, pagination
- GET /expenses/{id}: single expense
- POST /expenses/{id}/approve: mark as approved
- GET /analytics/summary: spend summary placeholder
- GET /health

Create services/expense-processor/tests/test_processor.py with tests for:
- Currency normalization (all symbols + codes)
- Amount rounding and None handling
- Date format parsing (ISO, US, EU)
- OCR fallback behavior
- All endpoint responses

Create services/expense-processor/pyproject.toml.
Run: pytest services/expense-processor/tests/ -v
Commit: "feat(expense-processor): OCR extraction, normalization, processing pipeline (#10, #11, #12)"'
fi

# =============================================================================
# ISSUES #13-17: AI Engine (complete)
# =============================================================================
if [[ "$START_FROM" -le 13 ]]; then
run_issue "13" "feat/issue-13-17-ai-engine" \
  "feat(ai-engine): LangGraph pipeline, prompts, RAG, chat agent, fraud tools (#13-#17)" \
  "AI Engine: LangGraph + prompts + RAG + chat + fraud" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #13, #14, #15, #16, #17: Complete AI Engine at services/ai-engine/

Create services/ai-engine/src/main.py:

LANGGRAPH PIPELINE (#13):
- ExpenseAgentState TypedDict: messages, expense_data, organization_id, policy_context, analysis_result, fraud_indicators, category_prediction
- build_analysis_graph() → StateGraph with 4 nodes:
  - extract_fields_node: calls GPT-4o with EXTRACTION_PROMPT
  - retrieve_policies_node: RAG retrieval (pgvector placeholder)
  - fraud_analysis_node: calls GPT-4o with FRAUD_ANALYSIS_PROMPT
  - categorize_node: refines category with policy context
- Edges: extract → retrieve → conditional(should_analyze_fraud) → categorize → END
- should_analyze_fraud: returns "fraud_analysis" if amount > 100, else "categorize"

PROMPTS (#14):
- EXTRACTION_PROMPT: extracts merchant_name, merchant_address, transaction_date, amount, currency, tax_amount, tip_amount, payment_method, line_items, category, category_confidence as JSON
- FRAUD_ANALYSIS_PROMPT: checks DUPLICATE, ROUND_NUMBER, WEEKEND_TIMING, SPLIT_TRANSACTION, UNUSUAL_AMOUNT, SUSPICIOUS_MERCHANT, RAPID_SUBMISSION, MISSING_DETAILS. Returns risk_level, risk_score, indicators, explanation, recommended_action as JSON
- CHAT_SYSTEM_PROMPT: conversational assistant with {policy_context} placeholder

RAG (#15):
- Create services/ai-engine/src/rag/retriever.py
- retrieve_policy_chunks(query, organization_id, top_k=8) async function
- Placeholder that returns sample policy strings (production: pgvector cosine search)

CHAT AGENT (#16):
- build_chat_graph() → StateGraph with agent + tools nodes
- Tools: query_spend_patterns(organization_id, period, group_by), search_similar_expenses(merchant_name, amount, date_range_days)
- Agent uses llm.bind_tools(tools), routes to ToolNode when tool_calls present
- POST /chat endpoint

FRAUD TOOLS (#17):
- detect_fraud_patterns tool definition
- GET /anomalies endpoint

ENDPOINTS:
- POST /analyze: invokes analysis graph
- POST /chat: invokes chat graph
- GET /anomalies: list anomalies
- GET /health

Create services/ai-engine/tests/test_ai_engine.py with tests for:
- Prompt contains required fields
- Graph compilation (both analysis and chat)
- should_analyze_fraud routing logic
- Health endpoint

Create services/ai-engine/pyproject.toml.
Run: pytest services/ai-engine/tests/ -v
Commit: "feat(ai-engine): LangGraph pipeline, prompts, RAG, chat agent, fraud tools (#13-#17)"'
fi

# =============================================================================
# ISSUES #18-20: Policy Engine
# =============================================================================
if [[ "$START_FROM" -le 18 ]]; then
run_issue "18" "feat/issue-18-20-policy-engine" \
  "feat(policy-engine): rule evaluation framework with default rules and CRUD (#18, #19, #20)" \
  "Policy Engine: rules + defaults + CRUD" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #18, #19, #20: Complete Policy Engine at services/policy-engine/

Create services/policy-engine/src/main.py:

RULE FRAMEWORK (#18):
- PolicyRule Pydantic model: id, name, description, category (nullable), condition_type, parameters dict, violation_severity, action_on_violation, is_active
- RuleEvaluator class with static evaluate(rule, expense_data) method
- Method dispatch by condition_type to evaluator methods
- Evaluators return None (compliant) or violation dict

EVALUATORS:
- _check_amount_limit: compares amount vs max_amount parameter
- _check_receipt_required: flags if amount > threshold and no file_key
- _check_auto_approve: returns {_auto_approve: True} if amount <= max_amount
- _check_weekend: parses transaction_date, flags if weekday >= 5
- _check_duplicate: placeholder (needs DB query)
- _check_fraud_risk: checks fraud_analysis.risk_level against block_levels

DEFAULT RULES (#19):
- meal-limit: meals > $75 → require_review (medium)
- travel-limit: travel > $2000 → escalate (high)
- receipt-required: any > $25 without receipt → require_review (medium)
- auto-approve-small: any <= $50 → auto_approve (low)
- weekend-flag: weekend date → require_review (low)
- duplicate-check: 7 days, 10% tolerance → escalate (high)
- high-risk-fraud: high/critical fraud → reject (critical)

DECISION LOGIC:
- POST /check: evaluate all applicable rules, collect violations
- Action priority: reject > escalate > require_review > auto_approve
- Auto-approve only if eligible AND zero violations

CRUD (#20):
- GET /policies?organization_id=X
- POST /policies: create new rule
- GET /health

Create services/policy-engine/tests/test_policy_engine.py with COMPREHENSIVE tests:
- Amount under/over/exact limit
- Receipt with/without for various amounts
- Weekend vs weekday dates
- Auto-approve eligibility
- Fraud risk blocking
- Full /check endpoint: compliant, over-limit, fraud-rejected
- Default rule integrity (unique IDs, valid condition types)

Create services/policy-engine/pyproject.toml.
Run: pytest services/policy-engine/tests/ -v
ALL TESTS MUST PASS.
Commit: "feat(policy-engine): rule evaluation framework with default rules and CRUD (#18, #19, #20)"'
fi

# =============================================================================
# ISSUES #21-25: Dashboard UI
# =============================================================================
if [[ "$START_FROM" -le 21 ]]; then
run_issue "21" "feat/issue-21-25-dashboard" \
  "feat(dashboard): React UI with expense views, analytics, chat, policy admin (#21-#25)" \
  "Dashboard UI: React + TypeScript" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #21-25: Dashboard UI at services/dashboard-ui/

Create a Vite + React 18 + TypeScript project:

package.json with dependencies: react, react-dom, @tanstack/react-query, zustand, axios, recharts
devDependencies: @types/react, @types/react-dom, @vitejs/plugin-react, typescript, vite, vitest, tailwindcss, postcss, autoprefixer

Create:
- vite.config.ts
- tsconfig.json (strict, ESNext, react-jsx)
- tailwind.config.js
- postcss.config.js
- index.html
- src/main.tsx (root render with QueryClientProvider)
- src/App.tsx (router shell with sidebar nav)
- src/lib/api.ts (axios instance with JWT interceptor from zustand store)
- src/stores/auth.ts (zustand store: token, user, login/logout)
- src/pages/Login.tsx (email + password form)
- src/pages/Expenses.tsx (table with status/category filters, pagination)
- src/pages/ExpenseDetail.tsx (extraction data, fraud panel, policy panel)
- src/pages/Upload.tsx (drag-and-drop file upload)
- src/pages/Analytics.tsx (KPI cards + Recharts: PieChart by category, AreaChart monthly trend)
- src/pages/Chat.tsx (message bubbles, input field, typing indicator)
- src/pages/Policies.tsx (policy list with create form)
- src/components/Layout.tsx (sidebar + header + content)
- src/components/StatusBadge.tsx (colored badges for expense status)

Make sure `npx tsc --noEmit` passes (or at least no blocking errors).
Commit: "feat(dashboard): React UI with expense views, analytics, chat, policy admin (#21-#25)"'
fi

# =============================================================================
# ISSUES #26-27: Notifications + Batch
# =============================================================================
if [[ "$START_FROM" -le 26 ]]; then
run_issue "26" "feat/issue-26-27-notifications-batch" \
  "feat: notification service and batch processor (#26, #27)" \
  "Notifications + Batch processor" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #26, #27:

Create services/notification-service/src/main.py:
- FastAPI app with POST /notify endpoint
- Accepts: channel (email/slack/webhook), recipient, template, context
- Email: sends via SMTP using smtplib (config from env)
- Slack: POST to webhook URL with formatted message
- 4 templates: expense_approved, expense_flagged, expense_rejected, batch_complete
- GET /health

Create services/batch-processor/src/main.py:
- FastAPI app with POST /batch endpoint
- Accepts base64 file content + filename
- CSV parsing with csv.DictReader
- Excel support mention (openpyxl)
- Queues individual process_single tasks via Celery
- Returns {processed, failed, errors} counts
- GET /health

Commit: "feat: notification service and batch processor (#26, #27)"'
fi

# =============================================================================
# ISSUES #28-29: Tests
# =============================================================================
if [[ "$START_FROM" -le 28 ]]; then
run_issue "28" "feat/issue-28-29-testing" \
  "test: integration tests and Locust load testing (#28, #29)" \
  "Integration + Load tests" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #28, #29:

Create tests/integration/conftest.py:
- pytest_addoption for --run-integration flag
- Skip integration tests unless flag is passed
- integration marker

Create tests/integration/test_full_pipeline.py:
- TestServiceHealth: health check all 4 backends + deep health
- TestExpenseUploadPipeline: upload receipt, list expenses
- TestPolicyCheckPipeline: compliant auto-approve, over-limit flag, fraud reject
- TestAIAnalysisPipeline: analyze endpoint, chat endpoint
- TestAnalyticsPipeline: spend summary, anomalies
- TestAuthIntegration: login, protected routes, invalid token
- All use httpx.Client with base URLs from env vars
- Accept 200 or 502 (services may not be running)

Create tests/load/locustfile.py:
- ExpenseUser (weight 3): list (3x), detail (2x), upload (1x), analytics (2x), chat (1x), health (1x)
- FinanceAdmin (weight 1): analytics (3x), anomalies (2x), policies (1x)
- Both login in on_start and use JWT headers
- Named endpoints for clean reporting

Commit: "test: integration tests and Locust load testing (#28, #29)"'
fi

# =============================================================================
# ISSUES #30-32: Production Infrastructure
# =============================================================================
if [[ "$START_FROM" -le 30 ]]; then
run_issue "30" "feat/issue-30-32-prod-infra" \
  "infra: production Dockerfiles, Kubernetes manifests, Terraform (#30, #31, #32)" \
  "Docker + K8s + Terraform" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #30, #31, #32:

DOCKERFILES (#30):
Create infrastructure/docker/Dockerfile.api-gateway: Python 3.12-slim, install deps, HEALTHCHECK, uvicorn with 4 workers on port 8000
Create infrastructure/docker/Dockerfile.ai-engine: Python 3.12-slim, langchain/langgraph deps, 2 workers on port 8001
Create infrastructure/docker/Dockerfile.expense-processor: Python 3.12-slim + tesseract-ocr + poppler-utils, 4 workers on port 8002
Create infrastructure/docker/Dockerfile.policy-engine: Python 3.12-slim, 4 workers on port 8003
Create infrastructure/docker/Dockerfile.dashboard-ui: node:20-alpine builder stage → nginx:alpine with built assets
Create infrastructure/docker/nginx.conf: SPA routing (try_files), /api/ proxy to api-gateway:8000, static asset caching, gzip

Create docker-compose.yml (root): all services + infra + celery-worker + celery-beat, x-common-env YAML anchor, service dependencies with health check conditions

KUBERNETES (#31):
Create infrastructure/k8s/base/deployments.yaml: namespace, Deployments (api-gateway, ai-engine, expense-processor, policy-engine, celery-worker), Services, ConfigMap, HPA for api-gateway, Ingress with TLS
Create infrastructure/k8s/base/kustomization.yaml
Create infrastructure/k8s/overlays/prod/kustomization.yaml: 3 replicas for gateway/ai-engine, 5 for celery, increased resources

TERRAFORM (#32):
Create infrastructure/terraform/environments/prod/main.tf: VPC (3 AZs), Aurora PG 16 Serverless v2, ElastiCache Redis, S3 with lifecycle, ECS cluster, ALB, security groups, Secrets Manager, outputs

Commit: "infra: production Dockerfiles, Kubernetes manifests, Terraform (#30, #31, #32)"'
fi

# =============================================================================
# ISSUES #33-35: Docs + Seed + Skill
# =============================================================================
if [[ "$START_FROM" -le 33 ]]; then
run_issue "33" "feat/issue-33-35-docs-seed-skill" \
  "docs: architecture diagrams, ADRs, seed data, implementation skill (#33, #34, #35)" \
  "Documentation + Seed data + Claude skill" \
'Read .claude/skills/expense-platform/SKILL.md first.

Implement Issues #33, #34, #35:

ARCHITECTURE DOCS (#33):
Create docs/architecture/ARCHITECTURE.md with Mermaid diagrams:
- C4 Level 1: System Context (users, platform, external systems)
- C4 Level 2: Container diagram (7 services + 3 data stores)
- C4 Level 3: Component diagram for AI Engine
- Sequence: expense upload flow (User→UI→Gateway→Processor→AI→Policy→DB)
- Sequence: batch processing flow
- Sequence: AI chat with tool routing
- Deployment: AWS architecture

Create docs/adr/001-microservices.md: why microservices over monolith
Create docs/adr/002-langgraph.md: why LangGraph for agent orchestration
Create docs/adr/003-pgvector.md: why pgvector over dedicated vector DB
Create docs/adr/004-rule-engine.md: why rule-based policy over LLM evaluation

SEED DATA (#34):
Create scripts/seed_data.py:
- 20 sample merchants with categories and typical amounts
- Generate 50+ expenses with random merchants, amounts, dates, statuses
- Print summary: total spend, by category, by status, user list
- Support --insert flag for actual DB insertion

SKILL (#35):
Create .claude/skills/expense-platform/SKILL.md if not exists, ensure it has:
- Project overview and repo structure
- Issue-by-issue implementation commands with branch names
- Git conventions, testing commands, deployment verification

Commit: "docs: architecture diagrams, ADRs, seed data, implementation skill (#33, #34, #35)"'
fi

# =============================================================================
# FINAL: Merge develop → main
# =============================================================================
echo ""
log "Final: Merging develop → main"
git checkout main
git merge develop --no-ff -m "release: v1.0.0 - all 35 issues implemented"
git push origin main
git checkout develop

echo ""
echo -e "${B}╔══════════════════════════════════════════════════════╗${N}"
echo -e "${B}║           ALL 35 ISSUES IMPLEMENTED                  ║${N}"
echo -e "${B}╚══════════════════════════════════════════════════════╝${N}"
echo ""
echo "  View PRs:    https://github.com/$REPO/pulls?q=is:closed"
echo "  View Issues: https://github.com/$REPO/issues?q=is:closed"
echo "  View Code:   https://github.com/$REPO"
echo ""
echo "  Next: docker compose up --build"
echo ""
