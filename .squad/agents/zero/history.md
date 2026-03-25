# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (FastAPI, Pydantic), React (TypeScript), Azure (Blob Storage, Table Storage, Container Apps, Bicep), FLUX.2-pro (image generation), Azure OpenAI
- **Architecture:** CLEAN architecture — interfaces/ (ABCs), services/ (implementations), models/ (Pydantic), runners/ (entry points), core.py (composition root)
- **Key services:** Room classifier, criteria checker, distance calculator, imagineering (FLUX.2-pro), local/Azure storage adapters
- **Created:** 2026-03-23

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-24: PR #40 Revision — Room Classifier Refactor

- **ILLMService interface** created at `interfaces/llm_service.py` — single LLM integration point per ADR-004. Two methods: `classify_image` (vision+structured) and `complete_structured` (text+structured). All LLM consumers should depend on this, never on `openai` directly.
- **IRoomClassifier interface** created at `interfaces/room_classifier.py` — ABC with `classify_house(slug, *, batch_size)`.
- **AzureOpenAIService** at `services/azure_openai_service.py` — the ONLY file that imports `openai`. Constructor reads env vars (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`) and raises `RuntimeError` if any are missing. `_call_api` is the VCR mocking boundary.
- **AzureOpenAIRoomClassifier** replaces `RoomClassifier`. Takes `ILLMService` + paths + batch_size (no Settings dependency). Decomposed into `_discover_photos`, `_load_previous_results`, `_classify_batch`. Uses structured output — no manual JSON parsing.
- **_VisionResponse** internal model in room_classifier.py — lightweight Pydantic model with just `room_type`/`confidence` for structured output. Avoids sending `filename` schema to the LLM.
- **settings.py deleted** — env var handling moved to `AzureOpenAIService` (service-level) and `core.py` (composition root for batch_size default). `pydantic-settings` removed from deps.
- **Removed deps**: `fastapi`, `uvicorn`, `opentelemetry-api`, `opentelemetry-sdk`, `pydantic-settings`.
- **Observability module** doesn't exist as source on this branch — only stale `__pycache__`. Replaced with stdlib `logging`.
- **Composition root** (`core.py`): `create_room_classifier()` now constructs `AzureOpenAIService`, gets paths from `load_storage_paths()`, batch_size from `ROOM_CLASSIFIER_BATCH_SIZE` env var (default "5"), returns `IRoomClassifier`.
- **ruff** is in the `dev` dependency group — run via `uv run --group dev ruff check src/`.
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

### 2026-03-24 — Gustave code review of eval harness: 11 gaps to fix

Gustave (Lead) reviewed the evaluation harness delivered in Issue #33 and identified 11 gaps (all direct fixes, no redesigns):
- `classification/` dir must be `classifier/` to match `plan.md`.
- `criteria_result.json` must be at `criteria/criteria_result.json`, not slug root.
- `_check_valid_json` must reject non-dict JSON roots — arrays crash callers on `.keys()`.
- `ConsistencyJudgment` is dead code — implement `_evaluate_consistency` or remove and update docstring.
- `run_llm_judge` docstring falsely claims batching — remove or note as future work.
- `_DEFAULT_API_VERSION` violates team decision — use `os.environ["AZURE_OPENAI_API_VERSION"]` and raise on missing.
- Silent `except Exception` with hardcoded path fallbacks in `llm_judge.py` and `deterministic.py` — let imports fail loudly.
- `write_summary` not exported from `__init__.py`. Full gap list in decisions.md.
### 2026-03-24: Distance calculator service (Issue #11, PR #52)

- **IDistanceCalculator** interface at `interfaces/distance_calculator.py` — ABC with `calculate_distances(slug) -> DistanceResult`.
- **TravelTime** and **DistanceResult** models at `models/distance.py` — frozen Pydantic BaseModels with `to_summary_dict()` and `to_detailed_dict()`.
- **GoogleMapsDistanceCalculator** at `services/distance_calculator.py` — calls Google Maps Distance Matrix API via `requests.get`. Uses `_call_distance_api` as the mocking boundary.
- Address extraction from `listing.txt`: regex patterns for `Address:`, `Adres:`, `Location:` labels, falls back to first non-empty line.
- Idempotent via `distances.json` + SHA-256 config hash comparison — recalculates only when destinations config changes.
- **Factory** `create_distance_calculator()` in `core.py` — requires `GOOGLE_MAPS_API_KEY` (no default, fails loudly).
- **`load_distance_config()`** in `config.py` reads `distance.destinations` from criteria.yaml.
- Sample destinations (Amsterdam Central, Office) added to `config/criteria.yaml`.
- Tests: 21 parametrised cases, NamedTuple + `@pytest.mark.parametrize`. Mocks `requests.get` at the service module boundary.
- `House` model already has `distances: dict[str, int]` and `with_distance()` — ready for pipeline integration.

### 2026-03-24: ConfigLoader refactor (PR #57 review response)

- **Decision**: Replaced 4 `load_*()` functions + `_load_raw()` + public globals with a single `ConfigLoader` class in `config.py`. Each function called `_load_raw()` independently; `ConfigLoader._load()` lazy-caches the YAML and is called once per instance.
- **Public API is the class**: `ConfigLoader(path)` or `ConfigLoader()` for default. Methods: `criteria()`, `storage_paths()`, `distance_config()`, `photo_criteria()`. Caller doesn't need to know the path OR that it's YAML-backed.
- **Private module constants**: `_DEFAULT_YAML` and `_REPO_ROOT` (underscore-prefixed) are implementation details, not the public API the reviewer objected to. They're necessary because Python classes can't resolve `__file__` at class body level conveniently.
- **Backward compat**: No thin wrappers added — updated all callers (core.py × 5 sites, run.py × 1, test_photo_checker.py × 3) directly. Cleaner than maintaining wrapper functions.
- **Swappable unit**: The class IS the swap point per the reviewer's request. An `AzureAppConfigLoader` would expose the same 4 methods.
- **Branch discipline**: Be explicit about which branch you're on before committing. `git branch --show-current` before any `git add`. This refactor accidentally committed to squad/11 first, required undo + re-apply on squad/10.
