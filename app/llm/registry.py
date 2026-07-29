"""Self-registration registry for LLM providers.

Adding a new provider requires exactly one new class decorated with
`@register_provider("name")` — no changes to the factory or any other
module are needed.
"""

from collections.abc import Callable

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import ProviderNotFoundError

_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {}


def register_provider(name: str) -> Callable[[type[BaseLLMProvider]], type[BaseLLMProvider]]:
    """Class decorator that registers a `BaseLLMProvider` subclass under `name`."""

    def decorator(provider_cls: type[BaseLLMProvider]) -> type[BaseLLMProvider]:
        _PROVIDER_REGISTRY[name] = provider_cls
        return provider_cls

    return decorator


def get_provider_class(name: str) -> type[BaseLLMProvider]:
    """Look up a registered provider class by name.

    Raises `ProviderNotFoundError` if no provider is registered under `name`.
    """
    try:
        return _PROVIDER_REGISTRY[name]
    except KeyError as exc:
        raise ProviderNotFoundError(f"No LLM provider registered under name '{name}'") from exc


def available_providers() -> list[str]:
    """Return the names of all currently registered providers."""
    return sorted(_PROVIDER_REGISTRY)
