"""Unit tests for `app.browser_automation.models`."""

from datetime import UTC, datetime

from app.browser_automation.models import (
    FormFillResult,
    LoginCredentials,
    PortalType,
    QuestionInputType,
    SubmissionResult,
    SubmissionStatus,
    UnsupportedQuestion,
)


def test_form_fill_result_is_complete_when_no_unsupported_questions() -> None:
    result = FormFillResult()
    assert result.is_complete is True


def test_form_fill_result_is_incomplete_with_unsupported_questions() -> None:
    result = FormFillResult(
        unsupported_questions=[
            UnsupportedQuestion(
                label="Why us?",
                input_type=QuestionInputType.TEXT,
                selector="#why",
                reason="free text",
            )
        ]
    )
    assert result.is_complete is False


def test_login_credentials_password_is_secret() -> None:
    credentials = LoginCredentials(username="jordan@example.com", password="hunter2")
    assert "hunter2" not in repr(credentials)
    assert credentials.password.get_secret_value() == "hunter2"


def test_submission_result_defaults() -> None:
    result = SubmissionResult(
        status=SubmissionStatus.SUBMITTED,
        portal=PortalType.GREENHOUSE,
        company="Acme",
        job_id="abc",
        application_url="https://example.com",
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.application_id is None
    assert result.screenshot_path is None
    assert result.error_message is None
    assert result.metadata == {}


def test_submission_result_serializes_round_trip() -> None:
    result = SubmissionResult(
        status=SubmissionStatus.FAILED,
        portal=PortalType.LEVER,
        company="Acme",
        job_id="abc",
        application_url="https://example.com",
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        error_message="boom",
    )
    restored = SubmissionResult.model_validate_json(result.model_dump_json())
    assert restored.status is SubmissionStatus.FAILED
    assert restored.error_message == "boom"
