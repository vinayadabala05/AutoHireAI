"""LLM platform layer.

Provides a single provider-agnostic entry point (`LLMService`) for all future
AI features. Business logic must never import a provider directly.
"""

from app.llm.exceptions import (
    GenerationError,
    LLMError,
    PromptNotFoundError,
    PromptRenderError,
    ProviderNotConfiguredError,
    ProviderNotFoundError,
    ResponseValidationError,
)
from app.llm.models import (
    GenerationMetadata,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    PromptContext,
    ProviderConfiguration,
    ResponseValidationResult,
    TokenUsage,
    ValidationIssue,
)
from app.llm.service import LLMService

__all__ = [
    "GenerationError",
    "GenerationMetadata",
    "LLMError",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMService",
    "ProviderConfiguration",
    "ProviderNotConfiguredError",
    "ProviderNotFoundError",
    "PromptContext",
    "PromptNotFoundError",
    "PromptRenderError",
    "ResponseValidationError",
    "ResponseValidationResult",
    "TokenUsage",
    "ValidationIssue",
]
