"""
AI Engine - LangGraph agents for expense analysis, categorization, fraud detection, and RAG.
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Sequence, TypedDict

from fastapi import FastAPI, HTTPException
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

import operator

START_TIME = time.time()


# =============================================================================
# Configuration
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DATABASE_URL = os.getenv("DATABASE_URL", "")


# =============================================================================
# LangGraph Agent State
# =============================================================================

class ExpenseAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    expense_data: dict
    organization_id: str
    policy_context: list[str]  # RAG-retrieved policy chunks
    analysis_result: dict
    fraud_indicators: list[str]
    category_prediction: dict


# =============================================================================
# Agent Tools
# =============================================================================

@tool
def extract_fields_from_text(raw_text: str) -> dict:
    """Extract structured expense fields (merchant, amount, date, category)
    from raw OCR text or transaction description."""
    # This is the tool definition; actual LLM call happens in the node
    return {"raw_text": raw_text}


@tool
def classify_expense_category(
    merchant_name: str, description: str, amount: float
) -> dict:
    """Classify an expense into a category based on merchant name,
    description, and amount. Returns category and confidence score."""
    return {
        "merchant": merchant_name,
        "description": description,
        "amount": amount,
    }


@tool
def detect_fraud_patterns(
    expense_id: str,
    amount: float,
    merchant: str,
    date: str,
    user_history: list[dict] | None = None,
) -> dict:
    """Analyze an expense for fraud indicators: duplicates, unusual amounts,
    suspicious timing, split transactions, round-number bias."""
    return {
        "expense_id": expense_id,
        "amount": amount,
        "merchant": merchant,
        "date": date,
    }


@tool
def query_spend_patterns(
    organization_id: str,
    period: str = "month",
    group_by: str = "category",
) -> dict:
    """Query aggregated spend patterns for an organization.
    Used by the chat agent to answer questions about spending trends."""
    return {
        "organization_id": organization_id,
        "period": period,
        "group_by": group_by,
    }


@tool
def search_similar_expenses(
    merchant_name: str,
    amount: float,
    date_range_days: int = 30,
) -> list[dict]:
    """Find similar expenses by merchant, amount, and date range
    to detect duplicates or split transactions."""
    return []


# =============================================================================
# Agent Nodes
# =============================================================================

llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0, api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)


EXTRACTION_PROMPT = """You are an expert expense data extractor. Given raw text from a receipt,
invoice, or transaction record, extract the following fields as JSON:

{
  "merchant_name": "string",
  "merchant_address": "string or null",
  "transaction_date": "YYYY-MM-DD",
  "amount": number,
  "currency": "3-letter code",
  "tax_amount": number or null,
  "tip_amount": number or null,
  "payment_method": "string or null",
  "line_items": [{"description": "str", "quantity": num, "unit_price": num, "total": num}],
  "category": "one of: travel, meals, office_supplies, software, marketing, utilities, rent, professional_services, equipment, insurance, training, entertainment, shipping, miscellaneous",
  "category_confidence": number between 0 and 1
}

Be precise. If a field is not present, use null. For amounts, use numeric values without currency symbols.
"""

FRAUD_ANALYSIS_PROMPT = """You are a forensic expense auditor. Analyze the following expense for fraud risk.

Consider these indicators:
1. DUPLICATE: Same merchant + similar amount within 7 days
2. ROUND_NUMBER: Suspiciously round amounts (e.g., exactly $500.00)
3. WEEKEND_TIMING: Business expenses on weekends
4. SPLIT_TRANSACTION: Multiple small transactions to same merchant to stay under limits
5. UNUSUAL_AMOUNT: Amount significantly deviates from user's typical spend pattern
6. SUSPICIOUS_MERCHANT: Merchant category doesn't match expense category
7. RAPID_SUBMISSION: Multiple expenses submitted in very short timeframe
8. MISSING_DETAILS: Key fields missing or inconsistent

Return JSON:
{
  "risk_level": "low|medium|high|critical",
  "risk_score": 0.0-1.0,
  "indicators": ["list of triggered indicators"],
  "explanation": "brief explanation",
  "recommended_action": "auto_approve|require_review|escalate|reject"
}
"""

CHAT_SYSTEM_PROMPT = """You are an AI expense assistant for a company. You help employees and
finance teams understand spending patterns, policy compliance, and expense management.

You have access to tools for querying spend data and searching expenses.
Be concise, data-driven, and helpful. When showing monetary values, always include the currency.
If you are unsure, say so rather than guessing.

Organization context from company policies:
{policy_context}
"""


async def extract_fields_node(state: ExpenseAgentState) -> dict:
    """Use LLM to extract structured fields from raw expense text."""
    expense_data = state["expense_data"]
    raw_text = expense_data.get("raw_text", "")

    response = await llm.ainvoke([
        SystemMessage(content=EXTRACTION_PROMPT),
        HumanMessage(content=f"Extract fields from this expense document:\n\n{raw_text}"),
    ])

    import json
    try:
        extracted = json.loads(response.content)
    except json.JSONDecodeError:
        extracted = {"error": "Failed to parse extraction", "raw": response.content}

    return {
        "analysis_result": {**state.get("analysis_result", {}), "extraction": extracted},
        "messages": [response],
    }


async def retrieve_policies_node(state: ExpenseAgentState) -> dict:
    """RAG: Retrieve relevant company policy chunks for the expense context."""
    expense_data = state.get("analysis_result", {}).get("extraction", {})
    category = expense_data.get("category", "miscellaneous")
    amount = expense_data.get("amount", 0)

    # Build query from expense context
    query = f"expense policy for {category} category amount {amount}"

    # In production: query pgvector for similar policy chunks
    # For now, return placeholder
    policy_chunks = [
        f"Policy: {category} expenses over $500 require manager approval.",
        f"Policy: All {category} expenses require itemized receipts.",
        "Policy: Duplicate expenses within 7 days are automatically flagged.",
    ]

    return {"policy_context": policy_chunks}


async def fraud_analysis_node(state: ExpenseAgentState) -> dict:
    """Run fraud detection on the expense."""
    extraction = state.get("analysis_result", {}).get("extraction", {})

    context = f"""
Expense details:
- Merchant: {extraction.get('merchant_name', 'Unknown')}
- Amount: {extraction.get('amount', 0)} {extraction.get('currency', 'USD')}
- Date: {extraction.get('transaction_date', 'Unknown')}
- Category: {extraction.get('category', 'Unknown')}
- Payment method: {extraction.get('payment_method', 'Unknown')}
"""

    response = await llm.ainvoke([
        SystemMessage(content=FRAUD_ANALYSIS_PROMPT),
        HumanMessage(content=context),
    ])

    import json
    try:
        fraud_result = json.loads(response.content)
    except json.JSONDecodeError:
        fraud_result = {"risk_level": "low", "risk_score": 0.1, "indicators": []}

    return {
        "analysis_result": {
            **state.get("analysis_result", {}),
            "fraud": fraud_result,
        },
        "fraud_indicators": fraud_result.get("indicators", []),
        "messages": [response],
    }


async def categorize_node(state: ExpenseAgentState) -> dict:
    """Refine category prediction using policy context."""
    extraction = state.get("analysis_result", {}).get("extraction", {})
    policies = state.get("policy_context", [])

    return {
        "category_prediction": {
            "category": extraction.get("category", "miscellaneous"),
            "confidence": extraction.get("category_confidence", 0.5),
            "policy_compliant": True,  # Placeholder
        }
    }


def should_analyze_fraud(state: ExpenseAgentState) -> str:
    """Decide whether to run full fraud analysis."""
    extraction = state.get("analysis_result", {}).get("extraction", {})
    amount = extraction.get("amount", 0)
    # Always run fraud analysis for amounts > 100, skip for trivial expenses
    if amount and float(amount) > 100:
        return "fraud_analysis"
    return "categorize"


# =============================================================================
# Build the Analysis Graph
# =============================================================================

def build_analysis_graph():
    graph = StateGraph(ExpenseAgentState)

    graph.add_node("extract_fields", extract_fields_node)
    graph.add_node("retrieve_policies", retrieve_policies_node)
    graph.add_node("fraud_analysis", fraud_analysis_node)
    graph.add_node("categorize", categorize_node)

    graph.set_entry_point("extract_fields")
    graph.add_edge("extract_fields", "retrieve_policies")
    graph.add_conditional_edges(
        "retrieve_policies",
        should_analyze_fraud,
        {"fraud_analysis": "fraud_analysis", "categorize": "categorize"},
    )
    graph.add_edge("fraud_analysis", "categorize")
    graph.add_edge("categorize", END)

    return graph.compile()


# =============================================================================
# Build the Chat Agent Graph
# =============================================================================

tools = [query_spend_patterns, search_similar_expenses]


def build_chat_graph():
    """Conversational agent for expense queries."""
    tool_node = ToolNode(tools)
    model_with_tools = llm.bind_tools(tools)

    async def agent_node(state: ExpenseAgentState):
        policy_context = "\n".join(state.get("policy_context", []))
        system = CHAT_SYSTEM_PROMPT.format(policy_context=policy_context)
        messages = [SystemMessage(content=system)] + list(state["messages"])
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_use_tools(state: ExpenseAgentState) -> str:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
        return END

    graph = StateGraph(ExpenseAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_use_tools, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


analysis_graph = build_analysis_graph()
chat_graph = build_chat_graph()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(title="AI Engine", version="1.0.0")


class AnalyzeRequest(BaseModel):
    expense_id: str
    organization_id: str
    raw_text: str = ""
    extraction_data: dict = {}


class ChatRequest(BaseModel):
    message: str
    user_id: str
    organization_id: str
    expense_id: str | None = None


@app.post("/analyze")
async def analyze_expense(request: AnalyzeRequest):
    """Run full AI analysis pipeline on an expense."""
    initial_state: ExpenseAgentState = {
        "messages": [],
        "expense_data": {
            "expense_id": request.expense_id,
            "raw_text": request.raw_text,
            **request.extraction_data,
        },
        "organization_id": request.organization_id,
        "policy_context": [],
        "analysis_result": {},
        "fraud_indicators": [],
        "category_prediction": {},
    }

    result = await analysis_graph.ainvoke(initial_state)

    return {
        "expense_id": request.expense_id,
        "extraction": result.get("analysis_result", {}).get("extraction"),
        "fraud_analysis": result.get("analysis_result", {}).get("fraud"),
        "category": result.get("category_prediction"),
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with the AI expense assistant."""
    initial_state: ExpenseAgentState = {
        "messages": [HumanMessage(content=request.message)],
        "expense_data": {},
        "organization_id": request.organization_id,
        "policy_context": [],
        "analysis_result": {},
        "fraud_indicators": [],
        "category_prediction": {},
    }

    result = await chat_graph.ainvoke(initial_state)

    last_ai_message = None
    for msg in reversed(result["messages"]):
        if not isinstance(msg, HumanMessage):
            last_ai_message = msg
            break

    return {
        "reply": last_ai_message.content if last_ai_message else "No response generated",
        "tools_used": [],
    }


@app.get("/anomalies")
async def get_anomalies(organization_id: str):
    """Return recent anomalies/fraud flags for an organization."""
    # In production: query fraud_analyses table
    return {"anomalies": [], "total": 0}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-engine",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 2),
    }
