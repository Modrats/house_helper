"""Imagineering result models.

Pure data structures for FLUX.2-pro image generation outputs.
Used by the imagineering service to represent per-photo
and per-house generation results.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImagineeringPhoto(BaseModel):
    """Generation result for a single photo."""

    filename: str = Field(description="Original photo filename")
    room_type: str = Field(description="Classified room type")
    prompt_used: str = Field(description="FLUX prompt used for generation")
    guidance_value: float = Field(description="Guidance scale used")
    output_path: str = Field(description="Relative path to generated image")
    timestamp: str = Field(description="ISO 8601 generation timestamp")

    model_config = {"frozen": True}


class ImagineeringResult(BaseModel):
    """All imagineering results for a single house."""

    slug: str = Field(description="House identifier")
    photos: list[ImagineeringPhoto] = Field(
        default_factory=list,
        description="Per-photo generation results",
    )

    model_config = {"frozen": True}
