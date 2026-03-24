# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (FastAPI, Pydantic), React (TypeScript), Azure (Blob Storage, Table Storage, Container Apps, Bicep), FLUX.2-pro (image generation), Azure OpenAI
- **Architecture:** CLEAN architecture — interfaces/ (ABCs), services/ (implementations), models/ (Pydantic), runners/ (entry points), core.py (composition root)
- **Key services:** Room classifier, criteria checker, distance calculator, imagineering (FLUX.2-pro), local/Azure storage adapters
- **Created:** 2026-03-23

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-24: Evaluation harness implemented (Issue #33)

- `backend/src/evaluation/` module created with `deterministic.py`, `llm_judge.py`, and `__init__.py`.
- `EvalResult` is a frozen Pydantic model: `{check_name, passed, details}`. Lives in `deterministic.py` and is re-exported from `__init__.py`.
- Deterministic checks: `filter_result_exists/valid_json/schema`, `classification_exists/valid_json/schema/completeness`, `criteria_result_exists/valid_json/schema`. Only runs later checks if earlier ones pass (avoids cascading noise).
- LLM judge uses lazy `import openai` inside `_get_client()` so the module is always importable without the package installed.
- `run_llm_judge` returns `llm_judge_skipped` (passed=True) when no output dirs exist — distinguishes "not ready yet" from "evaluated and failed".
- `openai>=1.0.0` added as `[project.optional-dependencies] llm` (not core) to avoid forcing the dep on deterministic-only users.
- `write_summary` is public (not `_write_summary`) so tests can call it directly and it can be used from CLI and pipeline runners.
- Standalone CLI: `python -m src.evaluation.deterministic --house {slug}` — uses `load_storage_paths()` with graceful fallback.
- Tests: 44 parametrised cases, NamedTuple + `@pytest.mark.parametrize`, zero class-based tests. `tmp_path` fixture for filesystem cases.
- VCR cassette structure placeholder at `tests/fixtures/cassettes/` — record with `pytest --record-mode=new_episodes` once API keys are available.
