# Deployment Guide

This is the path from a green CI run to a running production system. It covers
what to prepare, how images are published, how to deploy to each supported
target, and how to verify and roll back a release.

## 1. How releases work

| Stage | Where | What happens |
|-------|-------|--------------|
| PR | `.github/workflows/ci.yml` | Lint, backend + frontend tests, image build (no push) |
| Merge to `main` | `.github/workflows/release.yml` | All five images pushed to GHCR, tagged `latest` + commit SHA |
| Tag `vX.Y.Z` | `.github/workflows/release.yml` | Same images additionally tagged `X.Y.Z` |

Published images:

```
ghcr.io/amosbunde/expense-api-gateway
ghcr.io/amosbunde/expense-expense-processor
ghcr.io/amosbunde/expense-ai-engine
ghcr.io/amosbunde/expense-policy-engine
ghcr.io/amosbunde/expense-dashboard-ui
```

**Always deploy a commit-SHA or semver tag to production.** `latest` is for
dev environments only.

## 2. Prerequisites (all targets)

- PostgreSQL 16 with the `pgvector` extension (`CREATE EXTENSION vector;`)
- Redis 7
- S3-compatible object storage (AWS S3 in prod, MinIO for dev/staging)
- An OpenAI API key with GPT-4o access

### Secrets checklist

Generate and store these in your secret manager (never in git):

| Secret | Notes |
|--------|-------|
| `DATABASE_URL` / `DATABASE_URL_SYNC` | asyncpg + sync DSNs, dedicated app user (not superuser) |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis DBs 0/1/2 |
| `OPENAI_API_KEY` | scope a per-environment key so usage is attributable |
| `JWT_SECRET` | `openssl rand -hex 32`; rotating it invalidates all sessions |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | least-privilege credentials for the documents bucket |
| `SMTP_*`, `SLACK_WEBHOOK_URL` | optional, for notification-service |

## 3. Database migrations

Run migrations **before** rolling out new application containers:

```bash
pip install -e packages/db-client
cd packages/db-client
DATABASE_URL_SYNC=postgresql://... alembic upgrade head
```

Migrations are forward-only in production. To back out a bad release whose
migration is incompatible, restore from backup rather than `alembic downgrade`.

## 4. Deployment targets

### Option A — Docker Compose on a single VM (staging / small prod)

```bash
# on the VM
git clone https://github.com/AmosBunde/AI-Expense-Intelligence-Automation-Platform.git
cd AI-Expense-Intelligence-Automation-Platform
cp .env.example .env.prod            # fill in real values
IMAGE_TAG=<commit-sha> docker compose \
  -f infrastructure/docker/docker-compose.prod.yml \
  --env-file .env.prod up -d
```

The prod compose file publishes only the gateway (`:8000`) and dashboard
(`:80`); Postgres/Redis/MinIO stay on the internal network. Put a TLS
terminator (Caddy/nginx/ALB) in front of both published ports.

### Option B — Kubernetes (EKS / GKE)

```bash
# 1. Create the secret the deployments expect (see k8s/base/secrets.example.yaml)
kubectl create secret generic app-secrets -n expense-platform --from-literal=...

# 2. Review ConfigMap values (CORS origin, ingress host) in base/deployments.yaml

# 3. Apply the overlay for your environment
kubectl apply -k infrastructure/k8s/overlays/dev        # 1 replica, latest
kubectl apply -k infrastructure/k8s/overlays/staging    # 2 replicas
kubectl apply -k infrastructure/k8s/overlays/prod       # 3+ replicas, HPA

# 4. Watch the rollout
kubectl get pods -n expense-platform -w
```

The ingress expects cert-manager (`letsencrypt-prod` ClusterIssuer) and an
nginx ingress controller. Update `expenses.yourdomain.com` in
`base/deployments.yaml` to your real host before applying.

### Option C — AWS ECS via Terraform

```bash
cd infrastructure/terraform/environments/prod
terraform init
terraform plan -out=tfplan     # review carefully — VPC, RDS, ElastiCache, ECS
terraform apply tfplan
```

Point the ECS task definitions at the GHCR images (or mirror them to ECR if
you prefer same-cloud pulls).

## 5. Post-deploy smoke tests

```bash
BASE=https://your-host
curl -fsS $BASE/health                          # gateway liveness
curl -fsS $BASE/api/v1/health/deep              # gateway + downstream deps
curl -fsS -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke@example.com","password":"..."}' | jq .access_token
```

Then verify one end-to-end expense: upload a receipt via the dashboard,
confirm it reaches `processed` status and appears in analytics.

## 6. Rollback

- **Compose VM:** redeploy the previous SHA — `IMAGE_TAG=<previous-sha> docker compose -f infrastructure/docker/docker-compose.prod.yml --env-file .env.prod up -d`
- **Kubernetes:** `kubectl rollout undo deployment/<name> -n expense-platform` (repeat per service, or re-apply the overlay pinned to the previous tag)
- **Database:** restore from the pre-deploy backup; do not run `alembic downgrade` in prod

## 7. Production readiness checklist

- [ ] All secrets from a secret manager; `JWT_SECRET` and DB password are not the dev defaults
- [ ] TLS in front of every public endpoint
- [ ] Automated Postgres backups + restore tested once
- [ ] `LOG_LEVEL=INFO`, logs shipped somewhere searchable
- [ ] Alerting on `/api/v1/health/deep` failures and Celery queue depth
- [ ] OpenAI spend limit / budget alert configured
- [ ] Rate limits reviewed for expected traffic (gateway + ingress annotations)
- [ ] Load test run against staging (`tests/load/locustfile.py`)
