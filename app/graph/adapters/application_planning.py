"""Adapter: wraps Sprint 9's `ApplicationPlanningService` as a `GraphNode`.

Only wraps the existing service's public `build_application_package()`
method — no change to `app.application_planning` at all. Added in Sprint 11
alongside `browser_automation.py`, extending this package exactly the way
its own docs describe: one new file per wrapped service, no change to any
existing adapter, `graph.py`, or `executor.py`.
"""

from typing import Any

from app.application_planning.models import ApplicationPackage
from app.application_planning.service import ApplicationPlanningService
from app.career_profile.models import CareerProfile
from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import DiscoveredJob


class ApplicationPlanningNode(GraphNode):
    """Produces an `ApplicationPackage` via `ApplicationPlanningService`'s
    `build_application_package()`.

    Deliberately calls `build_application_package()`, not `create_plan()`
    — the decision of whether to apply is made once, cheaply, *before*
    this node runs (via `evaluate_job()`, which needs no resume/cover
    letter generation); this node only runs at all once that decision is
    already APPLY, so it goes straight to building the package.
    """

    def __init__(
        self,
        node_id: str,
        service: ApplicationPlanningService,
        *,
        name: str = "Application Planning",
        job_input: str = "job",
        profile_input: str = "profile",
        blueprint_input: str = "blueprint",
        job_id_input: str = "job_id",
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._service = service
        self._job_input = job_input
        self._profile_input = profile_input
        self._blueprint_input = blueprint_input
        self._job_id_input = job_id_input

    async def execute(self, context: ExecutionContext) -> ApplicationPackage:
        job: DiscoveredJob = resolve_input(context, self._job_input)
        profile: CareerProfile = resolve_input(context, self._profile_input)
        blueprint: ResumeBlueprint = resolve_input(context, self._blueprint_input)
        job_id = resolve_input(context, self._job_id_input, required=False)
        return await self._service.build_application_package(job, profile, blueprint, job_id=job_id)
