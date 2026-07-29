"""Shared test node classes for Sprint 8 Graph Engine tests."""

import asyncio
from typing import Any

from app.graph.context import ExecutionContext
from app.graph.node import GraphNode


class EchoNode(GraphNode):
    """Always succeeds, returning a deterministic string (or a fixed `result`)."""

    def __init__(
        self, node_id: str, name: str | None = None, result: Any = None, **kwargs: Any
    ) -> None:
        super().__init__(node_id, name or node_id, **kwargs)
        self._result = result
        self.calls = 0

    async def execute(self, context: ExecutionContext) -> Any:
        self.calls += 1
        return self._result if self._result is not None else f"{self.id}-done"


class FailingNode(GraphNode):
    """Always raises."""

    def __init__(
        self, node_id: str, name: str | None = None, error: Exception | None = None, **kwargs: Any
    ) -> None:
        super().__init__(node_id, name or node_id, **kwargs)
        self._error = error or ValueError(f"{node_id} failed")
        self.calls = 0

    async def execute(self, context: ExecutionContext) -> Any:
        self.calls += 1
        raise self._error


class FlakyNode(GraphNode):
    """Fails `fail_times` times, then succeeds."""

    def __init__(
        self, node_id: str, name: str | None = None, fail_times: int = 1, **kwargs: Any
    ) -> None:
        super().__init__(node_id, name or node_id, **kwargs)
        self.fail_times = fail_times
        self.calls = 0

    async def execute(self, context: ExecutionContext) -> Any:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"{self.id} transient failure #{self.calls}")
        return f"{self.id}-recovered"


class SlowNode(GraphNode):
    """Sleeps for `delay_seconds` before succeeding."""

    def __init__(
        self, node_id: str, name: str | None = None, delay_seconds: float = 0.05, **kwargs: Any
    ) -> None:
        super().__init__(node_id, name or node_id, **kwargs)
        self.delay_seconds = delay_seconds
        self.started = False
        self.completed = False

    async def execute(self, context: ExecutionContext) -> Any:
        self.started = True
        await asyncio.sleep(self.delay_seconds)
        self.completed = True
        return f"{self.id}-slow-done"


class RecordingNode(GraphNode):
    """Records each lifecycle call it receives, for asserting call order/hooks fired."""

    def __init__(self, node_id: str, name: str | None = None, **kwargs: Any) -> None:
        super().__init__(node_id, name or node_id, **kwargs)
        self.calls: list[str] = []

    async def validate(self, context: ExecutionContext) -> None:
        self.calls.append("validate")

    async def prepare(self, context: ExecutionContext) -> None:
        self.calls.append("prepare")

    async def execute(self, context: ExecutionContext) -> Any:
        self.calls.append("execute")
        return "ok"

    async def cleanup(self, context: ExecutionContext) -> None:
        self.calls.append("cleanup")

    async def rollback(self, context: ExecutionContext) -> None:
        self.calls.append("rollback")


class FailingRecordingNode(RecordingNode):
    async def execute(self, context: ExecutionContext) -> Any:
        self.calls.append("execute")
        raise ValueError("boom")


class FailWithBadHooksNode(GraphNode):
    """Fails execution, and its `rollback`/`cleanup` also raise — both must be swallowed."""

    def __init__(self, node_id: str, name: str | None = None, **kwargs: Any) -> None:
        super().__init__(node_id, name or node_id, **kwargs)

    async def execute(self, context: ExecutionContext) -> Any:
        raise ValueError(f"{self.id} failed")

    async def rollback(self, context: ExecutionContext) -> None:
        raise RuntimeError("rollback also failed")

    async def cleanup(self, context: ExecutionContext) -> None:
        raise RuntimeError("cleanup also failed")


class InputEchoNode(GraphNode):
    """Reads a named input/output and returns it verbatim — for context-plumbing tests."""

    def __init__(
        self, node_id: str, source_name: str, name: str | None = None, **kwargs: Any
    ) -> None:
        super().__init__(node_id, name or node_id, **kwargs)
        self.source_name = source_name

    async def execute(self, context: ExecutionContext) -> Any:
        value = context.get_input(self.source_name)
        if value is None:
            value = context.get_output(self.source_name)
        return value
