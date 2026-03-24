"""Pydantic metric result models and standalone stat functions.

Metric models store raw measured values only — no pass/fail logic.
Pass/fail is determined at report time by comparing values against
thresholds from ``eval_thresholds.yaml`` via ``EvaluationReport.check_thresholds()``.

Standalone stat functions are pure and reusable across all evaluators.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator

# ---------------------------------------------------------------------------
# Standalone stat functions
# ---------------------------------------------------------------------------


def compute_accuracy(correct: int, total: int) -> float:
    """Return ``correct / total``, or ``0.0`` when *total* is zero."""
    return correct / total if total > 0 else 0.0


def compute_fnr(false_negatives: int, total_positives: int) -> float:
    """Return ``false_negatives / total_positives``, or ``0.0`` when zero."""
    return false_negatives / total_positives if total_positives > 0 else 0.0


def compute_macro_precision_recall(
    tp: dict[Any, int],
    fp: dict[Any, int],
    fn: dict[Any, int],
    classes: frozenset,
) -> tuple[float, float]:
    """Return macro-averaged (precision, recall) over *classes*."""
    precision_vals = [tp[c] / (tp[c] + fp[c]) for c in classes if (tp[c] + fp[c]) > 0]
    recall_vals = [tp[c] / (tp[c] + fn[c]) for c in classes if (tp[c] + fn[c]) > 0]
    p = sum(precision_vals) / len(precision_vals) if precision_vals else 0.0
    r = sum(recall_vals) / len(recall_vals) if recall_vals else 0.0
    return p, r


# ---------------------------------------------------------------------------
# Metric models — raw values only, no pass/fail
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    """Base class for all metric results. Stores raw measured values only.

    Pass/fail is determined externally via ``EvaluationReport.check_thresholds()``
    so thresholds can be adjusted without rerunning measurements.
    """

    model_config = {"frozen": True}

    name: str = Field(description="Metric identifier (e.g. 'accuracy', 'latency')")
    value: float = Field(description="Raw measured value")
    unit: str = Field(description="Unit (e.g. 'ratio', 'seconds', 'usd')")
    details: dict[str, float | int | str] = Field(
        default_factory=dict,
        description="Supplementary diagnostic data",
    )


class LatencyMetric(MetricResult):
    """Wall-clock time measurement. ``threshold_seconds`` documents the target."""

    model_config = {"frozen": True}

    duration_seconds: float = Field(ge=0.0, description="Measured wall-clock time in seconds")
    threshold_seconds: float = Field(gt=0.0, description="Target maximum duration in seconds")

    @model_validator(mode="before")
    @classmethod
    def _set_value(cls, data: dict) -> dict:
        if isinstance(data, dict) and "value" not in data:
            data.setdefault("name", "latency")
            data.setdefault("unit", "seconds")
            data["value"] = float(data.get("duration_seconds", 0.0))
        return data


class CostMetric(MetricResult):
    """Token usage and USD cost. ``threshold_usd`` documents the budget."""

    model_config = {"frozen": True}

    tokens_used: int = Field(ge=0, description="Total tokens consumed")
    estimated_usd: float = Field(ge=0.0, description="Estimated cost in USD")
    threshold_usd: float = Field(gt=0.0, description="Target maximum cost in USD")

    @model_validator(mode="before")
    @classmethod
    def _set_value(cls, data: dict) -> dict:
        if isinstance(data, dict) and "value" not in data:
            data.setdefault("name", "cost")
            data.setdefault("unit", "usd")
            data["value"] = float(data.get("estimated_usd", 0.0))
        return data


class AccuracyMetric(MetricResult):
    """Correctness metric. Accepts ``correct``/``total`` counts; computes accuracy itself."""

    model_config = {"frozen": True}

    correct: int = Field(ge=0, description="Correctly predicted samples")
    total: int = Field(ge=0, description="Total samples")
    precision: float | None = Field(default=None, ge=0.0, le=1.0)
    recall: float | None = Field(default=None, ge=0.0, le=1.0)
    f1: float | None = Field(default=None, ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]  # Pydantic v2: @computed_field on @property needs this ignore
    @property
    def accuracy(self) -> float:
        """Fraction of samples correctly predicted."""
        return self.correct / self.total if self.total > 0 else 0.0

    @model_validator(mode="before")
    @classmethod
    def _set_value(cls, data: dict) -> dict:
        if isinstance(data, dict) and "value" not in data:
            data.setdefault("name", "accuracy")
            data.setdefault("unit", "ratio")
            c = int(data.get("correct", 0))
            t = int(data.get("total", 1))
            data["value"] = c / t if t > 0 else 0.0
        return data


class LLMJudgeMetric(MetricResult):
    """Qualitative LLM judge assessment. ``reason`` must precede ``score``."""

    model_config = {"frozen": True}

    reason: str = Field(description="Judge's reasoning before the score is assigned")
    score: float = Field(ge=1.0, le=5.0, description="Score (1=poor, 5=excellent)")

    @model_validator(mode="before")
    @classmethod
    def _set_value(cls, data: dict) -> dict:
        if isinstance(data, dict) and "value" not in data:
            data.setdefault("name", "llm_judge_score")
            data.setdefault("unit", "score_1_5")
            data["value"] = float(data.get("score", 1.0))
        return data


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

#: Metric names where lower is better — pass when value <= threshold.
_LOWER_IS_BETTER = frozenset({"latency", "latency_seconds", "cost", "cost_usd",
                               "false_negative_rate"})


class EvaluationReport(BaseModel):
    """Aggregated results for one pipeline stage run.

    Metrics carry raw values only. Call :meth:`check_thresholds` with the
    stage thresholds from ``eval_thresholds.yaml`` to compute pass/fail
    without re-running the evaluation.
    """

    model_config = {"frozen": True}

    stage: str = Field(description="Pipeline stage (e.g. 'text_filter')")
    run_date: datetime = Field(description="UTC timestamp of the evaluation run")
    model_name: str | None = Field(default=None)
    prompt_version: str | None = Field(default=None)
    metrics: list[MetricResult] = Field(description="All metric results for this run")

    def check_thresholds(self, thresholds: dict[str, float]) -> dict[str, bool]:
        """Return ``{metric_name: passed}`` evaluated against *thresholds*.

        Lower-is-better metrics use ``value <= threshold``; all others use
        ``value >= threshold``. Metrics not in *thresholds* are omitted.
        """
        result: dict[str, bool] = {}
        metric_map = {m.name: m for m in self.metrics}
        for metric_name, threshold in thresholds.items():
            m = metric_map.get(metric_name)
            if m is None:
                continue
            if any(kw in metric_name for kw in _LOWER_IS_BETTER):
                result[metric_name] = m.value <= threshold
            else:
                result[metric_name] = m.value >= threshold
        return result

    @property
    def passed(self) -> bool:
        """True when the report has no metrics — placeholder until check_thresholds is called."""
        return not self.metrics or True
