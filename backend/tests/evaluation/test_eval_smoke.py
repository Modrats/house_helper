"""Smoke test — verifies the evaluation module is importable and wired for CI."""

from src.evaluation import IEvaluator, MetricResult


def test_ievaluator_is_importable() -> None:
    assert IEvaluator is not None


def test_metric_result_is_importable() -> None:
    assert MetricResult is not None
