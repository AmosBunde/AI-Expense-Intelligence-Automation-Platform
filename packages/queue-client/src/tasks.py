"""
Queue Client - Celery task definitions for async expense processing.
"""
from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "expense_tasks",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "tasks.process_single": {"queue": "expense_processing"},
        "tasks.process_batch": {"queue": "batch_processing"},
        "tasks.generate_report": {"queue": "reporting"},
        "tasks.send_notification": {"queue": "notifications"},
    },
)


@celery_app.task(name="tasks.process_single", bind=True, max_retries=3)
def process_single(self, expense_id: str, file_key: str, organization_id: str):
    """Process a single expense through the full pipeline."""
    import httpx

    processor_url = os.getenv("EXPENSE_PROCESSOR_URL", "http://localhost:8002")
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{processor_url}/process",
                json={
                    "expense_id": expense_id,
                    "file_key": file_key,
                    "organization_id": organization_id,
                },
            )
            return response.json()
    except Exception as exc:
        self.retry(exc=exc, countdown=2**self.request.retries * 10)


@celery_app.task(name="tasks.process_batch", bind=True, max_retries=2)
def process_batch(
    self,
    file_content_b64: str,
    filename: str,
    organization_id: str,
    user_id: str,
):
    """Process a batch file (CSV/Excel) of transactions."""
    import base64
    import csv
    import io

    file_bytes = base64.b64decode(file_content_b64)
    results = {"processed": 0, "failed": 0, "errors": []}

    try:
        if filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(file_bytes.decode("utf-8")))
            for row in reader:
                try:
                    # Queue individual processing for each row
                    process_single.delay(
                        expense_id=row.get("id", ""),
                        file_key="",
                        organization_id=organization_id,
                    )
                    results["processed"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(str(e))
    except Exception as exc:
        self.retry(exc=exc, countdown=60)

    return results


@celery_app.task(name="tasks.generate_report")
def generate_report(organization_id: str, period: str, report_type: str):
    """Generate a spend report for an organization."""
    return {
        "organization_id": organization_id,
        "period": period,
        "report_type": report_type,
        "status": "generated",
    }


@celery_app.task(name="tasks.send_notification")
def send_notification(
    channel: str, recipient: str, template: str, context: dict
):
    """Deliver a notification via the notification service."""
    import httpx

    service_url = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8004")
    subject = context.get("subject", template.replace("_", " ").capitalize())
    message = context.get("message", "")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{service_url}/notify",
                json={
                    "channel": channel,
                    "recipient": recipient,
                    "subject": subject,
                    "message": message,
                    "metadata": {
                        k: v for k, v in context.items() if k not in ("subject", "message")
                    },
                },
            )
        delivered = resp.status_code == 200 and resp.json().get("delivered", False)
    except httpx.HTTPError:
        delivered = False
    return {
        "channel": channel,
        "recipient": recipient,
        "template": template,
        "status": "sent" if delivered else "not-delivered",
    }


# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "daily-reconciliation": {
        "task": "tasks.generate_report",
        "schedule": 86400.0,  # every 24 hours
        "args": ("all", "day", "reconciliation"),
    },
    "weekly-spend-summary": {
        "task": "tasks.generate_report",
        "schedule": 604800.0,  # every 7 days
        "args": ("all", "week", "spend_summary"),
    },
}
