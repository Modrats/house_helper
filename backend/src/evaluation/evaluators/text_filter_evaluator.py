from __future__ import annotations

from datetime import datetime, timezone

from ...models.house import FilterResult
from ..interfaces import IEvaluator
from ..models import EvaluationReport, MetricResult, TextFilterSample

_THRESHOLD_ACCURACY = 0.99
_THRESHOLD_FNR = 0.01
_THRESHOLD_LATENCY = 2.0


class TextFilterEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "text_filter"

    def evaluate(  # type: ignore[override]
        self,
        samples: list[TextFilterSample],
        actual: list[dict[str, FilterResult]],
        latency_seconds: float,
    ) -> EvaluationReport:
        actual_map: dict[str, FilterResult] = {}
        for d in actual:
            actual_map.update(d)

        total_keys = 0
        correct_keys = 0
        should_pass_count = 0
        false_negatives = 0

        for sample in samples:
            expected = sample.expected
            actual_fr = actual_map.get(sample.slug)

            if actual_fr is None:
                n = len(expected.p1) + len(expected.p2) + len(expected.excluded)
                total_keys += n
                if expected.passed:
                    should_pass_count += 1
                    false_negatives += 1
                continue

            for key, exp_val in expected.p1.items():
                total_keys += 1
                if actual_fr.p1.get(key, False) == exp_val:
                    correct_keys += 1

            for key, exp_val in expected.p2.items():
                total_keys += 1
                if actual_fr.p2.get(key, False) == exp_val:
                    correct_keys += 1

            for key, exp_val in expected.excluded.items():
                total_keys += 1
                if actual_fr.excluded.get(key, False) == exp_val:
                    correct_keys += 1

            if expected.passed:
                should_pass_count += 1
                if not actual_fr.passed:
                    false_negatives += 1

        accuracy = correct_keys / total_keys if total_keys > 0 else 1.0
        fnr = false_negatives / should_pass_count if should_pass_count > 0 else 0.0

        metrics = [
            MetricResult(
                name="accuracy",
                value=accuracy,
                unit="ratio",
                passed=accuracy >= _THRESHOLD_ACCURACY,
                threshold=_THRESHOLD_ACCURACY,
            ),
            MetricResult(
                name="false_negative_rate",
                value=fnr,
                unit="ratio",
                passed=fnr <= _THRESHOLD_FNR,
                threshold=_THRESHOLD_FNR,
            ),
            MetricResult(
                name="latency",
                value=latency_seconds,
                unit="seconds",
                passed=latency_seconds <= _THRESHOLD_LATENCY,
                threshold=_THRESHOLD_LATENCY,
            ),
        ]

        return EvaluationReport(
            stage="text_filter",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )
