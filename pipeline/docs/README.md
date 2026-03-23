# Architecture Decision Records — Pipeline

This log tracks architecture decisions for the House Helper pipeline (Python/FastAPI service).

## ADR Index

| ADR | Date | Decision | Status |
|-----|------|----------|--------|
| [ADR-001](adr/001-queue-service.md) | 2026-03-23 | Use Azure Service Bus for queue processing | Accepted |
| [ADR-002](adr/002-python-package-manager.md) | 2026-03-23 | Use UV for Python package management | Accepted |
| [ADR-003](adr/003-observability-stack.md) | 2026-03-23 | Use OpenTelemetry for observability | Accepted |
| [ADR-004](adr/004-llm-test-mocking.md) | 2026-03-23 | Use VCR-style recording for LLM test mocking | Accepted |

## How to Add an ADR

1. Create a new file in `docs/adr/` with the next sequential number: `NNN-short-title.md`
2. Use the template in the existing ADRs (Status, Date, Context, Decision, Rationale, Consequences)
3. Add an entry to this index table
4. Submit a PR for team review
