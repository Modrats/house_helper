from __future__ import annotations

from datetime import datetime, timezone

from ..eval_config import load_thresholds
from ..interfaces import IEvaluator
from ..metrics import (
    AccuracyMetric,
    EvaluationReport,
    MetricResult,
    compute_fnr,
    count_binary_outcomes,
)
from ..models import CriteriaEvaluationSample


class CriteriaEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "criteria_evaluator"

    def evaluate(
        self,
        samples: list[CriteriaEvaluationSample],
        actual: list[dict[str, bool]],
        latency_seconds: float,
        cost_usd: float,
        llm_judge_score: float | None = None,
        **kwargs: object,
    ) -> EvaluationReport:
        pairs = (
            (actual_verdicts.get(key, False), exp_val)
            for sample, actual_verdicts in zip(samples, actual)
            for key, exp_val in sample.expected.items()
        )
        total_keys, correct_keys, positives, false_negatives = count_binary_outcomes(pairs)
        fnr = compute_fnr(false_negatives, positives)

        metrics: list[MetricResult] = [
            AccuracyMetric(correct=correct_keys, total=total_keys),
            MetricResult(name="false_negative_rate", value=fnr, unit="ratio"),
            MetricResult(name="latency", value=latency_seconds, unit="seconds"),
            MetricResult(name="cost_usd", value=cost_usd, unit="usd"),
        ]
        if llm_judge_score is not None:
            metrics.append(
                MetricResult(name="llm_judge_score", value=llm_judge_score, unit="score_1_5")
            )

        return EvaluationReport(
            stage="criteria_evaluator",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )

    def thresholds(self) -> dict[str, float]:
        return load_thresholds("criteria_evaluator")
