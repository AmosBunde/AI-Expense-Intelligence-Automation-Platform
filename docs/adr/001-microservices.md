# ADR-001: Microservices Architecture

**Status:** Accepted
**Date:** 2026-04-12
**Decision Makers:** Engineering Team

## Context

We need to build an AI-powered expense platform that handles document ingestion, LLM extraction, policy evaluation, fraud detection, and dashboard analytics. The system must support both real-time single expense processing and batch operations.

## Decision

Adopt a modular microservices architecture with 7 services communicating via synchronous HTTP, backed by PostgreSQL, Redis, and S3.

## Services

1. **API Gateway** - Auth, rate limiting, routing
2. **Expense Processor** - OCR, extraction, normalization, pipeline orchestration
3. **AI Engine** - LangGraph agents, RAG, fraud detection
4. **Policy Engine** - Rule evaluation, auto-approval
5. **Dashboard UI** - React frontend
6. **Notification Service** - Email, Slack delivery
7. **Batch Processor** - Celery-based async processing

## Rationale

- **Independent scaling:** AI Engine needs more CPU/memory than Policy Engine. Different scaling profiles.
- **Technology isolation:** AI Engine uses LangGraph/LangChain stack. Policy Engine is pure Python rules. Dashboard is React. Each can evolve independently.
- **Fault isolation:** A crash in fraud detection should not take down expense listing.
- **Team parallelism:** Different engineers can work on different services simultaneously.

## Consequences

- **Positive:** Independent deployment, scaling, and technology choices per service.
- **Negative:** Network overhead for inter-service calls. Distributed tracing complexity. Eventual consistency considerations.
- **Mitigation:** All services in same VPC. Structured logging with correlation IDs. Health check cascade in API Gateway.

## Alternatives Considered

- **Monolith:** Simpler deployment but harder to scale AI workloads independently.
- **Event-driven (Kafka):** More decoupled but adds operational complexity for a v1.
