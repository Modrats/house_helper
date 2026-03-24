"""Composition root — wires interfaces to concrete implementations."""

from .config import load_storage_paths
from .interfaces.data_source import IDataSource
from .services.house_repository import HouseRepository
from .services.local_storage import LocalStorage


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
