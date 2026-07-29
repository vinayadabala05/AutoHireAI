"""Anthropic Claude provider (Messages API)."""

import time

import httpx

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import GenerationError, ProviderNotConfiguredError
from app.llm.models import GenerationMetadata, LLMProvider, LLMRequest, LLMResponse, TokenUsage
from app.llm.registry import register_provider

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"


@register_provider("claude")
class ClaudeProvider(BaseLLMProvider):
    """Provider implementation for Anthropic's Claude Messages API."""

    @property
    def provider_name(self) -> str:
        return LLMProvider.CLAUDE.value

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.config.is_configured:
            raise ProviderNotConfiguredError(
                "Claude provider requires ANTHROPIC_API_KEY to be set."
            )

        payload: dict[str, object] = {
            "model": request.model or self.config.model,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "temperature": (
                request.temperature if request.temperature is not None else self.config.temperature
            ),
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        headers = {
            "x-api-key": self.config.api_key or "",
            "anthropic-version": _ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

        start = time.monotonic()
        data = await self._send(_ANTHROPIC_API_URL, headers, payload)
        latency_ms = (time.monotonic() - start) * 1000

        content = "".join(
            block.get("text", "") for block in data.get("content", []) if isinstance(block, dict)
        )
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            metadata=GenerationMetadata(
                provider=LLMProvider.CLAUDE,
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
            raise GenerationError(f"Claude API call failed: {exc}") from exc
