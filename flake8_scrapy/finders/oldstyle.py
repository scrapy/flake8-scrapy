import ast
from collections.abc import Generator

from flake8_scrapy.issues import (
    IMPROPER_FIRST_MATCH_EXTRACTION,
    IMPROPER_RESPONSE_SELECTOR,
    IMPROPER_RESPONSE_URL_JOIN,
    Issue,
    Pos,
)

from . import IssueFinder


class UrlJoinIssueFinder(IssueFinder):
    def find_issues(self, node) -> Generator[Issue, None, None]:
        if not (
            isinstance(node.func, ast.Name) and node.func.id == "urljoin" and node.args
        ):
            return
        first_param = node.args[0]
        if not isinstance(first_param, ast.Attribute) or not isinstance(
            first_param.value, ast.Name
        ):
            return
        if first_param.value.id == "response" and first_param.attr == "url":
            yield Issue(IMPROPER_RESPONSE_URL_JOIN, Pos.from_node(node))


class OldSelectorIssueFinder(IssueFinder):
    def is_response_dot_body_as_unicode(self, node):
        """Returns True if node represents response.body_as_unicode()"""
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "response"
            and node.func.attr == "body_as_unicode"
        )

    def is_response_dot_text_or_body(self, node):
        """Return whether or not a node represents response.text or
        response.body
        """
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "response"
            and node.attr in ("text", "body")
        )

    def is_response(self, node):
        """Check if node represents an object named as response"""
        return isinstance(node, ast.Name) and node.id == "response"

    def has_response_for_keyword_parameter(self, node):
        """Check if response or response.text is passed as a keyword parameter
        as in: Selector(text=response.text) or Selector(response=response)
        """
        return (
            (node.arg == "text" and self.is_response_dot_text_or_body(node.value))
            or self.is_response_dot_body_as_unicode(node.value)
        ) or (node.arg == "response" and self.is_response(node.value))

    def issue_applies(self, node):
        return (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Selector"
        )

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if not self.issue_applies(node):
            return

        # look for: Selector(response)
        if node.value.args:
            param = node.value.args[0]
            if self.is_response(param):
                yield Issue(IMPROPER_RESPONSE_SELECTOR, Pos.from_node(node))
                return

        # look for: Selector(response=response) or Selector(text=response.text)
        for kw in node.value.keywords:
            if self.has_response_for_keyword_parameter(kw):
                yield Issue(IMPROPER_RESPONSE_SELECTOR, Pos.from_node(node))
                return


class GetFirstByIndexIssueFinder(IssueFinder):
    def find_issues(self, node) -> Generator[Issue, None, None]:
        node_func = node.func
        if not (
            isinstance(node_func, ast.Attribute)
            and node_func.attr in ("extract", "get")
        ):
            return

        subscript_node = node.func.value
        if not isinstance(subscript_node, ast.Subscript):
            return

        if not isinstance(subscript_node.slice, ast.Constant):
            return

        index = subscript_node.slice.value
        if index != 0:
            return

        subscripted_value = subscript_node.value
        if not isinstance(subscripted_value, ast.Call):
            return

        subscripted_value_func = subscripted_value.func
        if not (
            isinstance(subscripted_value_func, ast.Attribute)
            and subscripted_value_func.attr in ("css", "xpath")
        ):
            return

        yield Issue(IMPROPER_FIRST_MATCH_EXTRACTION, Pos.from_node(node))


class ExtractThenIndexIssueFinder(GetFirstByIndexIssueFinder):
    def find_issues(self, node) -> Generator[Issue, None, None]:
        if not isinstance(node.slice, ast.Constant):
            return
        if node.slice.value != 0:
            return
        if not isinstance(node.value, ast.Call):
            return
        if not (
            isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr in ("extract", "getall")
        ):
            return
        extract_target = node.value.func.value
        if not (
            isinstance(extract_target, ast.Call)
            and isinstance(extract_target.func, ast.Attribute)
            and extract_target.func.attr in ("css", "xpath")
        ):
            return
        yield Issue(IMPROPER_FIRST_MATCH_EXTRACTION, Pos.from_node(node))
