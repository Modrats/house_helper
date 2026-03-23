# ADR-001: Frontend Hosting

## Status
Accepted

## Date
2026-03-23

## Context
House Helper's frontend is a React SPA that consumes a FastAPI backend. We need to decide where to host it on Azure.

**Options considered:**
1. **Azure Static Web Apps** — Purpose-built for SPAs, includes CDN, HTTPS, staging environments
2. **Azure Container Apps** — Container-based hosting, more flexible but heavier

## Decision
**Azure Static Web Apps**

## Rationale
Static Web Apps is purpose-built for React SPAs and offers seamless Azure integration (auth, functions, deployment automation). Container Apps would waste resources and cost 3-5x more for a simple frontend. Static Web Apps gives us:
- Free CDN
- Automatic HTTPS  
- Built-in staging environments for team collaboration
- Native GitHub Actions integration

## Consequences

### Positive
- Lower cost than container-based hosting
- Zero infrastructure management for frontend
- Built-in preview environments for PRs
- Integrated Azure Functions for API routes if needed

### Negative
- Locked into Azure's SPA-specific offering
- Custom server-side logic requires Azure Functions
- No direct server-side rendering path if requirements change

### Mitigations
- Backend API handles all complex logic — frontend stays pure SPA
- If SSR becomes necessary, can migrate to Container Apps later
