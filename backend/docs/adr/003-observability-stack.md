# ADR-003: Observability Stack

## Status
Accepted

## Date
2026-03-23

## Context
The pipeline runs on Azure Container Apps and needs distributed tracing with correlation IDs across:
- FastAPI HTTP requests
- Service Bus message processing  
- External API calls (Azure OpenAI, FLUX)

**Options considered:**
1. **Azure App Insights native SDK** — Deep Azure integration, auto-instrumentation
2. **OpenTelemetry** — Vendor-agnostic standard, exportable to any backend

## Decision
**OpenTelemetry**

## Rationale
Distributed tracing across Python FastAPI → Service Bus → Container Apps is complex. OpenTelemetry provides:
- **Correlation ID propagation** — W3C Trace Context standard works everywhere
- **Vendor-agnostic design** — Not betting observability on single vendor
- **Azure Monitor exporter** — Still sends to App Insights, best of both worlds
- **Industry standard** — Better hiring pool and community knowledge

Works seamlessly with Azure Monitor when needed, but we own our instrumentation.

## Consequences

### Positive
- Portable traces if we ever move off Azure
- Standard APIs with excellent Python support (`opentelemetry-instrumentation-*`)
- Can export to multiple backends (Jaeger locally, Azure in prod)
- Future-proof as OTel becomes the universal standard

### Negative
- More boilerplate than App Insights auto-instrumentation
- Requires consistent instrumentation discipline across services
- Azure-specific features (Live Metrics, Profiler) need extra setup

### Mitigations
- Create shared `observability/` module with pre-configured setup
- Document instrumentation patterns in this docs folder
- Use auto-instrumentation packages where available (FastAPI, HTTPX, etc.)
