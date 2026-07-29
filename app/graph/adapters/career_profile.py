"""Adapter: wraps Sprint 3.5's `CareerProfileService` as a `GraphNode`.

Only wraps the existing service's public `build_profile()` method — no
change to `app.career_profile` at all. The wrapped `CareerProfileService`
instance is supplied at construction time (it already needs a live
`AsyncSession`, which the graph engine has no opinion about); the graph
only supplies the `user_id` input.
"""

import uuid
from typing import Any

from app.career_profile.models import CareerProfile
from app.career_profile.service import CareerProfileService
from app.graph.adapters._common import resolve_input
from app.graph.context import ExecutionContext
from app.graph.node import GraphNode


class CareerProfileNode(GraphNode):
    """Builds a `CareerProfile` for `user_id` via `CareerProfileService.build_profile()`."""

    def __init__(
        self,
        node_id: str,
        service: CareerProfileService,
        *,
        name: str = "Career Profile",
        user_id_input: str = "user_id",
        **kwargs: Any,
    ) -> None:
        super().__init__(node_id, name=name, **kwargs)
        self._service = service
        self._user_id_input = user_id_input

    async def execute(self, context: ExecutionContext) -> CareerProfile:
        user_id = resolve_input(context, self._user_id_input)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        return await self._service.build_profile(user_id)
