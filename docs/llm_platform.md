# LLM Platform Layer (Sprint 4)

## 1. Purpose

The LLM platform layer (`app/llm/`) is the **only** part of AutoHire AI allowed to
know that Claude, OpenAI, or Gemini exist. Every future AI feature — resume
generation, cover letter generation, ATS scoring, interview prep, chat — talks
to a single facade, `LLMService`, and never imports a provider, an HTTP client,
or a vendor SDK directly.

This sprint builds the platform itself. No resume generation, cover letter
generation, browser automation, or job scraping logic is implemented here —
those are future sprints that will *consume* this layer.

## 2. Architecture

```
app/llm/
├── models.py         # LLMRequest, LLMResponse, TokenUsage, GenerationMetadata,
│                     # PromptContext, ProviderConfiguration, ValidationIssue,
│                     # ResponseValidationResult, LLMProvider enum
├── exceptions.py      # LLMError hierarchy
├── config.py          # LLMSettings (env-driven configuration)
├── base.py            # BaseLLMProvider (abstract contract)
├── registry.py         # Self-registration: name -> provider class
├── providers/
│   ├── claude.py       # ClaudeProvider  (Anthropic Messages API)
│   ├── openai.py       # OpenAIProvider  (Chat Completions API)
│   └── gemini.py       # GeminiProvider  (generateContent API)
├── factory.py          # LLMFactory: builds a configured provider by name
├── prompt_loader.py    # PromptLoader: file-based templates + partials
├── validator.py        # ResponseValidator: structural checks on responses
├── service.py           # LLMService: the single public facade
└── __init__.py

prompts/
├── resume/, cover_letter/, job_analysis/, interview/,
│   ats/, behavioral/, technical/   # feature-specific templates
└── shared/                          # reusable fragments (persona, output format)
```

### Dependency direction

```
business logic  →  LLMService  →  BaseLLMProvider (abstract)
                         │              ▲
                         │              │ implements
                         ├─ PromptLoader │
                         ├─ ResponseValidator
                         └─ LLMFactory ──┴─ ClaudeProvider / OpenAIProvider / GeminiProvider
```

No arrows point backwards: providers know nothing about `LLMService`, and
`LLMService` never imports a concrete provider class directly — only through
`LLMFactory` + `registry`.

## 3. Sequence diagram — a single `generate()` call

```
Business module        LLMService              Provider (e.g. Claude)     Anthropic API
      |                     |                          |                       |
      |-- generate(req) --->|                          |                       |
      |                     |-- provider.generate() -->|                       |
      |                     |                          |-- POST /v1/messages ->|
      |                     |                          |<---- 200 JSON --------|
      |                     |<---- LLMResponse ---------|                       |
      |                     |  (attempt=1)             |                       |
      |<---- LLMResponse ---|                          |                       |
```

On a transient failure, `LLMService.generate()` retries up to
`settings.retry_count` additional times (only for `GenerationError`);
`ProviderNotConfiguredError` is never retried since it indicates a
configuration problem, not a transient one.

## 4. Provider abstraction

`BaseLLMProvider` (`app/llm/base.py`) is an ABC with three abstract members:

- `provider_name` (property) — canonical name, e.g. `"claude"`
- `async generate(request: LLMRequest) -> LLMResponse`
- `async health_check() -> bool`

...plus one concrete, shared method: `estimate_tokens(text) -> int`, a
universal `len(text) // 4` heuristic. It is intentionally **not** abstract —
it isn't provider-specific, so duplicating it three times would violate DRY
for no benefit. Real per-provider tokenization can override it later if
needed, but no provider currently does.

Each concrete provider (`ClaudeProvider`, `OpenAIProvider`, `GeminiProvider`):

1. Checks `self.config.is_configured` (i.e. an API key is present) and raises
   `ProviderNotConfiguredError` **before** attempting any network call.
2. Builds a provider-specific request payload matching that vendor's real
   REST API shape (Anthropic Messages API, OpenAI Chat Completions, Google
   Gemini `generateContent`).
3. Sends the request via a protected `_send()` method using `httpx.AsyncClient`,
   catching `httpx.HTTPError` and re-raising as `GenerationError` (retryable).
4. Parses the provider-specific response shape into the common `LLMResponse`
   model (`content`, `usage`, `metadata`, `raw`).

Because credentials are not available in this environment, `generate()` will
raise `ProviderNotConfiguredError` in practice — but the architecture is
real: dropping a valid `ANTHROPIC_API_KEY` into the environment makes
`ClaudeProvider` make genuine API calls with no code changes.

## 5. Extending with a new provider

Adding a fourth provider (e.g. Mistral) requires exactly one new file:

```python
# app/llm/providers/mistral.py
from app.llm.base import BaseLLMProvider
from app.llm.registry import register_provider

@register_provider("mistral")
class MistralProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "mistral"

    async def generate(self, request): ...
    async def health_check(self): ...
```

Then:

1. Add `MISTRAL = "mistral"` to the `LLMProvider` enum in `models.py`.
2. Add a `mistral_api_key` field to `LLMSettings` in `config.py`.
3. Import the new module in `app/llm/providers/__init__.py` (so the
   `@register_provider` decorator runs).

`LLMFactory`, `LLMService`, and every business module are unaffected —
`LLMFactory.create()` looks the provider up in the registry by name.

## 6. Prompt system

Prompts are never hardcoded in Python. `PromptLoader` (`app/llm/prompt_loader.py`)
reads plain-text files from `prompts/<category>/<name>.txt` and supports:

- **Variable substitution**: `{{variable_name}}`, replaced from
  `PromptContext.variables`. Rendering raises `PromptRenderError` if any
  placeholder has no matching value.
- **Partial includes**: `{{> category/name}}`, resolved recursively before
  variable substitution — used for shared fragments like `prompts/shared/persona.txt`
  and `prompts/shared/output_format_json.txt`. Circular includes are detected
  and raise `PromptRenderError`.
- **Template validation**: `validate_template(category, name)` (alias:
  `placeholders`) returns the declared variable names in a template, so a
  future feature can validate it has all the context it needs before calling
  `generate()`.

Category folders provided this sprint (each with at least one real
template, to prove the pattern rather than leave empty directories):
`resume/`, `cover_letter/`, `job_analysis/`, `interview/`, `ats/`,
`behavioral/`, `technical/`, `shared/`.

## 7. Models

| Model | Purpose |
|---|---|
| `LLMRequest` | prompt, optional system prompt, model/temperature/max_tokens overrides |
| `LLMResponse` | content, `TokenUsage`, `GenerationMetadata`, raw provider payload |
| `TokenUsage` | prompt/completion/total token counts |
| `GenerationMetadata` | provider, model, latency, attempt number, timestamp |
| `PromptContext` | category, name, variables dict for rendering |
| `ProviderConfiguration` | provider, model, api_key, temperature, max_tokens, timeout, retry_count |
| `ValidationIssue` / `ResponseValidationResult` | structured validation errors |
| `LLMProvider` (`StrEnum`) | `CLAUDE`, `OPENAI`, `GEMINI` |

## 8. Response validation

`ResponseValidator` (`app/llm/validator.py`) is the single place that checks
every AI response before business logic sees it:

- `validate_text(response)` — rejects empty/whitespace-only content.
- `validate_json(response, required_fields=None)` — rejects empty content,
  invalid JSON, non-object JSON (e.g. a bare list or scalar), and reports any
  `required_fields` missing from the parsed object.

Both return a `ResponseValidationResult(is_valid, issues, parsed)` rather
than raising directly, so callers can inspect issues; `LLMService.generate_structured()`
is the one place that turns a failed result into a raised
`ResponseValidationError`.

## 9. Configuration

`LLMSettings` (`app/llm/config.py`) is a `pydantic_settings.BaseSettings`
subclass using `env_prefix="LLM_"`:

| Env var | Field | Default |
|---|---|---|
| `LLM_PROVIDER` | `provider` | `claude` |
| `LLM_MODEL` | `model` | `claude-sonnet-5` |
| `LLM_TEMPERATURE` | `temperature` | `0.7` |
| `LLM_MAX_TOKENS` | `max_tokens` | `1024` |
| `LLM_TIMEOUT_SECONDS` | `timeout_seconds` | `30.0` |
| `LLM_RETRY_COUNT` | `retry_count` | `2` |

API keys intentionally bypass the `LLM_` prefix (via `validation_alias`), to
match each vendor's real SDK-conventional environment variable name:

| Env var | Field |
|---|---|
| `ANTHROPIC_API_KEY` | `anthropic_api_key` |
| `OPENAI_API_KEY` | `openai_api_key` |
| `GEMINI_API_KEY` | `gemini_api_key` |

`LLMSettings.to_provider_configuration(provider=None)` builds a
`ProviderConfiguration` for the configured (or explicitly overridden)
provider, wiring in the correct API key automatically.

## 10. `LLMService` — the one public entry point

```python
from app.llm.service import LLMService

service = LLMService()  # wires provider + settings + prompt loader + validator

response = await service.generate(LLMRequest(prompt="..."))

response, result = await service.generate_structured(
    LLMRequest(prompt="..."), required_fields=["match_score"]
)

healthy = await service.health_check()
tokens = service.estimate_tokens("some text")
rendered = service.render_prompt("resume", "summary_rewrite", {"full_name": "...", ...})
```

Retry logic lives entirely in `LLMService.generate()`: it retries only
`GenerationError` (transient), up to `settings.retry_count` additional
attempts, and never retries `ProviderNotConfiguredError` (a configuration
problem that a retry cannot fix).

## 11. Testing strategy

Sprint 4 has no database dependency — it's fully decoupled from Sprints 2/3/3.5
— so its tests run standalone with no Postgres container required:

- `test_llm_registry.py` — registration, lookup, `ProviderNotFoundError`
- `test_llm_factory.py` — correct provider class per `LLMProvider`, `create_default`
- `test_llm_prompt_loader.py` — load/render/partials/circular-include/validation
- `test_llm_validator.py` — text/JSON validation, missing fields, malformed JSON
- `test_llm_config.py` — env-prefix mapping, API key aliasing, cached singleton
- `test_llm_service.py` — retry logic (success, transient retry, non-retryable,
  exhausted retries), `generate_structured`, `health_check`, `estimate_tokens`,
  `render_prompt` — using a scripted fake provider, not real HTTP
- `test_llm_providers.py` — per-provider unconfigured behavior, successful
  response parsing (via monkeypatched `_send`), and HTTP error wrapping

## 12. What this sprint deliberately does NOT do

- No resume generation, cover letter generation, or ATS scoring logic — only
  the prompt templates and platform to support them later.
- No browser automation, no Playwright, no job scraping.
- No real API keys — the architecture supports real calls, but this sandbox
  has no credentials, so every provider's `generate()` raises
  `ProviderNotConfiguredError` in practice.
- No changes to Sprint 1–3.5 code — the existing test suite is unaffected.
