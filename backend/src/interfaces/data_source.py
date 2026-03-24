"""IDataSource abstract base class for storage abstraction.

Allows swapping between local filesystem and Azure Blob/Table Storage
without changing pipeline code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.house import House


class IDataSource(ABC):
    """Abstract base class for storage operations.

    Abstracts storage backend (local filesystem vs Azure Blob/Table Storage).
    Implementations handle reading houses and persisting pipeline outputs.

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

    async def get_all_houses_async(self) -> list[House]:
        """Async version of get_all_houses.

        Returns:
            List of all houses with metadata.
        """
        ...
