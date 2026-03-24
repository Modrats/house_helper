from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, computed_field

from .samples import (
    CriteriaEvaluationSample,
    ImagineeredSample,
    PhotoClassificationSample,
    TextFilterSample,
)


class MetricResult(BaseModel):
    model_config = {"frozen": True}

    name: str
    value: float
    unit: str
    passed: bool
    threshold: float


class EvaluationReport(BaseModel):
    model_config = {"frozen": True}

    stage: str
    model_name: str | None = None
    prompt_version: str | None = None
    run_date: datetime
    metrics: list[MetricResult]

    @computed_field
    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.metrics)


__all__ = [
    "MetricResult",
    "EvaluationReport",
    "TextFilterSample",
    "PhotoClassificationSample",
    "CriteriaEvaluationSample",
    "ImagineeredSample",
]
