from __future__ import annotations

from . import Cases, File, Issue, cases
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
                    ]
                ),
                path="a.py",
            ),
        ),
        (
            Issue(
                message="SCP01 disallowed domain",
                line=8,
                column=8,
                path="a.py",
            ),
            Issue(
                message="SCP01 disallowed domain",
                line=9,
                column=8,
                path="a.py",
            ),
            Issue(
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
    input: File | list[File], expected: Issue | list[Issue] | None, flake8_options
):
    check_project(input, expected, flake8_options)
