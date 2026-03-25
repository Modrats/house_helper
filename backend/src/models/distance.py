"""Distance calculation result models.

Pure data structures for travel-time outputs.
Used by the distance calculator service to represent per-destination
and per-house distance results.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TravelTime(BaseModel):
    """Travel time result for a single destination and mode."""

    destination_name: str = Field(description="Name of the destination")
    destination_address: str = Field(description="Address queried")
    mode: str = Field(description="Travel mode (driving, transit, cycling, walking)")
    duration_minutes: int = Field(ge=0, description="Travel time in minutes")
    duration_text: str = Field(description="Human-readable duration (e.g. '25 mins')")

    model_config = {"frozen": True}


class DistanceResult(BaseModel):
    """All distance results for a single house."""

    slug: str = Field(description="House identifier")
    origin_address: str = Field(default="", description="Resolved origin address")
    destinations: list[TravelTime] = Field(
        default_factory=list,
        description="Per-destination travel time results",
    )

    model_config = {"frozen": True}

    def to_summary_dict(self) -> dict[str, int]:
        """Return a {destination_name (mode): duration_minutes} mapping."""
        return {f"{d.destination_name} ({d.mode})": d.duration_minutes for d in self.destinations}

    def to_detailed_dict(self) -> list[dict[str, str | int]]:
        """Return a list of dicts with all travel time fields."""
        return [
            {
                "destination_name": d.destination_name,
                "destination_address": d.destination_address,
                "mode": d.mode,
                "duration_minutes": d.duration_minutes,
                "duration_text": d.duration_text,
            }
            for d in self.destinations
        ]
