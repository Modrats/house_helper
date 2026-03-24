# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (FastAPI, Pydantic), React (TypeScript), Azure (Blob Storage, Table Storage, Container Apps, Bicep), FLUX.2-pro (image generation), Azure OpenAI
- **Architecture:** CLEAN architecture — interfaces/ (ABCs), services/ (implementations), models/ (Pydantic), runners/ (entry points), core.py (composition root)
- **Migration:** Merging 5 legacy repos (funda_llm, house_helper, house_helper_app, house_helper_frontend, funda_scrape) into one monorepo
- **Created:** 2026-03-23

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-24 — Eval harness code review (Issue #33, Zero's implementation)

- Reviewed Zero's evaluation harness skeleton. Architecture is sound (module split, Pydantic models, optional dep pattern, NamedTuple tests). Found **11 concrete gaps** — none are redesigns.
- Key gaps: output path mismatches (`classification/` vs `classifier/`, `criteria_result.json` location), `_check_valid_json` crashes callers on JSON arrays, `ConsistencyJudgment` dead code, false batching docstring, `_DEFAULT_API_VERSION` violates team decision, silent `except Exception` with hardcoded fallback paths, `write_summary` not exported.
- All gaps documented in decisions.md and assigned to Zero.

### 2026-03-24 — Filed test quality checklist issue (#45)

- Filed GitHub issue #45 — "chore: evaluate and improve test extensibility, format, and quality".
- Four dimensions: coverage & completeness (90% gate), quality over quantity, naming & readability (AAA), design patterns (mocks/fakes, setup/teardown).
- No `chore` label on repo; issue created without it. Any gaps found produce follow-up issues or PRs.
