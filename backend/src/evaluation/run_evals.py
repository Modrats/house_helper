"""CLI entry point: uv run python -m src.evaluation.run_evals [--component NAME]"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ..models.room import Photo
from .eval_config import load_thresholds
from .evaluators.criteria_evaluator import CriteriaEvaluator
from .evaluators.imagineering_evaluator import ImagineeeringEvaluator
from .evaluators.photo_classifier_evaluator import PhotoClassifierEvaluator
from .evaluators.text_filter_evaluator import TextFilterEvaluator
from .local_publisher import LocalPublisher
from .models import (
    CriteriaEvaluationSample,
    EvaluationReport,
    ImagineeredSample,
    PhotoClassificationSample,
    TextFilterSample,
)
from .publisher_interface import IMetricsPublisher

FIXTURES_DIR = Path(__file__).parent / "ground_truth"

_COL_STAGE = 22  # character width of the stage name column
_COL_PASSED = 8  # character width of the PASS/FAIL column
_COL_METRICS = 50  # character width of the metrics summary column


def _load_records(filename: str) -> list[dict]:
    path = FIXTURES_DIR / filename
    with path.open() as f:
        records = json.load(f)
    return [r for r in records if "_comment" not in r]


def _run_text_filter() -> EvaluationReport:
    records = _load_records("text_filter_samples.json")
    samples = [TextFilterSample.model_validate(r) for r in records]
    actual = [{s.slug: s.expected} for s in samples]
    # TODO: measure actual latency
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
    # TODO: measure actual latency/cost
    return PhotoClassifierEvaluator().evaluate(samples, actual, latency_seconds=1.0, cost_usd=0.01)


def _run_criteria_evaluator() -> EvaluationReport:
    records = _load_records("criteria_evaluation_samples.json")
    samples = [CriteriaEvaluationSample.model_validate(r) for r in records]
    actual = [s.expected for s in samples]
    # TODO: measure actual latency/cost
    return CriteriaEvaluator().evaluate(samples, actual, latency_seconds=2.0, cost_usd=0.02)


def _run_imagineering() -> EvaluationReport:
    records = _load_records("imagineered_samples.json")
    samples = [ImagineeredSample.model_validate(r) for r in records]
    return ImagineeeringEvaluator().evaluate(
        # TODO: measure actual latency/cost
        samples,
        judge_score=4.0,
        latency_seconds=10.0,
        cost_usd=0.05,
    )


_RUNNERS = {
    "text_filter": _run_text_filter,
    "photo_classifier": _run_photo_classifier,
    "criteria_evaluator": _run_criteria_evaluator,
    "imagineering": _run_imagineering,
}


def _print_summary(results: list[tuple[EvaluationReport, dict[str, bool]]]) -> None:
    header = f"{'stage':<{_COL_STAGE}} {'passed':<{_COL_PASSED}} {'metrics'}"
    print(header)
    print("-" * (_COL_STAGE + _COL_PASSED + _COL_METRICS + 2))
    for report, checks in results:
        metric_summary = ", ".join(
            f"{m.name}={m.value:.3f}({'ok' if checks.get(m.name, True) else 'FAIL'})"
            for m in report.metrics
        )
        stage_passed = all(checks.values()) if checks else True
        passed_str = "PASS" if stage_passed else "FAIL"
        print(f"{report.stage:<{_COL_STAGE}} {passed_str:<{_COL_PASSED}} {metric_summary}")


def main(
    argv: list[str] | None = None,
    publisher: IMetricsPublisher | None = None,
) -> int:
    # Default publisher — override in tests via the publisher parameter
    if publisher is None:
        publisher = LocalPublisher()

    parser = argparse.ArgumentParser(description="Run evaluation suite.")
    parser.add_argument(
        "--component",
        choices=list(_RUNNERS),
        default=None,
        help="Run only the named evaluator (default: all).",
    )
    args = parser.parse_args(argv)

    to_run = {args.component: _RUNNERS[args.component]} if args.component else _RUNNERS
    results: list[tuple[EvaluationReport, dict[str, bool]]] = []
    for name, runner in to_run.items():
        print(f"Running {name}...")
        try:
            report = runner()
            thresholds = load_thresholds(name)
            checks = report.check_thresholds(thresholds)
            branch_name = os.environ.get("BRANCH_NAME", "")
            publisher.publish(
                report,
                experiment_name=name,
                run_tags={
                    "model_name": "local",
                    "prompt_version": "local",
                    "stage": name,
                    "branch_name": branch_name or "local",
                },
            )
            results.append((report, checks))
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            return 1

    print()
    _print_summary(results)

    any_failed = any(not all(checks.values()) for _, checks in results if checks)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
