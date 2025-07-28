from __future__ import annotations

from ast import (
    Call,
    ClassDef,
    Constant,
    Dict,
    FunctionDef,
    Import,
    ImportFrom,
    List,
    Name,
    alias,
    expr,
)
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


def definition_column(node: ClassDef | FunctionDef) -> int:
    offset = len("class ") if isinstance(node, ClassDef) else len("def ")
    return node.col_offset + offset


def import_column(node: Import | ImportFrom, alias_: alias) -> int:
    if alias_.asname:
        # For "from foo import BAR as BAZ" or "import foo as BAR", point to "BAZ"/"BAR"
        # Need to find position of alias name after " as "
        if hasattr(alias_, "col_offset"):
            return alias_.col_offset + len(alias_.name) + 4  # " as " is 4 chars
        # Python 3.9 compatibility: alias objects don't have col_offset
        return node.col_offset
    # For "from foo import FOO" or "import FOO", point to "FOO"
    if hasattr(alias_, "col_offset"):
        return alias_.col_offset
    # Python 3.9 compatibility: alias objects don't have col_offset
    return node.col_offset
