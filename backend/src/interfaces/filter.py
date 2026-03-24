"""IFilter protocol for house filtering pipeline.

Filters take a list of houses and criteria, returning filtered results.
Each filter implementation focuses on a single concern (text matching,
room classification, photo checking, distance, etc.).
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from ..models.house import House


class FilterCriteria(BaseModel):
    """Criteria for filtering houses.

    This is a base criteria model that can be extended by specific
    filter implementations. Contains common filtering parameters.
    """

    # Text-based criteria
    must_have_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that must appear in listing text",
    )
    must_not_have_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that must NOT appear in listing text",
    )

    # Room requirements
    min_bedrooms: int | None = Field(
        default=None,
        ge=0,
        description="Minimum number of bedrooms",
    )
    required_room_types: list[str] = Field(
        default_factory=list,
        description="Room types that must be present (e.g., 'kitchen', 'bathroom')",
    )

    # Location criteria
    max_commute_minutes: int | None = Field(
        default=None,
        ge=0,
        description="Maximum commute time in minutes",
    )
    commute_destination: str | None = Field(
        default=None,
        description="Destination address for commute calculation",
    )

    # Price criteria
    max_price: int | None = Field(
        default=None,
        ge=0,
        description="Maximum price in euros",
    )
    min_price: int | None = Field(
        default=None,
        ge=0,
        description="Minimum price in euros",
    )

    # Photo-based criteria
    must_have_garden: bool | None = Field(
        default=None,
        description="Whether the house must have a garden (detected from photos)",
    )
    must_have_balcony: bool | None = Field(
        default=None,
        description="Whether the house must have a balcony",
    )

    model_config = {"extra": "allow"}  # Allow extension with custom criteria


class IFilter(Protocol):
    """Protocol for house filtering operations.

    Implementations should focus on a single filtering concern.
    Filters can be chained in a pipeline for complex filtering.

    Example implementations:
        - TextFilter: Filters by keywords in listing text
        - RoomClassifierFilter: Filters by room types detected in photos
        - DistanceFilter: Filters by commute time
        - PhotoCheckerFilter: Filters by features detected in photos
    """

    def filter(
        self,
        houses: list[House],
        criteria: FilterCriteria,
    ) -> list[House]:
        """Filter houses based on criteria.

        Args:
            houses: List of houses to filter.
            criteria: Filtering criteria to apply.

        Returns:
            Filtered list of houses that match the criteria.
        """
        ...

    async def filter_async(
        self,
        houses: list[House],
        criteria: FilterCriteria,
    ) -> list[House]:
        """Async version of filter for parallel processing.

        Args:
            houses: List of houses to filter.
            criteria: Filtering criteria to apply.

        Returns:
            Filtered list of houses that match the criteria.
        """
        ...

    @property
    def name(self) -> str:
        """Human-readable name for this filter."""
        ...
