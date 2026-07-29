"""Unit tests for `app.llm.registry` — provider self-registration."""

import pytest

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import ProviderNotFoundError
from app.llm.models import LLMRequest, LLMResponse
from app.llm.registry import (
    _PROVIDER_REGISTRY,
    available_providers,
    get_provider_class,
    register_provider,
)


class _DummyProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "dummy"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True


def test_register_provider_adds_to_registry() -> None:
    original = dict(_PROVIDER_REGISTRY)
    try:
        register_provider("dummy_test_provider")(_DummyProvider)
        assert get_provider_class("dummy_test_provider") is _DummyProvider
        assert "dummy_test_provider" in available_providers()
    finally:
        _PROVIDER_REGISTRY.clear()
        _PROVIDER_REGISTRY.update(original)


def test_get_provider_class_raises_for_unknown_name() -> None:
    with pytest.raises(ProviderNotFoundError):
        get_provider_class("does-not-exist")


def test_built_in_providers_are_registered() -> None:
    import app.llm.providers  # noqa: F401  (triggers registration)

    names = available_providers()
    assert {"claude", "openai", "gemini"}.issubset(set(names))
