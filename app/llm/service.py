"""The single public entry point to the LLM platform.

Business modules must communicate with LLMs only through `LLMService` — never
by importing a provider or the httpx client directly. This keeps every future
AI feature (resume generation, cover letters, interview prep, chat) fully
decoupled from which provider is actually configured.
"""

from pathlib import Path

from app.llm.base import BaseLLMProvider
from app.llm.config import LLMSettings, get_llm_settings
from app.llm.exceptions import GenerationError, ProviderNotConfiguredError, ResponseValidationError
from app.llm.factory import LLMFactory
from app.llm.models import LLMRequest, LLMResponse, PromptContext, ResponseValidationResult
from app.llm.prompt_loader import PromptLoader
from app.llm.validator import ResponseValidator


class LLMService:
    """Facade over provider selection, retries, prompts, and validation."""

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        settings: LLMSettings | None = None,
        prompt_loader: PromptLoader | None = None,
        validator: ResponseValidator | None = None,
        prompts_dir: Path | str = "prompts",
    ) -> None:
        self.settings = settings or get_llm_settings()
        self.provider = provider or LLMFactory.create_default(self.settings)
        self.prompt_loader = prompt_loader or PromptLoader(prompts_dir)
        self.validator = validator or ResponseValidator()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate content, retrying transient failures up to `retry_count` times.

        `ProviderNotConfiguredError` is never retried — it indicates a
        configuration problem, not a transient one.
        """
        last_error: GenerationError | None = None
        attempts = self.settings.retry_count + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self.provider.generate(request)
            except ProviderNotConfiguredError:
                raise
            except GenerationError as exc:
                last_error = exc
                continue
            response.metadata.attempt = attempt
            return response
        assert last_error is not None
        raise last_error

    async def generate_structured(
        self, request: LLMRequest, required_fields: list[str] | None = None
    ) -> tuple[LLMResponse, ResponseValidationResult]:
        """Generate content and validate it as a JSON object with required fields.

        Raises `ResponseValidationError` if validation fails.
        """
        response = await self.generate(request)
        result = self.validator.validate_json(response, required_fields=required_fields)
        if not result.is_valid:
            raise ResponseValidationError(
                f"LLM response failed structured validation: {[i.message for i in result.issues]}"
            )
        return response, result

    async def health_check(self) -> bool:
        """Return True if the configured provider is reachable."""
        return await self.provider.health_check()

    def estimate_tokens(self, text: str) -> int:
        """Approximate the token count for `text` using the provider's estimator."""
        return self.provider.estimate_tokens(text)

    def render_prompt(self, category: str, name: str, variables: dict[str, object]) -> str:
        """Render a prompt template with the given variables."""
        context = PromptContext(category=category, name=name, variables=variables)
        return self.prompt_loader.render(category, name, context)
