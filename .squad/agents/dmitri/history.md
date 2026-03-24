# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (FastAPI, Pydantic), React (TypeScript), Azure (Blob Storage, Table Storage, Container Apps, Bicep), FLUX.2-pro (image generation), Azure OpenAI
- **Architecture:** CLEAN architecture — interfaces/ (ABCs), services/ (implementations), models/ (Pydantic), runners/ (entry points), core.py (composition root)
- **Evaluation scope:** 4 pipeline components — Text Filter (keyword, LLM upgrade planned), Photo Classifier, Criteria Evaluator, Imagineering. See `backend/src/evaluation/README.md` for full metrics and success criteria.
- **Ground truth:** JSON fixture files in `backend/tests/fixtures/`, schemas as Pydantic models in `backend/src/evaluation/`
- **Created:** 2026-03-24

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->
