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

---

### 2026-03-24: IDataSource / HouseRepository architecture (PR #41 review)

**By:** Zero | **Reviewed by:** Terri Modrakowski | **Branch:** `squad/13-fastapi-endpoints`

1. **`IDataSource` is a generic CRUD interface** — defines `read_json`, `write_json`, `list_keys`, `read_bytes`, `exists`. No domain knowledge. Adding a cloud backend = implement 5 methods.
2. **`HouseRepository` owns all house-domain storage logic** — path conventions, drift detection (`_criteria_match`, `_restore_filter_state`), and pipeline-resume logic at `backend/src/services/house_repository.py`.
3. **Criteria drift detection lives in `HouseRepository`, not `LocalStorage`** — storage layer is pure CRUD; business logic belongs in the repository.
4. **Photos served via API endpoints, not static mounts** — `GET /api/houses/{slug}/photos/{filename}` and `GET /api/houses/{slug}/imagineered/{filename}` replace `StaticFiles` mounts.
5. **OWASP A05 CORS rule** — `allow_headers=["*"]` is rejected by browsers when `allow_credentials=True`. Always use explicit allowlist: `["Content-Type", "Authorization"]`.

---

### 2026-03-24: Eval harness code review — 11 gaps found (assigned to Zero)

**By:** Gustave (Lead / Architect) | **Requested by:** Terri Modrakowski | **Assignee:** Zero

Gustave reviewed the evaluation harness skeleton (Issue #33) and identified 11 concrete gaps. Architecture is sound; all gaps are direct fixes, not redesigns.

Key gaps:
- **GAP-1:** Output dir `classification/` must be `classifier/` to match `plan.md` spec.
- **GAP-2:** `criteria_result.json` checked at slug root; must be `criteria/criteria_result.json`.
- **GAP-3:** `_check_valid_json` must reject non-dict JSON roots — callers crash on `.keys()` for arrays.
- **GAP-4:** `ConsistencyJudgment` is dead code — implement `_evaluate_consistency` or remove and update docstring.
- **GAP-5:** `run_llm_judge` docstring falsely claims batching — remove or mark as future work.
- **GAP-6:** `_DEFAULT_API_VERSION` violates the no-hardcoded-defaults team decision — use `os.environ["AZURE_OPENAI_API_VERSION"]` and raise on missing.
- **GAP-7:** Silent `except Exception` with hardcoded fallback paths in `llm_judge.py` and `deterministic.py` — let imports fail loudly.
- **GAP-8 through GAP-11:** `write_summary` not exported from `__init__.py`; additional schema and coverage gaps.

---

### 2026-03-24: Test quality checklist — Issue #45

**By:** Gustave (Lead) | **Requested by:** Terri Modrakowski

Filed GitHub issue #45 — "chore: evaluate and improve test extensibility, format, and quality" as a living team checklist. Covers: coverage and completeness (90% gate), quality over quantity, naming and readability (AAA structure), design patterns (mocks/fakes, setup/teardown). Gaps found produce follow-up issues or PRs. No `chore` label on the repo; issue created without it.
