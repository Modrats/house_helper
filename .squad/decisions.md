# Squad Decisions

## Active Decisions

### 2026-03-23: Priority 1 Work Breakdown

**By:** Gustave (Lead) | **Requested by:** Terri Modrakowski

Decomposed Priority 1 work into 16 GitHub issues across 3 workstreams:
- **W1 Frontend (Agatha):** 6 issues — App shell, house browser, detail page, gallery, image slider, API client
- **W2 Backend (Zero):** 7 issues — iFilter pipeline, text filter, room classifier, photo checker, distance calc, imagineering, FastAPI endpoints
- **W4 Experiments (Kovacs):** 3 issues — EXP-001 guidance parameter sweep

**Key decisions:**
- Issues sized for ~1-3 days / single PR
- Backend foundation (#7) and Frontend shell (#1) can start in parallel
- EXP-001 results will inform imagineering service defaults
- Follows CLEAN architecture per ADRs

### 2026-03-24: PR #40 Architectural Review — Room Classifier

**By:** Gustave (Lead) | **Requested by:** Terri Modrakowski

**Context:** Review of Zero's room classifier implementation (issue #9). Nine inline review comments from Terri, all accepted.

**Decisions:**

1. **Create `ILLMService` interface with structured output support.** Vision LLM calls, structured output parsing, and text completions are reusable across room classifier, photo checker, criteria evaluator, and LLM-as-judge. A single `ILLMService` ABC in `interfaces/` with an `AzureOpenAIService` implementation in `services/` eliminates direct `openai` SDK coupling. Structured output (via OpenAI's `response_format` with Pydantic model) replaces manual JSON parsing.

2. **Create `IRoomClassifier` interface.** The classifier needs its own ABC so implementations can be swapped (e.g., mock for tests, different provider).

3. **Remove premature `Settings` module.** Room classifier needs only Azure OpenAI credentials from env vars. Full `Settings` class belongs in a later PR.

4. **Scope pyproject.toml to what this PR uses.** Remove `fastapi`, `uvicorn`, `opentelemetry-*` from core deps. Only `openai`, `pydantic`, `pydantic-settings`, `pyyaml` needed now.

5. **Decompose `classify_house` into single-purpose functions.** Extract `_load_previous_results()`, `_discover_photos()`, `_batch_classify()`.

6. **Batch size must be configurable.** Default comes from env var `ROOM_CLASSIFIER_BATCH_SIZE` at the composition root, overridable via constructor/kwarg. No hardcoded module constants.

### 2026-03-24: PR #40 Revision — Implementation Details

**By:** Zero (Backend Dev) | **Requested by:** Terri Modrakowski (via Gustave's review)

1. **Internal `_VisionResponse` model** — Lightweight Pydantic model in `room_classifier.py` with only `room_type` and `confidence` for LLM structured output. Separate from `PhotoClassification` (which includes `filename` the LLM doesn't know).

2. **Batch size parameterization** — `classify_house()` accepts `batch_size` kwarg defaulting to instance `_batch_size`. Composition root reads `ROOM_CLASSIFIER_BATCH_SIZE` env var with default `"5"`.

3. **Structured output via `response_format` with `json_schema`** — `AzureOpenAIService._call_api` uses OpenAI `response_format` parameter. Guarantees valid JSON without manual parsing.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
