# Decision: Docker Infrastructure Conventions

**By:** Zero (Backend Dev) | **Date:** 2026-03-24 | **Issue:** #34 | **PR:** #36

## Context
Setting up Docker infrastructure for local dev required several conventions.

## Decisions
1. **uv via multi-stage copy** — `COPY --from=ghcr.io/astral-sh/uv:latest` instead of `pip install uv`. Keeps pip out of the build entirely per team directive.
2. **nginx as API proxy** — Frontend nginx proxies `/api/` to `http://backend:8000/api/`. This means the frontend doesn't need CORS configuration and `VITE_API_BASE_URL=/api` works in both dev and Docker.
3. **Volume mounts for data** — `input_data/` and `outputs/` are mounted as Docker volumes so local files flow through to the container without rebuilding.
4. **Non-root runtime** — Backend container runs as `appuser` (uid 1000) for security.

## Impact
All team members can use `make docker-up` for local development. Frontend and backend services communicate via Docker networking.
