"""Pydantic metric result models for the evaluation pipeline.

All metric types inherit from MetricResult. Typed subclasses carry
stage-specific fields (duration, tokens, scores) alongside the common
evaluator_name / passed / details triple.

Where a success criterion is a runtime parameter (latency threshold,
cost budget), the threshold field is part of the model and `passed`
is derived from it automatically via a before-mode model validator.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, model_validator


class MetricResult(BaseModel):
    """Base class for all metric results returned by an IEvaluator.

    Subclasses add stage-specific measured fields and may override
    `passed` computation via a model validator.
    """

    model_config = {"frozen": True}

    evaluator_name: str = Field(
        description="Name of the evaluator that produced this result",
    )
    passed: bool = Field(
        description="True when the measured value meets the success criterion",
    )
    details: dict[str, float | int | str] = Field(
        default_factory=dict,
        description="Freeform key/value pairs with supplementary diagnostic data",
    )


class LatencyMetric(MetricResult):
    """Metric for wall-clock time measurements.

    `passed` is computed automatically: True when duration_seconds
    is at or below threshold_seconds.
    """

    model_config = {"frozen": True}

    duration_seconds: float = Field(
        ge=0.0,
        description="Measured wall-clock time in seconds for the operation",
    )
    threshold_seconds: float = Field(
        gt=0.0,
        description="Maximum allowed duration in seconds (success criterion)",
    )

    @model_validator(mode="before")
    @classmethod
    def _compute_passed(cls, data: dict) -> dict:  # type: ignore[override]
        if isinstance(data, dict) and "passed" not in data:
            duration = data.get("duration_seconds", 0.0)
            threshold = data.get("threshold_seconds", float("inf"))
            data["passed"] = float(duration) <= float(threshold)
        return data


class CostMetric(MetricResult):
    """Metric for token usage and estimated USD cost.

    `passed` is computed automatically: True when estimated_usd
    is at or below threshold_usd.
    """

    model_config = {"frozen": True}

    tokens_used: int = Field(
        ge=0,
        description="Total tokens consumed (prompt + completion)",
    )
    estimated_usd: float = Field(
        ge=0.0,
        description="Estimated cost in USD derived from tokens_used and model pricing",
    )
    threshold_usd: float = Field(
        gt=0.0,
        description="Maximum allowed cost in USD (success criterion)",
    )

    @model_validator(mode="before")
    @classmethod
    def _compute_passed(cls, data: dict) -> dict:  # type: ignore[override]
        if isinstance(data, dict) and "passed" not in data:
            cost = data.get("estimated_usd", 0.0)
            threshold = data.get("threshold_usd", float("inf"))
            data["passed"] = float(cost) <= float(threshold)
        return data


class AccuracyMetric(MetricResult):
    """Metric for quantitative correctness against ground truth labels.

    Covers overall accuracy and optional per-class precision, recall,
    and F1. `passed` must be set explicitly by the evaluator based on
    the stage-specific threshold (e.g. ≥ 70% accuracy).
    """

    model_config = {"frozen": True}

    accuracy: float = Field(
        ge=0.0,
        le=1.0,
        description="Fraction of samples assigned the correct label",
    )
    precision: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="True positives / (true positives + false positives); None when not computed",
    )
    recall: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="True positives / (true positives + false negatives); None when not computed",
    )
    f1: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Harmonic mean of precision and recall; None when not computed",
    )


class LLMJudgeMetric(MetricResult):
    """Metric for qualitative assessment by an LLM judge.

    The judge scores the output on a 1–5 scale. `passed` must be set
    explicitly by the evaluator based on the stage-specific threshold
    (e.g. mean score ≥ 3.5).
    """

    model_config = {"frozen": True}

    score: float = Field(
        ge=1.0,
        le=5.0,
        description="LLM judge score on a 1–5 scale (1 = poor, 5 = excellent)",
    )
    rationale: str | None = Field(
        default=None,
        description="Free-text explanation from the LLM judge for the score assigned",
    )


class EvaluationReport(BaseModel):
    """Aggregated evaluation results for a single sample across all evaluators.

    Collects all MetricResult instances produced for one sample in one
    pipeline stage. overall_passed is True only when every metric passed.
    """

    model_config = {"frozen": True}

    sample_id: str = Field(
        description="Unique identifier of the evaluated sample (e.g. house slug or photo path)",
    )
    stage: str = Field(
        description="Pipeline stage this report covers (e.g. 'text_filter', 'photo_classifier')",
    )
    metrics: list[MetricResult] = Field(
        description="All metric results produced for this sample",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def overall_passed(self) -> bool:
        """True only when every metric in the report passed."""
        return all(m.passed for m in self.metrics)
