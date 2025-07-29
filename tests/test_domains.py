from __future__ import annotations

from . import Cases, ExpectedIssue, File, cases
from .helpers import check_project

CASES: Cases = (
    (
        (
            File(
                "\n".join(
                    [
                        "class MySpider(Spider):",
                        "    allowed_domains = (",
                        '        "a.example",',
                        '        "b.example",',
                        '        "https://toscrape.com",',
                        "    )",
                        "    start_urls = [",
                        '        "https://c.example",',
                        '        "https://d.example",',
                        "    ]",
                    ],
                ),
                path="a.py",
            ),
        ),
        (
            ExpectedIssue(
                message="SCP01 disallowed domain",
                line=8,
                column=8,
                path="a.py",
            ),
            ExpectedIssue(
                message="SCP01 disallowed domain",
                line=9,
                column=8,
                path="a.py",
            ),
            ExpectedIssue(
                message="SCP02 URL in allowed_domains",
                line=5,
                column=8,
                path="a.py",
            ),
        ),
        {},
    ),
)


@cases(CASES)
def test(
    files: File | list[File],
    expected: ExpectedIssue | list[ExpectedIssue] | None,
    options,
):
    check_project(files, expected, options)
