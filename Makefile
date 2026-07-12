# AI Expense Intelligence Platform — single entrypoint for dev and deploy.
# Run `make help` (or just `make`) to see everything available.

COMPOSE       := docker compose
INFRA_FILE    := infrastructure/docker/docker-compose.infra.yml
PROD_FILE     := infrastructure/docker/docker-compose.prod.yml
PROD_ENV      := .env.prod
IMAGE_TAG     ?= latest

.DEFAULT_GOAL := help

.PHONY: help dev dev-down infra infra-down migrate seed test test-backend \
        test-frontend lint build prod prod-down prod-logs k8s-dev k8s-staging \
        k8s-prod logs clean

help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

# ── Local development ────────────────────────────────────────────────

dev: ## Start the full dev stack (all services + infra, built from source)
	$(COMPOSE) up --build -d
	@echo "Gateway:   http://localhost:8000/docs"
	@echo "Dashboard: http://localhost:5173"

dev-down: ## Stop the dev stack
	$(COMPOSE) down

infra: ## Start only Postgres, Redis, MinIO (for running services on the host)
	$(COMPOSE) -f $(INFRA_FILE) up -d
	$(COMPOSE) -f $(INFRA_FILE) ps

infra-down: ## Stop infra services
	$(COMPOSE) -f $(INFRA_FILE) down

migrate: ## Apply database migrations (requires infra running)
	cd packages/db-client && alembic upgrade head

seed: ## Load demo data into the database
	python scripts/seed_data.py

logs: ## Tail dev stack logs
	$(COMPOSE) logs -f --tail=100

# ── Quality gates (same as CI) ───────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend test suites
	pytest services/api-gateway/tests services/expense-processor/tests \
	       services/ai-engine/tests services/policy-engine/tests \
	       packages/*/tests -q

test-frontend: ## Run dashboard type-check, tests, and build
	cd services/dashboard-ui && pnpm install && pnpm run type-check && \
	  pnpm test -- --run && pnpm build

lint: ## Lint and format-check Python code
	ruff check services/ packages/
	ruff format --check services/ packages/

build: ## Build all Docker images locally
	$(COMPOSE) build

# ── Production (single VM, prebuilt GHCR images) ─────────────────────

prod: ## Deploy prod stack (needs .env.prod; pin IMAGE_TAG=<sha> for releases)
	@test -f $(PROD_ENV) || { \
	  echo "ERROR: $(PROD_ENV) not found."; \
	  echo "  cp .env.example $(PROD_ENV)   # then fill in real secrets"; \
	  exit 1; }
	IMAGE_TAG=$(IMAGE_TAG) $(COMPOSE) -f $(PROD_FILE) --env-file $(PROD_ENV) up -d
	@echo "Deployed IMAGE_TAG=$(IMAGE_TAG). Check: curl -s localhost:8000/health"

prod-down: ## Stop the prod stack
	$(COMPOSE) -f $(PROD_FILE) --env-file $(PROD_ENV) down

prod-logs: ## Tail prod stack logs
	$(COMPOSE) -f $(PROD_FILE) --env-file $(PROD_ENV) logs -f --tail=100

# ── Kubernetes ───────────────────────────────────────────────────────

k8s-dev: ## Apply the dev overlay (1 replica, latest images)
	kubectl apply -k infrastructure/k8s/overlays/dev/

k8s-staging: ## Apply the staging overlay (2 replicas)
	kubectl apply -k infrastructure/k8s/overlays/staging/

k8s-prod: ## Apply the prod overlay (3+ replicas, HPA)
	kubectl apply -k infrastructure/k8s/overlays/prod/

# ── Housekeeping ─────────────────────────────────────────────────────

clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) down -v --remove-orphans 2>/dev/null || true
	$(COMPOSE) -f $(INFRA_FILE) down -v 2>/dev/null || true
	rm -rf services/dashboard-ui/dist .pytest_cache htmlcov .coverage
