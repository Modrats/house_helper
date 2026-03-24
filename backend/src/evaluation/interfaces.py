"""IEvaluator abstract base class for the evaluation pipeline.

Evaluation code must only import from models/ and interfaces/ — never
from services/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import EvaluationReport


class IEvaluator(ABC):
    """Abstract base class for pipeline evaluators."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(self, samples: list[Any], **kwargs: Any) -> EvaluationReport: ...
