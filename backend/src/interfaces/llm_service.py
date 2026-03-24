"""ILLMService abstract base class — single LLM integration point.

All LLM consumers (classifier, photo checker, criteria evaluator) use
this interface.  Implementations isolate the actual API call behind a
method boundary so tests can record/replay via VCR (ADR-004).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class ILLMService(ABC):
    """Abstract base class for LLM service operations."""

    @abstractmethod
    def classify_image(
        self,
        prompt: str,
        image_b64: str,
        media_type: str,
        response_model: type[T],
    ) -> T:
        """Send an image to a vision model and return a structured response.

        Args:
            prompt: System/user prompt describing the classification task.
            image_b64: Base64-encoded image data.
            media_type: MIME type of the image (e.g. ``"image/jpeg"``).
            response_model: Pydantic model class used for structured output.

        Returns:
            An instance of *response_model* populated by the LLM.
        """

    @abstractmethod
    def complete_structured(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:
        """Send a text prompt and return a structured response.

        Args:
            prompt: The text prompt.
            response_model: Pydantic model class used for structured output.

        Returns:
            An instance of *response_model* populated by the LLM.
        """
