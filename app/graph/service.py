"""Graph Service: the single entrypoint every caller should use.

Orchestrates `GraphExecutor`, `ExecutionPlanner`, `NodeRegistry`, and
`GraphVisualizer`, mirroring the "one facade per subsystem" convention
every prior sprint established (`CareerProfileService`, `LLMService`,
`ResumeGenerationService`, `CoverLetterGenerationService`,
`JobDiscoveryService`).
"""

from dataclasses import dataclass, field
from typing import Any

from app.graph.checkpoint import CheckpointStore
from app.graph.context import ExecutionContext
from app.graph.exceptions import GraphValidationError
from app.graph.executor import ExecutionMode, GraphExecutor
from app.graph.graph import Graph
from app.graph.memory import GraphMemory
from app.graph.planner import ExecutionPlanner
from app.graph.registry import NodeRegistry
from app.graph.state import ExecutionState
from app.graph.visualizer import GraphVisualizer


@dataclass
class GraphValidationResult:
    """Non-raising validation outcome — see `GraphService.validate_graph`."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)


class GraphService:
    def __init__(
        self,
        executor: GraphExecutor | None = None,
        registry: NodeRegistry | None = None,
        checkpoint_store: CheckpointStore | None = None,
    ) -> None:
        self._executor = executor or GraphExecutor(checkpoint_store=checkpoint_store)
        self.registry = registry or NodeRegistry()
        self._planner = ExecutionPlanner()

    async def run_graph(
        self,
        graph: Graph,
        *,
        inputs: dict[str, Any] | None = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        run_id: str | None = None,
        node_priorities: dict[str, int] | None = None,
        checkpoint: bool = False,
        context: ExecutionContext | None = None,
    ) -> ExecutionState:
        return await self._executor.run(
            graph,
            inputs=inputs,
            mode=mode,
            run_id=run_id,
            node_priorities=node_priorities,
            checkpoint=checkpoint,
            context=context,
        )

    async def resume_graph(
        self,
        graph: Graph,
        state: ExecutionState,
        *,
        memory: GraphMemory | None = None,
        inputs: dict[str, Any] | None = None,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
        node_priorities: dict[str, int] | None = None,
        checkpoint: bool = False,
        context: ExecutionContext | None = None,
    ) -> ExecutionState:
        return await self._executor.resume(
            graph,
            state,
            memory=memory,
            inputs=inputs,
            mode=mode,
            node_priorities=node_priorities,
            checkpoint=checkpoint,
            context=context,
        )

    def validate_graph(self, graph: Graph) -> GraphValidationResult:
        try:
            graph.validate()
        except GraphValidationError as exc:
            return GraphValidationResult(is_valid=False, errors=[str(exc)])
        return GraphValidationResult(is_valid=True)

    def plan_graph(self, graph: Graph) -> list[list[str]]:
        """The execution waves `run_graph(..., mode=PARALLEL)` would follow."""
        return self._planner.plan(graph)

    def visualize_graph(
        self,
        graph: Graph,
        *,
        state: ExecutionState | None = None,
        output_format: str = "mermaid",
    ) -> str | dict[str, list[str]]:
        """Render `graph` as `"mermaid"`, `"ascii"`, `"execution_tree"`, or `"dependency_graph"`."""
        visualizer = GraphVisualizer(graph)
        if output_format == "mermaid":
            return visualizer.to_mermaid(state)
        if output_format == "ascii":
            return visualizer.to_ascii()
        if output_format == "execution_tree":
            if state is None:
                raise ValueError("output_format='execution_tree' requires an ExecutionState.")
            return visualizer.execution_tree(state)
        if output_format == "dependency_graph":
            return visualizer.dependency_graph()
        raise ValueError(f"Unknown visualization output_format: '{output_format}'.")
