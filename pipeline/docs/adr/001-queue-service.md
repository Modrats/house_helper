# ADR-001: Queue Service

## Status
Accepted

## Date
2026-03-23

## Context
The House Helper pipeline processes houses through multiple stages: room classification, criteria checking, distance calculation, and imagineering. We need a queue service to trigger and coordinate this processing.

**Options considered:**
1. **Azure Storage Queue** — Simple, cheap, basic FIFO queue
2. **Azure Service Bus** — Enterprise messaging with dead-letter queues, deduplication, sessions

## Decision
**Azure Service Bus**

## Rationale
House processing involves complex, stateful workflows (room classification → imagineering → evaluation). Service Bus provides:
- **Dead-letter queues** — Failed messages don't block the queue, can be inspected and replayed
- **Message deduplication** — Prevents double-processing if a house gets queued twice
- **Scheduled redelivery** — Automatic retry with backoff for transient failures

Storage Queue's simplicity isn't worth the operational pain when one room fails during imagineering—we need guaranteed delivery and proper error handling.

## Consequences

### Positive
- Reliable processing with automatic retries
- Dead-letter queue for debugging failed houses
- Message sessions for ordering if needed
- Better observability via Azure Portal

### Negative
- Higher cost than Storage Queue (~$0.05/million operations vs nearly free)
- More operational overhead to configure and monitor
- Requires careful dead-letter queue monitoring and replay strategies

### Mitigations
- Set up alerts on dead-letter queue depth
- Document replay procedures for failed messages
- Cost is negligible at expected volume (hundreds of houses, not millions)
