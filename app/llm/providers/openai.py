"""OpenAI provider (Chat Completions API)."""

import time

import httpx

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import GenerationError, ProviderNotConfiguredError
from app.llm.models import GenerationMetadata, LLMProvider, LLMRequest, LLMResponse, TokenUsage
from app.llm.registry import register_provider

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


@register_provider("openai")
class OpenAIProvider(BaseLLMProvider):
    """Provider implementation for OpenAI's Chat Completions API."""

    @property
    def provider_name(self) -> str:
        return LLMProvider.OPENAI.value

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.config.is_configured:
            raise ProviderNotConfiguredError("OpenAI provider requires OPENAI_API_KEY to be set.")

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, object] = {
            "model": request.model or self.config.model,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": (
                request.temperature if request.temperature is not None else self.config.temperature
            ),
            "messages": messages,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key or ''}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        data = await self._send(_OPENAI_API_URL, headers, payload)
        latency_ms = (time.monotonic() - start) * 1000

        choices = data.get("choices", [])
        content = ""
        if choices and isinstance(choices[0], dict):
            content = choices[0].get("message", {}).get("content", "")

        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            metadata=GenerationMetadata(
                provider=LLMProvider.OPENAI,
                model=str(payload["model"]),
                latency_ms=latency_ms,
            ),
            raw=data,
        )

    async def health_check(self) -> bool:
        if not self.config.is_configured:
            return False
        try:
            await self.generate(LLMRequest(prompt="ping", max_tokens=1))
        except GenerationError:
            return False
        return True

    async def _send(
        self, url: str, headers: dict[str, str], payload: dict[str, object]
    ) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result: dict[str, object] = response.json()
                return result
        except httpx.HTTPError as exc:
            raise GenerationError(f"OpenAI API call failed: {exc}") from exc
