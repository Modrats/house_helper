"""Photo criteria result models.

Pure data structures for photo criteria checking outputs.
Used by the photo checker service to represent per-feature,
per-room, and per-house criteria evaluation results.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from .house import FilterResult
from .room import RoomType


class FeatureCheck(BaseModel):
    """Evaluation of a single visual feature in a room photo."""

    feature_name: str = Field(description="Name of the feature being checked")
    present: bool = Field(description="Whether the feature was detected in the photo")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the detection (0.0–1.0)",
    )
    notes: str = Field(description="LLM notes on the feature evaluation")

    model_config = {"frozen": True}


class RoomCriteriaResult(BaseModel):
    """Criteria evaluation result for a single room photo."""

    room_type: RoomType = Field(description="Classified room type")
    photo_filename: str = Field(description="Photo filename that was evaluated")
    required_features: list[FeatureCheck] = Field(
        default_factory=list,
        description="Evaluations of required (must-have) features",
    )
    preferred_features: list[FeatureCheck] = Field(
        default_factory=list,
        description="Evaluations of preferred (nice-to-have) features",
    )

    model_config = {"frozen": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def meets_required(self) -> bool:
        """True when ALL required features are present."""
        return all(f.present for f in self.required_features)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def meets_preferred(self) -> bool:
        """True when at least ONE preferred feature is present (or none required)."""
        if not self.preferred_features:
            return True
        return any(f.present for f in self.preferred_features)


class PhotoCriteriaResult(BaseModel):
    """All criteria evaluation results for a single house."""

    slug: str = Field(description="House identifier")
    room_results: list[RoomCriteriaResult] = Field(
        default_factory=list,
        description="Per-room criteria evaluation results",
    )

    model_config = {"frozen": True}

    def to_filter_result(self) -> FilterResult:
        """Convert criteria results to a FilterResult.

        Required features map to p1 (must-have), preferred to p2 (nice-to-have).
        Keys are formatted as ``{room_type}:{feature_name}``.

        Returns:
            FilterResult with p1/p2 criteria from all room evaluations.
        """
        p1: dict[str, bool] = {}
        p2: dict[str, bool] = {}
        for room in self.room_results:
            prefix = room.room_type.value
            for feat in room.required_features:
                p1[f"{prefix}:{feat.feature_name}"] = feat.present
            for feat in room.preferred_features:
                p2[f"{prefix}:{feat.feature_name}"] = feat.present
        return FilterResult(p1=p1, p2=p2)

    def to_detailed_dict(self) -> list[dict]:
        """Return a serializable list of per-room evaluation dicts.

        Returns:
            List of dicts with room_type, photo_filename, features,
            and computed pass/fail fields.
        """
        results = []
        for room in self.room_results:
            results.append(
                {
                    "room_type": room.room_type.value,
                    "photo_filename": room.photo_filename,
                    "meets_required": room.meets_required,
                    "meets_preferred": room.meets_preferred,
                    "required_features": [
                        {
                            "feature_name": f.feature_name,
                            "present": f.present,
                            "confidence": f.confidence,
                            "notes": f.notes,
                        }
                        for f in room.required_features
                    ],
                    "preferred_features": [
                        {
                            "feature_name": f.feature_name,
                            "present": f.present,
                            "confidence": f.confidence,
                            "notes": f.notes,
                        }
                        for f in room.preferred_features
                    ],
                }
            )
        return results
