"""Base class for all LLM structured output responses.

Every model passed to ILLMService as a response_model must extend this class.
This constrains the LLM service to only return domain-specific response types,
not arbitrary Pydantic models.
"""

from __future__ import annotations

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Base class for structured responses returned by ILLMService."""

    model_config = {"frozen": True}
