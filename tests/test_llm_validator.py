"""Unit tests for `app.llm.validator.ResponseValidator`."""

from app.llm.models import GenerationMetadata, LLMProvider, LLMResponse, TokenUsage
from app.llm.validator import ResponseValidator


def _response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        metadata=GenerationMetadata(
            provider=LLMProvider.CLAUDE, model="claude-sonnet-5", latency_ms=1.0
        ),
    )


def test_validate_text_passes_for_nonempty_content() -> None:
    result = ResponseValidator().validate_text(_response("Hello world"))
    assert result.is_valid is True
    assert result.issues == []


def test_validate_text_fails_for_empty_content() -> None:
    result = ResponseValidator().validate_text(_response("   "))
    assert result.is_valid is False
    assert any(issue.field == "content" for issue in result.issues)


def test_validate_json_passes_for_valid_object_with_required_fields() -> None:
    result = ResponseValidator().validate_json(
        _response('{"match_score": 80, "skills": ["Python"]}'),
        required_fields=["match_score", "skills"],
    )
    assert result.is_valid is True
    assert result.parsed == {"match_score": 80, "skills": ["Python"]}


def test_validate_json_fails_for_missing_required_field() -> None:
    result = ResponseValidator().validate_json(
        _response('{"match_score": 80}'), required_fields=["match_score", "skills"]
    )
    assert result.is_valid is False
    assert any(issue.field == "skills" for issue in result.issues)


def test_validate_json_fails_for_invalid_json() -> None:
    result = ResponseValidator().validate_json(_response("not json"))
    assert result.is_valid is False
    assert result.parsed is None


def test_validate_json_fails_for_non_object_json() -> None:
    result = ResponseValidator().validate_json(_response("[1, 2, 3]"))
    assert result.is_valid is False


def test_validate_json_fails_for_empty_content() -> None:
    result = ResponseValidator().validate_json(_response(""))
    assert result.is_valid is False
