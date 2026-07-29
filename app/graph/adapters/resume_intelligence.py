"""Adapter: wraps Sprint 3's `ResumePlanner` as a `GraphNode`.

Only wraps the existing planner's public, synchronous `plan()` method — no
change to `app.intelligence` at all. `ResumePlanner.plan()` takes Sprint 3's
own `CareerContext` (not the Sprint 3.5 `CareerProfile`, since no adapter
between them exists yet upstream — see `docs/graph_engine.md`) plus a
`JobPostingInput`; both must be supplied as graph inputs or upstream
node outputs.
"""

from typing import Any

from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode
from app.intelligence.models import CareerContext, JobPostingInput, ResumeBlueprint
from app.intelligence.resume_planner import ResumePlanner


class ResumeIntelligenceNode(GraphNode):
    """Produces a `ResumeBlueprint` via `ResumePlanner.plan(job, career_context)`."""

    def __init__(
        self,
        node_id: str,
        planner: ResumePlanner | None = None,
        *,
        name: str = "Resume Intelligence",
        job_input: str = "job",
        career_context_input: str = "career_context",
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._planner = planner or ResumePlanner()
        self._job_input = job_input
        self._career_context_input = career_context_input

    async def execute(self, context: ExecutionContext) -> ResumeBlueprint:
        job: JobPostingInput = resolve_input(context, self._job_input)
        career_context: CareerContext = resolve_input(context, self._career_context_input)
        return self._planner.plan(job, career_context)
