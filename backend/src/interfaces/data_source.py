"""IDataSource protocol for storage abstraction.

Allows swapping between local filesystem and Azure Blob/Table Storage
without changing pipeline code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models.house import House


class IDataSource(Protocol):
    """Protocol for data source operations.

    Abstracts storage backend (local filesystem vs Azure Blob/Table Storage).
    Implementations should handle reading houses, photos, and metadata.

    Example implementations:
        - LocalStorageService: Reads from local houses/ folder structure
        - AzureStorageService: Reads from Azure Blob + Table Storage
    """

    def get_house(self, slug: str) -> House:
        """Load a house by its slug.

        Args:
            slug: Unique identifier for the house (folder name).

        Returns:
            House model with all metadata loaded.

        Raises:
            HouseNotFoundError: If the house doesn't exist.
        """
        ...

    def get_all_houses(self) -> list[House]:
        """Load all houses from the data source.

        Returns:
            List of all houses with metadata.
        """
        ...

    def get_photo_path(self, slug: str, photo_name: str) -> Path:
        """Get the path to a specific photo.

        Args:
            slug: House slug identifier.
            photo_name: Name of the photo file.

        Returns:
            Path to the photo (local path or temp file for Azure).
        """
        ...

    def get_listing_text(self, slug: str) -> str:
        """Get the listing text for a house.

        Args:
            slug: House slug identifier.

        Returns:
            Full text of the listing description.
        """
        ...

    async def get_house_async(self, slug: str) -> House:
        """Async version of get_house for parallel loading.

        Args:
            slug: Unique identifier for the house.

        Returns:
            House model with all metadata loaded.
        """
        ...

    async def get_all_houses_async(self) -> list[House]:
        """Async version of get_all_houses.

        Returns:
            List of all houses with metadata.
        """
        ...
