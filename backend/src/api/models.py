"""Pydantic response models for the API layer.

These are dedicated API response shapes — separate from the internal
domain models in src/models/ — so the API contract can evolve
independently of the pipeline internals.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PhotoResponse(BaseModel):
    """A single photo returned by the API."""

    filename: str
    url: str = Field(description="URL to serve the photo")
    room_type: str | None = None
    confidence: float | None = None
    imagineered_url: str | None = None


class RoomClassificationResponse(BaseModel):
    """Room classification grouping for a house."""

    room_type: str
    display_name: str = Field(description="Human-readable room name")
    photo_count: int
    photos: list[str] = Field(description="Filenames of photos in this room")


class FilterResultResponse(BaseModel):
    """Criteria filter results."""

    p1: dict[str, bool] = Field(default_factory=dict)
    p2: dict[str, bool] = Field(default_factory=dict)
    excluded: dict[str, bool] = Field(default_factory=dict)
    passed: bool


class HouseListItemResponse(BaseModel):
    """Summary of a house for listing endpoints."""

    slug: str
    photo_count: int
    status: str
    has_filter_results: bool
    thumbnail_url: str | None = None


class HouseDetailResponse(BaseModel):
    """Full house details for the detail endpoint."""

    slug: str
    listing_text: str
    status: str
    photo_count: int
    room_count: int
    filter_results: FilterResultResponse
    photos: list[PhotoResponse]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
