from __future__ import annotations

from inspect import cleandoc

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases
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
                        "    foo = 'bar'",  # Make sure new assignments do not cause issues
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
    # The allowed_domains from a given class should not affect other classes.
    (
        (
            File(
                cleandoc(
                    """
                    class ASpider(Spider):
                        name = 'a'
                        start_urls = ['https://a.example/']

                    class BSpider(Spider):
                        name = 'b'
                        allowed_domains = ['b.example']
                        start_urls = ['https://b.example/']
                    """
                ),
                path="a.py",
            ),
        ),
        NO_ISSUE,
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
