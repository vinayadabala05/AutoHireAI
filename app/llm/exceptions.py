"""Exception hierarchy for the LLM platform layer."""


class LLMError(Exception):
    """Base class for all LLM platform errors."""


class ProviderNotFoundError(LLMError):
    """Raised when a requested provider name is not registered."""


class ProviderNotConfiguredError(LLMError):
    """Raised when a provider is selected but missing required configuration (e.g. API key).

    Not retryable — retrying without fixing configuration will always fail the same way.
    """


class GenerationError(LLMError):
    """Raised when a provider call fails during generation (network, timeout, provider error).

    Retryable — transient failures may succeed on a subsequent attempt.
    """


class PromptNotFoundError(LLMError):
    """Raised when a requested prompt template file does not exist."""


class PromptRenderError(LLMError):
    """Raised when a prompt template cannot be rendered (missing placeholder, circular include)."""


class ResponseValidationError(LLMError):
    """Raised when an LLM response fails structured validation."""
