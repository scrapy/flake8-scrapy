from __future__ import annotations

from ast import Constant, Dict, List
from typing import Any


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
