"""Text analysis result models.

Pure data structures for LLM-based text filter outputs.
Used by the LLM text filter service to represent per-criterion
evaluation results and their mapping to FilterResult.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .house import FilterResult


class CriterionResult(BaseModel):
    """Evaluation result for a single criterion against listing text."""

    criterion_name: str = Field(description="Name of the criterion evaluated")
    category: str = Field(description="Priority category: p1, p2, or excluded")
    met: bool = Field(description="Whether the criterion is met by the listing")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM confidence in the evaluation (0.0–1.0)",
    )
    reasoning: str = Field(description="LLM reasoning for the evaluation")

    model_config = {"frozen": True}


class TextAnalysis(BaseModel):
    """Persisted text analysis result for a single house."""

    slug: str = Field(description="House identifier")
    criteria_hash: str = Field(
        description="SHA-256 hash of the criteria config to detect drift",
    )
    evaluations: list[CriterionResult] = Field(
        default_factory=list,
        description="Per-criterion evaluation results",
    )

    model_config = {"frozen": True}

    def to_filter_result(self) -> FilterResult:
        """Convert text analysis evaluations to a FilterResult."""
        p1: dict[str, bool] = {}
        p2: dict[str, bool] = {}
        excluded: dict[str, bool] = {}

        for ev in self.evaluations:
            if ev.category == "p1":
                p1[ev.criterion_name] = ev.met
            elif ev.category == "p2":
                p2[ev.criterion_name] = ev.met
            elif ev.category == "excluded":
                excluded[ev.criterion_name] = ev.met

        return FilterResult(p1=p1, p2=p2, excluded=excluded)
