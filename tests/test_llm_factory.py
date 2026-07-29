"""Unit tests for `app.llm.factory.LLMFactory`."""

from app.llm.config import LLMSettings
from app.llm.factory import LLMFactory
from app.llm.models import LLMProvider, ProviderConfiguration
from app.llm.providers.claude import ClaudeProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider


def test_create_returns_claude_provider() -> None:
    config = ProviderConfiguration(provider=LLMProvider.CLAUDE, model="claude-sonnet-5")
    provider = LLMFactory.create(LLMProvider.CLAUDE, config)
    assert isinstance(provider, ClaudeProvider)
    assert provider.provider_name == "claude"


def test_create_returns_openai_provider() -> None:
    config = ProviderConfiguration(provider=LLMProvider.OPENAI, model="gpt-4o")
    provider = LLMFactory.create(LLMProvider.OPENAI, config)
    assert isinstance(provider, OpenAIProvider)


def test_create_returns_gemini_provider() -> None:
    config = ProviderConfiguration(provider=LLMProvider.GEMINI, model="gemini-1.5-pro")
    provider = LLMFactory.create(LLMProvider.GEMINI, config)
    assert isinstance(provider, GeminiProvider)


def test_create_default_uses_settings_provider() -> None:
    settings = LLMSettings(provider=LLMProvider.OPENAI, model="gpt-4o")
    provider = LLMFactory.create_default(settings)
    assert isinstance(provider, OpenAIProvider)
    assert provider.config.model == "gpt-4o"
