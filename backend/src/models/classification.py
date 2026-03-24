"""Room classification result models.

Pure data structures for photo classification outputs.
Used by the room classifier service to represent per-photo
and per-house classification results.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .room import RoomType


class PhotoClassification(BaseModel):
    """Classification result for a single photo."""

    filename: str = Field(description="Photo filename")
    room_type: RoomType = Field(description="Classified room type")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score (0.0–1.0)",
    )

    model_config = {"frozen": True}


class HouseClassifications(BaseModel):
    """All classification results for a single house."""

    slug: str = Field(description="House identifier")
    classifications: list[PhotoClassification] = Field(
        default_factory=list,
        description="Per-photo classification results",
    )

    model_config = {"frozen": True}

    def to_summary_dict(self) -> dict[str, str]:
        """Return a {filename: room_type} mapping for serialization."""
        return {c.filename: c.room_type.value for c in self.classifications}

    def to_detailed_dict(self) -> list[dict[str, str | float]]:
        """Return a list of dicts with filename, room_type, and confidence."""
        return [
            {
                "filename": c.filename,
                "room_type": c.room_type.value,
                "confidence": c.confidence,
            }
            for c in self.classifications
        ]
