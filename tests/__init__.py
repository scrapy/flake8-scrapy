from __future__ import annotations

import ast
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pytest

from flake8_scrapy import ScrapyStyleChecker

if TYPE_CHECKING:
    from collections.abc import Sequence

NO_ISSUE = None

pytest.register_assert_rewrite("tests.helpers")


def cases(
    test_cases: Sequence[tuple[File | Sequence[File], Issue | Sequence[Issue] | None]],
) -> Callable:
    def decorator(func):
        return pytest.mark.parametrize(
            ("input", "expected"),
            test_cases,
            ids=range(len(test_cases)),
        )(func)

    return decorator


def load_sample_file(filename):
    return (Path(__file__).parent / "samples" / filename).read_text()


def run_checker(code: str, file_path: str = "a.py") -> Sequence[tuple[int, int, str]]:
    tree = ast.parse(code)
    checker = ScrapyStyleChecker(tree, file_path)
    return tuple(checker.run())


@dataclass
class File:
    text: str
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
            message=message if message is not None else self.message,
            line=line if line is not None else self.line,
            column=column if column is not None else self.column,
            path=path if path is not None else self.path,
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
