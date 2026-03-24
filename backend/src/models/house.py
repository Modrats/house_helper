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
    """Processing status of a house in the pipeline.

    Stages are ordered: each downstream stage can resume from
    the highest completed status.
    """

    RAW = "raw"  # Just scraped, no processing
    FILTERED = "filtered"  # Text/criteria filters applied
    CLASSIFIED = "classified"  # Photos classified into rooms
    EVALUATED = "evaluated"  # Criteria checked
    IMAGINEERED = "imagineered"  # AI images generated
    COMPLETE = "complete"  # All processing done


class FilterResult(BaseModel):
    """Per-criterion filter results organized by priority.

    p1: Must-have criteria — ALL must be True for the house to pass.
    p2: Nice-to-have criteria — at least ONE must be True (if any exist).
    excluded: Dealbreaker criteria — ALL must be False to pass.
    """

    p1: dict[str, bool] = Field(
        default_factory=dict,
        description="Must-have criteria (ALL must be True)",
    )
    p2: dict[str, bool] = Field(
        default_factory=dict,
        description="Nice-to-have criteria (at least ONE must be True)",
    )
    excluded: dict[str, bool] = Field(
        default_factory=dict,
        description="Dealbreaker criteria (ALL must be False)",
    )

    model_config = {"frozen": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        """True when all p1 match, at least one p2 matches, and no excluded match."""
        if any(self.excluded.values()):
            return False
        if self.p1 and not all(self.p1.values()):
            return False
        if self.p2 and not any(self.p2.values()):
            return False
        return True

    def merge(self, other: FilterResult) -> FilterResult:
        """Return a new FilterResult combining criteria from both."""
        return FilterResult(
            p1={**self.p1, **other.p1},
            p2={**self.p2, **other.p2},
            excluded={**self.excluded, **other.excluded},
        )


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
    filter_results: FilterResult = Field(
        default_factory=FilterResult,
        description="Per-criterion filter results organized by priority",
    )
    # Distance calculation results (destination -> minutes)
    distances: dict[str, int] = Field(
        default_factory=dict,
        description="Travel time to destinations (destination -> minutes)",
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

    def with_filter_result(self, result: FilterResult) -> House:
        """Return a new House with merged filter results."""
        merged = self.filter_results.merge(result)
        return self.model_copy(update={"filter_results": merged})

    def with_distance(self, destination: str, minutes: int) -> House:
        """Return a new House with an additional distance entry."""
        new_distances = {**self.distances, destination: minutes}
        return self.model_copy(update={"distances": new_distances})

    def with_status(self, status: HouseStatus) -> House:
        """Return a new House with updated status."""
        return self.model_copy(update={"status": status})
