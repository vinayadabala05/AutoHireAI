"""Unit tests for the concrete provider implementations.

No real network calls are made: successful-path tests monkeypatch the
provider's protected `_send` method, and unconfigured-path tests rely on
`ProviderNotConfiguredError` being raised before any network call happens.
"""

import httpx
import pytest

from app.llm.exceptions import GenerationError, ProviderNotConfiguredError
from app.llm.models import LLMProvider, LLMRequest, ProviderConfiguration
from app.llm.providers.claude import ClaudeProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider


def _config(provider: LLMProvider, api_key: str | None) -> ProviderConfiguration:
    return ProviderConfiguration(provider=provider, model="test-model", api_key=api_key)


async def test_claude_generate_raises_when_unconfigured() -> None:
    provider = ClaudeProvider(_config(LLMProvider.CLAUDE, None))
    with pytest.raises(ProviderNotConfiguredError):
        await provider.generate(LLMRequest(prompt="hi"))


async def test_claude_generate_parses_successful_response(monkeypatch) -> None:
    provider = ClaudeProvider(_config(LLMProvider.CLAUDE, "sk-test"))

    async def fake_send(url, headers, payload):
        return {
            "content": [{"type": "text", "text": "Hello there"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

    monkeypatch.setattr(provider, "_send", fake_send)
    response = await provider.generate(LLMRequest(prompt="hi"))
    assert response.content == "Hello there"
    assert response.usage.total_tokens == 15
    assert response.metadata.provider is LLMProvider.CLAUDE


async def test_claude_generate_wraps_http_errors(monkeypatch) -> None:
    provider = ClaudeProvider(_config(LLMProvider.CLAUDE, "sk-test"))

    async def fake_send(url, headers, payload):
        raise GenerationError("network down")

    monkeypatch.setattr(provider, "_send", fake_send)
    with pytest.raises(GenerationError):
        await provider.generate(LLMRequest(prompt="hi"))


async def test_claude_health_check_false_when_unconfigured() -> None:
    provider = ClaudeProvider(_config(LLMProvider.CLAUDE, None))
    assert await provider.health_check() is False


async def test_openai_generate_raises_when_unconfigured() -> None:
    provider = OpenAIProvider(_config(LLMProvider.OPENAI, None))
    with pytest.raises(ProviderNotConfiguredError):
        await provider.generate(LLMRequest(prompt="hi"))


async def test_openai_generate_parses_successful_response(monkeypatch) -> None:
    provider = OpenAIProvider(_config(LLMProvider.OPENAI, "sk-test"))

    async def fake_send(url, headers, payload):
        return {
            "choices": [{"message": {"content": "Hi from GPT"}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
        }

    monkeypatch.setattr(provider, "_send", fake_send)
    response = await provider.generate(LLMRequest(prompt="hi"))
    assert response.content == "Hi from GPT"
    assert response.usage.total_tokens == 12


async def test_gemini_generate_raises_when_unconfigured() -> None:
    provider = GeminiProvider(_config(LLMProvider.GEMINI, None))
    with pytest.raises(ProviderNotConfiguredError):
        await provider.generate(LLMRequest(prompt="hi"))


async def test_gemini_generate_parses_successful_response(monkeypatch) -> None:
    provider = GeminiProvider(_config(LLMProvider.GEMINI, "gemini-test"))

    async def fake_send(url, headers, params, payload):
        return {
            "candidates": [{"content": {"parts": [{"text": "Hi from Gemini"}]}}],
            "usageMetadata": {
                "promptTokenCount": 6,
                "candidatesTokenCount": 3,
                "totalTokenCount": 9,
            },
        }

    monkeypatch.setattr(provider, "_send", fake_send)
    response = await provider.generate(LLMRequest(prompt="hi"))
    assert response.content == "Hi from Gemini"
    assert response.usage.total_tokens == 9


async def test_provider_send_wraps_httpx_errors(monkeypatch) -> None:
    provider = ClaudeProvider(_config(LLMProvider.CLAUDE, "sk-test"))

    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FailingClient())
    with pytest.raises(GenerationError):
        await provider.generate(LLMRequest(prompt="hi"))


def test_estimate_tokens_is_shared_across_providers() -> None:
    provider = ClaudeProvider(_config(LLMProvider.CLAUDE, "sk-test"))
    assert provider.estimate_tokens("a" * 40) == 10
