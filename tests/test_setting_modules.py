from __future__ import annotations

from collections.abc import Sequence

from tests.helpers import check_project

from . import NO_ISSUE, File, Issue, cases


def default_issues(
    path: str | None = None, exclude: int | set[int] | None = None
) -> Sequence[Issue]:
    exclude = {exclude} if isinstance(exclude, int) else exclude or set()
    return [
        Issue(
            message=message,
            path=path,
        )
        for message in ("SCP08 no project USER_AGENT",)
        if not any(message.startswith(f"SCP{code:02} ") for code in exclude)
    ]


CASES = [
    # Code checks on a single setting module
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            (
                *(
                    issues
                    if isinstance(issues, Sequence)
                    else (issues,)
                    if issues
                    else ()
                ),
                *default_issues(path),
            ),
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
        for default_issues in (default_issues(),)
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
                    File("", path="a.py"),
                    File("", path="b.py"),
                    File("", path="d.py"),
                    File("", path="d/__init__.py"),
                    File("", path="settings.py"),
                ),
                tuple(
                    issue.replace(path=path)
                    for path in ("b.py", "d/__init__.py")
                    for issue in default_issues
                ),
            ),
            # scrapy.cfg files may miss the [settings] section, in which case
            # no module is treated as a setting module.
            (
                (
                    File("", path="scrapy.cfg"),
                    File("", path="a.py"),
                ),
                NO_ISSUE,
            ),
        )
    ),
    # Checks that may work with unknown settings should ignore module variables
    # with any lowercase character in the name, but should take into account
    # anything else.
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            (
                *(
                    issues
                    if isinstance(issues, Sequence)
                    else (issues,)
                    if issues and is_setting_like
                    else ()
                ),
                *default_issues(path),
            ),
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
    # Checks that trigger on empty setting modules
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            (*default_issues(path, exclude=exclude),),
        )
        for path in ["a.py"]
        for code, exclude in (
            # SCP08 no project USER_AGENT
            (
                "USER_AGENT = 'Jane Doe (jane@doe.example)'",
                8,
            ),
            (
                "if a:\n"
                "    USER_AGENT = 'Jane Doe (jane@doe.example)'\n"
                "else:\n"
                "    USER_AGENT = 'Example Company (+https://company.example)'",
                8,
            ),
        )
    ),
]


@cases(CASES)
def test(input: File | list[File], expected: Issue | list[Issue] | None):
    check_project(input, expected)
