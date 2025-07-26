from __future__ import annotations

from ast import Call, Constant, Dict, List, Name, expr
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator


def extract_literal_value(node) -> tuple[Any, bool]:
    """Extract a literal value from an AST node.

    Returns:
        tuple: (value, is_literal) where is_literal indicates if the node
        represents a literal value that can be compared.
    """
    if isinstance(node, Constant):
        return node.value, True
    if isinstance(node, List):
        # Only extract if all elements are literals
        elements = []
        for elt in node.elts:
            value, is_literal = extract_literal_value(elt)
            if not is_literal:
                return None, False  # Contains non-literal
            elements.append(value)
        return elements, True
    if isinstance(node, Dict):
        result = {}
        for key_node, value_node in zip(node.keys, node.values):
            key, key_is_literal = extract_literal_value(key_node)
            value, value_is_literal = extract_literal_value(value_node)
            if not key_is_literal or not value_is_literal:
                return None, False  # Contains non-literal
            result[key] = value
        return result, True
    return None, False  # Not a literal


def is_dict(node: expr) -> bool:
    return isinstance(node, Dict) or (
        isinstance(node, Call)
        and isinstance(node.func, Name)
        and node.func.id == "dict"
    )


def iter_dict(node: Dict | Call) -> Generator[tuple[expr, expr]]:
    if isinstance(node, Dict):
        yield from zip(node.keys, node.values)
    elif (
        isinstance(node, Call)
        and isinstance(node.func, Name)
        and node.func.id == "dict"
    ):
        for kw in node.keywords:
            yield (
                Constant(value=kw.arg, col_offset=kw.col_offset, lineno=kw.lineno),
                kw.value,
            )
