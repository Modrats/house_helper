from __future__ import annotations

from datetime import datetime, timezone

from ..eval_config import load_thresholds
from ..interfaces import IEvaluator
from ..metrics import EvaluationReport, MetricResult
from ..models import ImagineeredSample


class ImagineeeringEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "imagineering"

    def evaluate(
        self,
        samples: list[ImagineeredSample],
        judge_score: float,
        latency_seconds: float,
        cost_usd: float,
        **kwargs: object,
    ) -> EvaluationReport:
        metrics: list[MetricResult] = [
            MetricResult(name="llm_judge_score", value=judge_score, unit="score_1_5"),
            MetricResult(name="latency", value=latency_seconds, unit="seconds"),
            MetricResult(name="cost_usd", value=cost_usd, unit="usd"),
        ]

        return EvaluationReport(
            stage="imagineering",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )

    def thresholds(self) -> dict[str, float]:
        return load_thresholds("imagineering")
