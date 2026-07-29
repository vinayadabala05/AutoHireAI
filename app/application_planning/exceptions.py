"""Exception hierarchy for the Application Planning Engine.

Mirrors every prior sprint's convention (`app.llm.exceptions`,
`app.job_discovery.exceptions`, `app.graph.exceptions`): one base class,
specific subclasses so callers can catch broadly or narrowly.
"""


class ApplicationPlanningError(Exception):
    """Base class for every exception raised by `app.application_planning`."""


class PackageBuildError(ApplicationPlanningError):
    """Raised when resume/cover letter generation fails for a job."""

    def __init__(self, job_id: str, original: BaseException) -> None:
        self.job_id = job_id
        self.original = original
        super().__init__(f"Failed to build application package for job '{job_id}': {original}")


class PlanningConfigurationError(ApplicationPlanningError):
    """Raised when a service is asked to do something it wasn't configured for.

    E.g. `build_application_package()` without a package builder injected.
    """
