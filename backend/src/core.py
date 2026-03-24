"""Composition root — wires interfaces to concrete implementations."""

from __future__ import annotations

import os

from .config import load_distance_config, load_storage_paths
from .interfaces.data_source import IDataSource
from .interfaces.distance_calculator import IDistanceCalculator
from .interfaces.room_classifier import IRoomClassifier
from .services.azure_openai_service import AzureOpenAIService
from .services.distance_calculator import GoogleMapsDistanceCalculator
from .services.house_repository import HouseRepository
from .services.local_storage import LocalStorage
from .services.room_classifier import AzureOpenAIRoomClassifier


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


def create_distance_calculator() -> IDistanceCalculator:
    """Create a distance calculator wired to Google Maps and storage paths.

    Reads GOOGLE_MAPS_API_KEY from environment. Reads destinations from
    the distance section of criteria.yaml.

    Returns:
        A configured IDistanceCalculator implementation.

    Raises:
        RuntimeError: If GOOGLE_MAPS_API_KEY is not set.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: GOOGLE_MAPS_API_KEY")

    input_dir, output_dir = load_storage_paths()
    destinations = load_distance_config()
    return GoogleMapsDistanceCalculator(
        api_key=api_key,
        input_dir=input_dir,
        output_dir=output_dir,
        destinations=destinations,
    )
