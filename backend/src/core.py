"""Composition root — wires interfaces to concrete implementations."""

from .config import load_storage_paths
from .interfaces.data_source import IDataSource
from .services.local_storage import LocalStorage


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
