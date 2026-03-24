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
