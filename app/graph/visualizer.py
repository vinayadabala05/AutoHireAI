"""Graph visualization: Mermaid, ASCII, execution tree, dependency graph.

All four are pure string/dict builders over a `Graph` (optionally
annotated with an `ExecutionState`) — no rendering engine, no image
generation, no external dependency, consistent with this package's
"lightweight and dependency-free where practical" mandate.
"""

from app.graph.graph import Graph
from app.graph.state import ExecutionState, ExecutionStatus

_MERMAID_STATUS_STYLE: dict[ExecutionStatus, str] = {
    ExecutionStatus.SUCCEEDED: "fill:#c6f6d5,stroke:#22543d,color:#1a202c",
    ExecutionStatus.FAILED: "fill:#fed7d7,stroke:#822727,color:#1a202c",
    ExecutionStatus.SKIPPED: "fill:#edf2f7,stroke:#4a5568,color:#1a202c",
    ExecutionStatus.CANCELLED: "fill:#feebc8,stroke:#7b341e,color:#1a202c",
    ExecutionStatus.RUNNING: "fill:#bee3f8,stroke:#2c5282,color:#1a202c",
    ExecutionStatus.RETRYING: "fill:#fefcbf,stroke:#744210,color:#1a202c",
}


class GraphVisualizer:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def dependency_graph(self) -> dict[str, list[str]]:
        """`node_id -> [ids it depends on]`, for programmatic consumption."""
        return {node.id: list(node.dependencies) for node in self.graph.nodes.values()}

    def to_mermaid(self, state: ExecutionState | None = None) -> str:
        """A Mermaid `flowchart TD` diagram, optionally colored by execution status."""
        lines = ["flowchart TD"]
        for node in self.graph.nodes.values():
            safe_name = node.name.replace('"', "'")
            lines.append(f'    {node.id}["{safe_name}"]')
        for edge in self.graph.edges:
            lines.append(f"    {edge.source} --> {edge.target}")
        if state is not None:
            for node_id, record in state.node_records.items():
                style = _MERMAID_STATUS_STYLE.get(record.status)
                if style:
                    lines.append(f"    style {node_id} {style}")
        return "\n".join(lines)

    def to_ascii(self) -> str:
        """A simple, deterministic ASCII listing in topological order."""
        lines = []
        for node_id in self.graph.topological_order():
            node = self.graph.get_node(node_id)
            deps = ", ".join(node.dependencies) if node.dependencies else "-"
            lines.append(f"[{node_id}] {node.name} (deps: {deps})")
        return "\n".join(lines)

    def execution_tree(self, state: ExecutionState) -> str:
        """Nested-indentation tree (by dependency depth), annotated with status + duration."""
        order = self.graph.topological_order()
        depth: dict[str, int] = {}
        for node_id in order:
            node = self.graph.get_node(node_id)
            depth[node_id] = (
                0 if not node.dependencies else max(depth[dep] for dep in node.dependencies) + 1
            )

        lines = []
        for node_id in order:
            node = self.graph.get_node(node_id)
            record = state.node_records.get(node_id)
            status = record.status.value if record else ExecutionStatus.PENDING.value
            duration = (
                f"{record.duration_ms:.1f}ms"
                if record is not None and record.duration_ms is not None
                else "-"
            )
            indent = "  " * depth[node_id]
            lines.append(f"{indent}- {node_id} ({node.name}) [{status}] {duration}")
        return "\n".join(lines)
