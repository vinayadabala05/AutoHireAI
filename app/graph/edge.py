"""Graph edges: a directed dependency from one node to another."""

from typing import Any

from pydantic import BaseModel, Field


class GraphEdge(BaseModel):
    """A directed edge: `target` depends on `source` having completed first."""

    source: str
    target: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.source, self.target))
