"""Event system: what the executor publishes as a graph runs.

`EventBus` is a plain observer registry — synchronous or async callbacks
both work, since `emit` is itself async and awaits any callback that
returns a coroutine. This is what powers `ExecutionState.trace` (every
emitted event is also appended there) and lets a caller attach logging,
metrics, or UI-streaming callbacks without `executor.py` knowing anything
about them.
"""

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    GRAPH_STARTED = "graph_started"
    GRAPH_COMPLETED = "graph_completed"
    GRAPH_FAILED = "graph_failed"
    GRAPH_CANCELLED = "graph_cancelled"
    NODE_STARTED = "node_started"
    NODE_FINISHED = "node_finished"
    NODE_FAILED = "node_failed"
    NODE_RETRYING = "node_retrying"
    NODE_SKIPPED = "node_skipped"
    NODE_CANCELLED = "node_cancelled"


class Event(BaseModel):
    """A single occurrence emitted during graph execution."""

    type: EventType
    graph_id: str
    run_id: str
    node_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


EventCallback = Callable[[Event], None] | Callable[[Event], Awaitable[None]]


class EventBus:
    """Publish/subscribe registry for graph execution events."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType | None, list[EventCallback]] = defaultdict(list)

    def subscribe(self, callback: EventCallback, event_type: EventType | None = None) -> None:
        """Subscribe to one `event_type`, or every event if `event_type` is `None`."""
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, callback: EventCallback, event_type: EventType | None = None) -> None:
        subscribers = self._subscribers.get(event_type, [])
        if callback in subscribers:
            subscribers.remove(callback)

    async def emit(self, event: Event) -> None:
        for callback in [*self._subscribers.get(event.type, []), *self._subscribers.get(None, [])]:
            result = callback(event)
            if inspect.isawaitable(result):
                await result
