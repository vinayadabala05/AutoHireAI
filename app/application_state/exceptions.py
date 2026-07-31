"""Exceptions for the Application State & Recovery Engine."""

from app.application_state.models import ApplicationStatus


class ApplicationStateError(Exception):
    """Base exception for this package."""


class ApplicationNotFoundError(ApplicationStateError):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"No application state found for job_id={job_id!r}.")


class InvalidTransitionError(ApplicationStateError):
    def __init__(
        self, job_id: str, from_status: ApplicationStatus, to_status: ApplicationStatus
    ) -> None:
        self.job_id = job_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid transition for job_id={job_id!r}: {from_status.value} -> {to_status.value}."
        )


class DuplicateSubmissionError(ApplicationStateError):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"job_id={job_id!r} was already submitted; refusing to resubmit.")
