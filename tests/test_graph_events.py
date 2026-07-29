"""Unit tests for `app.graph.events`."""

from app.graph.events import Event, EventBus, EventType


def _event(event_type: EventType = EventType.NODE_STARTED) -> Event:
    return Event(type=event_type, graph_id="g1", run_id="r1", node_id="a")


async def test_subscribe_to_specific_event_type_receives_only_that_type() -> None:
    received: list[Event] = []
    bus = EventBus()
    bus.subscribe(received.append, EventType.NODE_STARTED)
    await bus.emit(_event(EventType.NODE_STARTED))
    await bus.emit(_event(EventType.NODE_FINISHED))
    assert len(received) == 1
    assert received[0].type is EventType.NODE_STARTED


async def test_subscribe_to_none_receives_every_event() -> None:
    received: list[Event] = []
    bus = EventBus()
    bus.subscribe(received.append)
    await bus.emit(_event(EventType.NODE_STARTED))
    await bus.emit(_event(EventType.NODE_FAILED))
    assert len(received) == 2


async def test_async_callback_is_awaited() -> None:
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus = EventBus()
    bus.subscribe(handler, EventType.GRAPH_STARTED)
    await bus.emit(_event(EventType.GRAPH_STARTED))
    assert len(received) == 1


async def test_unsubscribe_removes_callback() -> None:
    received: list[Event] = []
    bus = EventBus()
    bus.subscribe(received.append, EventType.NODE_STARTED)
    bus.unsubscribe(received.append, EventType.NODE_STARTED)
    await bus.emit(_event(EventType.NODE_STARTED))
    assert received == []


def test_unsubscribe_unknown_callback_is_a_no_op() -> None:
    bus = EventBus()

    def handler(event: Event) -> None:
        pass

    bus.unsubscribe(handler, EventType.NODE_STARTED)  # should not raise


async def test_multiple_subscribers_all_receive_event() -> None:
    received_a: list[Event] = []
    received_b: list[Event] = []
    bus = EventBus()
    bus.subscribe(received_a.append, EventType.NODE_FINISHED)
    bus.subscribe(received_b.append, EventType.NODE_FINISHED)
    await bus.emit(_event(EventType.NODE_FINISHED))
    assert len(received_a) == 1
    assert len(received_b) == 1


def test_event_default_payload_and_timestamp() -> None:
    event = _event()
    assert event.payload == {}
    assert event.timestamp is not None


def test_event_type_enum_covers_required_lifecycle_events() -> None:
    required = {
        "graph_started",
        "graph_completed",
        "node_started",
        "node_finished",
        "node_failed",
    }
    values = {member.value for member in EventType}
    assert required.issubset(values)
