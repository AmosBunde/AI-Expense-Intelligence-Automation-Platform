# ADR-002: LangGraph for Agent Orchestration

**Status:** Accepted
**Date:** 2026-04-12

## Context

The AI Engine must orchestrate multi-step workflows: extract fields from documents, retrieve relevant policies via RAG, run fraud detection, categorize expenses, and support conversational queries with tool use. We need a framework that makes these pipelines visible, testable, and extensible.

## Decision

Use LangGraph (from LangChain) for building stateful agent graphs with explicit node routing, conditional edges, and tool integration.

## Rationale

- **Explicit state management:** `ExpenseAgentState` TypedDict makes all pipeline data visible and type-checked.
- **Conditional routing:** `should_analyze_fraud` decides at runtime whether to run full fraud analysis, avoiding unnecessary LLM calls for small expenses.
- **Tool integration:** `ToolNode` and `bind_tools` provide structured tool calling for the chat agent.
- **Observability:** Each node execution is traceable. LangSmith integration available for production monitoring.
- **Testability:** Individual nodes can be unit tested. Graph structure can be validated at compile time.

## Consequences

- **Positive:** Clear pipeline visualization. Each step is independently testable. Easy to add new analysis nodes.
- **Negative:** LangGraph adds a dependency layer. Learning curve for developers unfamiliar with the framework.
- **Mitigation:** Wrap LangGraph behind clean interfaces. Document graph structure in architecture diagrams.
