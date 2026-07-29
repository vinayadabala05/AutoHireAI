"""Abstract base provider contract for the LLM platform layer.

No provider-specific logic lives here — only the shared contract every
provider must implement, plus a single generic (non-provider-specific)
utility (`estimate_tokens`) that is a universal approximation, not tied to
any provider's actual tokenizer.
"""

from abc import ABC, abstractmethod

from app.llm.models import LLMRequest, LLMResponse, ProviderConfiguration

_CHARS_PER_TOKEN_ESTIMATE = 4


class BaseLLMProvider(ABC):
    """Contract every concrete LLM provider must implement."""

    def __init__(self, config: ProviderConfiguration) -> None:
        self.config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """The canonical name of this provider (e.g. "claude")."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate content for the given request.

        Raises `ProviderNotConfiguredError` if the provider lacks required
        configuration (e.g. an API key), and `GenerationError` for any
        transient failure during the call itself.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is configured and reachable."""

    def estimate_tokens(self, text: str) -> int:
        """Approximate token count using a universal chars-per-token heuristic.

        This is intentionally provider-agnostic (~4 characters per token,
        a common rough approximation for English text) and is not a
        substitute for a provider's real tokenizer.
        """
        return max(1, len(text) // _CHARS_PER_TOKEN_ESTIMATE)
