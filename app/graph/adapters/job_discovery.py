"""Adapter: wraps Sprint 7's `JobDiscoveryService` as a `GraphNode`.

Only wraps the existing service's public `discover_ranked()` method — no
change to `app.job_discovery` at all.
"""

from typing import Any

from app.career_profile.models import CareerProfile
from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode
from app.intelligence.models import ResumeBlueprint
from app.job_discovery.models import (
    JobFilterCriteria,
    JobRankingResult,
    JobSearchPreferences,
    JobSearchQuery,
)
from app.job_discovery.service import JobDiscoveryService


class JobDiscoveryNode(GraphNode):
    """Produces ranked `DiscoveredJob`s via `JobDiscoveryService.discover_ranked()`."""

    def __init__(
        self,
        node_id: str,
        service: JobDiscoveryService,
        *,
        name: str = "Job Discovery",
        query_input: str = "query",
        profile_input: str = "profile",
        blueprint_input: str = "blueprint",
        criteria_input: str = "criteria",
        preferences_input: str = "preferences",
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._service = service
        self._query_input = query_input
        self._profile_input = profile_input
        self._blueprint_input = blueprint_input
        self._criteria_input = criteria_input
        self._preferences_input = preferences_input

    async def execute(self, context: ExecutionContext) -> list[JobRankingResult]:
        query: JobSearchQuery = resolve_input(context, self._query_input)
        profile: CareerProfile = resolve_input(context, self._profile_input)
        blueprint: ResumeBlueprint | None = resolve_input(
            context, self._blueprint_input, required=False
        )
        criteria: JobFilterCriteria | None = resolve_input(
            context, self._criteria_input, required=False
        )
        preferences: JobSearchPreferences | None = resolve_input(
            context, self._preferences_input, required=False
        )
        return await self._service.discover_ranked(
            query, profile, blueprint, criteria=criteria, preferences=preferences
        )
