# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (pytest), test fixtures for LLM responses, deterministic + LLM-as-judge evaluation harness
- **Key test areas:** Room classifier accuracy, criteria checker logic, distance calculations, imagineering output validation, API endpoints, data model integrity
- **Created:** 2026-03-23

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->

### 2026-03-24: NamedTuple + parametrize refactor (Issue #28)

- **Pattern adopted:** All test files now use `NamedTuple`-based test cases with `@pytest.mark.parametrize`. No more class-based `TestX` groupings.
- **Module-level helper classes:** Filter helper classes (PassAllFilter, RejectAllFilter, etc.) live at module level, NOT inside NamedTuples or test functions.
- **Fixture → module constant:** pytest fixtures that created shared data (e.g., `sample_houses`) were replaced with module-level constants (`SAMPLE_HOUSES`).
- **Inner classes → module level:** Classes defined inside test methods (FilterA, FilterB, IncompleteFilter, CompleteFilter) were promoted to module scope so they can be referenced from NamedTuple fields.
- **Single-field NamedTuples are fine:** For tests with no meaningful inputs, a 2-field NamedTuple (`description` + one semantic field like `expected_count`) avoids ambiguity with pytest's 1-tuple unpacking.
- **`test_placeholder.py` removed:** Contained only a trivial `assert True` — no real coverage contribution.
- **All 29 tests passed** after refactor (was 30 including placeholder).
