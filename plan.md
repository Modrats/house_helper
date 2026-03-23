# House Helper Migration Plan

Reconcile existing repos (`funda_llm`, `house_helper`, `house_helper_app`, `house_helper_frontend`, `funda_scrape`) into one clean monorepo.

## Context
A user wants to narrow down house choices based on qualitative and quantitative preferences. For candidate houses, run an imagineering process with the user's design taste so they can picture themselves living there.

---

## Architecture

Each container runs as a standalone service with its own `pyproject.toml` / `package.json`.

```
┌─────────────────────────────────────────────────────────────┐
│  1. Data Layer                                              │
│  • Local: houses/ folder with photos, listing.json, etc.    │
│  • Azure: Blob Storage + Table Storage (same schema)        │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  2. Backend (Python service)                                │
│  Modes: CLI | Queue-triggered | API                         │
│  ├─ Classifier (room photos → room type)                    │
│  ├─ Criteria Checker (text + photos → P1/P2 evaluation)     │
│  ├─ Distance Calculator (address → commute time)            │
│  ├─ Imagineering (photos → AI-reimagined versions)          │
│  ├─ Evaluation harness (deterministic + LLM-based)          │
│  └─ API (FastAPI) — thin layer serving processed data       │
│       /houses, /rooms, /photos endpoints                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  3. Frontend (React SPA)                                    │
│  • Browse houses, view criteria, compare photos             │
│  • Before/after slider for imagineered rooms                │
└─────────────────────────────────────────────────────────────┘
                            
┌─────────────────────────────────────────────────────────────┐
│  4. Infrastructure (IaC)                                    │
│  • Bicep/Terraform templates                                │
│  • Makefile with deploy/destroy/status commands             │
│  • Targets: Static Web App, Container Apps, Storage, etc.   │
└─────────────────────────────────────────────────────────────┘
```

---

## Monorepo Structure

```
house_helper/
├── .github/
│   └── workflows/
│       ├── ci.yml           # Lint + test gates on PR
│       └── deploy.yml       # Deploy to Azure on merge
├── input_data/                    # IMMUTABLE raw data (gitignored real data)
│   └── houses/
│       └── <house_slug>/    # See "House Data Structure" below
├── outputs/                       # REGENERABLE pipeline artifacts
│   └── houses/
│       └── <house_slug>/    # Mirrors input_data structure
├── backend/                 # AI pipeline + API (Python service)
│   ├── src/
│   │   ├── config/          # Environment-based configuration
│   │   │   ├── __init__.py
│   │   │   └── settings.py  # Pydantic Settings (env vars, secrets)
│   │   ├── interfaces/      # ABCs and Protocols only — no implementation
│   │   │   ├── classifier.py
│   │   │   ├── criteria_checker.py
│   │   │   ├── distance_calculator.py
│   │   │   ├── imagineering.py
│   │   │   ├── data_source.py   # IDataSource — local or Azure interchangeably
│   │   │   └── queue.py         # IQueueConsumer
│   │   ├── services/        # Concrete implementations — one responsibility each
│   │   │   ├── azure_openai_agent.py
│   │   │   ├── room_classifier_service.py
│   │   │   ├── criteria_checker_service.py
│   │   │   ├── distance_service.py
│   │   │   ├── flux_image_service.py
│   │   │   ├── local_storage_service.py   # IDataSource impl (file system)
│   │   │   ├── azure_storage_service.py   # IDataSource impl (Blob + Table)
│   │   │   └── queue_consumer_service.py  # IQueueConsumer impl
│   │   ├── models/          # Pure Pydantic data structures — no business logic
│   │   │   ├── house.py
│   │   │   ├── room.py
│   │   │   ├── criteria_result.py
│   │   │   └── imagineering_result.py
│   │   ├── api/             # FastAPI routes (thin layer, depends on interfaces)
│   │   │   ├── __init__.py
│   │   │   ├── app.py       # FastAPI app factory, OpenAPI config
│   │   │   └── routes/
│   │   │       ├── houses.py
│   │   │       ├── photos.py
│   │   │       └── health.py
│   │   ├── runners/         # Entry points with `if __name__ == "__main__":`
│   │   │   ├── run_pipeline.py
│   │   │   ├── run_api.py
│   │   │   └── run_single_house.py
│   │   ├── observability/   # Logging, tracing, metrics
│   │   │   ├── __init__.py
│   │   │   ├── correlation.py   # Correlation ID middleware
│   │   │   ├── logging.py       # Structured logging setup
│   │   │   └── tracing.py       # OpenTelemetry / App Insights setup
│   │   ├── evaluation/      # Pipeline quality checks
│   │   │   ├── __init__.py
│   │   │   ├── deterministic.py # Rule-based checks
│   │   │   └── llm_judge.py     # LLM-as-judge evaluations
│   │   ├── core.py          # Wires interfaces → implementations (composition root)
│   │   ├── exceptions.py    # Custom domain exceptions (not models — control flow)
│   │   └── helpers.py       # Small stateless utilities
│   ├── prompts/             # LLM prompt templates
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/        # Sample data, LLM response mocks
│   ├── docs/
│   │   └── adr/             # Backend-specific ADRs
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                # React SPA
│   ├── src/
│   │   └── api/
│   │       └── generated/   # Auto-generated from OpenAPI spec
│   ├── public/
│   ├── scripts/
│   │   └── generate-api-types.sh  # Fetches openapi.json → TypeScript
│   ├── docs/
│   │   └── adr/             # Frontend-specific ADRs
│   ├── Dockerfile
│   └── package.json
├── infra/                   # Infrastructure as Code
│   ├── bicep/               # Azure Bicep templates
│   └── Makefile             # deploy, destroy, status commands
├── experiments/             # Ad-hoc notebooks, scripts, and explorations
├── Makefile                 # Root orchestration
├── docker-compose.yml       # Local dev environment
└── README.md
```

### CLEAN Architecture (Backend)

```
┌──────────────────────────────────────────────────────────────┐
│  runners/         Entry points (CLI, API, queue triggers)    │
│      │            Each with `if __name__ == "__main__":`     │
└──────┼───────────────────────────────────────────────────────┘
       │ uses
       ▼
┌──────────────────────────────────────────────────────────────┐
│  core.py          Composition root — wires dependencies      │
│                   Container class with interface bindings    │
└──────┼───────────────────────────────────────────────────────┘
       │ injects                              
       ▼                                      
┌──────────────────────────────────────────────────────────────┐
│  interfaces/      ABCs only — IClassifier, ICriteriaChecker, │
│                   IImagineer, IStorage, etc.                 │
└──────┬───────────────────────────────────────────────────────┘
       │ implemented by
       ▼
┌──────────────────────────────────────────────────────────────┐
│  services/        Concrete implementations with single       │
│                   responsibility (Azure SDK calls, LLM, etc) │
└──────┬───────────────────────────────────────────────────────┘
       │ operates on
       ▼
┌──────────────────────────────────────────────────────────────┐
│  models/          Pure data structures (Pydantic)            │
│                   No business logic, no side effects         │
└──────────────────────────────────────────────────────────────┘

helpers.py — stateless utilities used anywhere
exceptions.py — custom domain exceptions (control flow, not data models)
```

---

## Observability

All services share a **correlation ID** propagated via:
- HTTP header: `X-Correlation-ID`
- Queue message property: `correlation_id`
- Log field: `correlation_id`

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Frontend   │───▶│   API       │───▶│  Pipeline   │
│             │    │             │    │             │
│ X-Corr-ID   │    │ X-Corr-ID   │    │ X-Corr-ID   │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
               ┌─────────────────────┐
               │  Structured Logs    │
               │  (JSON, correlation │
               │   ID in every line) │
               └─────────────────────┘
```

Middleware in `observability/correlation.py` generates or extracts the ID and injects it into:
- Python `logging` context (via `contextvars`)
- Outgoing HTTP requests
- Queue messages

---

## CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml
on: [pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
      - name: Install dependencies
        run: make install
      - name: Lint
        run: make lint
      - name: Test
        run: make test
      - name: Generate OpenAPI spec
        run: make openapi
      - name: Verify TypeScript types are up-to-date
        run: make verify-api-types
```

Gates: PR cannot merge if lint or test fails.

---

## House Data Structure

Raw data and pipeline outputs are stored in **separate top-level directories** with mirrored structure.
This keeps immutable source data cleanly separated from regenerable artifacts.

```
input_data/                              # IMMUTABLE — scraper output
└── houses/
    └── house-slug/
        ├── listing.json                 # Schema.org metadata from Funda
        ├── listing.txt                  # Text description
        ├── url.txt                      # Source URL
        ├── screenshot.png               # Page screenshot
        └── photos/                      # Original images
            ├── 001.jpg
            ├── 002.jpg
            └── ...

outputs/                                 # REGENERABLE — pipeline artifacts
└── houses/
    └── house-slug/                    # Mirrors input_data/houses/<slug>
        ├── classifier/
        │   └── room_classifications.json   # Maps photos/*.jpg → room type
        ├── criteria/
        │   └── criteria_result.json
        ├── distance/
        │   └── distance_result.json
        └── imagineering/
            ├── summary.json             # Manifest of all runs
            └── kitchen_008/
                └── generated.png        # AI output (source ref in summary.json)
```

### Key Design Decisions

1. **Separate directories** — `input_data/` and `outputs/` are top-level siblings with mirrored `houses/<slug>/` structure

2. **No image duplication** — `outputs/` only contains:
   - JSON files with path references (e.g., `"source_image": "input_data/houses/Acacialaan_6/photos/008.jpg"`)
   - Generated images from imagineering
   - "Photos by room" is a query, not a folder — read `room_classifications.json`

3. **Idempotency** — Delete `outputs/` and re-run pipeline; raw data in `input_data/` untouched

3. **Prompt structure (simplified):**
   - **Style templates** (`backend/prompts/`) — shared across all houses (user's design preferences)
   - **No room descriptions needed** — FLUX.2-pro sees the input image directly via image-to-image
   - Model preserves room structure; prompt only specifies decoration/style changes
   - `guidance` parameter controls style adherence vs structure preservation

### input_data/houses/<slug>/listing.json schema (Schema.org format from scraper)
```json
{
  "@type": ["Appartement", "Product"],
  "name": "Acacialaan 6",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Acacialaan 6",
    "addressLocality": "Utrecht",
    "addressRegion": "Utrecht"
  },
  "offers": { "price": 450000, "priceCurrency": "EUR" },
  "photo": [{ "@type": "ImageObject", "contentUrl": "https://..." }]
}
```

### outputs/imagineering/summary.json schema
```json
{
  "house_slug": "Acacialaan_6",
  "model": "FLUX.2-pro",
  "guidance": 15,                              // Tuned via experiment
  "total_photos": 45,
  "results": [
    {
      "style_template": "kitchen",             // References backend/prompts/kitchen.md
      "room_type": "kitchen",
      "source_image": "input_data/houses/Acacialaan_6/photos/008.jpg",  // Input to FLUX (no copy)
      "confidence": 0.98,
      "generated_image": "outputs/houses/Acacialaan_6/imagineering/kitchen_008/generated.png"
    }
  ]
}
```

### backend/prompts/ (style templates)
```markdown
# kitchen.md
Transform into a pastel themed sweet heaven kitchen with baking supplies,
pastel cooking utensils in purple/blue/orange/pink on a rail,
color-coded jars, decorated cakes, and a kitchen island with baked goods.
Themed like a sweets laboratory. Keep room structure exactly as shown.
```

---

## API & TypeScript Generation

FastAPI exposes `/openapi.json`. Frontend build pipeline:

1. `make openapi` → exports `backend/openapi.json`
2. `npx openapi-typescript openapi.json -o src/api/generated/types.ts`
3. CI verifies generated types match committed version

This keeps frontend types in sync with backend at all times.

---

## Legacy Repo Mapping

| Legacy Repo | Maps To | Notes |
|-------------|---------|-------|
| `funda_llm` | `backend/` | AI pipeline logic, agents, services |
| `house_helper` | `backend/` | Merge with funda_llm (production features) |
| `house_helper_app/backend` | `backend/src/api/` | Thin API layer merged into backend |
| `house_helper_frontend` | `frontend/` | React SPA |
| `house_helper_app/infra` | `infra/` | Bicep templates |
| `funda_scrape/houses` | `data/` | Sample data structure |

---

## Out of Scope (Future)
- Scraping: data is assumed to exist externally
- Multi-scraper abstraction layer
- Prompt experimentation for architecture preservation
- SonarQube agent or pre-commit hook
Please write up an ADR under docs/ which is named 00-poetry-vs-uv.md and write up an ADR on which package manager we should use.
---

---

## Experiments Needed

### EXP-001: FLUX.2-pro Guidance Parameter Tuning

**Goal:** Find optimal `guidance` value balancing style adherence vs structure preservation.

**Setup:**
- Select 3 diverse rooms (kitchen, bedroom, living room) from different houses
- Apply same style template to each
- Generate at guidance values: `5, 10, 15, 20, 30, 50`

**Metrics:**
1. **Structure preservation** (manual 1-5): Do walls, windows, floor layout match?
2. **Style adherence** (manual 1-5): Are requested decorations/colors present?
3. **Realism** (manual 1-5): Does it look like a real room?

**Expected tradeoff:**
```
guidance=5  → Very close to original, minimal style changes
guidance=15 → Balanced (current default)
guidance=50 → Heavy style, may distort structure
```

**Output:** Recommended default guidance value + per-room-type adjustments if needed.

# TODO:
Make sure the structure is aligned with the ADR docs.