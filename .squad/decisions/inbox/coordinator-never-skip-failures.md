### 2026-03-24: Never skip lint or test failures — always fix

**By:** Terri Modrakowski (via Copilot)
**What:** If a lint check, type check, or test fails, agents MUST fix the issue — never skip it, gloss over it, or bypass the hook. No `--no-verify`, no `SKIP=`, no "pre-existing issue" excuses. If it fails, fix it before proceeding.
**Why:** User directive — quality gates are non-negotiable.
