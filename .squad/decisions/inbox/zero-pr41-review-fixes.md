# Decision: PR #41 Review Fixes — Zero

**Date:** 2026-03-24
**Author:** Zero
**Context:** Addressing 4 review comments from Terri on PR #41 "[Backend] FastAPI endpoints for frontend" (branch `squad/13-fastapi-endpoints`)

---

## Decisions Made

### 1. CORS headers must be explicit when credentials are enabled
**Decision:** `allow_headers=["*"]` is not allowed alongside `allow_credentials=True`. Using `["Content-Type", "Authorization"]` instead.
**Reason:** OWASP A05 — browsers reject wildcard headers with credentialed requests. Explicit allowlist is required.

### 2. `IDataSource` is a generic CRUD interface — no domain knowledge
**Decision:** `IDataSource` now defines 5 generic methods: `read_json`, `write_json`, `list_keys`, `read_bytes`, `exists`. It has no concept of houses, rooms, or pipeline stages.
**Reason:** Terri's feedback: "this service should be performing CRUD ... we shouldn't care if these are houses, especially at interface level."

### 3. `HouseRepository` owns all house-domain storage logic
**Decision:** Created `backend/src/services/house_repository.py`. It wraps `IDataSource` and provides `load_houses`, `save_filter_results`, `list_houses`, `get_house`, `get_photos`, `get_room_classifications`, `get_criteria_results`, `get_imagineered_photos`, `get_photo_bytes`, `get_imagineered_photo_bytes`.
**Reason:** Clear separation — repository owns path conventions and business logic; storage owns bytes.

### 4. Criteria drift detection moved from `LocalStorage` → `HouseRepository`
**Decision:** `_criteria_match` and `_restore_filter_state` now live in `HouseRepository`, not `LocalStorage`.
**Reason:** Terri's feedback: "a storage device/file CRUD service shouldn't be concerned with criteria_matching." This is business logic, not storage logic.

### 5. Photos served via API endpoints, not static directory mounts
**Decision:** Added `GET /api/houses/{slug}/photos/{filename}` and `GET /api/houses/{slug}/imagineered/{filename}`. Removed `StaticFiles` mounts from `app.py`.
**Reason:** Terri's feedback: "can we get these files from the apis instead of mounting them? this seems clunky to refact if we switch storage." Now only `HouseRepository` changes when backing storage changes.

### 6. `Settings` reads all env vars without defaults
**Decision:** `settings.py` reads `CORS_ORIGINS` via `os.environ["CORS_ORIGINS"]` — raises `KeyError` if missing.
**Reason:** Per team decision (2026-03-24): no hardcoded defaults for env vars.
