"""
Decision audit trail.

Every AI analysis and policy verdict is recorded append-only in the
`decision_audit` table so that any auto-approval or fraud flag can later be
explained: what was decided, from which inputs, by which prompt/rule version.

Design constraints:
- Writing an audit record must NEVER fail or slow the decision path. On any
  database problem the record is emitted as a structured log line instead
  (grep for "audit-fallback") and the caller continues.
- Records are append-only: this module exposes no update or delete.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import asyncpg

logger = logging.getLogger("decision-audit")

_pool: asyncpg.Pool | None = None

_INSERT = """
INSERT INTO decision_audit
  (expense_id, organization_id, decision_type, decision, risk_level,
   fraud_score, rule_ids, model_version, details)
VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9::jsonb)
RETURNING id
"""

_SELECT = """
SELECT id, expense_id, organization_id, decision_type, decision, risk_level,
       fraud_score, rule_ids, model_version, details, created_at
FROM decision_audit
WHERE expense_id = $1 AND organization_id = $2
ORDER BY created_at ASC
"""


def _dsn() -> str:
    # asyncpg wants a plain postgres:// DSN, not SQLAlchemy's +asyncpg form
    url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL", "")
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_dsn(), min_size=1, max_size=4, timeout=5)
    return _pool


async def record_decision(
    *,
    expense_id: str,
    organization_id: str,
    decision_type: str,  # "ai_analysis" | "policy_verdict"
    decision: str,
    risk_level: str | None = None,
    fraud_score: float | None = None,
    rule_ids: list[str] | None = None,
    model_version: str | None = None,
    details: dict[str, Any] | None = None,
) -> bool:
    """Persist one decision record. Returns False (and logs) on any failure."""
    payload = {
        "expense_id": expense_id,
        "organization_id": organization_id,
        "decision_type": decision_type,
        "decision": decision,
        "risk_level": risk_level,
        "fraud_score": fraud_score,
        "rule_ids": rule_ids,
        "model_version": model_version,
        "details": details,
    }
    try:
        pool = await _get_pool()
        await pool.fetchval(
            _INSERT,
            expense_id,
            organization_id,
            decision_type,
            decision,
            risk_level,
            fraud_score,
            json.dumps(rule_ids or []),
            model_version,
            json.dumps(details or {}, default=str),
        )
        return True
    except Exception as exc:  # noqa: BLE001 — auditing must never break the caller
        logger.warning("audit-fallback %s error=%s", json.dumps(payload, default=str), exc)
        return False


async def fetch_decisions(expense_id: str, organization_id: str) -> list[dict[str, Any]]:
    """All decision records for one expense, oldest first."""
    pool = await _get_pool()
    rows = await pool.fetch(_SELECT, expense_id, organization_id)
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["id"] = str(d["id"])
        d["created_at"] = d["created_at"].isoformat()
        for k in ("rule_ids", "details"):
            if isinstance(d.get(k), str):
                d[k] = json.loads(d[k])
        out.append(d)
    return out
