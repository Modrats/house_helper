"""IDistanceCalculator abstract base class for travel time calculation."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.distance import DistanceResult


class IDistanceCalculator(ABC):
    """Abstract base class for distance/travel-time calculation."""

    @abstractmethod
    def calculate_distances(self, slug: str) -> DistanceResult:
        """Calculate travel times from a house to all configured destinations.

        Reads the house address from input data, queries a distance/transit API,
        and writes results to the output directory.

        Args:
            slug: House identifier (folder name under input_dir/houses/).

        Returns:
            DistanceResult with per-destination travel times.
        """
