"""LocalPublisher — writes evaluation results to local JSON files in AML-compatible format.

Produces the same structure as AMLPublisher so local runs and AML runs
can be compared directly. Use this instead of touching AML during
development or CI.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from .publisher_interface import EvaluationReport, IMetricsPublisher

_DEFAULT_OUTPUT_DIR = Path("eval-results")


class LocalPublisher(IMetricsPublisher):
    """Writes evaluation reports to local JSON files in AML-compatible format.

    Each call to :meth:`publish` writes one file under
    ``{output_dir}/{experiment_name}/{run_id}.json``.  The JSON schema
    mirrors what :class:`AMLPublisher` logs to mlflow so results from
    both publishers can be compared directly.

    Example::

        publisher = LocalPublisher()
        run_id = publisher.publish(report, "my-experiment", {
            "model_name": "gpt-4o",
            "prompt_version": "v1",
            "stage": "text_filter",
        })
        # File written to eval-results/my-experiment/{run_id}.json
    """

    def __init__(self, output_dir: Path | str = _DEFAULT_OUTPUT_DIR) -> None:
        self.output_dir = Path(output_dir)
        self.published: list[EvaluationReport] = []

    def publish(
        self,
        report: EvaluationReport,
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> str:
        """Write *report* to a local JSON file and return the run ID.

        Args:
            report: The evaluation report to persist.
            experiment_name: Used as a subdirectory name under :attr:`output_dir`.
            run_tags: Must include ``model_name``, ``prompt_version``, and
                      ``stage``; validated before writing.

        Returns:
            A run ID of the form ``"local-run-{uuid4}"``.

        Raises:
            ValueError: If *run_tags* is missing a required key.
        """
        self._validate_run_tags(run_tags)
        run_id = f"local-run-{uuid.uuid4()}"

        out_dir = self.output_dir / experiment_name
        out_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_id": run_id,
            "experiment_name": experiment_name,
            "tags": run_tags,
            "metrics": {m.name: m.value for m in report.metrics},
            "params": {
                "stage": report.stage,
                "run_date": report.run_date.isoformat(),
                "model_name": report.model_name,
                "prompt_version": report.prompt_version,
            },
        }
        (out_dir / f"{run_id}.json").write_text(json.dumps(payload, indent=2))
        self.published.append(report)
        return run_id

    def publish_batch(
        self,
        reports: list[EvaluationReport],
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> list[str]:
        return [self.publish(r, experiment_name, run_tags) for r in reports]
