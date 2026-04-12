"""
Tests for Expense Processor - OCR, normalization, processing pipeline.
"""
import pytest
from fastapi.testclient import TestClient

from services.expense_processor.src.main import (
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
    def test_currency_symbol_to_code(self):
        result = normalize_extraction({"currency": "$"})
        assert result["currency"] == "USD"

    def test_euro_symbol(self):
        result = normalize_extraction({"currency": "€"})
        assert result["currency"] == "EUR"

    def test_currency_code_uppercase(self):
        result = normalize_extraction({"currency": "kes"})
        assert result["currency"] == "KES"

    def test_amount_rounded(self):
        result = normalize_extraction({"amount": 12.999})
        assert result["amount"] == 13.0

    def test_amount_none_handled(self):
        result = normalize_extraction({"amount": None})
        assert result["amount"] is None

    def test_amount_invalid_string(self):
        result = normalize_extraction({"amount": "not-a-number"})
        assert result["amount"] is None

    def test_date_iso_format_passthrough(self):
        result = normalize_extraction({"transaction_date": "2026-04-10"})
        assert "2026-04-10" in result["transaction_date"]

    def test_date_us_format(self):
        result = normalize_extraction({"transaction_date": "04/10/2026"})
        assert "2026-04-10" in result["transaction_date"]

    def test_date_eu_format(self):
        result = normalize_extraction({"transaction_date": "10/04/2026"})
        # EU format: day/month/year
        assert "2026" in result["transaction_date"]

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
        # Should not crash on binary
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_receipt_without_tesseract(self):
        """Gracefully handles missing Tesseract."""
        fake_image = b"fake-image-bytes"
        text = await extract_text_from_document(fake_image, "receipt")
        assert isinstance(text, str)


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

    def test_get_expense_not_found(self, client):
        response = client.get("/expenses/nonexistent?user_id=user-123")
        assert response.status_code == 200  # Returns status: not_found

    def test_approve_expense(self, client):
        response = client.post(
            "/expenses/exp-123/approve",
            json={"approved_by": "manager-456"},
        )
        assert response.status_code == 200

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
        assert response.json()["service"] == "expense-processor"
