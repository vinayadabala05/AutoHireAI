"""File-based prompt loading and rendering.

Prompts are never hardcoded in Python — every template lives under the
`prompts/` directory as a plain text file, organized by category. Templates
support two constructs:

  - `{{variable_name}}` — substituted from the rendering context
  - `{{> category/name}}` — includes another template verbatim before
    variable substitution, allowing shared fragments (e.g. `prompts/shared/`)
    to be reused across categories
"""

import re
from pathlib import Path

from app.llm.exceptions import PromptNotFoundError, PromptRenderError
from app.llm.models import PromptContext

_VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")
_PARTIAL_PATTERN = re.compile(r"{{>\s*([a-zA-Z0-9_/-]+)\s*}}")


class PromptLoader:
    """Loads, resolves, and renders prompt templates from disk."""

    def __init__(self, base_dir: Path | str = "prompts") -> None:
        self.base_dir = Path(base_dir)

    def _template_path(self, category: str, name: str) -> Path:
        return self.base_dir / category / f"{name}.txt"

    def load(self, category: str, name: str) -> str:
        """Read the raw template text for `category/name`, without rendering."""
        path = self._template_path(category, name)
        if not path.is_file():
            raise PromptNotFoundError(f"Prompt template not found: {category}/{name}")
        return path.read_text(encoding="utf-8")

    def _resolve_partials(self, text: str, _seen: frozenset[str] = frozenset()) -> str:
        def _replace(match: re.Match[str]) -> str:
            ref = match.group(1)
            if ref in _seen:
                raise PromptRenderError(f"Circular prompt include detected: {ref}")
            category, _, name = ref.partition("/")
            if not name:
                raise PromptRenderError(
                    f"Invalid partial reference (expected 'category/name'): {ref}"
                )
            partial_text = self.load(category, name)
            return self._resolve_partials(partial_text, _seen | {ref})

        return _PARTIAL_PATTERN.sub(_replace, text)

    def placeholders(self, category: str, name: str) -> list[str]:
        """Return the sorted, de-duplicated set of `{{variable}}` names in a template."""
        raw = self._resolve_partials(self.load(category, name))
        return sorted({match.group(1) for match in _VARIABLE_PATTERN.finditer(raw)})

    def validate_template(self, category: str, name: str) -> list[str]:
        """Alias for `placeholders` — returns the declared variable names for a template."""
        return self.placeholders(category, name)

    def render(self, category: str, name: str, context: PromptContext) -> str:
        """Render `category/name`, substituting variables from `context.variables`.

        Raises `PromptRenderError` if any placeholder has no matching value.
        """
        raw = self._resolve_partials(self.load(category, name))
        missing: list[str] = []

        def _substitute(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in context.variables:
                missing.append(key)
                return match.group(0)
            return str(context.variables[key])

        rendered = _VARIABLE_PATTERN.sub(_substitute, raw)
        if missing:
            raise PromptRenderError(
                f"Missing values for placeholder(s) {sorted(set(missing))} in {category}/{name}"
            )
        return rendered
