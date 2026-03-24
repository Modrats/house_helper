from __future__ import annotations

from datetime import datetime, timezone

from ..interfaces import IEvaluator
from ..models import EvaluationReport, ImagineeredSample, MetricResult

_THRESHOLD_JUDGE = 3.5
_THRESHOLD_LATENCY = 60.0
_THRESHOLD_COST = 0.50


class ImagineeeringEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "imagineering"

    def evaluate(  # type: ignore[override]
        self,
        samples: list[ImagineeredSample],
        judge_score: float,
        latency_seconds: float,
        cost_usd: float,
    ) -> EvaluationReport:
        metrics = [
            MetricResult(
                name="llm_judge_score",
                value=judge_score,
                unit="score_1_5",
                passed=judge_score >= _THRESHOLD_JUDGE,
                threshold=_THRESHOLD_JUDGE,
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
        ]

        return EvaluationReport(
            stage="imagineering",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )
