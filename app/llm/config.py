"""Configuration for the LLM platform layer.

All provider selection, model choice, and generation parameters are sourced
from environment variables — nothing here is hardcoded per-environment. API
keys use their real SDK-conventional env var names (e.g. `ANTHROPIC_API_KEY`)
rather than the `LLM_` prefix, so the same variables work if a provider SDK
is later used directly for anything outside this platform (e.g. tooling).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.models import LLMProvider, ProviderConfiguration


class LLMSettings(BaseSettings):
    """Central LLM platform settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        case_sensitive=False,
        extra="ignore",
    )

    provider: LLMProvider = LLMProvider.CLAUDE
    model: str = "claude-sonnet-5"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    timeout_seconds: float = Field(default=30.0, gt=0)
    retry_count: int = Field(default=2, ge=0)

    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")

    def api_key_for(self, provider: LLMProvider) -> str | None:
        """Return the configured API key for the given provider, if any."""
        return {
            LLMProvider.CLAUDE: self.anthropic_api_key,
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.GEMINI: self.gemini_api_key,
        }[provider]

    def to_provider_configuration(
        self, provider: LLMProvider | None = None
    ) -> ProviderConfiguration:
        """Build a `ProviderConfiguration` for the given (or default) provider."""
        resolved_provider = provider or self.provider
        return ProviderConfiguration(
            provider=resolved_provider,
            model=self.model,
            api_key=self.api_key_for(resolved_provider),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
            retry_count=self.retry_count,
        )


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Return a cached `LLMSettings` instance (parsed once per process)."""
    return LLMSettings()


llm_settings = get_llm_settings()
