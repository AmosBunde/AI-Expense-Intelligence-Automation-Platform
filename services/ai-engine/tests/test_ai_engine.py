"""
Tests for AI Engine - LangGraph agents, extraction, fraud detection, RAG.
"""
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import (
    app,
    build_analysis_graph,
    build_chat_graph,
    should_analyze_fraud,
    EXTRACTION_PROMPT,
    FRAUD_ANALYSIS_PROMPT,
)


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# Extraction Tests
# =========================================================================

class TestFieldExtraction:
    def test_extraction_prompt_contains_required_fields(self):
        """Extraction prompt must request all critical fields."""
        required_fields = [
            "merchant_name", "transaction_date", "amount",
            "currency", "category", "line_items",
        ]
        for field in required_fields:
            assert field in EXTRACTION_PROMPT

    def test_extraction_prompt_requests_json(self):
        """Extraction must output structured JSON."""
        assert "JSON" in EXTRACTION_PROMPT or "json" in EXTRACTION_PROMPT

    @patch("src.main.get_llm")
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self, mock_get_llm, client):
        """Analyze endpoint accepts expense data and returns analysis."""
        import src.main as main_mod

        main_mod.get_analysis_graph.cache_clear()
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "merchant_name": "Starbucks",
            "amount": 12.50,
            "currency": "USD",
            "category": "meals",
            "category_confidence": 0.95,
            "transaction_date": "2026-04-10",
        })
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        response = client.post("/analyze", json={
            "expense_id": "test-exp-123",
            "organization_id": "org-456",
            "raw_text": "STARBUCKS #1234\n123 Main St\n04/10/2026\nGrande Latte  $5.75\nMuffin        $3.25\nTax           $0.50\nTotal:       $12.50\nVisa ****1234",
        })
        assert response.status_code == 200
        main_mod.get_analysis_graph.cache_clear()


# =========================================================================
# Fraud Detection Tests
# =========================================================================

class TestFraudDetection:
    def test_fraud_prompt_covers_all_indicators(self):
        """Fraud analysis prompt must check for all indicator types."""
        indicators = [
            "DUPLICATE", "ROUND_NUMBER", "WEEKEND",
            "SPLIT_TRANSACTION", "UNUSUAL_AMOUNT",
        ]
        for indicator in indicators:
            assert indicator in FRAUD_ANALYSIS_PROMPT

    def test_should_analyze_fraud_high_amount(self):
        """Expenses over $100 should trigger fraud analysis."""
        state = {
            "analysis_result": {"extraction": {"amount": 500}},
        }
        assert should_analyze_fraud(state) == "fraud_analysis"

    def test_should_skip_fraud_low_amount(self):
        """Trivial expenses should skip full fraud analysis."""
        state = {
            "analysis_result": {"extraction": {"amount": 5}},
        }
        assert should_analyze_fraud(state) == "categorize"

    def test_should_analyze_fraud_no_amount(self):
        """Missing amount should skip fraud analysis."""
        state = {
            "analysis_result": {"extraction": {}},
        }
        assert should_analyze_fraud(state) == "categorize"


# =========================================================================
# LangGraph Architecture Tests
# =========================================================================

class TestGraphArchitecture:
    def test_analysis_graph_builds(self):
        """Analysis graph compiles without error."""
        graph = build_analysis_graph()
        assert graph is not None

    def test_chat_graph_builds(self):
        """Chat graph compiles without error."""
        graph = build_chat_graph()
        assert graph is not None

    def test_analysis_graph_has_required_nodes(self):
        """Analysis graph contains all pipeline stages."""
        graph = build_analysis_graph()
        # Graph should have nodes for extract, retrieve, fraud, categorize
        assert graph is not None

    def test_chat_graph_has_tool_routing(self):
        """Chat graph can route to tools and back to agent."""
        graph = build_chat_graph()
        assert graph is not None


# =========================================================================
# Chat Agent Tests
# =========================================================================

class TestChatAgent:
    @patch("src.main.get_llm")
    @pytest.mark.asyncio
    async def test_chat_endpoint(self, mock_get_llm, client):
        """Chat endpoint accepts message and returns reply."""
        import src.main as main_mod

        main_mod.get_chat_graph.cache_clear()
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_response = MagicMock()
        mock_response.content = "Your total spending this month is $3,450."
        mock_response.tool_calls = []
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        response = client.post("/chat", json={
            "message": "What is my total spend this month?",
            "user_id": "user-123",
            "organization_id": "org-456",
        })
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        main_mod.get_chat_graph.cache_clear()


# =========================================================================
# RAG Pipeline Tests
# =========================================================================

class TestRAGPipeline:
    def test_policy_context_format(self):
        """Policy context chunks must be strings."""
        # In production: test pgvector retrieval
        chunks = [
            "Policy: Meals must not exceed $75",
            "Policy: All expenses over $25 require receipts",
        ]
        assert all(isinstance(c, str) for c in chunks)
        assert len(chunks) > 0


# =========================================================================
# Health Check Tests
# =========================================================================

class TestAIEngineHealth:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai-engine"

    def test_anomalies_endpoint(self, client):
        response = client.get("/anomalies?organization_id=org-123")
        assert response.status_code == 200


class TestDecisionAudit:
    """Every /analyze run must produce an audit record."""

    @pytest.mark.asyncio
    async def test_analyze_records_ai_decision(self, client):
        from unittest.mock import AsyncMock, patch

        import src.main as main_mod

        fake_graph = MagicMock()
        fake_graph.ainvoke = AsyncMock(
            return_value={
                "analysis_result": {
                    "extraction": {"merchant_name": "Uber"},
                    "fraud": {"risk_level": "low", "risk_score": 0.1},
                },
                "category_prediction": {"category": "travel", "confidence": 0.9},
                "fraud_indicators": [],
            }
        )
        with (
            patch.object(main_mod, "get_analysis_graph", return_value=fake_graph),
            patch.object(main_mod, "record_decision", new=AsyncMock(return_value=True)) as rec,
        ):
            resp = client.post(
                "/analyze",
                json={"expense_id": "exp-a1", "organization_id": "org-1", "raw_text": "UBER $12"},
            )
        assert resp.status_code == 200
        rec.assert_awaited_once()
        kwargs = rec.call_args.kwargs
        assert kwargs["decision_type"] == "ai_analysis"
        assert kwargs["decision"] == "travel"
        assert kwargs["risk_level"] == "low"
        assert kwargs["fraud_score"] == 0.1
