from __future__ import annotations

import os
import sys
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Union

import pytest

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from scrapy_lint.issues import Issue

NO_ISSUE = None

pytest.register_assert_rewrite("tests.helpers")


@dataclass
class File:
    text: str | bytes
    path: str | None = None


@dataclass
class ExpectedIssue:
    message: str
    line: int = 1
    column: int = 0
    path: str | None = None

    @classmethod
    def from_issue(cls, issue: Issue) -> ExpectedIssue:
        assert issue.file
        return cls(
            message=issue.message,
            line=issue.pos.line,
            column=issue.pos.column,
            path=str(issue.file),
        )

    def replace(
        self,
        *,
        message: str | None = None,
        line: int | None = None,
        column: int | None = None,
        path: str | None = None,
    ) -> ExpectedIssue:
        return ExpectedIssue(
            message=message if message else self.message,
            line=line if line else self.line,
            column=column if column is not None else self.column,
            path=path if path else self.path,
        )


@contextmanager
def chdir(path: str | Path):
    old_cwd = Path.cwd()
    try:
        os.chdir(str(path))
        yield
    finally:
        os.chdir(str(old_cwd))


Files: TypeAlias = Union[Sequence[File], File]
ExpectedIssues: TypeAlias = Union[Sequence[ExpectedIssue], ExpectedIssue, None]
Options: TypeAlias = dict[str, Any]
Cases: TypeAlias = Sequence[tuple[Files, ExpectedIssues, Options]]


def cases(test_cases: Cases) -> Callable:
    def decorator(func):
        return pytest.mark.parametrize(
            ("input", "expected", "flake8_options"),
            test_cases,
            ids=range(len(test_cases)),
        )(func)

    return decorator


def iter_issues(
    issues: Iterable[ExpectedIssue] | ExpectedIssue | None,
) -> Generator[ExpectedIssue]:
    if issues is None:
        return
    if isinstance(issues, ExpectedIssue):
        yield issues
        return
    yield from issues
