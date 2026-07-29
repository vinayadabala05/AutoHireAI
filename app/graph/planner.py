"""Execution planning: turns a `Graph` into ordered "waves" of node ids.

A wave is a set of nodes whose dependencies are all satisfied by earlier
waves — every node within a wave can run concurrently. `GraphExecutor`'s
parallel mode drives execution one wave at a time; sequential mode simply
flattens the waves back into `Graph.topological_order()`.
"""

from app.graph.graph import Graph


class ExecutionPlanner:
    def plan(self, graph: Graph) -> list[list[str]]:
        """Compute waves of node ids ready to run concurrently, in dependency order.

        Raises `CycleDetectedError`/`UnknownNodeError` (via `graph.validate()`)
        if the graph isn't a valid DAG.
        """
        graph.validate()

        nodes = graph.nodes
        children: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        in_degree: dict[str, int] = {}
        for node in nodes.values():
            in_degree[node.id] = len(node.dependencies)
            for dependency in node.dependencies:
                children[dependency].append(node.id)

        waves: list[list[str]] = []
        current_wave = sorted(node_id for node_id, degree in in_degree.items() if degree == 0)

        while current_wave:
            waves.append(current_wave)
            next_wave: list[str] = []
            for node_id in current_wave:
                for child in children[node_id]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_wave.append(child)
            current_wave = sorted(next_wave)

        return waves

    def flatten(self, graph: Graph) -> list[str]:
        """The equivalent single-file execution order (for sequential mode)."""
        return [node_id for wave in self.plan(graph) for node_id in wave]
