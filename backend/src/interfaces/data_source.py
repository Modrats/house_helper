"""IDataSource abstract base class for storage abstraction.

Allows swapping between local filesystem and Azure Blob/Table Storage
without changing pipeline code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.house import FilterResult, House


class IDataSource(ABC):
    """Abstract base class for storage operations.

    Abstracts storage backend (local filesystem vs Azure Blob/Table Storage).
    Implementations handle reading houses and persisting pipeline outputs.

    Provides two categories of methods:
        - Pipeline methods: load_houses, save_filter_results (batch processing)
        - Query methods: list_houses, get_house, get_photos, etc. (API layer)

    Example implementations:
        - LocalStorage: Reads from local houses/ folder structure
        - AzureStorageService: Reads from Azure Blob + Table Storage
    """

    @abstractmethod
    def load_houses(self, criteria: dict[str, Any]) -> list[House]:
        """Load all houses, restoring status from existing outputs.

        Args:
            criteria: Current filter criteria from config, used to detect drift.

        Returns:
            List of houses with status restored from any prior outputs.
        """

    @abstractmethod
    def save_filter_results(self, houses: list[House]) -> None:
        """Write filter results for each house.

        Args:
            houses: Houses with filter_results populated by the pipeline.
        """

    # -- Query methods (API layer) --------------------------------------------

    @abstractmethod
    def list_houses(self) -> list[str]:
        """List all available house slugs.

        Returns:
            Sorted list of house slug strings.
        """

    @abstractmethod
    def get_house(self, slug: str) -> House:
        """Load a single house with its metadata, listing text, and photos.

        Args:
            slug: House identifier (directory name).

        Returns:
            Fully populated House model.

        Raises:
            FileNotFoundError: If the house slug does not exist.
        """

    @abstractmethod
    def get_photos(self, slug: str) -> list[str]:
        """Get absolute file paths for all photos of a house.

        Args:
            slug: House identifier.

        Returns:
            List of absolute file path strings for supported image files.

        Raises:
            FileNotFoundError: If the house slug does not exist.
        """

    @abstractmethod
    def get_room_classifications(self, slug: str) -> dict[str, list[str]]:
        """Get room-to-photo mappings from classifier output.

        Args:
            slug: House identifier.

        Returns:
            Mapping of room type string to list of photo filenames.
            Empty dict if no classification output exists yet.
        """

    @abstractmethod
    def get_criteria_results(self, slug: str) -> FilterResult:
        """Get criteria pass/fail results from pipeline output.

        Args:
            slug: House identifier.

        Returns:
            FilterResult with p1/p2/excluded results.
            Empty FilterResult if no criteria output exists yet.
        """

    @abstractmethod
    def get_imagineered_photos(self, slug: str) -> list[str]:
        """Get absolute file paths for imagineered (AI-reimagined) photos.

        Args:
            slug: House identifier.

        Returns:
            List of absolute file path strings for imagineered images.
            Empty list if no imagineered output exists yet.
        """
