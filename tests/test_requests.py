from __future__ import annotations

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases
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
            # Baseline
            *(
                (code, NO_ISSUE)
                for code in (
                    'Request(url, meta={"foo": "bar"})',
                    "Request(url, meta=meta)",
                )
            ),
            # SCP45 unsafe meta copy
            *(
                (
                    code,
                    ExpectedIssue(
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
            # SCP46 raw Zyte API params
            *(
                (code, NO_ISSUE)
                for code in ('Request(url, meta={"zyte_api_automap": True})',)
            ),
            *(
                (
                    code,
                    ExpectedIssue(
                        message="SCP46 raw Zyte API params",
                        column=column,
                        path=PATH,
                    ),
                )
                for code, column in (
                    ('Request(url, meta={"zyte_api": {"httpResponseBody": True}})', 19),
                )
            ),
        )
    ),
)


@cases(CASES)
def test(
    input_: File | list[File],
    expected: ExpectedIssue | list[ExpectedIssue] | None,
    flake8_options,
):
    check_project(input_, expected, flake8_options)
