from __future__ import annotations

from tests.helpers import check_project

from . import NO_ISSUE, File, Issue, cases

CASES = [
    # Code checks on a single setting module
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            issues,
        )
        for path in ["a.py"]
        for code, issues in (
            # Baseline
            ("BOT_NAME = 'a'", NO_ISSUE),
            # SCP07 redefined setting
            *(
                (
                    code,
                    Issue(
                        "SCP07 redefined setting: seen first at line 1",
                        line=2,
                        path=path,
                    ),
                )
                for code in (
                    'BOT_NAME = "a"\nBOT_NAME = "a"',
                    'BOT_NAME = "a"\nBOT_NAME = "b"',
                )
            ),
            (
                'if a:\n    BOT_NAME = "a"\nelse:\n    BOT_NAME = "b"',
                NO_ISSUE,
            ),
        )
    ),
    # Setting module detection and checking
    *(
        (files, issues)
        for code, issue in (
            (
                'BOT_NAME = "a"\nBOT_NAME = "a"',
                Issue("SCP07 redefined setting: seen first at line 1", line=2),
            ),
        )
        for files, issues in (
            # - Only modules declared in scrapy.cfg are checked.
            # - settings.py is not assumed to be a setting module.
            # - Multiple setting modules are supported.
            # - module/__init__.py is supported and takes precedence over
            #   module.py
            # - Unexisting modules are ignored.
            (
                (
                    File("[settings]\na=b\nc=d\ne=f", path="scrapy.cfg"),
                    File(code, path="a.py"),
                    File(code, path="b.py"),
                    File(code, path="d.py"),
                    File(code, path="d/__init__.py"),
                    File(code, path="settings.py"),
                ),
                (
                    issue.replace(path="b.py"),
                    issue.replace(path="d/__init__.py"),
                ),
            ),
            # scrapy.cfg files may miss the [settings] section, in which case
            # no module is treated as a setting module.
            (
                (
                    File("", path="scrapy.cfg"),
                    File(code, path="a.py"),
                ),
                NO_ISSUE,
            ),
        )
    ),
    # Checks supporting unknown settings should ignore module variables with
    # any lowercase character in the name, but should take into account
    # anything else.
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            issues if is_setting_like else NO_ISSUE,
        )
        for path in ["a.py"]
        for setting, is_setting_like in (
            ("_FOO", True),  # _-prefixed
            ("F", True),  # short
            ("FoO", False),  # mixed case
        )
        for code, issues in (
            # SCP07 redefined setting
            (
                f'{setting} = "a"\n{setting} = "a"',
                Issue(
                    "SCP07 redefined setting: seen first at line 1",
                    line=2,
                    path=path,
                ),
            ),
        )
    ),
]


@cases(CASES)
def test(input: File | list[File], expected: Issue | list[Issue] | None):
    check_project(input, expected)
