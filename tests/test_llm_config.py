"""Unit tests for `app.llm.config.LLMSettings`."""

from app.llm.config import LLMSettings, get_llm_settings
from app.llm.models import LLMProvider


def test_default_settings_use_claude() -> None:
    settings = LLMSettings(_env_file=None)
    assert settings.provider is LLMProvider.CLAUDE
    assert settings.retry_count == 2
    assert settings.temperature == 0.7


def test_env_prefix_overrides_provider_and_model(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_RETRY_COUNT", "5")
    settings = LLMSettings(_env_file=None)
    assert settings.provider is LLMProvider.OPENAI
    assert settings.model == "gpt-4o"
    assert settings.retry_count == 5


def test_api_keys_bypass_llm_prefix(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    settings = LLMSettings(_env_file=None)
    assert settings.anthropic_api_key == "sk-ant-test"
    assert settings.openai_api_key == "sk-openai-test"
    assert settings.gemini_api_key == "gemini-test"
    assert settings.api_key_for(LLMProvider.CLAUDE) == "sk-ant-test"
    assert settings.api_key_for(LLMProvider.OPENAI) == "sk-openai-test"
    assert settings.api_key_for(LLMProvider.GEMINI) == "gemini-test"


def test_to_provider_configuration_builds_expected_shape() -> None:
    settings = LLMSettings(_env_file=None, provider=LLMProvider.CLAUDE, model="claude-sonnet-5")
    config = settings.to_provider_configuration()
    assert config.provider is LLMProvider.CLAUDE
    assert config.model == "claude-sonnet-5"
    assert config.is_configured is (config.api_key is not None)


def test_to_provider_configuration_accepts_explicit_provider_override() -> None:
    settings = LLMSettings(_env_file=None, provider=LLMProvider.CLAUDE)
    config = settings.to_provider_configuration(LLMProvider.GEMINI)
    assert config.provider is LLMProvider.GEMINI


def test_get_llm_settings_is_cached() -> None:
    assert get_llm_settings() is get_llm_settings()
