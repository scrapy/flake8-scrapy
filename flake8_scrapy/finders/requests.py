from __future__ import annotations

from ast import Attribute, Call, Constant, Dict, Name, expr
from typing import TYPE_CHECKING

from flake8_scrapy.ast import is_dict, iter_dict
from flake8_scrapy.issues import (
    UNSAFE_META_COPY,
    ZYTE_RAW_PARAMS,
    Issue,
    Pos,
)

if TYPE_CHECKING:
    from collections.abc import Generator


def get_func_name(f: expr) -> str | None:
    if hasattr(f, "attr"):
        return f.attr
    if hasattr(f, "id"):
        return f.id
    return None


def is_request_construction(node: Call) -> bool:
    fn_name = get_func_name(node.func)
    return bool(
        fn_name
        and (
            fn_name.endswith("Request")
            or fn_name in {"follow", "follow_all", "replace"}
        )
    )


def is_response_meta(value: expr) -> bool:
    return (
        isinstance(value, Attribute)
        and value.attr == "meta"
        and isinstance(value.value, Name)
        and value.value.id == "response"
    )


class RequestIssueFinder:
    def find_issues(self, node: Call) -> Generator[Issue]:
        if not is_request_construction(node):
            return
        for arg in node.args:
            if is_response_meta(arg):
                yield Issue(UNSAFE_META_COPY, Pos.from_node(arg))
                break
        for kw in node.keywords:
            if is_response_meta(kw.value):
                yield Issue(UNSAFE_META_COPY, Pos.from_node(kw.value))
            elif kw.arg == "meta":
                yield from self.check_meta(kw.value)

    def check_meta(self, meta: expr) -> Generator[Issue]:
        if not is_dict(meta):
            return
        assert isinstance(meta, (Call, Dict))
        for key, _ in iter_dict(meta):
            if isinstance(key, Constant) and key.value == "zyte_api":
                yield Issue(ZYTE_RAW_PARAMS, Pos.from_node(key))
