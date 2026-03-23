"""House model - the core entity in the pipeline.

A house represents a property listing with all its metadata, photos,
rooms, and pipeline processing results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field

from .room import Photo, Room, RoomType


class HouseStatus(str, Enum):
    """Processing status of a house in the pipeline."""

    RAW = "raw"  # Just scraped, no processing
    CLASSIFIED = "classified"  # Photos classified into rooms
    EVALUATED = "evaluated"  # Criteria checked
    IMAGINEERED = "imagineered"  # AI images generated
    COMPLETE = "complete"  # All processing done


class HouseMetadata(BaseModel):
    """Metadata about a house listing.

    Contains structured data extracted from the listing or Schema.org.
    """

    address: str | None = Field(default=None, description="Full street address")
    city: str | None = Field(default=None, description="City name")
    postal_code: str | None = Field(default=None, description="Postal code")
    price: int | None = Field(default=None, ge=0, description="Listing price in euros")
    living_area_m2: int | None = Field(default=None, ge=0, description="Living area in m²")
    plot_area_m2: int | None = Field(default=None, ge=0, description="Plot area in m²")
    num_rooms: int | None = Field(default=None, ge=0, description="Number of rooms")
    year_built: int | None = Field(default=None, description="Year the house was built")
    listing_url: str | None = Field(default=None, description="URL of the original listing")
    listing_date: datetime | None = Field(default=None, description="Date listed")

    model_config = {"frozen": True}


class House(BaseModel):
    """A house listing with all associated data.

    This is the primary entity flowing through the pipeline.
    Starts with raw data and gets enriched at each stage.
    """

    slug: str = Field(description="Unique identifier (folder name)")
    metadata: HouseMetadata = Field(
        default_factory=HouseMetadata,
        description="Structured listing metadata",
    )
    listing_text: str = Field(
        default="",
        description="Full text description from listing",
    )

    # Photos and rooms
    photos: list[Photo] = Field(
        default_factory=list,
        description="All photos of the house",
    )
    rooms: list[Room] = Field(
        default_factory=list,
        description="Rooms identified from photos",
    )

    # Pipeline status
    status: HouseStatus = Field(
        default=HouseStatus.RAW,
        description="Current processing status",
    )

    # Filtering results
    filter_results: dict[str, bool] = Field(
        default_factory=dict,
        description="Results from each filter (filter_name -> passed)",
    )
    filter_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric scores from filters (for ranking)",
    )
    excluded_by: str | None = Field(
        default=None,
        description="Name of filter that excluded this house (if any)",
    )

    # Distance calculation results
    commute_minutes: int | None = Field(
        default=None,
        ge=0,
        description="Calculated commute time in minutes",
    )
    commute_destination: str | None = Field(
        default=None,
        description="Destination used for commute calculation",
    )

    model_config = {"frozen": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_count(self) -> int:
        """Total number of photos."""
        return len(self.photos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def room_count(self) -> int:
        """Number of identified rooms."""
        return len(self.rooms)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bedroom_count(self) -> int:
        """Number of bedrooms identified."""
        return sum(1 for room in self.rooms if room.room_type == RoomType.BEDROOM)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_garden(self) -> bool:
        """Whether a garden was detected."""
        return any(room.room_type == RoomType.GARDEN for room in self.rooms)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_balcony(self) -> bool:
        """Whether a balcony was detected."""
        return any(room.room_type == RoomType.BALCONY for room in self.rooms)

    def passed_all_filters(self) -> bool:
        """Check if the house passed all applied filters."""
        return all(self.filter_results.values()) if self.filter_results else True

    def with_filter_result(self, filter_name: str, passed: bool) -> House:
        """Return a new House with an additional filter result.

        Since House is frozen, this creates a copy with updated results.
        """
        new_results = {**self.filter_results, filter_name: passed}
        return self.model_copy(
            update={
                "filter_results": new_results,
                "excluded_by": filter_name
                if not passed and self.excluded_by is None
                else self.excluded_by,
            }
        )

    def with_filter_score(self, filter_name: str, score: float) -> House:
        """Return a new House with an additional filter score."""
        new_scores = {**self.filter_scores, filter_name: score}
        return self.model_copy(update={"filter_scores": new_scores})

    def with_status(self, status: HouseStatus) -> House:
        """Return a new House with updated status."""
        return self.model_copy(update={"status": status})
