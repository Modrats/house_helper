"""Azure OpenAI service — concrete ILLMService implementation.

This is the ONLY module that imports ``openai``.
"""

from __future__ import annotations

import json
import logging
import os

from openai import AzureOpenAI

from ..exceptions import MissingConfigError
from ..interfaces.llm_service import ILLMService
from ..models.llm import LLMResponse

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
)


def load_azure_openai_config() -> dict[str, str]:
    """Load Azure OpenAI connection details from environment variables.

    Returns:
        A dict keyed by variable name with their values.

    Raises:
        MissingConfigError: If any required variable is unset or empty.
    """
    values = {name: os.environ.get(name, "") for name in _REQUIRED_ENV_VARS}
    missing = [name for name, val in values.items() if not val]
    if missing:
        raise MissingConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them before constructing AzureOpenAIService."
        )
    return values


class AzureOpenAIService(ILLMService):
    """ILLMService backed by Azure OpenAI.

    Reads connection details from environment variables at construction
    time and raises ``MissingConfigError`` immediately if any are missing.
    """

    def __init__(self) -> None:
        config = load_azure_openai_config()

        self._client = AzureOpenAI(
            azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
            api_key=config["AZURE_OPENAI_API_KEY"],
            api_version="2024-10-21",
        )
        self._deployment = config["AZURE_OPENAI_DEPLOYMENT"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify_image(
        self,
        prompt: str,
        image_b64: str,
        media_type: str,
        response_model: type[LLMResponse],
    ) -> LLMResponse:
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
        response_model: type[LLMResponse],
    ) -> LLMResponse:
        """Send a text prompt and return a structured response."""
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(messages, response_model)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_api(self, messages: list[dict], response_model: type[LLMResponse]) -> LLMResponse:
        """Execute the actual OpenAI API call.

        This is the single integration point with the LLM — isolate it
        so tests can record and replay responses.
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
