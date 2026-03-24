"""Room and photo models.

Rooms are logical groupings of photos within a house. Room types
are determined by the classifier service based on photo analysis.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RoomType(str, Enum):
    """Types of rooms that can be classified from photos."""

    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    TOILET = "toilet"
    HALLWAY = "hallway"
    GARDEN = "garden"
    BALCONY = "balcony"
    GARAGE = "garage"
    STORAGE = "storage"
    OFFICE = "office"
    DINING_ROOM = "dining_room"
    LAUNDRY = "laundry"
    BASEMENT = "basement"
    ATTIC = "attic"
    EXTERIOR = "exterior"
    FLOOR_PLAN = "floor_plan"
    OTHER = "other"
    UNKNOWN = "unknown"


class Photo(BaseModel):
    """A single photo of a house or room."""

    filename: str = Field(description="Original filename of the photo")
    path: str = Field(description="Relative path within the house folder")

    # Classifier outputs (populated after classification)
    room_type: RoomType | None = Field(
        default=None,
        description="Detected room type from classifier",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Classification confidence score",
    )

    # Features found while evaluating criteria (populated by the criteria evaluator).
    detected_features: list[str] = Field(
        default_factory=list,
        description="Features observed while evaluating criteria (e.g., 'dishwasher_present').",
    )

    # Imagineering outputs
    imagineered_path: str | None = Field(
        default=None,
        description="Path to AI-reimagined version of this photo",
    )

    model_config = {"frozen": True}


class Room(BaseModel):
    """A room within a house, containing one or more photos."""

    room_type: RoomType = Field(description="Type of room")
    photos: list[Photo] = Field(
        default_factory=list,
        description="Photos of this room",
    )

    # Aggregated features from all photos
    features: list[str] = Field(
        default_factory=list,
        description="Aggregated features from all photos in this room",
    )

    # Criteria evaluation results
    meets_criteria: bool | None = Field(
        default=None,
        description="Whether this room meets user criteria",
    )
    criteria_notes: str | None = Field(
        default=None,
        description="Notes about criteria evaluation",
    )

    model_config = {"frozen": True}

    @property
    def photo_count(self) -> int:
        """Number of photos in this room."""
        return len(self.photos)
