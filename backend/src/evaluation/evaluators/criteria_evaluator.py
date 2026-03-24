from __future__ import annotations

from datetime import datetime, timezone

from ..interfaces import IEvaluator
from ..models import CriteriaEvaluationSample, EvaluationReport, MetricResult

_THRESHOLD_ACCURACY = 0.70
_THRESHOLD_FNR = 0.15
_THRESHOLD_LATENCY = 15.0
_THRESHOLD_COST = 0.10


class CriteriaEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "criteria_evaluator"

    def evaluate(  # type: ignore[override]
        self,
        samples: list[CriteriaEvaluationSample],
        actual: list[dict[str, bool]],
        latency_seconds: float,
        cost_usd: float,
        llm_judge_score: float | None = None,
    ) -> EvaluationReport:
        total_keys = 0
        correct_keys = 0
        should_be_true = 0
        false_negatives = 0

        for sample, actual_verdicts in zip(samples, actual):
            for key, exp_val in sample.expected.items():
                actual_val = actual_verdicts.get(key, False)
                total_keys += 1
                if actual_val == exp_val:
                    correct_keys += 1
                if exp_val:
                    should_be_true += 1
                    if not actual_val:
                        false_negatives += 1

        accuracy = correct_keys / total_keys if total_keys > 0 else 1.0
        fnr = false_negatives / should_be_true if should_be_true > 0 else 0.0

        judge_value = llm_judge_score if llm_judge_score is not None else -1.0

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
            MetricResult(
                name="cost",
                value=cost_usd,
                unit="usd",
                passed=cost_usd <= _THRESHOLD_COST,
                threshold=_THRESHOLD_COST,
            ),
            MetricResult(
                name="llm_judge_score",
                value=judge_value,
                unit="score_1_5",
                passed=True,
                threshold=3.5,
            ),
        ]

        return EvaluationReport(
            stage="criteria_evaluator",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )
