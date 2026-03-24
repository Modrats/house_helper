# EXP-001: FLUX.2-pro Guidance Parameter Experiment

Tests how the `guidance` parameter affects FLUX.2-pro interior redesign quality across values `[5, 10, 15, 20, 30, 50]`.

See [setup.md](setup.md) for the full hypothesis and test plan.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An Azure AI Foundry API key for the FLUX.2-pro deployment (`FLUX_KEY`)

---

## Setup

```bash
cp sample.env .env
# Edit .env and fill in FLUX_KEY and FLUX_ENDPOINT
```

---

## Running the Experiment

**Full run (kitchen + living room, all 6 guidance values — 12 API calls):**

```bash
uv run python run.py
```

**Single room:**

```bash
uv run python run.py --room kitchen
uv run python run.py --room living_room
```

**Specific guidance values only:**

```bash
uv run python run.py --guidance 15 20 30
```

**Dry run (no API calls, just prints the plan):**

```bash
uv run python run.py --dry-run
```

Already-generated images are skipped automatically, so re-running is safe.

`uv` will install `requests` into an isolated environment automatically on first run — no `pip install` needed.

---

## Evaluating Results

Once images are generated, open the evaluator in your browser:

```bash
# From this directory:
open evaluate.html
# or
"$BROWSER" evaluate.html
```

The evaluator shows the original photo alongside all 6 guidance outputs per room. Rate each 1–5 stars and add notes. Scores are saved in your browser's localStorage. Click **Show Summary & Recommendation** to see which guidance value scored highest.

---

## Output Structure

```
results/
├── kitchen/
│   ├── guidance_05.png
│   ├── guidance_10.png
│   ├── guidance_15.png
│   ├── guidance_20.png
│   ├── guidance_30.png
│   └── guidance_50.png
└── living_room/
    └── (same)
```

---

## Recording Results

Fill in [analysis.md](analysis.md) with your scores and the recommended guidance value once evaluation is complete.
