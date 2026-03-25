# House Helper

An AI-powered pipeline for evaluating real-estate listings and helping users visualize themselves in potential homes.

## What it does

Given scraped house data (photos + listing text), House Helper runs a multi-stage filtering pipeline:

1. **Text Criteria Check** — evaluates listing text against your written criteria (price, location, size, etc.) to filter out unsuitable houses early
2. **Room Classification** — for candidates that pass, classifies each photo by room type (kitchen, bedroom, garden, etc.) using an LLM
3. **Photo Criteria Check** — evaluates rooms against visual criteria (natural light, modern kitchen, garden size, etc.)
4. **Enrichment** (parallel on remaining candidates):
   - **Distance Calculator** — computes travel time to reference addresses via Azure Maps
   - **Imagineering** — generates AI-reimagined room photos using FLUX.2-pro with your personal design style

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Input: Scraped Houses                                      │
│  (photos + listing.json + listing.txt)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Text Criteria Check                               │
│  Filter houses based on written listing criteria            │
│  (price range, location, sqm, bedrooms, etc.)               │
└───────────────────────────┬─────────────────────────────────┘
                            │ candidates
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Room Classification                               │
│  Classify each photo → room type                            │
│  (kitchen, bedroom, bathroom, garden, etc.)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Photo Criteria Check                              │
│  Evaluate rooms against visual criteria                     │
│  (natural light, modern finishes, outdoor space, etc.)      │
└───────────────────────────┬─────────────────────────────────┘
                            │ finalists
                            ▼
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
┌───────────────────────┐       ┌───────────────────────┐
│  Distance Calculator  │       │  Imagineering         │
│  (Azure Maps)         │       │  (FLUX.2-pro)         │
│  Commute times to     │       │  Reimagine rooms in   │
│  key locations        │       │  your design style    │
└───────────────────────┘       └───────────────────────┘
          │                                   │
          └─────────────────┬─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Output: Enriched Candidates                                │
│  Ready for browsing in frontend                             │
└─────────────────────────────────────────────────────────────┘
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Data Layer                                                 │
│  • Local: houses/ folder with photos, listing.json, etc.    │
│  • Azure: Blob Storage + Table Storage                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Pipeline (Python)                                          │
│  ├─ Text Criteria Checker (filter early)                    │
│  ├─ Room Classifier (categorize photos)                     │
│  ├─ Photo Criteria Checker (visual evaluation)              │
│  ├─ Distance Calculator (commute times)                     │
│  ├─ Imagineering (FLUX.2-pro)                               │
│  └─ FastAPI serving processed data                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Frontend (React SPA)                                       │
│  • Browse houses, view criteria, compare photos             │
│  • Before/after slider for imagineered rooms                │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
house_helper/
├── input_data/              # Immutable scraper output (source of truth)
│   └── houses/
│       └── <house_slug>/    # Each house in its own folder
├── outputs/                 # Regenerable pipeline artifacts (gitignored)
│   └── houses/
│       └── <house_slug>/
├── backend/                 # AI pipeline + API (Python / uv)
│   ├── config/
│   │   └── criteria.yaml    # Pipeline criteria (text, photo, distance)
│   ├── prompts/             # LLM prompt templates
│   ├── src/
│   │   ├── config.py        # YAML config loader
│   │   ├── core.py          # Composition root — wires interfaces to services
│   │   ├── run.py           # CLI entry point for the full pipeline
│   │   ├── interfaces/      # ABCs / Protocols only (no implementation)
│   │   ├── services/        # Concrete implementations (one responsibility each)
│   │   ├── filters/         # Pipeline stage orchestrators
│   │   ├── models/          # Pydantic data structures
│   │   ├── api/             # FastAPI app (routes, models)
│   │   ├── runners/         # FilterPipeline runner
│   │   └── evaluation/      # Evaluation harness
│   └── tests/
├── frontend/                # React SPA (Vite + TypeScript)
├── infra/                   # Terraform templates (Azure)
├── experiments/             # One-off experiment notebooks/scripts
└── old/                     # Legacy repos (archived)
```

## House Data Structure

Input data and pipeline outputs are stored in separate top-level directories so raw scraped data is never mutated:

```
input_data/houses/<house_slug>/
├── metadata.json        # Listing metadata (price, address, sqm, etc.)
├── listing.txt          # Full text description
├── url.txt              # Source URL
├── screenshot.png       # Page screenshot
└── photos/              # Original images (001.jpg, 002.jpg, ...)

outputs/houses/<house_slug>/
├── room_classifications.json    # Stage 2 — room type per photo
├── photo_criteria.json          # Stage 3 — visual criteria results
└── criteria/
    └── filter_result.json       # Stage 1 — text criteria result
```

Imagineering outputs (Stage 4) are written alongside inputs as `outputs/houses/<house_slug>/imagineering/`.

## Quick Start

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and pnpm (for frontend)
- Azure OpenAI resource (for text filtering, room classification, photo evaluation)
- Azure Maps key (optional — enables commute-time calculations)
- Azure AI Foundry endpoint with FLUX.2-pro deployed (optional — enables imagineering)

### Setup

```bash
# Install all dependencies
make install

# Copy and fill in environment variables
cp backend/sample.env backend/.env
# Edit backend/.env with your API keys (see Environment Variables below)

# Run linters and tests
make lint
make test
```

### Running the pipeline

```bash
# Run all stages (text → classify → photo criteria → distance)
make pipeline

# Include the imagineering stage (calls FLUX.2-pro — costs money per image)
make pipeline IMAGINEERING=1
```

Results are written to `outputs/houses/`.

### Running the dev servers

```bash
# Start backend (port 8000) and frontend (port 5173) together
make dev

# Or individually
make dev-backend
make dev-frontend
```

### Docker

```bash
make docker-build     # Build images
make docker-up        # Start all services
make docker-down      # Stop all services
make backend-run      # Start only the backend container
make frontend-run     # Start only the frontend container
```

## Environment Variables

Copy `backend/sample.env` to `backend/.env` and set the following:

| Variable | Required | Description |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | ✅ | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | ✅ | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | ✅ | Deployment name (e.g. `gpt-4o`) |
| `AZURE_MAPS_KEY` | optional | Azure Maps subscription key — enables distance stage |
| `FLUX_API_KEY` | optional* | FLUX.2-pro API key — required for `--imagineering` |
| `FLUX_ENDPOINT` | optional* | FLUX.2-pro endpoint URL — required for `--imagineering` |
| `FLUX_GUIDANCE` | optional* | Guidance scale (e.g. `3.5`) — required for `--imagineering` |
| `FLUX_SEED` | optional | Fixed seed for reproducible imagineering runs |
| `CORS_ORIGINS` | optional | Comma-separated allowed origins (default: `http://localhost:5173`) |

\* All three `FLUX_*` vars are required together when the imagineering stage is enabled.

## License

MIT
