"""Pydantic data models for the House Helper pipeline.

Pure data structures with no business logic. Models are immutable
and focused on data representation.
"""

from .classification import HouseClassifications, PhotoClassification
from .distance import DistanceResult, TravelTime
from .house import FilterResult, House, HouseMetadata, HouseStatus
from .imagineering import ImagineeringPhoto, ImagineeringResult
from .llm import LLMResponse
from .room import Photo, Room, RoomType
from .text_analysis import CriterionResult, TextAnalysis

__all__ = [
    "DistanceResult",
    "CriterionResult",
    "FilterResult",
    "House",
    "HouseClassifications",
    "HouseMetadata",
    "HouseStatus",
    "ImagineeringPhoto",
    "ImagineeringResult",
    "LLMResponse",
    "Photo",
    "PhotoClassification",
    "Room",
    "RoomType",
    "TravelTime",
    "TextAnalysis",
]
