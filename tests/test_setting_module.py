from __future__ import annotations

import ast
from collections.abc import Sequence
from inspect import cleandoc

from tests.helpers import check_project
from tests.settings import default_issues

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases, iter_issues

FALSE_BOOLS = ("False", "'false'", "0")
TRUE_BOOLS = ("True", "'true'", "1")
PATH = "a.py"


def supports_alias_col_offset():
    code = "import foo"
    tree = ast.parse(code)
    assert isinstance(tree.body[0], ast.Import)
    alias = tree.body[0].names[0]
    return hasattr(alias, "col_offset")


# Python 3.10+
ALIAS_HAS_COL_OFFSET = supports_alias_col_offset()


CASES: Cases = (
    # Setting module detection
    *(
        (files, issues, {})
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
    # Setting module checks
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(code, path=PATH),
            ],
            (
                *default_issues(PATH),
                *iter_issues(issues),
            ),
            {},
        )
        for code, issues in (
            # Baseline
            ("BOT_NAME = 'a'", NO_ISSUE),
            # Non-setting-module specific checks for Python files also apply
            (
                "settings['FOO']",
                ExpectedIssue("SCP27 unknown setting", column=9, path=PATH),
            ),
            # Setting name checks work with module-specific setting syntax
            *(
                (
                    code,
                    (
                        ExpectedIssue(
                            "SCP27 unknown setting",
                            column=column,
                            path=PATH,
                        ),
                        *extra_issues,
                    ),
                )
                for code, column, extra_issues in (
                    ("FOO = 'bar'", 0, ()),
                    (
                        "class FOO:\n    pass",
                        6,
                        (
                            ExpectedIssue(
                                "SCP11 improper setting definition",
                                column=6,
                                path=PATH,
                            ),
                        ),
                    ),
                    (
                        "def FOO():\n    pass",
                        4,
                        (
                            ExpectedIssue(
                                "SCP11 improper setting definition",
                                column=4,
                                path=PATH,
                            ),
                        ),
                    ),
                    (
                        "import FOO",
                        7 if ALIAS_HAS_COL_OFFSET else 0,
                        (
                            ExpectedIssue(
                                "SCP12 imported setting",
                                column=7 if ALIAS_HAS_COL_OFFSET else 0,
                                path=PATH,
                            ),
                        ),
                    ),
                )
            ),
            # SCP07 redefined setting
            *(
                (
                    code,
                    ExpectedIssue(
                        "SCP07 redefined setting: seen first at line 1",
                        line=2,
                        path=PATH,
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
            # SCP11 improper setting definition
            *(
                (
                    "\n".join(lines),
                    ExpectedIssue(
                        "SCP11 improper setting definition",
                        column=column,
                        path=PATH,
                    ),
                )
                for lines, column in (
                    (
                        (
                            "class DEFAULT_ITEM_CLASS:",
                            "    pass",
                        ),
                        6,
                    ),
                    (
                        (
                            "def FEED_URI_PARAMS(params, spider):",
                            "    return params",
                        ),
                        4,
                    ),
                )
            ),
            *(
                (
                    "\n".join(lines),
                    NO_ISSUE,
                )
                for lines in (
                    (
                        "class DefaultItemClass:",
                        "    pass",
                    ),
                    (
                        "def feed_uri_params(params, spider):",
                        "    return params",
                    ),
                )
            ),
            # SCP12 imported setting
            *(
                (
                    code,
                    ExpectedIssue(
                        "SCP12 imported setting",
                        column=column if ALIAS_HAS_COL_OFFSET else 0,
                        path=PATH,
                    ),
                )
                for code, column in (
                    ("from foo import BOT_NAME", 16),
                    ("from foo import bar as BOT_NAME", 23),
                    ("import BOT_NAME", 7),
                    ("import foo as BOT_NAME", 14),
                )
            ),
            (
                "from foo import BOT_NAME, SPIDER_MODULES",
                [
                    ExpectedIssue(
                        "SCP12 imported setting",
                        column=16 if ALIAS_HAS_COL_OFFSET else 0,
                        path=PATH,
                    ),
                    ExpectedIssue(
                        "SCP12 imported setting",
                        column=26 if ALIAS_HAS_COL_OFFSET else 0,
                        path=PATH,
                    ),
                ],
            ),
            (
                "import foo, BOT_NAME",
                ExpectedIssue(
                    "SCP12 imported setting",
                    column=12 if ALIAS_HAS_COL_OFFSET else 0,
                    path=PATH,
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
            # SCP17 redundant setting value
            *(
                (
                    f"{name} = {value}",
                    ExpectedIssue(
                        "SCP17 redundant setting value",
                        line=1,
                        column=len(name) + 3,
                        path=PATH,
                    ),
                )
                for name, value in (
                    ("BOT_NAME", "'scrapybot'"),
                    ("CONCURRENT_REQUESTS", "16"),
                    ("COOKIES_ENABLED", "True"),
                    ("COOKIES_ENABLED", '"true"'),
                    ("COOKIES_ENABLED", '"True"'),
                    ("COOKIES_ENABLED", "1"),
                    ("AUTOTHROTTLE_DEBUG", '"false"'),
                    ("AUTOTHROTTLE_DEBUG", '"False"'),
                    ("AUTOTHROTTLE_DEBUG", "0"),
                    ("AUTOTHROTTLE_DEBUG", "False"),
                    ("ADDONS", "{}"),
                    ("SPIDER_MODULES", "[]"),
                    ("HTTPCACHE_IGNORE_SCHEMES", '["file"]'),
                    ("TELNETCONSOLE_PORT", "[6023, 6073]"),
                    (
                        "DEFAULT_REQUEST_HEADERS",
                        '{"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en"}',
                    ),
                    ("ASYNCIO_EVENT_LOOP", "None"),
                )
            ),
            *(
                (
                    f"{name} = {value}",
                    (
                        ExpectedIssue(
                            "SCP17 redundant setting value",
                            line=1,
                            column=len(name) + 3,
                            path=PATH,
                        ),
                        *iter_issues(issues),
                    ),
                )
                for name, value, issues in (
                    *(
                        (
                            "DOWNLOAD_DELAY",
                            value,
                            ExpectedIssue(
                                "SCP38 low project throttling",
                                column=17,
                                path=PATH,
                            ),
                        )
                        for value in ("0", "0.0")
                    ),
                )
            ),
            *(
                (code, NO_ISSUE)
                for code in (
                    # Literals
                    'BOT_NAME = "myproject"',
                    "CONCURRENT_REQUESTS = 32",
                    "COOKIES_ENABLED = False",
                    "DOWNLOAD_DELAY = 1.5",
                    "AUTOTHROTTLE_DEBUG = True",
                    "JOBDIR = 'value'",
                    'ADDONS = {"addon1.Addon": True}',
                    'ADDONS = {"addon1.Addon": 100}',
                    'SPIDER_MODULES = ["myproject.spiders"]',
                    "RETRY_HTTP_CODES = [500, 502]",
                    # Unparseable values
                    "BOT_NAME = get_bot_name()",
                    "SPIDER_MODULES = [module]",
                    "SPIDER_MODULES = [module for module in modules]",
                    'DEFAULT_REQUEST_HEADERS = {"User-Agent": get_user_agent()}',
                    "LOG_FILE = None if debug else 'app.log'",
                    # Settings with default_value=UNKNOWN_SETTING_VALUE
                    "EDITOR = 'vi'",
                    # Versioned settings (SCP17 is not triggered without requirements.txt)
                    "TWISTED_REACTOR = None",
                    'TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"',
                )
            ),
            # SCP27 unknown setting
            (
                "FOO = 'bar'",
                ExpectedIssue("SCP27 unknown setting", path=PATH),
            ),
            # SCP35 no-op setting update
            (
                "SPIDER_MODULES = ['myproject.spiders']",
                NO_ISSUE,
            ),
            (
                "settings['SPIDER_MODULES'] = ['myproject.spiders']",
                ExpectedIssue("SCP35 no-op setting update", column=9, path=PATH),
            ),
            # Setting value checks for pre-crawler settings
            (
                "ADDONS = '{}'",
                ExpectedIssue("SCP17 redundant setting value", column=9, path=PATH),
            ),
            (
                "ADDONS = {}",
                ExpectedIssue("SCP17 redundant setting value", column=9, path=PATH),
            ),
            *(
                (
                    f"ADDONS = {value}",
                    NO_ISSUE,
                )
                for value in (
                    "{'my.addons.Addon': 100}",
                    "{'my.addons.Addon': value}",
                )
            ),
            *(
                (
                    f"ADDONS = {value}",
                    ExpectedIssue(
                        f"SCP36 invalid setting value: {detail}",
                        column=9 + offset,
                        path=PATH,
                    ),
                )
                for value, detail, offset in (
                    ("1", "must be a dict, not int (1)", 0),
                    ("{1: 100}", "keys must be components, not int (1)", 1),
                    (
                        "{'myaddons': 100}",
                        "'myaddons' does not look like an import path",
                        1,
                    ),
                    (
                        "{Addon: 'foo'}",
                        "dict values must be integers, not str ('foo')",
                        8,
                    ),
                    (
                        "{Addon: None}",
                        "dict values must be integers, not NoneType (None)",
                        8,
                    ),
                    ("{Addon: {}}", "dict values must be integers", 8),
                )
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
                File(code, path=PATH),
            ],
            (
                *(
                    issues
                    if isinstance(issues, Sequence)
                    else (issues,)
                    if issues and is_setting_like
                    else ()
                ),
                *default_issues(PATH),
                *(
                    ExpectedIssue(
                        "SCP27 unknown setting",
                        line=line,
                        path=PATH,
                    )
                    for line in range(1, 3)
                    if is_setting_like
                ),
            ),
            {},
        )
        for setting, is_setting_like in (
            ("_FOO", True),  # _-prefixed
            ("F", True),  # short
            ("FoO", False),  # mixed case
        )
        for code, issues in (
            # SCP07 redefined setting
            (
                f'{setting} = "a"\n{setting} = "a"',
                ExpectedIssue(
                    "SCP07 redefined setting: seen first at line 1",
                    line=2,
                    path=PATH,
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
                File(code, path=PATH),
            ],
            (
                *default_issues(PATH, exclude=exclude),
                *iter_issues(issues),
            ),
            {},
        )
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
            *((f"ROBOTSTXT_OBEY = {value}", 9, ()) for value in TRUE_BOOLS),
            *(
                (
                    f"ROBOTSTXT_OBEY = {value}",
                    9,
                    (
                        ExpectedIssue(
                            "SCP09 robots.txt ignored by default",
                            column=17,
                            path=PATH,
                        ),
                        ExpectedIssue(
                            "SCP17 redundant setting value",
                            column=17,
                            path=PATH,
                        ),
                    ),
                )
                for value in FALSE_BOOLS
            ),
            ("ROBOTSTXT_OBEY = foo", 9, ()),
            (
                "ROBOTSTXT_OBEY = 'foo'",
                9,
                (ExpectedIssue("SCP36 invalid setting value", column=17, path=PATH),),
            ),
            # SCP10 incomplete project throttling
            (
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1\nDOWNLOAD_DELAY = 1.0",
                10,
                NO_ISSUE,
            ),
            *(
                (
                    code,
                    10,
                    (
                        ExpectedIssue(
                            "SCP10 incomplete project throttling",
                            column=0,
                            path=PATH,
                        ),
                    ),
                )
                for code in (
                    "CONCURRENT_REQUESTS_PER_DOMAIN = 1",
                    "DOWNLOAD_DELAY = 1.0",
                )
            ),
            # SCP10 incomplete project throttling: AUTOTHROTTLE is ignored
            *(
                (
                    f"AUTOTHROTTLE_ENABLED = {value}",
                    10,
                    ExpectedIssue("SCP10 incomplete project throttling", path=PATH),
                )
                for value in TRUE_BOOLS
            ),
            (
                "AUTOTHROTTLE_ENABLED = foo",
                10,
                ExpectedIssue("SCP10 incomplete project throttling", path=PATH),
            ),
            (
                "AUTOTHROTTLE_ENABLED = 'foo'",
                10,
                (
                    ExpectedIssue("SCP10 incomplete project throttling", path=PATH),
                    ExpectedIssue("SCP36 invalid setting value", column=23, path=PATH),
                ),
            ),
            *(
                (
                    f"AUTOTHROTTLE_ENABLED = {value}",
                    10,
                    (
                        ExpectedIssue("SCP10 incomplete project throttling", path=PATH),
                        ExpectedIssue(
                            "SCP17 redundant setting value",
                            column=23,
                            path=PATH,
                        ),
                    ),
                )
                for value in FALSE_BOOLS
            ),
            # SCP34 missing changing setting: FEED_EXPORT_ENCODING
            ("FEED_EXPORT_ENCODING = 'utf-8'", 34, ()),
            ("FEED_EXPORT_ENCODING = None", 34, ()),
            ("FEED_EXPORT_ENCODING = 'foo'", 34, ()),
            # SCP38 low project throttling
            (
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1\nDOWNLOAD_DELAY = 5.0",
                10,
                NO_ISSUE,
            ),
            (
                "CONCURRENT_REQUESTS_PER_DOMAIN = 1\nDOWNLOAD_DELAY = 1.0",
                10,
                NO_ISSUE,
            ),
            (
                "CONCURRENT_REQUESTS_PER_DOMAIN = 2\nDOWNLOAD_DELAY = 0.9",
                10,
                (
                    ExpectedIssue("SCP38 low project throttling", column=33, path=PATH),
                    ExpectedIssue(
                        "SCP38 low project throttling",
                        line=2,
                        column=17,
                        path=PATH,
                    ),
                ),
            ),
            (
                "CONCURRENT_REQUESTS_PER_DOMAIN = foo\nDOWNLOAD_DELAY = bar",
                10,
                NO_ISSUE,
            ),
            (
                "CONCURRENT_REQUESTS_PER_DOMAIN = 'foo'\nDOWNLOAD_DELAY = 'bar'",
                10,
                (
                    ExpectedIssue("SCP36 invalid setting value", column=33, path=PATH),
                    ExpectedIssue(
                        "SCP36 invalid setting value",
                        line=2,
                        column=17,
                        path=PATH,
                    ),
                ),
            ),
        )
    ),
    # SCP27 must not trigger for assignments within class of function
    # definitions.
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(
                    cleandoc(code),
                    path=PATH,
                ),
            ],
            (*default_issues(PATH),),
            {},
        )
        for code in (
            """
            class Foo:
                BAR = 'baz'
            """,
            """
            def foo():
                BAR = 'baz'
            """,
        )
    ),
    # Settings defined in any branch of a try-except block must be taken into
    # account.
    (
        [
            File("[settings]\na=a", path="scrapy.cfg"),
            File(
                cleandoc(
                    """
                    try:
                        USER_AGENT = 'a'
                    except Exception as e:
                        USER_AGENT = 'b'
                    else:
                        USER_AGENT = 'c'
                    finally:
                        USER_AGENT = 'd'
                    """
                ),
                path=PATH,
            ),
        ],
        (
            *default_issues(PATH, exclude=8),
            *(
                ExpectedIssue(
                    "SCP39 no contact info",
                    line=line,
                    column=17,
                    path=PATH,
                )
                for line in (2, 4, 6, 8)
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
