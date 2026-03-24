"""IFilter protocol for house filtering pipeline.

Filters take a list of houses and return filtered results.
Each filter implementation focuses on a single concern (text matching,
room classification, photo checking, distance, etc.).

Filters are criteria-agnostic. Criteria are defined in YAML config
and passed as a dict to each filter.
"""

from __future__ import annotations

from typing import Any, Protocol

from ..models.house import House


class IFilter(Protocol):
    """Protocol for house filtering operations.

    Implementations should focus on a single filtering concern.
    Filters can be chained in a pipeline for complex filtering.
    Criteria are loaded from YAML and passed as a generic dict.

    Example implementations:
        - TextFilter: Filters by keywords in listing text
        - RoomClassifierFilter: Filters by room types detected in photos
        - DistanceFilter: Filters by commute time
        - PhotoCheckerFilter: Filters by features detected in photos
    """

    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> list[House]:
        """Filter houses based on criteria.

        Args:
            houses: List of houses to filter.
            criteria: Filtering criteria loaded from YAML config.

        Returns:
            Filtered list of houses that match the criteria.
        """
        ...

    async def filter_async(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> list[House]:
        """Async version of filter for parallel processing.

        Args:
            houses: List of houses to filter.
            criteria: Filtering criteria loaded from YAML config.

        Returns:
            Filtered list of houses that match the criteria.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name for this filter."""
        ...
