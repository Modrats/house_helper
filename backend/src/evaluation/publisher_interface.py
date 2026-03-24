"""IMetricsPublisher abstract base class for evaluation metric publishing.

Allows swapping between real AML publishing, a null publisher for tests,
and any future metrics backend without touching evaluation runner code.

Evaluation code must only import from models/ and interfaces/ — never
from services/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


class StageMetrics(BaseModel):
    """Metrics collected for a single pipeline stage in one evaluation run.

    Attributes:
        stage: Stage identifier, e.g. ``"text_filter"``, ``"photo_classifier"``.
        metrics: Mapping of metric name to numeric value,
                 e.g. ``{"accuracy": 0.97, "latency_s": 1.4}``.
    """

    model_config = {"frozen": True}

    stage: str = Field(description="Pipeline stage identifier")
    metrics: dict[str, float] = Field(
        description="Metric name → numeric value pairs for this stage"
    )


class EvaluationReport(BaseModel):
    """Full evaluation report produced by one evaluation run.

    Attributes:
        model_name: Name/version of the LLM or model under evaluation,
                    e.g. ``"gpt-4o-2024-11-20"``.
        prompt_version: Version string for the prompt template used,
                        e.g. ``"v2.1"``.
        run_date: UTC timestamp when the evaluation run started.
        stage_metrics: Per-stage metric collections.
    """

    model_config = {"frozen": True}

    model_name: str = Field(description="Name/version of the model under evaluation")
    prompt_version: str = Field(description="Version of the prompt template used")
    run_date: datetime = Field(description="UTC timestamp of the evaluation run start")
    stage_metrics: list[StageMetrics] = Field(
        description="Metrics collected per pipeline stage"
    )


class IMetricsPublisher(ABC):
    """Abstract base class for publishing evaluation metrics to a metrics backend.

    Abstracts the destination (Azure ML, null sink for tests, local CSV, etc.)
    so evaluation runners are not coupled to AML.

    Example implementations:
        - AMLPublisher: Publishes to Azure ML experiments via mlflow
        - NullPublisher: Discards all metrics (useful in tests and dry-run mode)
    """

    @abstractmethod
    def publish(
        self,
        report: EvaluationReport,
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> str:
        """Publish one evaluation report as a single experiment run.

        Args:
            report: The evaluation report to publish.
            experiment_name: Target experiment name in the metrics backend.
            run_tags: Arbitrary string tags to attach to the run.
                      Should include at minimum ``model_name``,
                      ``prompt_version``, and ``stage``.

        Returns:
            An opaque run identifier assigned by the backend.
        """

    @abstractmethod
    def publish_batch(
        self,
        reports: list[EvaluationReport],
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> list[str]:
        """Publish multiple evaluation reports as separate experiment runs.

        Args:
            reports: Evaluation reports to publish.
            experiment_name: Target experiment name in the metrics backend.
            run_tags: Tags applied to every run in the batch.

        Returns:
            List of run identifiers in the same order as ``reports``.
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    _REQUIRED_TAG_KEYS: frozenset[str] = frozenset({"model_name", "prompt_version", "stage"})

    def _validate_run_tags(self, run_tags: dict[str, str]) -> None:
        """Raise ``ValueError`` if any required tag key is absent.

        Args:
            run_tags: Caller-supplied tags dict to validate.

        Raises:
            ValueError: When one or more of ``model_name``, ``prompt_version``,
                        or ``stage`` are missing from *run_tags*.
        """
        missing = self._REQUIRED_TAG_KEYS - run_tags.keys()
        if missing:
            raise ValueError(
                f"run_tags is missing required keys: {', '.join(sorted(missing))}. "
                f"Required: {', '.join(sorted(self._REQUIRED_TAG_KEYS))}"
            )
