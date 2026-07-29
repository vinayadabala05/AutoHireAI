"""Unit tests for `app.graph.node.GraphNode`."""

from app.graph.retry import FixedDelayRetryPolicy, NoRetryPolicy
from tests.graph_fixtures import EchoNode


def test_node_defaults() -> None:
    node = EchoNode("a")
    assert node.id == "a"
    assert node.name == "a"
    assert node.description == ""
    assert node.inputs == []
    assert node.outputs == []
    assert node.dependencies == []
    assert node.metadata == {}
    assert node.optional is False
    assert node.timeout_seconds is None
    assert isinstance(node.retry_policy, NoRetryPolicy)
    assert node.last_record is None


def test_node_accepts_full_configuration() -> None:
    policy = FixedDelayRetryPolicy(1.0, max_retries=2)
    node = EchoNode(
        "a",
        name="A",
        description="desc",
        inputs=["x"],
        outputs=["y"],
        dependencies=["z"],
        metadata={"key": "value"},
        retry_policy=policy,
        timeout_seconds=5.0,
        optional=True,
    )
    assert node.name == "A"
    assert node.description == "desc"
    assert node.inputs == ["x"]
    assert node.outputs == ["y"]
    assert node.dependencies == ["z"]
    assert node.metadata == {"key": "value"}
    assert node.retry_policy is policy
    assert node.timeout_seconds == 5.0
    assert node.optional is True


def test_default_lifecycle_hooks_are_no_ops() -> None:
    import asyncio

    node = EchoNode("a")

    async def run() -> None:
        await node.validate(None)  # type: ignore[arg-type]
        await node.prepare(None)  # type: ignore[arg-type]
        await node.cleanup(None)  # type: ignore[arg-type]
        await node.rollback(None)  # type: ignore[arg-type]

    asyncio.run(run())  # should not raise


def test_to_definition_dict_contains_static_fields() -> None:
    node = EchoNode("a", name="A", dependencies=["b"], metadata={"k": "v"})
    definition = node.to_definition_dict()
    assert definition["id"] == "a"
    assert definition["type"] == "EchoNode"
    assert definition["name"] == "A"
    assert definition["dependencies"] == ["b"]
    assert definition["metadata"] == {"k": "v"}


def test_node_repr_includes_id_and_name() -> None:
    node = EchoNode("a", name="A")
    assert "a" in repr(node)
    assert "A" in repr(node)


async def test_execute_returns_expected_output() -> None:
    node = EchoNode("a", result="custom")
    result = await node.execute(None)  # type: ignore[arg-type]
    assert result == "custom"
