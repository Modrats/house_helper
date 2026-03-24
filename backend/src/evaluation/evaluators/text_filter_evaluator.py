from __future__ import annotations

from datetime import datetime, timezone

from ..eval_config import load_thresholds
from ..interfaces import IEvaluator
from ..metrics import AccuracyMetric, EvaluationReport, MetricResult, compute_fnr
from ..models import TextFilterSample


class TextFilterEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "text_filter"

    def evaluate(
        self,
        samples: list[TextFilterSample],
        actual: list[dict[str, bool]],
        latency_seconds: float,
        **kwargs: object,
    ) -> EvaluationReport:
        total = 0
        correct = 0
        should_be_true = 0
        false_negatives = 0

        for sample, actual_map in zip(samples, actual):
            expected = sample.expected
            predicted = actual_map.get(sample.slug, False)
            total += 1
            if predicted == expected:
                correct += 1
            if expected:
                should_be_true += 1
                if not predicted:
                    false_negatives += 1

        fnr = compute_fnr(false_negatives, should_be_true)

        metrics: list[MetricResult] = [
            AccuracyMetric(correct=correct, total=total),
            MetricResult(name="false_negative_rate", value=fnr, unit="ratio"),
            MetricResult(name="latency", value=latency_seconds, unit="seconds"),
        ]

        return EvaluationReport(
            stage="text_filter",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )

    def thresholds(self) -> dict[str, float]:
        return load_thresholds("text_filter")
