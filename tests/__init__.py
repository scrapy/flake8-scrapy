from __future__ import annotations

import ast
import os
import sys
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable, Union

import pytest

from flake8_scrapy import ScrapyFlake8Plugin

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

HAS_FLAKE8_REQUIREMENTS = bool(find_spec("flake8_requirements"))
NO_ISSUE = None

pytest.register_assert_rewrite("tests.helpers")


class MockParser:
    def __init__(self):
        self.options = {}

    def add_option(self, *args, **kwargs):
        option_name = args[0].lstrip("-").replace("-", "_")
        default_value = kwargs.get("default", "")
        self.options[option_name] = default_value


class MockOptions:
    def __init__(self, options_dict: dict):
        parser = MockParser()
        ScrapyFlake8Plugin.add_options(parser)
        for option_name, default_value in parser.options.items():
            setattr(self, option_name, default_value)
        for key, value in options_dict.items():
            setattr(self, key, value)


def run_checker(
    code: str, file_path: str = "a.py", flake8_options: dict | None = None
) -> Sequence[tuple[int, int, str]]:
    if file_path.endswith(".py"):
        tree = ast.parse(code)
        lines = None
    else:
        tree = None
        lines = code.splitlines()
    if flake8_options is None:
        flake8_options = {}
    original_class_dict = ScrapyFlake8Plugin.__dict__.copy()
    mock_options = MockOptions(flake8_options)
    try:
        ScrapyFlake8Plugin.parse_options(mock_options)  # type: ignore[arg-type]
        checker = ScrapyFlake8Plugin(tree, file_path, lines)
        return tuple(checker.run())
    finally:
        current_attrs = set(ScrapyFlake8Plugin.__dict__.keys())
        original_attrs = set(original_class_dict.keys())
        for new_attr in current_attrs - original_attrs:
            delattr(ScrapyFlake8Plugin, new_attr)


@dataclass
class File:
    text: str | bytes
    path: str | None = None


@dataclass
class Issue:
    message: str
    line: int = 1
    column: int = 0
    path: str | None = None

    @classmethod
    def from_tuple(cls, issue: tuple[int, int, str], path: str | None = None) -> Issue:
        return cls(
            message=issue[2],
            line=issue[0],
            column=issue[1],
            path=path,
        )

    def replace(
        self,
        *,
        message: str | None = None,
        line: int | None = None,
        column: int | None = None,
        path: str | None = None,
    ) -> Issue:
        return Issue(
            message=message if message else self.message,
            line=line if line else self.line,
            column=column if column is not None else self.column,
            path=path if path else self.path,
        )


# TODO: Use contextlib.chdir when Python 3.11 is the minimum version
@contextmanager
def chdir(path: str | Path):
    old_cwd = Path.cwd()
    try:
        os.chdir(str(path))
        yield
    finally:
        os.chdir(str(old_cwd))


Files: TypeAlias = Union[Sequence[File], File]
Issues: TypeAlias = Union[Sequence[Issue], Issue, None]
Flake8Options: TypeAlias = dict[str, Any]
Cases: TypeAlias = Sequence[tuple[Files, Issues, Flake8Options]]


def cases(test_cases: Cases) -> Callable:
    def decorator(func):
        return pytest.mark.parametrize(
            ("input", "expected", "flake8_options"),
            test_cases,
            ids=range(len(test_cases)),
        )(func)

    return decorator


def iter_issues(issues: Iterable[Issue] | Issue | None) -> Generator[Issue]:
    if issues is None:
        return
    if isinstance(issues, Issue):
        yield issues
        return
    yield from issues
