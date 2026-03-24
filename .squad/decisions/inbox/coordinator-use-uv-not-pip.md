### 2026-03-24: Use UV, not pip — all Python package management

**By:** Terri Modrakowski (via Copilot)
**What:** All agents MUST use `uv` for Python dependency management — never `pip`. This aligns with ADR-002 which chose UV as the project's package manager. Commands: `uv pip install`, `uv sync`, `uv add` — never bare `pip install`.
**Why:** User directive — reinforcing ADR-002. UV is the team standard.
