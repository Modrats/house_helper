"""ILLMService abstract base class — single LLM integration point.

All LLM consumers (classifier, photo checker, criteria evaluator) use
this interface.  Implementations isolate the actual API call behind a
method boundary so tests can record and replay responses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.llm import LLMResponse


class ILLMService(ABC):
    """Abstract base class for LLM service operations."""

    @abstractmethod
    def classify_image(
        self,
        prompt: str,
        image_b64: str,
        media_type: str,
        response_model: type[LLMResponse],
    ) -> LLMResponse:
        """Send an image to a vision model and return a structured response.

        Args:
            prompt: System/user prompt describing the classification task.
            image_b64: Base64-encoded image data.
            media_type: MIME type of the image (e.g. ``"image/jpeg"``).
            response_model: LLMResponse subclass for structured output.

        Returns:
            An instance of *response_model* populated by the LLM.
        """

    @abstractmethod
    def complete_structured(
        self,
        prompt: str,
        response_model: type[LLMResponse],
    ) -> LLMResponse:
        """Send a text prompt and return a structured response.

        Args:
            prompt: The text prompt.
            response_model: LLMResponse subclass for structured output.

        Returns:
            An instance of *response_model* populated by the LLM.
        """
