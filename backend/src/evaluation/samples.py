"""Ground truth sample schemas for all 4 pipeline stages.

Each class defines the shape of one fixture record — an input/expected-output
pair used by evaluation runners and the test suite.  Schemas mirror the
documentation in README.md exactly.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models.house import FilterResult
from ..models.room import RoomType


class TextFilterSample(BaseModel):
    """Ground truth sample for the Text Filter stage (RAW → FILTERED).

    Captures a raw listing text and the expected per-criterion filter verdicts.
    """

    model_config = {"frozen": True}

    slug: str = Field(description="Unique identifier for the house listing")
    listing_text: str = Field(description="Raw listing text submitted to the filter")
    expected: FilterResult = Field(
        description="Expected p1/p2/excluded verdict for every criterion keyword"
    )


class PhotoClassificationSample(BaseModel):
    """Ground truth sample for the Photo Classifier stage (FILTERED → CLASSIFIED).

    Labels a single photo with its correct room type and the minimum confidence
    score the classifier must return to be considered well-calibrated.
    """

    model_config = {"frozen": True}

    photo_path: str = Field(description="Path to the image file (relative to repo root)")
    expected_room_type: RoomType = Field(description="Correct room type label for this photo")
    expected_confidence_min: float = Field(
        ge=0.0,
        le=1.0,
        description="Minimum acceptable confidence score for a correct prediction",
    )


class CriteriaEvaluationSample(BaseModel):
    """Ground truth sample for the Criteria Evaluator stage (CLASSIFIED → EVALUATED).

    Provides a classified house (photos + listing text) together with the
    criteria to check and the expected per-criterion verdict.
    """

    model_config = {"frozen": True}

    photos: list[str] = Field(
        description="Paths to house photos submitted for visual criteria checking"
    )
    listing_text: str = Field(
        description="Full listing description submitted for text criteria checking"
    )
    photo_criteria: dict[str, str] = Field(
        description="Criteria checked from photos — {key: human-readable description}"
    )
    text_criteria: dict[str, str] = Field(
        description="Criteria checked from listing text — {key: human-readable description}"
    )
    expected: dict[str, bool] = Field(
        description="Expected verdict for every criteria key (True = criterion met)"
    )


class ImagineeredSample(BaseModel):
    """Ground truth sample for the Imagineering stage (EVALUATED → IMAGINEERED).

    Specifies the source photo, target room type, generation prompt, and the
    visual features the output image should exhibit.
    """

    model_config = {"frozen": True}

    photo_path: str = Field(description="Path to the source photo (relative to repo root)")
    room_type: RoomType = Field(description="Room type of the source photo")
    style_prompt: str = Field(
        description="Full prompt used to generate the reimagined version of the room"
    )
    reference_features: list[str] = Field(
        description="Features the generated output should visibly exhibit"
    )
