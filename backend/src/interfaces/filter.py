"""IFilter abstract base class for house filtering pipeline.

Filters take a list of houses and return filtered results.
Each filter implementation focuses on a single concern (text matching,
room classification, photo checking, distance, etc.).

Filters are criteria-agnostic. Criteria are defined in YAML config
and passed as a dict to each filter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.house import FilterResult, House


class IFilter(ABC):
    """Abstract base class for house filtering operations.

    Implementations should focus on a single filtering concern.
    Filters can be chained in a pipeline for complex filtering.
    Criteria are loaded from YAML and passed as a generic dict.

    Each filter evaluates houses and returns per-criterion results
    organized into P1 (must-have), P2 (nice-to-have), and excluded
    (dealbreaker) buckets via FilterResult.

    Example implementations:
        - TextFilter: Filters by keywords in listing text
        - RoomClassifierFilter: Filters by room types detected in photos
        - DistanceFilter: Filters by commute time
        - PhotoCheckerFilter: Filters by features detected in photos
    """

    @abstractmethod
    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> dict[str, FilterResult]:
        """Evaluate houses against criteria.

        Args:
            houses: List of houses to evaluate.
            criteria: Filtering criteria loaded from YAML config.

        Returns:
            Mapping of slug -> FilterResult with per-criterion matches.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this filter."""
