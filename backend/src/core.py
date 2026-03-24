"""Composition root — wires interfaces to concrete implementations."""

from __future__ import annotations

import os

from .config import load_storage_paths
from .interfaces.data_source import IDataSource
from .interfaces.room_classifier import IRoomClassifier
from .services.azure_openai_service import AzureOpenAIService
from .services.local_storage import LocalStorage
from .services.room_classifier import AzureOpenAIRoomClassifier


def create_storage() -> IDataSource:
    """Create a storage instance from config.

    Reads input/output paths from criteria.yaml storage section.
    Swap LocalStorage for AzureStorageService (or similar)
    when running in the cloud.

    Returns:
        A configured IDataSource implementation.
    """
    input_dir, output_dir = load_storage_paths()
    return LocalStorage(input_dir=input_dir, output_dir=output_dir)


def create_room_classifier() -> IRoomClassifier:
    """Create a room classifier wired to the LLM service and storage paths.

    Returns:
        A configured IRoomClassifier implementation.

    Raises:
        RuntimeError: If Azure OpenAI credentials are not configured.
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
