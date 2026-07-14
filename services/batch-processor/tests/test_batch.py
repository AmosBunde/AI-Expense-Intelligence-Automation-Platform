"""Tests for the batch processor: CSV validation, enqueueing, limits."""
import base64
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.workers.csv_processor import parse_expense_csv

client = TestClient(app)


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()

GOOD_CSV = "merchant,amount,date,category\nUber,42.50,2026-07-01,Travel\nAWS,310,2026-07-02,Software\n"


class TestParser:
    def test_parses_valid_rows(self):
        valid, errors = parse_expense_csv(GOOD_CSV.encode())
        assert errors == []
        assert len(valid) == 2
        assert valid[0] == {
            "external_id": "",
            "merchant": "Uber",
            "amount": 42.5,
            "date": "2026-07-01",
            "category": "Travel",
            "currency": "USD",
            "description": "",
        }

    def test_reports_bad_rows_with_line_numbers(self):
        csv_text = "merchant,amount,date\nUber,-5,2026-07-01\n,10,not-a-date\n"
        valid, errors = parse_expense_csv(csv_text.encode())
        assert valid == []
        assert len(errors) == 2
        assert errors[0].startswith("line 2:") and "positive" in errors[0]
        assert errors[1].startswith("line 3:") and "merchant" in errors[1]

    def test_missing_required_column(self):
        valid, errors = parse_expense_csv(b"merchant,amount\nUber,5\n")
        assert valid == []
        assert "date" in errors[0]


class TestEndpoints:
    def test_health(self):
        assert client.get("/health").json()["service"] == "batch-processor"

    def test_validate_is_dry_run(self):
        with patch("src.main.celery_app") as celery:
            resp = client.post(
                "/batch/validate",
                json={"file_content_b64": b64(GOOD_CSV), "organization_id": "org-1"},
            )
        assert resp.status_code == 200
        assert resp.json()["valid_rows"] == 2
        celery.send_task.assert_not_called()

    def test_process_enqueues_per_valid_row(self):
        fake = MagicMock()
        with patch("src.main.celery_app", fake):
            resp = client.post(
                "/batch/process",
                json={"file_content_b64": b64(GOOD_CSV), "organization_id": "org-1"},
            )
        body = resp.json()
        assert body["enqueued"] == 2
        assert body["status"] == "queued"
        assert fake.send_task.call_count == 2
        name = fake.send_task.call_args.args[0]
        assert name == "tasks.process_single"
        assert fake.send_task.call_args.kwargs["queue"] == "expense_processing"

    def test_rejects_bad_base64(self):
        resp = client.post(
            "/batch/process",
            json={"file_content_b64": "!!!", "organization_id": "org-1"},
        )
        assert resp.status_code == 400

    def test_rejects_non_csv(self):
        resp = client.post(
            "/batch/process",
            json={"file_content_b64": b64("x"), "filename": "data.xlsx", "organization_id": "o"},
        )
        assert resp.status_code == 415
