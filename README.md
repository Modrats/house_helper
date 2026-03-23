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
├── input_data/              # Sample house data
│   └── houses/
│       └── <house_slug>/    # Each house in its own folder
├── pipeline/                # AI pipeline + API (Python)
│   ├── src/
│   │   ├── interfaces/      # ABCs and Protocols
│   │   ├── services/        # Concrete implementations
│   │   ├── models/          # Pydantic data structures
│   │   ├── api/             # FastAPI routes
│   │   └── runners/         # Entry points (CLI, API, queue)
│   ├── prompts/             # LLM prompt templates
│   └── tests/
├── frontend/                # React SPA
├── infra/                   # Bicep/Terraform templates
└── old/                     # Legacy repos (being migrated)
```

## House Data Structure

Each house is stored in a folder named by slug (address with underscores):

```
houses/
└── house_1/
    ├── raw/                         # Immutable scraper output
    │   ├── listing.json             # Schema.org metadata
    │   ├── listing.txt              # Text description
    │   ├── url.txt                  # Source URL
    │   ├── screenshot.png           # Page screenshot
    │   └── photos/                  # Original images
    │       └── 001.jpg, 002.jpg...
    │
    └── outputs/                     # Regenerable pipeline artifacts
        ├── classifier/
        │   └── room_classifications.json
        ├── criteria/
        │   └── criteria_result.json
        ├── distance/
        │   └── distance_result.json
        └── imagineering/
            ├── summary.json
            └── kitchen_001/
                └── generated.png
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ (for frontend)
- API keys for Azure OpenAI, Azure Maps, and Azure AI Foundry (FLUX)

### Setup

```bash
TBD
```

## License

MIT
