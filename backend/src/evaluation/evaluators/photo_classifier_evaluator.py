from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ...models.room import Photo, RoomType
from ..interfaces import IEvaluator
from ..models import EvaluationReport, MetricResult, PhotoClassificationSample

COMMON_ROOMS: frozenset[RoomType] = frozenset(
    {
        RoomType.LIVING_ROOM,
        RoomType.BEDROOM,
        RoomType.KITCHEN,
        RoomType.BATHROOM,
        RoomType.GARDEN,
    }
)

_THRESHOLD_ACCURACY = 0.70
_THRESHOLD_PRECISION = 0.65
_THRESHOLD_RECALL = 0.65
_THRESHOLD_CALIBRATION = 0.70
_THRESHOLD_LATENCY = 10.0
_THRESHOLD_COST = 0.05


class PhotoClassifierEvaluator(IEvaluator):
    @property
    def name(self) -> str:
        return "photo_classifier"

    def evaluate(  # type: ignore[override]
        self,
        samples: list[PhotoClassificationSample],
        actual: list[Photo],
        latency_seconds: float,
        cost_usd: float,
        llm_judge_score: float | None = None,
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

        accuracy = correct / total if total > 0 else 0.0

        precision_vals = [
            tp[rt] / (tp[rt] + fp[rt]) for rt in COMMON_ROOMS if (tp[rt] + fp[rt]) > 0
        ]
        recall_vals = [
            tp[rt] / (tp[rt] + fn[rt]) for rt in COMMON_ROOMS if (tp[rt] + fn[rt]) > 0
        ]
        precision = sum(precision_vals) / len(precision_vals) if precision_vals else 0.0
        recall = sum(recall_vals) / len(recall_vals) if recall_vals else 0.0
        calibration = calibration_pass / calibration_total if calibration_total > 0 else 0.0

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
                name="precision",
                value=precision,
                unit="ratio",
                passed=precision >= _THRESHOLD_PRECISION,
                threshold=_THRESHOLD_PRECISION,
            ),
            MetricResult(
                name="recall",
                value=recall,
                unit="ratio",
                passed=recall >= _THRESHOLD_RECALL,
                threshold=_THRESHOLD_RECALL,
            ),
            MetricResult(
                name="confidence_calibration",
                value=calibration,
                unit="ratio",
                passed=calibration >= _THRESHOLD_CALIBRATION,
                threshold=_THRESHOLD_CALIBRATION,
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
            stage="photo_classifier",
            run_date=datetime.now(tz=timezone.utc),
            metrics=metrics,
        )
