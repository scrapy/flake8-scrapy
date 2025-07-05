# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from . import File, Issue, chdir, run_checker

if TYPE_CHECKING:
    from collections.abc import Sequence


def sort_issues(issues: Sequence[Issue]) -> Sequence[Issue]:
    return sorted(issues, key=lambda issue: (issue.message, issue.line, issue.column))


def check_project(
    input: File | Sequence[File],
    expected: Issue | Sequence[Issue] | None,
    flake8_options: dict | None = None,
):
    if isinstance(input, File):
        input = [input]
    if isinstance(expected, Issue):
        expected = [expected]
    elif expected is None:
        expected = []
    with TemporaryDirectory() as dir:
        for file in input:
            assert file.path
            file_path = Path(dir) / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(file.text, bytes):
                file_path.write_bytes(file.text)
            else:
                file_path.write_text(file.text)
        with chdir(dir):
            issues = []
            for file in input:
                assert file.path
                if isinstance(file.text, bytes):
                    continue  # flake8 does not support binary files
                issue_tuples = run_checker(file.text, file.path, flake8_options)
                issues.extend(
                    [Issue.from_tuple(issue, path=file.path) for issue in issue_tuples]
                )
            assert sort_issues(expected) == sort_issues(issues)
