"""Composition root — wires interfaces to concrete implementations."""

from __future__ import annotations

import os

from .config import load_photo_criteria, load_storage_paths
from .interfaces.data_source import IDataSource
from .interfaces.filter import IFilter
from .interfaces.imagineering import IImagineeringService
from .interfaces.photo_checker import IPhotoChecker
from .interfaces.room_classifier import IRoomClassifier
from .services.azure_openai_service import AzureOpenAIService
from .services.house_repository import HouseRepository
from .services.imagineering_service import FluxImagineeringService
from .services.local_storage import LocalStorage
from .services.photo_checker import VisionPhotoChecker
from .services.room_classifier import AzureOpenAIRoomClassifier
from .services.text_filter_service import LLMTextFilterService


def create_storage() -> IDataSource:
    """Create a generic storage backend.

    Swap LocalStorage for a cloud implementation (e.g. AzureStorageService)
    when running in the cloud.

    Returns:
        A configured IDataSource implementation.
    """
    return LocalStorage()


def create_repository() -> HouseRepository:
    """Create a HouseRepository wired to local storage.

    Reads input/output paths from criteria.yaml storage section.
    The repository wraps the storage backend with house-domain logic.

    Returns:
        A configured HouseRepository for house-specific operations.
    """
    input_dir, output_dir = load_storage_paths()
    return HouseRepository(create_storage(), input_dir, output_dir)


def create_room_classifier() -> IRoomClassifier:
    """Create a room classifier wired to the LLM service and storage paths.

    Returns:
        A configured IRoomClassifier implementation.

    Raises:
        MissingConfigError: If Azure OpenAI credentials are not configured.
    """
    llm_service = AzureOpenAIService()
    input_dir, output_dir = load_storage_paths()
    batch_size = int(os.environ.get("ROOM_CLASSIFIER_BATCH_SIZE", "5"))
    return AzureOpenAIRoomClassifier(
        llm_service=llm_service,
        input_dir=input_dir,
        output_dir=output_dir,
        batch_size=batch_size,
    )


def create_imagineering_service() -> IImagineeringService:
    """Create an imagineering service wired to FLUX.2-pro and storage paths.

    Reads FLUX_API_KEY, FLUX_ENDPOINT, and FLUX_GUIDANCE from environment
    variables. All three are required — missing values raise RuntimeError.
    FLUX_SEED is optional (defaults to random per-image).

    Returns:
        A configured IImagineeringService implementation.

    Raises:
        RuntimeError: If required FLUX environment variables are missing.
    """
    missing = [
        name
        for name in ("FLUX_API_KEY", "FLUX_ENDPOINT", "FLUX_GUIDANCE")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    input_dir, output_dir = load_storage_paths()
    seed_raw = os.environ.get("FLUX_SEED")
    return FluxImagineeringService(
        api_key=os.environ["FLUX_API_KEY"],
        endpoint=os.environ["FLUX_ENDPOINT"],
        input_dir=input_dir,
        output_dir=output_dir,
        guidance=float(os.environ["FLUX_GUIDANCE"]),
        default_seed=int(seed_raw) if seed_raw is not None else None,
    )


def create_llm_text_filter() -> IFilter:
    """Create an LLM-based text filter wired to Azure OpenAI and storage paths.

    Returns:
        A configured IFilter implementation for LLM text analysis.

    Raises:
        MissingConfigError: If Azure OpenAI credentials are not configured.
    """
    llm_service = AzureOpenAIService()
    _, output_dir = load_storage_paths()
    return LLMTextFilterService(
        llm_service=llm_service,
        output_dir=output_dir,
    )


def create_photo_checker() -> IPhotoChecker:
    """Create a photo criteria checker wired to the LLM service and storage paths.

    Returns:
        A configured IPhotoChecker implementation.

    Raises:
        MissingConfigError: If Azure OpenAI credentials are not configured.
        KeyError: If photo_criteria section is missing from config.
    """
    llm_service = AzureOpenAIService()
    input_dir, output_dir = load_storage_paths()
    criteria = load_photo_criteria()
    return VisionPhotoChecker(
        llm_service=llm_service,
        input_dir=input_dir,
        output_dir=output_dir,
        criteria=criteria,
    )
