"""
Expense Processor - Document ingestion, OCR, field extraction, and normalization.
Handles real-time single expense processing and batch operations.
"""
from __future__ import annotations

import base64
import io
import os
import time
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

START_TIME = time.time()

AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8001")
POLICY_ENGINE_URL = os.getenv("POLICY_ENGINE_URL", "http://localhost:8003")


app = FastAPI(title="Expense Processor", version="1.0.0")


# =============================================================================
# Models
# =============================================================================

class ProcessRequest(BaseModel):
    file_key: str
    document_type: str
    user_id: str
    organization_id: str
    file_content_b64: str


class ProcessResponse(BaseModel):
    expense_id: str
    status: str
    extraction: dict | None = None


# =============================================================================
# OCR & Text Extraction
# =============================================================================

async def extract_text_from_document(file_bytes: bytes, document_type: str) -> str:
    """Extract text from uploaded document using OCR or text parsing."""
    # For PDFs: use pdf2image + Tesseract
    # For images: use Tesseract directly
    # For CSVs/Excel: parse directly

    if document_type in ("receipt", "invoice"):
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            return text
        except ImportError:
            # Fallback: return base64 for LLM vision processing
            return f"[IMAGE_BASE64:{base64.b64encode(file_bytes).decode()[:200]}...]"
        except Exception as e:
            return f"[OCR_ERROR: {str(e)}]"

    elif document_type == "bank_statement":
        # Parse CSV/PDF bank statements
        try:
            text = file_bytes.decode("utf-8")
            return text
        except UnicodeDecodeError:
            return "[BINARY_DOCUMENT]"

    return file_bytes.decode("utf-8", errors="replace")


# =============================================================================
# Normalization
# =============================================================================

def normalize_extraction(raw_extraction: dict) -> dict:
    """Normalize extracted fields: currency codes, date formats, amount precision."""
    normalized = {**raw_extraction}

    # Normalize currency
    currency_map = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "KES": "KES"}
    if "currency" in normalized:
        normalized["currency"] = currency_map.get(
            normalized["currency"], normalized["currency"]
        ).upper()

    # Normalize amount to 2 decimal places
    if "amount" in normalized and normalized["amount"] is not None:
        try:
            normalized["amount"] = round(float(normalized["amount"]), 2)
        except (ValueError, TypeError):
            normalized["amount"] = None

    # Normalize date to ISO format
    if "transaction_date" in normalized and normalized["transaction_date"]:
        date_str = normalized["transaction_date"]
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                dt = datetime.strptime(str(date_str), fmt)
                normalized["transaction_date"] = dt.isoformat()
                break
            except ValueError:
                continue

    return normalized


# =============================================================================
# Processing Pipeline
# =============================================================================

@app.post("/process", response_model=ProcessResponse)
async def process_expense(request: ProcessRequest):
    """
    Full expense processing pipeline:
    1. Decode uploaded document
    2. Extract text via OCR
    3. Send to AI Engine for field extraction + fraud analysis
    4. Normalize extracted fields
    5. Send to Policy Engine for compliance check
    6. Store result and return
    """
    expense_id = str(uuid.uuid4())

    # Step 1: Decode file
    file_bytes = base64.b64decode(request.file_content_b64)

    # Step 2: Extract text
    raw_text = await extract_text_from_document(file_bytes, request.document_type)

    # Step 3: AI extraction + fraud analysis
    async with httpx.AsyncClient(timeout=60.0) as client:
        ai_response = await client.post(
            f"{AI_ENGINE_URL}/analyze",
            json={
                "expense_id": expense_id,
                "organization_id": request.organization_id,
                "raw_text": raw_text,
            },
        )

        if ai_response.status_code != 200:
            raise HTTPException(status_code=502, detail="AI Engine analysis failed")

        ai_result = ai_response.json()

    # Step 4: Normalize
    extraction = ai_result.get("extraction", {})
    normalized = normalize_extraction(extraction)

    # Step 5: Policy check
    async with httpx.AsyncClient(timeout=30.0) as client:
        policy_response = await client.post(
            f"{POLICY_ENGINE_URL}/check",
            json={
                "expense_id": expense_id,
                "organization_id": request.organization_id,
                "amount": normalized.get("amount"),
                "category": normalized.get("category"),
                "merchant_name": normalized.get("merchant_name"),
                "transaction_date": normalized.get("transaction_date"),
                "fraud_analysis": ai_result.get("fraud_analysis"),
            },
        )
        policy_result = policy_response.json() if policy_response.status_code == 200 else {}

    # Step 6: Determine final status
    fraud = ai_result.get("fraud_analysis", {})
    risk_level = fraud.get("risk_level", "low")
    is_compliant = policy_result.get("is_compliant", True)

    if risk_level in ("high", "critical") or not is_compliant:
        status = "flagged"
    elif policy_result.get("auto_approved", False):
        status = "approved"
    else:
        status = "categorized"

    # In production: persist to database here
    return ProcessResponse(
        expense_id=expense_id,
        status=status,
        extraction={
            **normalized,
            "fraud_analysis": fraud,
            "policy_check": policy_result,
        },
    )


@app.get("/expenses")
async def list_expenses(
    user_id: str,
    organization_id: str,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    category: str | None = None,
):
    """List expenses with filtering. In production: query PostgreSQL."""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "has_next": False,
    }


@app.get("/expenses/{expense_id}")
async def get_expense(expense_id: str, user_id: str):
    """Get single expense details."""
    # In production: query PostgreSQL
    return {"expense_id": expense_id, "status": "not_found"}


@app.post("/expenses/{expense_id}/approve")
async def approve_expense(expense_id: str, approved_by: str = ""):
    """Mark expense as approved."""
    return {"expense_id": expense_id, "status": "approved", "approved_by": approved_by}


@app.get("/analytics/summary")
async def spend_summary(organization_id: str, period: str = "month"):
    """Aggregated spend analytics."""
    return {
        "period": period,
        "total_spend": 0,
        "by_category": {},
        "by_department": {},
        "top_merchants": [],
        "flagged_count": 0,
        "auto_approved_count": 0,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "expense-processor",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }
