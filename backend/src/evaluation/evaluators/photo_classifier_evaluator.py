from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ...models.room import Photo, RoomType
from ..eval_config import load_thresholds
from ..interfaces import IEvaluator
from ..metrics import (
    AccuracyMetric,
    EvaluationReport,
    MetricResult,
    compute_macro_precision_recall,
)
from ..models import PhotoClassificationSample

COMMON_ROOMS: frozenset[RoomType] = frozenset(
    {
        RoomType.LIVING_ROOM,
        RoomType.BEDROOM,
        RoomType.KITCHEN,
        RoomType.BATHROOM,
        RoomType.GARDEN,
    }
)


class PhotoClassifierEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "photo_classifier"

    def evaluate(
        self,
        samples: list[PhotoClassificationSample],
        actual: list[Photo],
        latency_seconds: float,
        cost_usd: float,
        llm_judge_score: float | None = None,
        **kwargs: object,
    ) -> EvaluationReport:
        actual_map: dict[str, Photo] = {Path(p.path).name: p for p in actual}

        total = 0
        correct = 0
        tp: dict[RoomType, int] = defaultdict(int)
        fp: dict[RoomType, int] = defaultdict(int)
        fn: dict[RoomType, int] = defaultdict(int)
        calibration_pass = 0
        calibration_total = 0

        for sample in samples:
            total += 1
            photo = actual_map.get(Path(sample.photo_path).name)
            expected = sample.expected_room_type

            if photo is None or photo.room_type is None:
                fn[expected] += 1
                calibration_total += 1
                continue

            predicted = photo.room_type
            calibration_total += 1

            if predicted == expected:
                correct += 1
                tp[expected] += 1
                conf = photo.confidence or 0.0
                if conf >= sample.expected_confidence_min:
                    calibration_pass += 1
            else:
                fn[expected] += 1
                fp[predicted] += 1

        precision, recall = compute_macro_precision_recall(tp, fp, fn, COMMON_ROOMS)
        calibration = calibration_pass / calibration_total if calibration_total > 0 else 0.0

        metrics: list[MetricResult] = [
            AccuracyMetric(correct=correct, total=total),
            MetricResult(name="precision", value=precision, unit="ratio"),
            MetricResult(name="recall", value=recall, unit="ratio"),
            MetricResult(name="confidence_calibration", value=calibration, unit="ratio"),
            MetricResult(name="latency", value=latency_seconds, unit="seconds"),
            MetricResult(name="cost_usd", value=cost_usd, unit="usd"),
        ]
        if llm_judge_score is not None:
            metrics.append(
                MetricResult(name="llm_judge_score", value=llm_judge_score, unit="score_1_5")
            )

        return EvaluationReport(
            stage="photo_classifier",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )

    def thresholds(self) -> dict[str, float]:
        return load_thresholds("photo_classifier")
