"""Azure OpenAI service — concrete ILLMService implementation.

This is the ONLY module that imports ``openai``.  The ``_call_api``
helper is the single method boundary for VCR-style test mocking
(ADR-004).
"""

from __future__ import annotations

import json
import logging
import os
from typing import TypeVar

from openai import AzureOpenAI
from pydantic import BaseModel

from ..interfaces.llm_service import ILLMService

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AzureOpenAIService(ILLMService):
    """ILLMService backed by Azure OpenAI.

    Reads connection details from environment variables at construction
    time and raises ``RuntimeError`` immediately if any are missing.
    """

    def __init__(self) -> None:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

        missing = [
            name
            for name, val in [
                ("AZURE_OPENAI_ENDPOINT", endpoint),
                ("AZURE_OPENAI_API_KEY", api_key),
                ("AZURE_OPENAI_DEPLOYMENT", deployment),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Set them before constructing AzureOpenAIService."
            )

        self._client = AzureOpenAI(
            azure_endpoint=endpoint,  # type: ignore[arg-type]
            api_key=api_key,
            api_version="2024-10-21",
        )
        self._deployment: str = deployment  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify_image(
        self,
        prompt: str,
        image_b64: str,
        media_type: str,
        response_model: type[T],
    ) -> T:
        """Send an image to a vision model and return a structured response."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ]
        raw = self._call_api(messages, response_model)
        return raw

    def complete_structured(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:
        """Send a text prompt and return a structured response."""
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages, response_model)

    # ------------------------------------------------------------------
    # VCR mocking boundary (ADR-004)
    # ------------------------------------------------------------------

    def _call_api(self, messages: list[dict], response_model: type[T]) -> T:
        """Execute the actual OpenAI API call.

        This is the single integration point with the LLM — isolate it
        for VCR-style test mocking per ADR-004.
        """
        schema = response_model.model_json_schema()
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=150,
            temperature=0.1,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return response_model.model_validate(data)
