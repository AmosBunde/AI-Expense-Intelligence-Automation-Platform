"""
Tests for Expense Processor - OCR, normalization, processing pipeline.
"""
import pytest
from fastapi.testclient import TestClient

from src.main import (
    app,
    normalize_extraction,
    extract_text_from_document,
)


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# Normalization Tests
# =========================================================================

class TestNormalization:
    def test_currency_dollar_to_usd(self):
        result = normalize_extraction({"currency": "$"})
        assert result["currency"] == "USD"

    def test_currency_euro_to_eur(self):
        result = normalize_extraction({"currency": "€"})
        assert result["currency"] == "EUR"

    def test_currency_pound_to_gbp(self):
        result = normalize_extraction({"currency": "£"})
        assert result["currency"] == "GBP"

    def test_currency_yen_to_jpy(self):
        result = normalize_extraction({"currency": "¥"})
        assert result["currency"] == "JPY"

    def test_currency_code_uppercase(self):
        result = normalize_extraction({"currency": "kes"})
        assert result["currency"] == "KES"

    def test_currency_code_already_uppercase(self):
        result = normalize_extraction({"currency": "USD"})
        assert result["currency"] == "USD"

    def test_amount_rounded_to_two_decimals(self):
        result = normalize_extraction({"amount": 12.999})
        assert result["amount"] == 13.0

    def test_amount_string_parsed(self):
        result = normalize_extraction({"amount": "42.567"})
        assert result["amount"] == 42.57

    def test_amount_none_preserved(self):
        result = normalize_extraction({"amount": None})
        assert result["amount"] is None

    def test_amount_invalid_string_becomes_none(self):
        result = normalize_extraction({"amount": "not-a-number"})
        assert result["amount"] is None

    def test_date_iso_format(self):
        result = normalize_extraction({"transaction_date": "2026-04-10"})
        assert "2026-04-10" in result["transaction_date"]

    def test_date_us_format(self):
        result = normalize_extraction({"transaction_date": "04/10/2026"})
        assert "2026-04-10" in result["transaction_date"]

    def test_date_eu_format(self):
        result = normalize_extraction({"transaction_date": "10/04/2026"})
        assert "2026" in result["transaction_date"]

    def test_date_natural_format(self):
        result = normalize_extraction({"transaction_date": "April 10, 2026"})
        assert "2026-04-10" in result["transaction_date"]

    def test_empty_extraction(self):
        result = normalize_extraction({})
        assert isinstance(result, dict)


# =========================================================================
# OCR Tests
# =========================================================================

class TestTextExtraction:
    @pytest.mark.asyncio
    async def test_csv_extraction(self):
        csv_data = b"merchant,amount,date\nStarbucks,5.75,2026-04-10"
        text = await extract_text_from_document(csv_data, "bank_statement")
        assert "Starbucks" in text

    @pytest.mark.asyncio
    async def test_binary_document_handling(self):
        binary_data = bytes(range(256))
        text = await extract_text_from_document(binary_data, "bank_statement")
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_receipt_without_tesseract(self):
        """Gracefully handles missing Tesseract or invalid image data."""
        fake_image = b"fake-image-bytes"
        text = await extract_text_from_document(fake_image, "receipt")
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_invoice_fallback(self):
        """Invoice type uses same OCR path as receipt."""
        fake_image = b"fake-invoice-bytes"
        text = await extract_text_from_document(fake_image, "invoice")
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_unknown_document_type(self):
        text_data = b"plain text content"
        text = await extract_text_from_document(text_data, "other")
        assert "plain text content" in text


# =========================================================================
# API Endpoint Tests
# =========================================================================

class TestProcessorEndpoints:
    def test_list_expenses(self, client):
        response = client.get(
            "/expenses?user_id=user-123&organization_id=org-456"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_expenses_with_pagination(self, client):
        response = client.get(
            "/expenses?user_id=user-123&organization_id=org-456&page=2&page_size=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    def test_get_expense(self, client):
        response = client.get("/expenses/exp-123?user_id=user-123")
        assert response.status_code == 200
        data = response.json()
        assert data["expense_id"] == "exp-123"

    def test_approve_expense(self, client):
        response = client.post("/expenses/exp-123/approve?approved_by=manager-456")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"

    def test_spend_summary(self, client):
        response = client.get(
            "/analytics/summary?organization_id=org-123&period=month"
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_spend" in data
        assert "by_category" in data

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "expense-processor"
        assert data["status"] == "ok"
        assert "uptime_seconds" in data


class TestAIDegradedPath:
    """AI engine unavailability must not block receipt intake."""

    def test_process_succeeds_with_needs_review_when_ai_down(self, monkeypatch):
        import base64 as b64
        from unittest.mock import AsyncMock, MagicMock, patch

        import httpx as _httpx
        from fastapi.testclient import TestClient

        from src.main import app

        ai_fail = MagicMock(status_code=503)
        policy_ok = MagicMock(status_code=200)
        policy_ok.json.return_value = {"is_compliant": True, "auto_approved": False}

        async_client = MagicMock()
        async_client.__aenter__ = AsyncMock(return_value=async_client)
        async_client.__aexit__ = AsyncMock(return_value=False)
        async_client.post = AsyncMock(side_effect=[ai_fail, policy_ok])

        with patch("src.main.httpx.AsyncClient", return_value=async_client):
            client = TestClient(app)
            resp = client.post(
                "/process",
                json={
                    "file_key": "k",
                    "document_type": "receipt",
                    "user_id": "u",
                    "organization_id": "o",
                    "file_content_b64": b64.b64encode(b"RECEIPT Total: $5").decode(),
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "needs_review"
