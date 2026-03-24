from __future__ import annotations

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
    count_multiclass_outcomes,
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

        # Resolve each sample to its predicted room (None when photo is missing or unclassified)
        photos = [actual_map.get(Path(s.photo_path).name) for s in samples]
        predicted_rooms: list[RoomType | None] = [
            p.room_type if p is not None else None for p in photos
        ]

        total, correct, tp, fp, fn = count_multiclass_outcomes(
            zip(predicted_rooms, (s.expected_room_type for s in samples))
        )
        precision, recall = compute_macro_precision_recall(tp, fp, fn, COMMON_ROOMS)

        # Calibration: fraction of all samples that are both correctly classified
        # and meet the per-sample confidence threshold
        calibration_pass = sum(
            1
            for photo, sample, predicted in zip(photos, samples, predicted_rooms)
            if predicted == sample.expected_room_type
            and photo is not None
            and (photo.confidence or 0.0) >= sample.expected_confidence_min
        )
        calibration = calibration_pass / total if total > 0 else 0.0

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
