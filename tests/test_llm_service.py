"""Unit tests for `app.llm.service.LLMService` — retry logic, structured
generation, and delegation to the provider/prompt loader/validator.

Uses a fake in-memory provider rather than mocking HTTP, since the retry
and validation logic under test lives entirely in `LLMService`, not in any
real provider's network call.
"""

from pathlib import Path

import pytest

from app.llm.base import BaseLLMProvider
from app.llm.config import LLMSettings
from app.llm.exceptions import GenerationError, ProviderNotConfiguredError, ResponseValidationError
from app.llm.models import (
    GenerationMetadata,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderConfiguration,
    TokenUsage,
)
from app.llm.service import LLMService
from app.llm.validator import ResponseValidator


class _ScriptedProvider(BaseLLMProvider):
    """A fake provider whose `generate()` follows a scripted sequence of outcomes."""

    def __init__(self, config: ProviderConfiguration, outcomes: list[Exception | str]) -> None:
        super().__init__(config)
        self._outcomes = list(outcomes)
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "scripted"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return LLMResponse(
            content=outcome,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            metadata=GenerationMetadata(
                provider=LLMProvider.CLAUDE, model="test-model", latency_ms=1.0
            ),
        )

    async def health_check(self) -> bool:
        return True


def _make_service(outcomes: list[Exception | str], retry_count: int = 2) -> LLMService:
    config = ProviderConfiguration(
        provider=LLMProvider.CLAUDE, model="test-model", retry_count=retry_count
    )
    provider = _ScriptedProvider(config, outcomes)
    settings = LLMSettings(_env_file=None, retry_count=retry_count)
    return LLMService(provider=provider, settings=settings, validator=ResponseValidator())


async def test_generate_succeeds_on_first_attempt() -> None:
    service = _make_service(["hello"])
    response = await service.generate(LLMRequest(prompt="hi"))
    assert response.content == "hello"
    assert response.metadata.attempt == 1


async def test_generate_retries_transient_generation_errors() -> None:
    service = _make_service([GenerationError("boom"), "recovered"])
    response = await service.generate(LLMRequest(prompt="hi"))
    assert response.content == "recovered"
    assert response.metadata.attempt == 2
    assert service.provider.calls == 2  # type: ignore[attr-defined]


async def test_generate_does_not_retry_provider_not_configured() -> None:
    service = _make_service([ProviderNotConfiguredError("no key"), "unreachable"])
    with pytest.raises(ProviderNotConfiguredError):
        await service.generate(LLMRequest(prompt="hi"))
    assert service.provider.calls == 1  # type: ignore[attr-defined]


async def test_generate_raises_after_exhausting_retries() -> None:
    service = _make_service(
        [GenerationError("one"), GenerationError("two"), GenerationError("three")], retry_count=2
    )
    with pytest.raises(GenerationError):
        await service.generate(LLMRequest(prompt="hi"))
    assert service.provider.calls == 3  # type: ignore[attr-defined]


async def test_generate_structured_returns_parsed_result() -> None:
    service = _make_service(['{"match_score": 90}'])
    response, result = await service.generate_structured(
        LLMRequest(prompt="hi"), required_fields=["match_score"]
    )
    assert response.content == '{"match_score": 90}'
    assert result.is_valid is True
    assert result.parsed == {"match_score": 90}


async def test_generate_structured_raises_on_invalid_json() -> None:
    service = _make_service(["not json"])
    with pytest.raises(ResponseValidationError):
        await service.generate_structured(LLMRequest(prompt="hi"))


async def test_health_check_delegates_to_provider() -> None:
    service = _make_service(["irrelevant"])
    assert await service.health_check() is True


def test_estimate_tokens_delegates_to_provider() -> None:
    service = _make_service(["irrelevant"])
    assert service.estimate_tokens("abcd" * 10) == 10


def test_render_prompt_uses_configured_prompt_loader(tmp_path: Path) -> None:
    (tmp_path / "resume").mkdir()
    (tmp_path / "resume" / "hi.txt").write_text("Hi {{name}}", encoding="utf-8")
    config = ProviderConfiguration(provider=LLMProvider.CLAUDE, model="test-model")
    provider = _ScriptedProvider(config, ["unused"])
    settings = LLMSettings(_env_file=None)
    service = LLMService(provider=provider, settings=settings, prompts_dir=tmp_path)
    assert service.render_prompt("resume", "hi", {"name": "Jordan"}) == "Hi Jordan"
