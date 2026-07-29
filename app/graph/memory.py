"""Graph Memory: shared state that flows between nodes during one run.

Deliberately a plain class, not Pydantic — node outputs are arbitrary
Python objects (a `CareerProfile`, a `ResumeDocument`, a `list[DiscoveredJob]`,
...), not necessarily JSON-serializable, so validating them would be both
wrong and impossible in the general case. `checkpoint.py` persists what it
can of this on a best-effort basis; see `docs/graph_engine.md` for exactly
what that means for resuming a graph.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphMemory:
    """Shared context for one execution: node outputs, a scratch dict, and history."""

    outputs: dict[str, Any] = field(default_factory=dict)
    shared: dict[str, Any] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def set_output(self, node_id: str, value: Any) -> None:
        self.outputs[node_id] = value
        self.history.append(f"{node_id} -> output set")

    def get_output(self, node_id: str, default: Any = None) -> Any:
        return self.outputs.get(node_id, default)

    def has_output(self, node_id: str) -> bool:
        return node_id in self.outputs

    def set_shared(self, key: str, value: Any) -> None:
        self.shared[key] = value

    def get_shared(self, key: str, default: Any = None) -> Any:
        return self.shared.get(key, default)
