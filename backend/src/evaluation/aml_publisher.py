"""Azure ML metrics publisher — publishes evaluation reports via mlflow.

Uses mlflow's AzureML tracking backend so the module remains importable
without the package installed (lazy import, same pattern as openai in
the LLM judge evaluator).

Configuration is supplied entirely through environment variables so the
publisher can be swapped for a NullPublisher in tests without patching
environment state.

Required environment variables (pick one of two approaches):

  Option A — single URI:
    AML_TRACKING_URI   Full mlflow tracking URI for the AzureML workspace.

  Option B — component parts (URI is constructed at runtime):
    AML_SUBSCRIPTION_ID   Azure subscription ID.
    AML_RESOURCE_GROUP    Azure resource group containing the workspace.
    AML_WORKSPACE_NAME    Azure ML workspace name.
    AML_REGION            Azure region slug, e.g. "westeurope".
"""

from __future__ import annotations

import logging
import os

from .publisher_interface import EvaluationReport, IMetricsPublisher

logger = logging.getLogger(__name__)

_COMPONENT_ENV_VARS: tuple[str, ...] = (
    "AML_SUBSCRIPTION_ID",
    "AML_RESOURCE_GROUP",
    "AML_WORKSPACE_NAME",
    "AML_REGION",
)


def _build_tracking_uri() -> str:
    """Return the mlflow tracking URI, either directly from env or constructed.

    Raises:
        EnvironmentError: If neither ``AML_TRACKING_URI`` nor all four
                          component variables are set.
    """
    if uri := os.environ.get("AML_TRACKING_URI"):
        return uri

    missing = [v for v in _COMPONENT_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            "AMLPublisher requires either AML_TRACKING_URI or all four component "
            f"variables. Missing: {', '.join(missing)}"
        )

    sub = os.environ["AML_SUBSCRIPTION_ID"]
    rg = os.environ["AML_RESOURCE_GROUP"]
    ws = os.environ["AML_WORKSPACE_NAME"]
    region = os.environ["AML_REGION"]

    return (
        f"azureml://{region}.api.azureml.ms/mlflow/v1.0/subscriptions/{sub}"
        f"/resourceGroups/{rg}/providers/Microsoft.MachineLearningServices"
        f"/workspaces/{ws}"
    )


class AMLPublisher(IMetricsPublisher):
    """Publishes evaluation metrics to Azure ML experiments via mlflow.

    Args:
        tracking_uri: Full mlflow tracking URI for the AzureML workspace.
                      Pass an explicit value in tests to avoid reading env vars.
                      If ``None``, the URI is built from environment variables
                      at construction time (see module docstring).

    Example::

        # Production — reads AML_TRACKING_URI from env
        publisher = AMLPublisher()
        run_id = publisher.publish(report, "house-helper-eval", {"stage": "text_filter"})

        # Test — inject the URI directly (or use NullPublisher)
        publisher = AMLPublisher(tracking_uri="http://localhost:5000")
    """

    def __init__(self, tracking_uri: str | None = None) -> None:
        self._tracking_uri = tracking_uri if tracking_uri is not None else _build_tracking_uri()

    # ------------------------------------------------------------------
    # mlflow lazy-load helper
    # ------------------------------------------------------------------

    def _get_mlflow(self):  # type: ignore[return]
        """Return the mlflow module, raising a clear error if not installed."""
        try:
            import mlflow  # noqa: PLC0415

            return mlflow
        except ImportError as exc:
            raise ImportError(
                "mlflow is required to use AMLPublisher. "
                "Install with: pip install 'house-helper-backend[aml]'"
            ) from exc

    # ------------------------------------------------------------------
    # IMetricsPublisher implementation
    # ------------------------------------------------------------------

    def publish(
        self,
        report: EvaluationReport,
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> str:
        """Publish one evaluation report as a single AML experiment run.

        Logs every stage metric as ``{stage}.{metric_name}`` and attaches
        ``model_name``, ``prompt_version``, ``run_date`` from the report
        plus any caller-supplied ``run_tags``.

        Args:
            report: The evaluation report to publish.
            experiment_name: Target AML experiment name.
            run_tags: Tags for this run; should include at minimum
                      ``model_name``, ``prompt_version``, and ``stage``.

        Returns:
            The mlflow run ID assigned by the AML backend.
        """
        self._validate_run_tags(run_tags)
        mlflow = self._get_mlflow()
        mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(experiment_name)

        tags: dict[str, str] = {
            "model_name": report.model_name,
            "prompt_version": report.prompt_version,
            "run_date": report.run_date.isoformat(),
            **run_tags,
        }

        with mlflow.start_run(tags=tags) as run:
            for stage_metrics in report.stage_metrics:
                for metric_name, value in stage_metrics.metrics.items():
                    mlflow.log_metric(f"{stage_metrics.stage}.{metric_name}", value)

            run_id: str = run.info.run_id

        logger.info(
            "Published evaluation report to AML experiment=%r run_id=%s",
            experiment_name,
            run_id,
        )
        return run_id

    def publish_batch(
        self,
        reports: list[EvaluationReport],
        experiment_name: str,
        run_tags: dict[str, str],
    ) -> list[str]:
        """Publish multiple evaluation reports as separate AML experiment runs.

        Args:
            reports: Evaluation reports to publish.
            experiment_name: Target AML experiment name.
            run_tags: Tags applied to every run in the batch.

        Returns:
            List of mlflow run IDs in the same order as ``reports``.
        """
        return [self.publish(report, experiment_name, run_tags) for report in reports]
