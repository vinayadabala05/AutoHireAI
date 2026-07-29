"""Shared helper for adapter nodes.

Every adapter resolves its arguments the same way: prefer an explicit
graph input (`context.get_input(name)`), falling back to an upstream
node's output when the input name matches a dependency's node id — the
convention every adapter documents is "wire this node's input name to the
id of the node that produces it, or pass it directly as a graph input."
"""

from typing import Any

from app.graph.context import ExecutionContext
from app.graph.exceptions import GraphValidationError


def resolve_input(context: ExecutionContext, name: str, *, required: bool = True) -> Any:
    value = context.get_input(name)
    if value is not None:
        return value
    output = context.get_output(name)
    if output is not None:
        return output
    if required:
        raise GraphValidationError(
            f"Missing required input '{name}': supply it via graph inputs, or via a "
            f"dependency node whose id is '{name}'."
        )
    return None
