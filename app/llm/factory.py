"""Factory for constructing `BaseLLMProvider` instances.

Adding a future provider requires only one new class (registered via
`@register_provider`) — this factory never needs to change.
"""

from app.llm import providers as _providers  # noqa: F401  (registers built-in providers)
from app.llm.base import BaseLLMProvider
from app.llm.config import LLMSettings, get_llm_settings
from app.llm.models import LLMProvider, ProviderConfiguration
from app.llm.registry import get_provider_class


class LLMFactory:
    """Builds configured `BaseLLMProvider` instances by provider name."""

    @staticmethod
    def create(provider: LLMProvider, config: ProviderConfiguration) -> BaseLLMProvider:
        """Instantiate the provider registered under `provider` with `config`."""
        provider_cls = get_provider_class(provider.value)
        return provider_cls(config)

    @staticmethod
    def create_default(settings: LLMSettings | None = None) -> BaseLLMProvider:
        """Instantiate the provider selected by `LLMSettings.provider`."""
        resolved_settings = settings or get_llm_settings()
        config = resolved_settings.to_provider_configuration()
        return LLMFactory.create(resolved_settings.provider, config)
