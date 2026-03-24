"""FastAPI application factory.

Creates and configures the app with CORS, static file serving,
routes, and OpenAPI documentation.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import load_storage_paths
from ..observability import get_logger
from ..settings import get_settings
from .routes import router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Build and return a configured FastAPI application.

    Wires up:
    - CORS middleware (origins from settings)
    - API routes
    - Static file mounts for house photos and pipeline outputs
    - OpenAPI metadata
    """
    settings = get_settings()
    input_dir, output_dir = load_storage_paths()

    app = FastAPI(
        title="House Helper API",
        description="Backend API for the House Helper pipeline — browse houses, rooms, and photos.",
        version="0.1.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(router)

    # Static file mounts for serving photos
    input_houses = input_dir
    output_houses = output_dir

    if input_houses.exists():
        app.mount(
            "/static/input",
            StaticFiles(directory=str(input_houses)),
            name="input-photos",
        )
    else:
        logger.warning("Input directory %s does not exist; skipping static mount", input_houses)

    if output_houses.exists():
        app.mount(
            "/static/output",
            StaticFiles(directory=str(output_houses)),
            name="output-photos",
        )
    else:
        logger.warning("Output directory %s does not exist; skipping static mount", output_houses)

    logger.info("House Helper API ready — docs at /docs")
    return app
