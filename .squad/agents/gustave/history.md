# Project Context

- **Owner:** Terri Modrakowski
- **Project:** House Helper Pipeline — refactoring a house visualization pipeline that helps users narrow down house choices and visualize rooms reimagined to their taste using AI (FLUX.2-pro).
- **Stack:** Python (FastAPI, Pydantic), React (TypeScript), Azure (Blob Storage, Table Storage, Container Apps, Bicep), FLUX.2-pro (image generation), Azure OpenAI
- **Architecture:** CLEAN architecture — interfaces/ (ABCs), services/ (implementations), models/ (Pydantic), runners/ (entry points), core.py (composition root)
- **Migration:** Merging 5 legacy repos (funda_llm, house_helper, house_helper_app, house_helper_frontend, funda_scrape) into one monorepo
- **Created:** 2026-03-23

## Learnings

<!-- Append new learnings below. Each entry is something lasting about the project. -->
