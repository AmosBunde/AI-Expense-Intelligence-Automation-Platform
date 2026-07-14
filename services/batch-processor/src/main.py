"""
Batch Processor - HTTP surface for bulk expense imports.

Validates CSV files row-by-row and enqueues one `tasks.process_single`
Celery job per valid row. Validation is separated from submission so
finance can dry-run a file (`/batch/validate`) before committing it.
"""
from __future__ import annotations

import base64
import binascii
import os
import time

from celery import Celery
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .workers.csv_processor import parse_expense_csv

START_TIME = time.time()

app = FastAPI(
    title="Batch Processor",
    description="CSV batch import validation and submission",
    version="1.0.0",
)

# Producer-only Celery app: enqueues by task name (same pattern as the gateway)
celery_app = Celery(broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"))

MAX_ROWS = int(os.getenv("MAX_BATCH_ROWS", "5000"))


class BatchRequest(BaseModel):
    file_content_b64: str
    filename: str = "batch.csv"
    organization_id: str
    user_id: str = ""


class ValidationReport(BaseModel):
    filename: str
    valid_rows: int
    invalid_rows: int
    errors: list[str] = Field(default_factory=list)


class SubmitReport(ValidationReport):
    enqueued: int
    status: str


def _decode_and_parse(req: BatchRequest) -> tuple[list[dict], list[str]]:
    try:
        content = base64.b64decode(req.file_content_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="file_content_b64 is not valid base64")
    if not req.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="only CSV batches are supported")

    valid, errors = parse_expense_csv(content)
    if len(valid) > MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"batch has {len(valid)} rows; the limit is {MAX_ROWS}",
        )
    return valid, errors


@app.post("/batch/validate", response_model=ValidationReport)
async def validate_batch(req: BatchRequest) -> ValidationReport:
    """Dry-run: report row-level problems without enqueuing anything."""
    valid, errors = _decode_and_parse(req)
    return ValidationReport(
        filename=req.filename,
        valid_rows=len(valid),
        invalid_rows=len(errors),
        errors=errors[:100],
    )


@app.post("/batch/process", response_model=SubmitReport)
async def process_batch(req: BatchRequest) -> SubmitReport:
    """Validate, then enqueue one processing job per valid row."""
    valid, errors = _decode_and_parse(req)
    enqueued = 0
    for row in valid:
        celery_app.send_task(
            "tasks.process_single",
            kwargs={
                "expense_id": row["external_id"],
                "file_key": "",
                "organization_id": req.organization_id,
            },
            queue="expense_processing",
        )
        enqueued += 1

    return SubmitReport(
        filename=req.filename,
        valid_rows=len(valid),
        invalid_rows=len(errors),
        errors=errors[:100],
        enqueued=enqueued,
        status="queued" if enqueued else "nothing-to-do",
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "batch-processor",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }
