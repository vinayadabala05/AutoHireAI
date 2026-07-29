"""Pydantic models for the LLM platform layer.

These models form the contract between business logic and the platform:
requests going in, responses coming out, plus configuration and validation
result shapes. No provider-specific fields live here.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMProvider(StrEnum):
    """Supported LLM providers."""

    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"


class PromptContext(BaseModel):
    """Values used to render a prompt template."""

    model_config = ConfigDict(extra="allow")

    category: str
    name: str
    variables: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    """Token accounting for a single generation call."""

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class GenerationMetadata(BaseModel):
    """Metadata describing how a generation call was executed."""

    provider: LLMProvider
    model: str
    latency_ms: float = Field(ge=0)
    attempt: int = Field(ge=1, default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMRequest(BaseModel):
    """A single request to generate content from an LLM provider."""

    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """The result of a generation call."""

    content: str
    usage: TokenUsage
    metadata: GenerationMetadata
    raw: dict[str, Any] | None = None


class ProviderConfiguration(BaseModel):
    """Configuration required to construct and operate a provider."""

    provider: LLMProvider
    model: str
    api_key: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    retry_count: int = Field(default=2, ge=0)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


class ValidationIssue(BaseModel):
    """A single problem found while validating an LLM response."""

    field: str | None = None
    message: str


class ResponseValidationResult(BaseModel):
    """The outcome of validating an LLM response."""

    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    parsed: dict[str, Any] | None = None
