from __future__ import annotations

from . import NO_ISSUE, Cases, File, Issue, cases
from .helpers import check_project

PATH = "a.py"
CASES: Cases = (
    *(
        (
            File(code, path=PATH),
            issues,
            {},
        )
        for code, issues in (
            # SCP45 unsafe meta copy
            *((code, NO_ISSUE) for code in ('Request(url, meta={"foo": "bar"})',)),
            *(
                (
                    code,
                    Issue(
                        message="SCP45 unsafe meta copy",
                        column=column,
                        path=PATH,
                    ),
                )
                for code, column in (
                    ('Request(url, self.parse, "GET", response.meta)', 32),
                    ("scrapy.FormRequest(url, meta=response.meta)", 29),
                    ("response.follow_all(urls, meta=response.meta)", 31),
                )
            ),
        )
    ),
)


@cases(CASES)
def test(
    input: File | list[File], expected: Issue | list[Issue] | None, flake8_options
):
    check_project(input, expected, flake8_options)
