"""NullPublisher — no-op IMetricsPublisher for use in tests.

Has no Azure or mlflow imports so the module is importable in any
environment, including CI runners without the ``aml`` optional dependency.
"""

from __future__ import annotations

import uuid

from .publisher_interface import EvaluationReport, IMetricsPublisher


class NullPublisher(IMetricsPublisher):
    """No-op metrics publisher that records published reports in memory.

    Useful in tests and dry-run scenarios where real AML publishing is
    undesirable. All reports are available via ``self.published`` after the
    fact for assertion in tests.

    Example::

        publisher = NullPublisher()
        run_id = publisher.publish(report, "my-experiment", {
            "model_name": "gpt-4o",
            "prompt_version": "v1",
            "stage": "text_filter",
        })
        assert run_id.startswith("null-run-")
        assert publisher.published == [report]
    """

    def __init__(self) -> None:
        self.published: list[EvaluationReport] = []

    def publish(
        self,
        report: EvaluationReport,
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> str:
        """Record *report* and return a stable fake run ID.

        Args:
            report: The evaluation report to record.
            experiment_name: Unused; accepted for interface compatibility.
            run_tags: Must include ``model_name``, ``prompt_version``, and
                      ``stage``; validated before recording.

        Returns:
            A fake run ID of the form ``"null-run-{uuid4}"``.

        Raises:
            ValueError: If *run_tags* is missing a required key.
        """
        self._validate_run_tags(run_tags)
        self.published.append(report)
        return f"null-run-{uuid.uuid4()}"

    def publish_batch(
        self,
        reports: list[EvaluationReport],
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> list[str]:
        """Publish each report via :meth:`publish` and return all run IDs.

        Args:
            reports: Evaluation reports to record.
            experiment_name: Passed through to :meth:`publish` unchanged.
            run_tags: Passed through to :meth:`publish` unchanged.

        Returns:
            List of fake run IDs in the same order as *reports*.
        """
        return [self.publish(report, experiment_name, run_tags) for report in reports]
