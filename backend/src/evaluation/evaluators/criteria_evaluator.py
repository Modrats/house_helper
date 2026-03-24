from __future__ import annotations

from datetime import datetime, timezone

from ..eval_config import load_thresholds
from ..interfaces import IEvaluator
from ..metrics import EvaluationReport, MetricResult, compute_accuracy, compute_fnr
from ..models import CriteriaEvaluationSample


class CriteriaEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "criteria_evaluator"

    def evaluate(  # type: ignore[override]  # extra kwargs beyond base signature
        self,
        samples: list[CriteriaEvaluationSample],
        actual: list[dict[str, bool]],
        latency_seconds: float,
        cost_usd: float,
        llm_judge_score: float | None = None,
        **kwargs: object,
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

        accuracy = compute_accuracy(correct_keys, total_keys)
        fnr = compute_fnr(false_negatives, should_be_true)

        metrics: list[MetricResult] = [
            MetricResult(name="accuracy", value=accuracy, unit="ratio"),
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
