# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (FastAPI, Pydantic), React (TypeScript), Azure (Blob Storage, Table Storage, Container Apps, Bicep), FLUX.2-pro (image generation), Azure OpenAI
- **Architecture:** CLEAN architecture — interfaces/ (ABCs), services/ (implementations), models/ (Pydantic), runners/ (entry points), core.py (composition root)
- **Key services:** Room classifier, criteria checker, distance calculator, imagineering (FLUX.2-pro), local/Azure storage adapters
- **Created:** 2026-03-23

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-24: PR #40 Revision — Room Classifier Refactor

- **ILLMService interface** created at `interfaces/llm_service.py` — single LLM integration point per ADR-004. Two methods: `classify_image` (vision+structured) and `complete_structured` (text+structured). All LLM consumers should depend on this, never on `openai` directly.
- **IRoomClassifier interface** created at `interfaces/room_classifier.py` — ABC with `classify_house(slug, *, batch_size)`.
- **AzureOpenAIService** at `services/azure_openai_service.py` — the ONLY file that imports `openai`. Constructor reads env vars (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`) and raises `RuntimeError` if any are missing. `_call_api` is the VCR mocking boundary.
- **AzureOpenAIRoomClassifier** replaces `RoomClassifier`. Takes `ILLMService` + paths + batch_size (no Settings dependency). Decomposed into `_discover_photos`, `_load_previous_results`, `_classify_batch`. Uses structured output — no manual JSON parsing.
- **_VisionResponse** internal model in room_classifier.py — lightweight Pydantic model with just `room_type`/`confidence` for structured output. Avoids sending `filename` schema to the LLM.
- **settings.py deleted** — env var handling moved to `AzureOpenAIService` (service-level) and `core.py` (composition root for batch_size default). `pydantic-settings` removed from deps.
- **Removed deps**: `fastapi`, `uvicorn`, `opentelemetry-api`, `opentelemetry-sdk`, `pydantic-settings`.
- **Observability module** doesn't exist as source on this branch — only stale `__pycache__`. Replaced with stdlib `logging`.
- **Composition root** (`core.py`): `create_room_classifier()` now constructs `AzureOpenAIService`, gets paths from `load_storage_paths()`, batch_size from `ROOM_CLASSIFIER_BATCH_SIZE` env var (default "5"), returns `IRoomClassifier`.
- **ruff** is in the `dev` dependency group — run via `uv run --group dev ruff check src/`.
