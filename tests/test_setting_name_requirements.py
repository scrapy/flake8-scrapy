from __future__ import annotations

from tests.helpers import check_project

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases, iter_issues
from .test_requirements import (
    SCRAPY_ANCIENT_VERSION,
    SCRAPY_FUTURE_VERSION,
    SCRAPY_HIGHEST_KNOWN,
    SCRAPY_LOWEST_SUPPORTED,
)

CASES: Cases = (
    *(
        (
            (
                File("", path="scrapy.cfg"),
                File("\n".join(requirements), path="requirements.txt"),
                File(f"settings[{setting_name!r}]", path=path),
            ),
            (
                ExpectedIssue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
                *iter_issues(issues),  # type: ignore[arg-type]
            ),
            {},
        )
        for path, column in (("a.py", 9),)
        for requirements, setting_name, issues in (
            # SCP27 unknown setting (suggestions based on requirements)
            *(
                (
                    requirements,
                    setting_name,
                    (
                        ExpectedIssue(
                            f"SCP27 unknown setting: did you mean: {', '.join(suggestions)}?"
                            if suggestions
                            else "SCP27 unknown setting",
                            column=column,
                            path=path,
                        ),
                        *extra_issues,
                    ),
                )
                for requirements, setting_name, suggestions, extra_issues in (
                    # No extra issues
                    *(
                        (requirements, setting, suggestions, ())
                        for requirements, setting, suggestions in (
                            # Predefined suggestions
                            ((), "TIMEOUT", ("DOWNLOAD_TIMEOUT", "TIMEOUT_LIMIT")),
                            (("scrapy",), "TIMEOUT", ("DOWNLOAD_TIMEOUT",)),
                            (
                                ("scrapy", "scrapyrt"),
                                "TIMEOUT",
                                ("DOWNLOAD_TIMEOUT", "TIMEOUT_LIMIT"),
                            ),
                            # Automatic suggestions
                            (
                                (),
                                "MAX_REQUESTS",
                                (
                                    "MAX_NEXT_REQUESTS",
                                    "ZYTE_API_MAX_REQUESTS",
                                ),
                            ),
                            (
                                ("scrapy", "scrapy-zyte-api"),
                                "MAX_REQUESTS",
                                ("ZYTE_API_MAX_REQUESTS",),
                            ),
                            (
                                ("hcf-backend", "scrapy", "scrapy-zyte-api"),
                                "MAX_REQUESTS",
                                (
                                    "MAX_NEXT_REQUESTS",
                                    "ZYTE_API_MAX_REQUESTS",
                                ),
                            ),
                            # Invalid requirements, comments, etc.
                            (
                                ("scrapy! #foo", "#scrapy"),
                                "TIMEOUT",
                                (
                                    "DOWNLOAD_TIMEOUT",
                                    "TIMEOUT_LIMIT",
                                ),
                            ),
                            # deprecated_in
                            (
                                ("scrapy==2.13.0",),
                                "AJAXCRAWL_ENABLE",
                                (),
                            ),
                            (
                                ("scrapy==2.12.0",),
                                "AJAXCRAWL_ENABLE",
                                ("AJAXCRAWL_ENABLED",),
                            ),
                        )
                    ),
                    # added_in
                    (
                        ("scrapy==2.10.0",),
                        "ADD_ONS",
                        ("ADDONS",),
                        (
                            ExpectedIssue(
                                "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                                path="requirements.txt",
                            ),
                        ),
                    ),
                    (
                        ("scrapy==2.9.0",),
                        "ADD_ONS",
                        (),
                        (
                            ExpectedIssue(
                                "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                                path="requirements.txt",
                            ),
                        ),
                    ),
                )
            ),
            # SCP28 deprecated setting
            (
                ("scrapy==2.12.0",),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                ExpectedIssue(
                    "SCP28 deprecated setting: deprecated in scrapy 2.12.0",
                    path=path,
                    column=column,
                ),
            ),
            (
                ("scrapy==2.11.2",),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                NO_ISSUE,
            ),
            # SCP28 deprecated setting: sunset guidance
            (
                ("scrapy==2.1.0",),
                "FEED_FORMAT",
                (
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP28 deprecated setting: deprecated in scrapy 2.1.0; use FEEDS instead",
                        path=path,
                        column=column,
                    ),
                ),
            ),
            # SCP28 deprecated setting: no version in requirements.txt
            (
                (),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                NO_ISSUE,
            ),
            # SCP28 deprecated setting: deprecation extends to future versions
            (
                (f"scrapy=={SCRAPY_FUTURE_VERSION}",),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                ExpectedIssue(
                    "SCP28 deprecated setting: deprecated in scrapy 2.12.0",
                    path=path,
                    column=column,
                ),
            ),
            # SCP28 deprecated setting: deprecations are supported in packages
            # other than Scrapy.
            (
                ("scrapy-poet==0.9.0",),
                "SCRAPY_POET_OVERRIDES",
                ExpectedIssue(
                    "SCP28 deprecated setting: deprecated in scrapy-poet "
                    "0.9.0; use SCRAPY_POET_DISCOVER and/or SCRAPY_POET_RULES "
                    "instead",
                    path=path,
                    column=column,
                ),
            ),
            # SCP28 deprecated setting: deprecations in unsupported Scrapy
            # versions are also reported.
            (
                (f"scrapy=={SCRAPY_ANCIENT_VERSION}",),
                "SPIDER_MANAGER_CLASS",
                (
                    ExpectedIssue(
                        "SCP14 unsupported requirement: flake8-scrapy only supports scrapy 2.0.1+",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP28 deprecated setting: deprecated in scrapy 1.0.0",
                        path=path,
                        column=column,
                    ),
                ),
            ),
            # SCP28 deprecated setting: for settings deprecated in an unknown,
            # unsupported Scrapy version, deprecations are only reported if
            # using a supported Scrapy version, because on unsupported Scrapy
            # versions we cannot tell whether or not it is deprecated.
            (
                (f"scrapy=={SCRAPY_LOWEST_SUPPORTED}",),
                "LOG_UNSERIALIZABLE_REQUESTS",
                (
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP28 deprecated setting: deprecated in scrapy 2.0.1 or lower; use SCHEDULER_DEBUG instead",
                        path=path,
                        column=column,
                    ),
                    ExpectedIssue(
                        "SCP32 wrong setting method: use getbool()",
                        path=path,
                        column=column - 1,
                    ),
                ),
            ),
            (
                (f"scrapy=={SCRAPY_ANCIENT_VERSION}",),
                "LOG_UNSERIALIZABLE_REQUESTS",
                (
                    ExpectedIssue(
                        "SCP14 unsupported requirement: flake8-scrapy only supports scrapy 2.0.1+",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP32 wrong setting method: use getbool()",
                        path=path,
                        column=column - 1,
                    ),
                ),
            ),
            # SCP29 setting needs upgrade
            (
                ("scrapy==2.7.0",),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                (
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                ),
            ),
            (
                ("scrapy==2.6.3",),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                (
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP29 setting needs upgrade: added in scrapy 2.7.0",
                        column=column,
                        path=path,
                    ),
                ),
            ),
            # SCP30 removed setting
            (
                ("scrapy==2.1.0",),
                "LOG_UNSERIALIZABLE_REQUESTS",
                (
                    ExpectedIssue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        "SCP30 removed setting: deprecated in scrapy 2.0.1 or "
                        "lower, removed in 2.1.0; use SCHEDULER_DEBUG instead",
                        path=path,
                        column=column,
                    ),
                    ExpectedIssue(
                        "SCP32 wrong setting method: use getbool()",
                        path=path,
                        column=column - 1,
                    ),
                ),
            ),
            # SCP31 missing setting requirement
            (
                ("scrapy",),
                "SCRAPY_POET_CACHE",
                ExpectedIssue(
                    "SCP31 missing setting requirement: scrapy-poet",
                    path=path,
                    column=column,
                ),
            ),
            (
                (f"scrapy=={SCRAPY_HIGHEST_KNOWN}",),
                "SCRAPY_POET_CACHE",
                ExpectedIssue(
                    "SCP31 missing setting requirement: scrapy-poet",
                    path=path,
                    column=column,
                ),
            ),
            (
                (f"scrapy=={SCRAPY_HIGHEST_KNOWN}", "scrapy-poet==0.26.0"),
                "SCRAPY_POET_CACHE",
                NO_ISSUE,
            ),
            (
                ("scrapy", "scrapy-poet"),
                "SCRAPY_POET_CACHE",
                NO_ISSUE,
            ),
        )
    ),
)


@cases(CASES)
def test(
    files: File | list[File],
    expected: ExpectedIssue | list[ExpectedIssue] | None,
    options,
):
    check_project(files, expected, options)
