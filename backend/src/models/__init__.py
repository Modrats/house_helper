"""Pydantic data models for the House Helper pipeline.

Pure data structures with no business logic. Models are immutable
and focused on data representation.
"""

from .classification import HouseClassifications, PhotoClassification
from .distance import DistanceResult, TravelTime
from .house import FilterResult, House, HouseMetadata, HouseStatus
from .llm import LLMResponse
from .room import Photo, Room, RoomType

__all__ = [
    "DistanceResult",
    "FilterResult",
    "House",
    "HouseClassifications",
    "HouseMetadata",
    "HouseStatus",
    "LLMResponse",
    "Photo",
    "PhotoClassification",
    "Room",
    "RoomType",
    "TravelTime",
]
