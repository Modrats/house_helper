"""IRoomClassifier abstract base class for room classification."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.classification import HouseClassifications


class IRoomClassifier(ABC):
    """Abstract base class for room classification operations."""

    @abstractmethod
    def classify_house(self, slug: str, *, batch_size: int) -> HouseClassifications:
        """Classify all photos for a single house.

        Args:
            slug: House identifier (folder name under input_dir/houses/).
            batch_size: Number of photos to process per batch.

        Returns:
            HouseClassifications with per-photo results.
        """
