from __future__ import annotations

import ast
from collections.abc import Sequence

from tests.helpers import check_project

from . import NO_ISSUE, File, Issue, cases


def supports_alias_col_offset():
    code = "import foo"
    tree = ast.parse(code)
    assert isinstance(tree.body[0], ast.Import)
    alias = tree.body[0].names[0]
    return hasattr(alias, "col_offset")


# Python 3.10+
ALIAS_HAS_COL_OFFSET = supports_alias_col_offset()

FALSE_BOOLS = ("False", "'false'", "0")
TRUE_UNKNOWN_OR_INVALID_BOOLS = ("True", "'true'", "1", "foo", "'foo'")


def default_issues(
    path: str | None = None, exclude: int | set[int] | None = None
) -> Sequence[Issue]:
    exclude = {exclude} if isinstance(exclude, int) else exclude or set()
    return [
        Issue(message=message, path=path)
        for message in (
            "SCP08 no project USER_AGENT",
            "SCP09 robots.txt ignored by default",
            "SCP10 incomplete project throttling",
        )
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
            # SCP12 imported setting
            *(
                (
                    code,
                    Issue(
                        "SCP12 imported setting",
                        column=column if ALIAS_HAS_COL_OFFSET else 0,
                        path=path,
                    ),
                )
                for code, column in (
                    ("from foo import FOO", 16),
                    ("from foo import bar as BAR", 23),
                    ("import FOO", 7),
                    ("import foo as BAR", 14),
                )
            ),
            (
                "from foo import FOO, BAR",
                [
                    Issue(
                        "SCP12 imported setting",
                        column=16 if ALIAS_HAS_COL_OFFSET else 0,
                        path=path,
                    ),
                    Issue(
                        "SCP12 imported setting",
                        column=21 if ALIAS_HAS_COL_OFFSET else 0,
                        path=path,
                    ),
                ],
            ),
            (
                "import foo, BAR",
                Issue(
                    "SCP12 imported setting",
                    column=12 if ALIAS_HAS_COL_OFFSET else 0,
                    path=path,
                ),
            ),
            *(
                (code, NO_ISSUE)
                for code in (
                    "from foo import bar",
                    "from foo import Bar",
                    "import foo",
                    "from foo import FOO as bar",
                    "import FOO as bar",
                )
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
    # Silencing or repositioning of checks that trigger on empty setting
    # modules.
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=path),
            ],
            (*default_issues(path, exclude=exclude), *issues),
        )
        for path in ["a.py"]
        for code, exclude, issues in (
            # SCP08 no project USER_AGENT
            *(
                (code, 8, ())
                for code in (
                    "USER_AGENT = 'Jane Doe (jane@doe.example)'",
                    "if a:\n"
                    "    USER_AGENT = 'Jane Doe (jane@doe.example)'\n"
                    "else:\n"
                    "    USER_AGENT = 'Example Company (+https://company.example)'",
                )
            ),
            # SCP09 robots.txt ignored by default
            *(
                (f"ROBOTSTXT_OBEY = {value}", 9, ())
                for value in TRUE_UNKNOWN_OR_INVALID_BOOLS
            ),
            *(
                (
                    f"ROBOTSTXT_OBEY = {value}",
                    9,
                    (
                        Issue(
                            "SCP09 robots.txt ignored by default", column=17, path=path
                        ),
                    ),
                )
                for value in FALSE_BOOLS
            ),
            # SCP10 incomplete project throttling
            *(
                (f"AUTOTHROTTLE_ENABLED = {value}", 10, ())
                for value in TRUE_UNKNOWN_OR_INVALID_BOOLS
            ),
            *(
                (
                    f"AUTOTHROTTLE_ENABLED = {value}",
                    10,
                    (
                        Issue(
                            "SCP10 incomplete project throttling", column=0, path=path
                        ),
                    ),
                )
                for value in FALSE_BOOLS
            ),
            (
                "CONCURRENT_REQUESTS = 1\nCONCURRENT_REQUESTS_PER_DOMAIN = 1\nDOWNLOAD_DELAY = 5.0",
                10,
                (),
            ),
            *(
                (
                    code,
                    10,
                    (
                        Issue(
                            "SCP10 incomplete project throttling", column=0, path=path
                        ),
                    ),
                )
                for code in (
                    "CONCURRENT_REQUESTS = 1\nCONCURRENT_REQUESTS_PER_DOMAIN = 1",
                    "CONCURRENT_REQUESTS = 1\nDOWNLOAD_DELAY = 5.0",
                    "CONCURRENT_REQUESTS_PER_DOMAIN = 1\nDOWNLOAD_DELAY = 5.0",
                )
            ),
        )
    ),
]


@cases(CASES)
def test(input: File | list[File], expected: Issue | list[Issue] | None):
    check_project(input, expected)
