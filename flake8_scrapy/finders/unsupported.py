from __future__ import annotations

import ast
from ast import Assign, Attribute, Call, Name, expr
from typing import TYPE_CHECKING

from flake8_scrapy.issues import LAMBDA_CALLBACK, Issue, Pos

from . import IssueFinder

if TYPE_CHECKING:
    from collections.abc import Generator


def import_paths_from_complete(
    complete_paths: set[tuple[str, ...]],
) -> set[tuple[str, ...]]:
    """Return a set of tuple of both complete and partial import paths based on
    the provided complete import paths.

    >>> import_paths_from_complete({(("scrapy",), ("scrapy", "http"), ("scrapy", "http", "request"))})
    {('scrapy',), ('http',), ('request',), ('scrapy', 'http'), ('scrapy', 'http', 'request'), ('http', 'request')}
    """
    result = set(complete_paths)
    for complete_path in complete_paths:
        if len(complete_path) <= 1:
            continue
        for i in range(1, len(complete_path)):
            result.add(complete_path[i:])
    return result


VALID_REQUEST_IMPORT_PATHS = {
    cls: import_paths_from_complete(complete_paths)
    for cls, complete_paths in (
        ("Request", {("scrapy",), ("scrapy", "http"), ("scrapy", "http", "request")}),
        (
            "FormRequest",
            {("scrapy",), ("scrapy", "http"), ("scrapy", "http", "request", "form")},
        ),
        (
            "JsonRequest",
            {("scrapy", "http"), ("scrapy", "http", "request", "json_request")},
        ),
        ("XmlRpcRequest", {("scrapy", "http"), ("scrapy", "http", "request", "rpc")}),
    )
}


def import_path_from_attribute(attr: expr) -> tuple[str, ...]:
    """Return the import path as a tuple of strings from an Attribute node."""
    if not isinstance(attr, (Attribute, Name)):
        return ()
    parts = []
    current_attr: Attribute | Name = attr
    while isinstance(current_attr, Attribute):
        parts.append(current_attr.attr)
        if not isinstance(current_attr.value, (Attribute, Name)):
            return ()
        current_attr = current_attr.value
    if isinstance(current_attr, Name):
        parts.append(current_attr.id)
    return tuple(reversed(parts))


class LambdaCallbackIssueFinder(IssueFinder):
    def looks_like_request(self, func: expr):
        return (
            isinstance(func, Name)
            and func.id
            in {
                "Request",
                "FormRequest",
                "JsonRequest",
                "XmlRpcRequest",
                # In code where different request classes are used,
                # importing scrapy.Request as ScrapyRequest is common.
                "ScrapyRequest",
            }
        ) or (
            isinstance(func, Attribute)
            and func.attr in {"Request", "FormRequest", "JsonRequest", "XmlRpcRequest"}
            and import_path_from_attribute(func.value)
            in VALID_REQUEST_IMPORT_PATHS[func.attr]
        )

    def looks_like_request_replace(self, func: expr):
        """Check if this looks like a Request.replace() call."""
        return isinstance(func, Attribute) and func.attr == "replace"

    def looks_like_response_follow(self, func: expr):
        """Check if this looks like a Response.follow() or Response.follow_all() call."""
        return isinstance(func, Attribute) and func.attr in {"follow", "follow_all"}

    def looks_like_from_response(self, func: expr):
        """Check if this looks like a FormRequest.from_response() call."""
        return isinstance(func, Attribute) and func.attr == "from_response"

    def find_issues(self, node: Call | Assign) -> Generator[Issue, None, None]:
        if isinstance(node, Call):
            yield from self._find_issues_in_call(node)
        elif isinstance(node, Assign):
            yield from self._find_issues_in_assign(node)

    def _check_lambda_callbacks_positional(
        self, node: Call
    ) -> Generator[Issue, None, None]:
        """Check for lambda callbacks in positional arguments."""
        for position in (
            1,  # callback
            10,  # errback
        ):
            if len(node.args) > position:
                arg = node.args[position]
                if isinstance(arg, ast.Lambda):
                    yield Issue(LAMBDA_CALLBACK, Pos.from_node(arg))

    def _check_lambda_callbacks_keyword_only(
        self, node: Call
    ) -> Generator[Issue, None, None]:
        """Check for lambda callbacks in keyword arguments only."""
        for kw in node.keywords:
            if kw.arg in {"callback", "errback"} and isinstance(kw.value, ast.Lambda):
                yield Issue(LAMBDA_CALLBACK, Pos.from_node(kw.value))

    def _check_lambda_callbacks_in_call(
        self, node: Call
    ) -> Generator[Issue, None, None]:
        """Check for lambda callbacks in call arguments (both positional and keyword)."""
        yield from self._check_lambda_callbacks_positional(node)
        yield from self._check_lambda_callbacks_keyword_only(node)

    def _find_issues_in_call(self, node: Call) -> Generator[Issue, None, None]:
        if (
            self.looks_like_request(node.func)
            or self.looks_like_request_replace(node.func)
            or self.looks_like_response_follow(node.func)
        ):
            yield from self._check_lambda_callbacks_in_call(node)
        elif self.looks_like_from_response(node.func):
            yield from self._check_lambda_callbacks_keyword_only(node)

    def _find_issues_in_assign(self, node: Assign) -> Generator[Issue, None, None]:
        # Check for assignments like obj.callback = lambda x: x or obj.errback = lambda x: x
        if not isinstance(node.value, ast.Lambda):
            return

        # Check if any target is a callback/errback attribute assignment
        has_callback_errback_target = any(
            isinstance(target, Attribute) and target.attr in {"callback", "errback"}
            for target in node.targets
        )

        if has_callback_errback_target:
            yield Issue(LAMBDA_CALLBACK, Pos.from_node(node.value))
