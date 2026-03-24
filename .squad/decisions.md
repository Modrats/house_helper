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
### 2026-03-24: Use UV, not pip — all Python package management

**By:** Terri Modrakowski (directive)

All agents MUST use `uv` for Python dependency management — never `pip`. This aligns with ADR-002 which chose UV as the project's package manager. Commands: `uv pip install`, `uv sync`, `uv add` — never bare `pip install`.

### 2026-03-24: Never skip lint or test failures — always fix

**By:** Terri Modrakowski (directive)

If a lint check, type check, or test fails, agents MUST fix the issue — never skip it, gloss over it, or bypass the hook. No `--no-verify`, no `SKIP=`, no "pre-existing issue" excuses. If it fails, fix it before proceeding.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction

---

### 2026-03-24: No hardcoded defaults for environment variables

**By:** Terri (via Copilot)
**What:** Never supply default values for environment variables. If a required env var is missing, fail loudly at runtime with a clear error message.
**Why:** Defaults hide misconfiguration. Every env var must be explicitly set.

---

### 2026-03-24: NamedTuple + parametrize as the standard test pattern

**By:** Kovacs
**What:** All backend tests use `NamedTuple`-based test cases combined with `@pytest.mark.parametrize`. Class-based `TestX` groupings are retired. Every test case has a `description` field. One NamedTuple type per group of related cases.
**Why:** All scenarios visible at a glance; `description` gives pytest readable IDs without custom lambdas; flat functions are easier to scan than nested class hierarchies; adding a new scenario is a single list entry.

---

### 2026-03-24: Evaluation harness design decisions

**By:** Zero
**Related to:** Issue #33

1. **`EvalResult` lives in `deterministic.py`, re-exported from `__init__.py`** — avoids a separate `models.py`; deterministic is the non-optional evaluator.
2. **`openai` is an optional dependency (`[llm]`)** — deterministic-only usage should not require the package; lazy import inside `_get_client()` defers the error to call time.
3. **`run_llm_judge` returns `llm_judge_skipped` (passed=True) when no outputs exist** — signals "not ready yet" vs "evaluated and failed".
4. **`write_summary` is public** — needed by CLI, tests, and future pipeline runners.
5. **VCR cassettes deferred; static mocks used for LLM judge tests** — per ADR-004, cassettes require a real API key not available in CI. `unittest.mock` + env var mocking covers error-path tests. Cassette structure (`tests/fixtures/cassettes/`) is in place for future recording.

---

### 2026-03-24: All agents MUST use PRs — no direct pushes to main

**By:** Coordinator | **Requested by:** Terri Modrakowski

- Every agent is prohibited from pushing directly to `main`.
- Domain work (code, tests, config, docs) MUST go through a feature branch → PR → review → merge.
- **Scribe's git commit scope is strictly `.squad/` only.** Never stage or commit files outside `.squad/`.
- Scribe MAY open PRs, but only for `.squad/` documentation updates — never for domain work.
- Violation: Scribe committed evaluation source files directly to main (2026-03-24). Rebased and corrected.
