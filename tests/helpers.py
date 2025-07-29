# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

from typing import TYPE_CHECKING

from scrapy_lint import lint

from . import ExpectedIssue, File, iter_issues, project

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def sort_issues(issues: Iterable[ExpectedIssue]) -> Iterable[ExpectedIssue]:
    return sorted(issues, key=lambda issue: (issue.message, issue.line, issue.column))


def check_project(
    files: File | Sequence[File],
    expected: ExpectedIssue | Sequence[ExpectedIssue] | None,
    options: dict | None = None,
    args: Sequence[str] | None = None,
):
    args = args or []
    expected = list(iter_issues(expected))
    with project(files, options):
        issues = (ExpectedIssue.from_issue(issue) for issue in lint(args))
        assert sort_issues(expected) == sort_issues(issues)
