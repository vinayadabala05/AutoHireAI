"""Scheduler architecture: dependency-aware, priority-ordered node scheduling.

Unlike `planner.py` (which computes static "waves" up front), `GraphScheduler`
exposes a pull-based API — `pop_ready()` / `mark_complete()` — so a node
becomes eligible to run the instant its dependencies finish, not only at a
wave boundary. This is deliberately the seam a future distributed backend
would replace: `pop_ready()` becomes "dequeue from a shared broker" (Celery,
Ray, a Redis-backed queue, ...) and `mark_complete()` becomes "publish
completion back to the broker" — the dependency/priority bookkeeping here
is exactly what such a backend still needs, so no rewrite is required, only
a different transport underneath. No external scheduler is used or
required today; `executor.py`'s in-process parallel mode is the only
consumer in this sprint.
"""

import heapq

from app.graph.graph import Graph


class GraphScheduler:
    """In-process, dependency-aware, priority-ordered ready-node queue."""

    def __init__(self, graph: Graph, priorities: dict[str, int] | None = None) -> None:
        self._graph = graph
        self._priorities = priorities or {}
        self._children: dict[str, list[str]] = {node_id: [] for node_id in graph.nodes}
        self._in_degree: dict[str, int] = {}
        for node in graph.nodes.values():
            self._in_degree[node.id] = len(node.dependencies)
            for dependency in node.dependencies:
                self._children[dependency].append(node.id)

        self._heap: list[tuple[int, str]] = []
        self._completed: set[str] = set()
        for node_id, degree in self._in_degree.items():
            if degree == 0:
                self._push(node_id)

    def _push(self, node_id: str) -> None:
        priority = self._priorities.get(node_id, 0)
        heapq.heappush(self._heap, (-priority, node_id))

    def has_ready(self) -> bool:
        return bool(self._heap)

    def pop_ready(self) -> str | None:
        """Pop the highest-priority ready node id (ties broken by node id), or `None`."""
        if not self._heap:
            return None
        _, node_id = heapq.heappop(self._heap)
        return node_id

    def pop_all_ready(self) -> list[str]:
        """Pop every currently-ready node, highest priority first."""
        popped = []
        while (node_id := self.pop_ready()) is not None:
            popped.append(node_id)
        return popped

    def mark_complete(self, node_id: str) -> None:
        """Record `node_id` as finished, unlocking any newly-ready dependents."""
        self._completed.add(node_id)
        for child in self._children.get(node_id, []):
            self._in_degree[child] -= 1
            if self._in_degree[child] == 0:
                self._push(child)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def total_count(self) -> int:
        return len(self._graph.nodes)

    @property
    def is_exhausted(self) -> bool:
        """True once every node has either completed or nothing more can become ready."""
        return not self._heap and self.completed_count == self.total_count
