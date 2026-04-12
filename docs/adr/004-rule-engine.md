# ADR-004: Rule-Based Policy Engine

**Status:** Accepted
**Date:** 2026-04-12

## Context

The platform must evaluate expenses against company policies to determine compliance, auto-approve eligible expenses, and flag violations. Policies vary per organization and can change frequently. We considered three approaches: pure LLM evaluation, a dedicated rules engine library, or a custom rule evaluator.

## Decision

Build a custom rule evaluation framework with a pluggable evaluator pattern and structured rule definitions stored as JSON in PostgreSQL.

## Rationale

- **Determinism:** Policy evaluation must produce identical results for identical inputs. LLM-based evaluation introduces non-determinism that is unacceptable for financial compliance.
- **Auditability:** Every rule evaluation must produce a clear trace: which rule fired, what the threshold was, what the actual value was, and what action was recommended. Structured evaluators provide this naturally.
- **Performance:** Rule evaluation runs in microseconds versus seconds for LLM calls. This matters for batch processing thousands of expenses.
- **Customizability:** Organizations can define their own rules via the API without requiring code changes. Rules are stored as JSON with a defined schema.

## Rule Structure

```json
{
  "id": "meal-limit",
  "name": "Meal Expense Limit",
  "condition_type": "amount_limit",
  "parameters": {"max_amount": 75.0, "currency": "USD"},
  "category": "meals",
  "violation_severity": "medium",
  "action_on_violation": "require_review"
}
```

## Evaluator Pattern

Each `condition_type` maps to a static evaluator method in `RuleEvaluator`. Adding a new rule type requires adding one method. Evaluators return `None` for compliance or a `PolicyViolation` dict for violations.

## Action Priority

When multiple rules fire, the most severe action wins: `reject > escalate > require_review > auto_approve`.

## Consequences

- **Positive:** Fast, deterministic, auditable. Easy to test every rule in isolation. Organizations can self-serve policy changes.
- **Negative:** Cannot handle nuanced or context-dependent policy interpretation. Complex conditional logic (if category is X and department is Y and amount is Z) requires structured rule composition.
- **Mitigation:** Use the AI Engine's LLM for advisory analysis (fraud detection, anomaly explanation) while the Policy Engine handles deterministic compliance. The two complement each other.
