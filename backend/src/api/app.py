"""FastAPI application factory.

Creates and configures the app with CORS, routes, and OpenAPI documentation.
Photos are served through the API layer (see routes.py) rather than
mounted static directories, so swapping storage backends only requires
changing the storage service — not the API surface.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..observability import get_logger
from ..settings import get_settings
from .routes import router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application.

    Wires up:
    - CORS middleware (origins from CORS_ORIGINS env var)
    - API routes (including photo-serving endpoints)
    - OpenAPI metadata
    """
    settings = get_settings()

    app = FastAPI(
        title="House Helper API",
        description="Backend API for the House Helper pipeline — browse houses, rooms, and photos.",
        version="0.1.0",
    )

    # CORS — explicit header list required when credentials are enabled.
    # Using allow_headers=["*"] with allow_credentials=True is an OWASP A05
    # security issue: when credentials are present, browsers require explicit
    # header names rather than the wildcard. Origins are read from the
    # CORS_ORIGINS environment variable (comma-separated list).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Routes (photos are served via /api/houses/{slug}/photos/{filename})
    app.include_router(router)

    logger.info("House Helper API ready — docs at /docs")
    return app
