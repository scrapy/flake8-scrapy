# Helper functions that require pytest assert rewriting
# https://docs.pytest.org/en/latest/how-to/writing_plugins.html#assertion-rewriting

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import tomli_w

from scrapy_lint import lint

from . import ExpectedIssue, File, chdir

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def sort_issues(issues: Iterable[ExpectedIssue]) -> Iterable[ExpectedIssue]:
    return sorted(issues, key=lambda issue: (issue.message, issue.line, issue.column))


def check_project(
    input_: File | Sequence[File],
    expected: ExpectedIssue | Sequence[ExpectedIssue] | None,
    options: dict | None = None,
):
    if isinstance(input_, File):
        input_ = [input_]
    if isinstance(expected, ExpectedIssue):
        expected = [expected]
    elif expected is None:
        expected = []
    with TemporaryDirectory() as directory:
        for file in input_:
            assert file.path
            file_path = Path(directory) / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(file.text, bytes):
                file_path.write_bytes(file.text)
            else:
                file_path.write_text(file.text)
        if options:
            options_path = Path(directory) / "pyproject.toml"
            toml_dict = {"tool": {"scrapy-lint": options}}
            with options_path.open("wb") as f:
                f.write(tomli_w.dumps(toml_dict).encode("utf-8"))
        with chdir(directory):
            issues = (ExpectedIssue.from_issue(issue) for issue in lint())
            assert sort_issues(expected) == sort_issues(issues)
