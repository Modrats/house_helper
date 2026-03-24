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
