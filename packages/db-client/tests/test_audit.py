"""Audit helper: writes must never raise; failures degrade to log-only."""
import asyncio

import pytest

from src import audit


def test_record_decision_never_raises_on_db_failure(monkeypatch, caplog):
    # Unreachable DSN: the helper must swallow the error, log a fallback
    # record, and report False — never break the decision path
    monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://nobody:x@127.0.0.1:1/none")
    monkeypatch.setattr(audit, "_pool", None)

    async def run():
        return await audit.record_decision(
            expense_id="exp-1",
            organization_id="org-1",
            decision_type="policy_verdict",
            decision="auto_approve",
        )

    with caplog.at_level("WARNING", logger="decision-audit"):
        ok = asyncio.run(run())
    assert ok is False
    assert any("audit-fallback" in r.message for r in caplog.records)
    assert any("exp-1" in r.message for r in caplog.records)


def test_dsn_strips_sqlalchemy_driver(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_SYNC", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/db")
    assert audit._dsn() == "postgresql://u:p@h:5432/db"


def test_fetch_decisions_propagates_errors(monkeypatch):
    # Reads are allowed to fail loudly — the gateway maps this to 503
    monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://nobody:x@127.0.0.1:1/none")
    monkeypatch.setattr(audit, "_pool", None)
    with pytest.raises(Exception):
        asyncio.run(audit.fetch_decisions("exp-1", "org-1"))
