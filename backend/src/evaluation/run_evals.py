"""CLI entry point: uv run python -m src.evaluation.run_evals [--component NAME]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..models.room import Photo
from .evaluators.criteria_evaluator import CriteriaEvaluator
from .evaluators.imagineering_evaluator import ImagineeeringEvaluator
from .evaluators.photo_classifier_evaluator import PhotoClassifierEvaluator
from .evaluators.text_filter_evaluator import TextFilterEvaluator
from .models import (
    CriteriaEvaluationSample,
    EvaluationReport,
    ImagineeredSample,
    PhotoClassificationSample,
    TextFilterSample,
)

FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures"


def _load_records(filename: str) -> list[dict]:
    path = FIXTURES_DIR / filename
    with path.open() as f:
        records = json.load(f)
    return [r for r in records if "_comment" not in r]


def _run_text_filter() -> EvaluationReport:
    records = _load_records("text_filter_samples.json")
    samples = [TextFilterSample.model_validate(r) for r in records]
    actual = [{s.slug: s.expected} for s in samples]
    return TextFilterEvaluator().evaluate(samples, actual, latency_seconds=0.1)


def _run_photo_classifier() -> EvaluationReport:
    records = _load_records("photo_classification_samples.json")
    samples = [PhotoClassificationSample.model_validate(r) for r in records]
    actual = [
        Photo(
            filename=Path(s.photo_path).name,
            path=s.photo_path,
            room_type=s.expected_room_type,
            confidence=s.expected_confidence_min,
        )
        for s in samples
    ]
    return PhotoClassifierEvaluator().evaluate(
        samples, actual, latency_seconds=1.0, cost_usd=0.01
    )


def _run_criteria_evaluator() -> EvaluationReport:
    records = _load_records("criteria_evaluation_samples.json")
    samples = [CriteriaEvaluationSample.model_validate(r) for r in records]
    actual = [s.expected for s in samples]
    return CriteriaEvaluator().evaluate(samples, actual, latency_seconds=2.0, cost_usd=0.02)


def _run_imagineering() -> EvaluationReport:
    records = _load_records("imagineered_samples.json")
    samples = [ImagineeredSample.model_validate(r) for r in records]
    return ImagineeeringEvaluator().evaluate(
        samples, judge_score=4.0, latency_seconds=10.0, cost_usd=0.05
    )


_RUNNERS = {
    "text_filter": _run_text_filter,
    "photo_classifier": _run_photo_classifier,
    "criteria_evaluator": _run_criteria_evaluator,
    "imagineering": _run_imagineering,
}


def _print_summary(reports: list[EvaluationReport]) -> None:
    col_stage = 22
    col_passed = 8
    col_metrics = 50
    header = f"{'stage':<{col_stage}} {'passed':<{col_passed}} {'metrics'}"
    print(header)
    print("-" * (col_stage + col_passed + col_metrics + 2))
    for report in reports:
        metric_summary = ", ".join(
            f"{m.name}={m.value:.3f}({'ok' if m.passed else 'FAIL'})"
            for m in report.metrics
        )
        passed_str = "PASS" if report.passed else "FAIL"
        print(f"{report.stage:<{col_stage}} {passed_str:<{col_passed}} {metric_summary}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run evaluation suite.")
    parser.add_argument(
        "--component",
        choices=list(_RUNNERS),
        default=None,
        help="Run only the named evaluator (default: all).",
    )
    args = parser.parse_args(argv)

    to_run = {args.component: _RUNNERS[args.component]} if args.component else _RUNNERS
    reports: list[EvaluationReport] = []
    for name, runner in to_run.items():
        print(f"Running {name}...")
        try:
            reports.append(runner())
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            return 1

    print()
    _print_summary(reports)

    any_failed = any(not r.passed for r in reports)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
