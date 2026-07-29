"""Structured validation of LLM responses.

Every response returned from a provider must pass through here before
business logic consumes it — this is the single place that checks for
empty output, invalid JSON, and missing required fields.
"""

import json
from typing import Any

from app.llm.models import LLMResponse, ResponseValidationResult, ValidationIssue


class ResponseValidator:
    """Validates `LLMResponse` content against structural expectations."""

    def validate_text(self, response: LLMResponse) -> ResponseValidationResult:
        """Validate a plain-text response: only checks for non-empty content."""
        issues: list[ValidationIssue] = []
        if not response.content or not response.content.strip():
            issues.append(ValidationIssue(field="content", message="Response content is empty."))
        return ResponseValidationResult(is_valid=not issues, issues=issues)

    def validate_json(
        self, response: LLMResponse, required_fields: list[str] | None = None
    ) -> ResponseValidationResult:
        """Validate a response expected to contain a JSON object.

        Checks that content is non-empty, parses as valid JSON, parses to a
        dict (not a list/scalar), and contains every field in
        `required_fields` if given.
        """
        issues: list[ValidationIssue] = []

        if not response.content or not response.content.strip():
            issues.append(ValidationIssue(field="content", message="Response content is empty."))
            return ResponseValidationResult(is_valid=False, issues=issues)

        parsed: Any
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(field=None, message=f"Response is not valid JSON: {exc}"))
            return ResponseValidationResult(is_valid=False, issues=issues)

        if not isinstance(parsed, dict):
            issues.append(
                ValidationIssue(
                    field=None,
                    message=f"Expected a JSON object, got {type(parsed).__name__}.",
                )
            )
            return ResponseValidationResult(is_valid=False, issues=issues)

        for field in required_fields or []:
            if field not in parsed:
                issues.append(
                    ValidationIssue(field=field, message=f"Required field '{field}' is missing.")
                )

        return ResponseValidationResult(is_valid=not issues, issues=issues, parsed=parsed)
