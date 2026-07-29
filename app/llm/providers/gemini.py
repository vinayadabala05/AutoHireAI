"""Google Gemini provider (generateContent API)."""

import time

import httpx

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import GenerationError, ProviderNotConfiguredError
from app.llm.models import GenerationMetadata, LLMProvider, LLMRequest, LLMResponse, TokenUsage
from app.llm.registry import register_provider

_GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


@register_provider("gemini")
class GeminiProvider(BaseLLMProvider):
    """Provider implementation for Google's Gemini `generateContent` API."""

    @property
    def provider_name(self) -> str:
        return LLMProvider.GEMINI.value

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.config.is_configured:
            raise ProviderNotConfiguredError("Gemini provider requires GEMINI_API_KEY to be set.")

        model = request.model or self.config.model
        contents = [{"role": "user", "parts": [{"text": request.prompt}]}]
        payload: dict[str, object] = {
            "contents": contents,
            "generationConfig": {
                "temperature": (
                    request.temperature
                    if request.temperature is not None
                    else self.config.temperature
                ),
                "maxOutputTokens": request.max_tokens or self.config.max_tokens,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        url = _GEMINI_API_URL_TEMPLATE.format(model=model)
        headers = {"Content-Type": "application/json"}
        params = {"key": self.config.api_key or ""}

        start = time.monotonic()
        data = await self._send(url, headers, params, payload)
        latency_ms = (time.monotonic() - start) * 1000

        candidates = data.get("candidates", [])
        content = ""
        if candidates and isinstance(candidates[0], dict):
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))

        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = int(usage_meta.get("promptTokenCount", 0))
        completion_tokens = int(usage_meta.get("candidatesTokenCount", 0))
        total_tokens = int(usage_meta.get("totalTokenCount", prompt_tokens + completion_tokens))

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            metadata=GenerationMetadata(
                provider=LLMProvider.GEMINI,
                model=model,
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
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(url, headers=headers, params=params, json=payload)
                response.raise_for_status()
                result: dict[str, object] = response.json()
                return result
        except httpx.HTTPError as exc:
            raise GenerationError(f"Gemini API call failed: {exc}") from exc
