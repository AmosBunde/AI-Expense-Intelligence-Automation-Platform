"""Tests for queue-client Celery task definitions."""
from __future__ import annotations

import base64

import pytest

from src.tasks import (
    celery_app,
    generate_report,
    process_batch,
    process_single,
    send_notification,
)


class TestCeleryConfig:
    """Tests for Celery app configuration."""

    def test_broker_url_configured(self):
        assert celery_app.conf.broker_url is not None

    def test_serializer_is_json(self):
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_timezone_utc(self):
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_acks_late_enabled(self):
        assert celery_app.conf.task_acks_late is True

    def test_prefetch_multiplier(self):
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_task_routes(self):
        routes = celery_app.conf.task_routes
        assert routes["tasks.process_single"] == {"queue": "expense_processing"}
        assert routes["tasks.process_batch"] == {"queue": "batch_processing"}
        assert routes["tasks.generate_report"] == {"queue": "reporting"}
        assert routes["tasks.send_notification"] == {"queue": "notifications"}


class TestTaskRegistration:
    """Tests that tasks are properly registered."""

    def test_process_single_registered(self):
        assert "tasks.process_single" in celery_app.tasks

    def test_process_batch_registered(self):
        assert "tasks.process_batch" in celery_app.tasks

    def test_generate_report_registered(self):
        assert "tasks.generate_report" in celery_app.tasks

    def test_send_notification_registered(self):
        assert "tasks.send_notification" in celery_app.tasks


class TestProcessSingle:
    """Tests for process_single task."""

    def test_max_retries(self):
        assert process_single.max_retries == 3

    def test_task_name(self):
        assert process_single.name == "tasks.process_single"


class TestProcessBatch:
    """Tests for process_batch task."""

    def test_max_retries(self):
        assert process_batch.max_retries == 2

    def test_task_name(self):
        assert process_batch.name == "tasks.process_batch"


class TestGenerateReport:
    """Tests for generate_report task."""

    def test_task_name(self):
        assert generate_report.name == "tasks.generate_report"

    def test_returns_report_stub(self):
        result = generate_report("org-1", "day", "reconciliation")
        assert result["organization_id"] == "org-1"
        assert result["period"] == "day"
        assert result["report_type"] == "reconciliation"
        assert result["status"] == "generated"


class TestSendNotification:
    """Tests for send_notification task."""

    def test_task_name(self):
        assert send_notification.name == "tasks.send_notification"

    def test_forwards_to_notification_service(self):
        from unittest.mock import MagicMock, patch

        fake_resp = MagicMock(status_code=200)
        fake_resp.json.return_value = {"delivered": True}
        with patch("httpx.Client") as client_cls:
            post = client_cls.return_value.__enter__.return_value.post
            post.return_value = fake_resp
            result = send_notification(
                channel="email",
                recipient="user@example.com",
                template="expense_approved",
                context={"expense_id": "exp-1"},
            )
            url = post.call_args.args[0]
            payload = post.call_args.kwargs["json"]
        assert url.endswith("/notify")
        assert payload["channel"] == "email"
        assert payload["metadata"] == {"expense_id": "exp-1"}
        assert result["status"] == "sent"

    def test_reports_not_delivered_when_service_down(self):
        from unittest.mock import patch

        import httpx as _httpx

        with patch("httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value.post.side_effect = (
                _httpx.ConnectError("down")
            )
            result = send_notification(
                channel="slack", recipient="", template="fraud_alert", context={}
            )
        assert result["status"] == "not-delivered"


class TestBeatSchedule:
    """Tests for Celery Beat periodic task schedule."""

    def test_daily_reconciliation_schedule(self):
        schedule = celery_app.conf.beat_schedule
        assert "daily-reconciliation" in schedule
        daily = schedule["daily-reconciliation"]
        assert daily["task"] == "tasks.generate_report"
        assert daily["schedule"] == 86400.0
        assert daily["args"] == ("all", "day", "reconciliation")

    def test_weekly_summary_schedule(self):
        schedule = celery_app.conf.beat_schedule
        assert "weekly-spend-summary" in schedule
        weekly = schedule["weekly-spend-summary"]
        assert weekly["task"] == "tasks.generate_report"
        assert weekly["schedule"] == 604800.0
        assert weekly["args"] == ("all", "week", "spend_summary")
