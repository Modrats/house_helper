"""Evaluation module — ground truth schemas, interfaces, and metric models.

Exports
-------
Sample schemas (ground truth fixture shapes):
    TextFilterSample
    PhotoClassificationSample
    CriteriaEvaluationSample
    ImagineeredSample

Interface:
    IEvaluator              Abstract base class for all evaluators

Base metric:
    MetricResult            Base class for all typed metric results

Metric types:
    LatencyMetric           Wall-clock time vs threshold
    CostMetric              Token usage and estimated USD vs budget
    AccuracyMetric          Precision / recall / accuracy vs ground truth
    LLMJudgeMetric          LLM judge score (1-5 scale)

Aggregation:
    EvaluationReport        All metrics for one stage
"""

from ..models.eval_samples import (
    CriteriaEvaluationSample,
    ImagineeredSample,
    PhotoClassificationSample,
    TextFilterSample,
)
from .interfaces import IEvaluator
from .metrics import (
    AccuracyMetric,
    CostMetric,
    EvaluationReport,
    LatencyMetric,
    LLMJudgeMetric,
    MetricResult,
)

__all__ = [
    # Sample schemas
    "TextFilterSample",
    "PhotoClassificationSample",
    "CriteriaEvaluationSample",
    "ImagineeredSample",
    # Interface
    "IEvaluator",
    # Metrics
    "MetricResult",
    "LatencyMetric",
    "CostMetric",
    "AccuracyMetric",
    "LLMJudgeMetric",
    "EvaluationReport",
]
