# ADR-004: LLM Test Mocking

## Status
Accepted

## Date
2026-03-23

## Context
The pipeline uses LLMs for:
- Room classification (photo → room type)
- Criteria checking (text + photos → P1/P2 evaluation)
- LLM-as-judge evaluations

We need deterministic tests without burning API tokens on every CI run.

**Options considered:**
1. **VCR-style recording** — Record real responses, replay in tests
2. **Static fixtures** — Hand-crafted mock responses
3. **Live-skip** — Skip LLM tests in CI, run only locally

## Decision
**VCR-style recording** with static fixtures as fallback

## Rationale
Record real Azure OpenAI responses once during test setup, replay deterministically in CI/CD:
- **Zero token burn** — Recordings are free to replay
- **Identical outputs** — Perfect for LLM-judge assertions where consistency matters
- **Real responses** — Captures actual model behavior, not guessed outputs
- **Battle-tested** — `vcrpy` and `pytest-recording` are mature libraries

Static fixtures complement VCR for edge cases that are hard to trigger naturally.

### Why Recordings Over Static Fixtures?

**Static fixtures** = you hand-write fake LLM responses based on what you *think* the model will say.  
**VCR recording** = you capture what the model *actually* says, then replay it.

The difference matters for LLMs because:

1. **LLM outputs are unpredictable** — You can't accurately guess the exact JSON structure, wording, or edge cases an LLM will produce. A hand-written fixture might pass tests but not reflect real behavior.

2. **Prompt changes have subtle effects** — If you tweak a prompt, a static fixture stays the same (false confidence). A recording forces you to re-record and see what actually changed.

3. **LLM-as-judge needs real baselines** — Our evaluation harness compares outputs against expected results. If the "expected" was never real, we're testing fiction against fiction.

**Example:** The room classifier prompt asks for `{"room_type": "bedroom", "confidence": 0.95}`. But the actual model might return `{"room_type": "bedroom", "confidence": 0.9523, "reasoning": "..."}`. A static fixture would miss that extra field — and our code might break on it in production.

### When Static Fixtures Are Appropriate

- Edge cases you can't easily trigger (malformed JSON, timeouts)
- Testing error handling paths
- Unit tests for parsing logic (decoupled from LLM)

## Consequences

### Positive
- CI runs are fast and free (no API calls)
- Tests are deterministic and reproducible
- Recordings serve as documentation of expected LLM behavior
- Can re-record when prompts change intentionally

### Negative
- Requires maintenance when LLM prompts change (must re-record)
- Large cassette files in git (YAML/JSON of full responses)
- Recording step needs valid API keys (dev machine only)
- Recordings become stale if model behavior changes

### Mitigations
- Store cassettes in `tests/fixtures/cassettes/` with clear naming
- Add `make record-fixtures` command for re-recording
- Document recording process in CONTRIBUTING.md
- Use `.gitattributes` to mark cassettes as generated (cleaner diffs)
- Consider LFS for very large recordings if needed
