from __future__ import annotations

import ast
from collections.abc import Sequence

from packaging.version import Version

from tests.helpers import check_project

from . import NO_ISSUE, Cases, File, Issue, cases

FALSE_BOOLS = ("False", "'false'", "0")
TRUE_UNKNOWN_OR_INVALID_BOOLS = ("True", "'true'", "1", "foo", "'foo'")


def supports_alias_col_offset():
    code = "import foo"
    tree = ast.parse(code)
    assert isinstance(tree.body[0], ast.Import)
    alias = tree.body[0].names[0]
    return hasattr(alias, "col_offset")


# Python 3.10+
ALIAS_HAS_COL_OFFSET = supports_alias_col_offset()


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


CASES: Cases = (
    # Non-settings module Python file
    *(
        (
            [File(code, path=path)],
            issues,
            {},
        )
        for path in ["a.py"]
        for code, issues in (
            # Any object or attribute named “settings” used as a Settings
            # object (subscript, Settings getters) is assumed to be one.
            ("settings['FOO']", Issue("SCP27 unknown setting", column=9, path=path)),
            (
                "self.settings['FOO']",
                Issue("SCP27 unknown setting", column=14, path=path),
            ),
            (
                "crawler.settings['FOO']",
                Issue("SCP27 unknown setting", column=17, path=path),
            ),
            # Anything else is not considered a Settings object and thus
            # ignored.
            ("setting['FOO']", NO_ISSUE),
            ("foo['FOO']", NO_ISSUE),
            ("foo.bar['FOO']", NO_ISSUE),
            # Outside setting modules, module variables are not considered
            # settings. (separate test cases later verify that they are
            # interpreted as settings in setting modules)
            ("FOO = 'bar'", NO_ISSUE),
            # Subscript assignment also triggers setting name checks,
            (
                "settings['FOO'] = 'bar'",
                Issue("SCP27 unknown setting", column=9, path=path),
            ),
            # even if the value is not supported for setting value checks,
            (
                "settings['FOO'] = bar",
                Issue("SCP27 unknown setting", column=9, path=path),
            ),
            # and even on attributes.
            (
                "self.settings['FOO'] = 'bar'",
                Issue("SCP27 unknown setting", column=14, path=path),
            ),
            # BaseSetting methods that have a setting name as a parameter
            # trigger setting name checks,
            *(
                (
                    f"settings.{method_name}('FOO')",
                    Issue(
                        "SCP27 unknown setting", column=len(method_name) + 10, path=path
                    ),
                )
                for method_name in (
                    "__contains__",
                    "__delitem__",
                    "__getitem__",
                    "__init__",
                    "__setitem__",
                    "add_to_list",
                    "delete",
                    "get",
                    "getbool",
                    "getint",
                    "getfloat",
                    "getlist",
                    "getdict",
                    "getdictorlist",
                    "getpriority",
                    "getwithbase",
                    "pop",
                    "remove_from_list",
                    "replace_in_component_priority_dict",
                    "set",
                    "set_in_component_priority_dict",
                    "setdefault",
                    "setdefault_in_component_priority_dict",
                )
            ),
            # regardless of parameter syntax used,
            *(
                (
                    f"settings.get({params})",
                    Issue(
                        "SCP27 unknown setting", column=13 + column_offset, path=path
                    ),
                )
                for params, column_offset in (
                    ("name='FOO'", 5),
                    ("'FOO', foo", 0),
                    ("'FOO', default=foo", 0),
                    ("name='FOO', default=foo", 5),
                    ("default=foo, name='FOO'", 18),
                    # and even if parameters do not match the expected function
                    # signature, since the similarities could suggest that it
                    # is still about a setting name.
                    ("'FOO', foo, bar", 0),
                )
            ),
            # and not triggering issues with unparseable values.
            *(
                (
                    f"settings.get({params})",
                    NO_ISSUE,
                )
                for params in (
                    "foo",
                    "name=foo",
                )
            ),
            # Callables that expect a setting dict also trigger setting name
            # checks,
            *(
                (
                    f"{callable}({{'FOO': 'bar'}})",
                    Issue("SCP27 unknown setting", column=len(callable) + 2, path=path),
                )
                for callable in (
                    "BaseSettings",
                    "Settings",
                    "overridden_settings",
                    "settings.setdict",
                    "settings.update",
                    # even if they are attributes,
                    "settings.BaseSettings",
                    "settings.overridden_settings",
                    "self.settings.setdict",
                )
            ),
            # ignoring unparseable values,
            *(
                (
                    f"Settings({params})",
                    NO_ISSUE,
                )
                for params in (
                    "foo",
                    "values=foo",
                    "settings=foo",
                )
            ),
            # supporting different parameter syntaxes,
            *(
                (
                    f"Settings({params})",
                    Issue("SCP27 unknown setting", column=9 + column_offset, path=path),
                )
                for params, column_offset in (
                    ('{"FOO": "bar"}, foo=bar', 1),
                    ('settings={"FOO": "bar"}', 10),
                    ('values={"FOO": "bar"}', 8),
                    ('foo=bar, values={"FOO": "bar"}', 17),
                    ('foo=bar, settings={"FOO": "bar"}', 19),
                )
            ),
            # dict() syntax,
            (
                "Settings(dict(FOO='bar'))",
                Issue("SCP27 unknown setting", column=14, path=path),
            ),
            # and checking all keys in the dict.
            (
                'Settings({"USER_AGENT": "foo", "BAR": "baz"})',
                Issue("SCP27 unknown setting", column=31, path=path),
            ),
            (
                "Settings(dict(USER_AGENT='foo', BAR='baz'))",
                Issue("SCP27 unknown setting", column=32, path=path),
            ),
            # "`FOO" in settings` triggers setting name checks,
            (
                "'FOO' in settings",
                Issue("SCP27 unknown setting", path=path),
            ),
            # also when not is involved,
            (
                "'FOO' not in settings",
                Issue("SCP27 unknown setting", path=path),
            ),
            # even for attributes,
            (
                "'FOO' in self.settings",
                Issue("SCP27 unknown setting", path=path),
            ),
            # but not for non-settings objects.
            (
                "'FOO' in foo",
                NO_ISSUE,
            ),
            # SCP27 unknown setting
            *(
                (
                    f"settings['{name}']",
                    (
                        Issue("SCP27 unknown setting", column=9, path=path)
                        if issue is True
                        else Issue(
                            f"SCP27 unknown setting: did you mean: {issue}?",
                            column=9,
                            path=path,
                        )
                        if isinstance(issue, str)
                        else Issue(
                            f"SCP27 unknown setting: did you mean: {', '.join(issue)}?",
                            column=9,
                            path=path,
                        )
                        if isinstance(issue, Sequence)
                        else NO_ISSUE
                    ),
                )
                for name, issue in (
                    # Known setting
                    ("BOT_NAME", False),
                    # No suggestions
                    ("FOO", True),
                    # Predefined suggestions
                    (
                        "CONCURRENCY",
                        ("CONCURRENT_REQUESTS", "CONCURRENT_REQUESTS_PER_DOMAIN"),
                    ),
                    ("DELAY", "DOWNLOAD_DELAY"),
                    # Automatic suggestions
                    ("ADD_ONS", "ADDONS"),
                    ("DEFAULT_ITEM_CLS", "DEFAULT_ITEM_CLASS"),
                    ("REQUEST_HEADERS", "DEFAULT_REQUEST_HEADERS"),
                    (
                        "DOWNLOAD_MIDDLEWARES",
                        (
                            "DOWNLOADER_MIDDLEWARES",
                            "DOWNLOAD_HANDLERS",
                            "DOWNLOAD_DELAY",
                        ),
                    ),
                    (
                        "DOWNLOADER_HANDLERS",
                        (
                            "DOWNLOAD_HANDLERS",
                            "DOWNLOADER_MIDDLEWARES",
                            "DOWNLOADER_STATS",
                        ),
                    ),
                    ("TIMEOUT", ("DNS_TIMEOUT", "TIMEOUT_LIMIT")),
                )
            ),
        )
    ),
    # Single setting module
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
            {},
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
            # SCP17 redundant setting value
            *(
                (
                    f"{name} = {value}",
                    Issue(
                        "SCP17 redundant setting value",
                        line=1,
                        column=len(name) + 3,
                        path=path,
                    ),
                )
                for name, value in (
                    ("BOT_NAME", "'scrapybot'"),
                    ("CONCURRENT_REQUESTS", "16"),
                    ("COOKIES_ENABLED", "True"),
                    ("DOWNLOAD_DELAY", "0"),
                    ("DOWNLOAD_DELAY", "0.0"),
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
                (code, NO_ISSUE)
                for code in (
                    # Literals
                    'BOT_NAME = "myproject"',
                    "CONCURRENT_REQUESTS = 32",
                    "COOKIES_ENABLED = False",
                    "DOWNLOAD_DELAY = 1.5",
                    "AUTOTHROTTLE_DEBUG = True",
                    "JOBDIR = 'value'",
                    'ADDONS = {"addon1": True}',
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
                Issue("SCP27 unknown setting", path=path),
            ),
        )
    ),
    # Versioned settings
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(f"scrapy=={version}", path="requirements.txt"),
                File(f"{name} = {value}", path=path),
            ],
            (
                *default_issues(path),
                Issue("SCP13 incomplete requirements freeze", path="requirements.txt"),
                *(
                    Issue(message, path="requirements.txt")
                    for message, min_version in (
                        (
                            "SCP14 unsupported requirement: scrapy-flake8 only supports scrapy>=2.0.1+",
                            "2.0.1",
                        ),
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                            "2.11.2 ",
                        ),
                    )
                    if Version(version) < Version(min_version)
                ),
                *(
                    (
                        Issue(
                            "SCP17 redundant setting value",
                            column=len(name) + 3,
                            path=path,
                        ),
                    )
                    if should_trigger
                    else ()
                ),
            ),
            {},
        )
        for path in ["a.py"]
        for version, name, value, should_trigger in (
            (
                "2.13.0",
                "TWISTED_REACTOR",
                '"twisted.internet.asyncioreactor.AsyncioSelectorReactor"',
                True,
            ),
            ("2.13.0", "TWISTED_REACTOR", "None", False),
            ("2.12.0", "TWISTED_REACTOR", "None", True),
            (
                "2.12.0",
                "TWISTED_REACTOR",
                '"twisted.internet.asyncioreactor.AsyncioSelectorReactor"',
                False,
            ),
            # Unsupported Scrapy version. SCP17 does not trigger for any value
            # because the default value of the setting at that version of
            # Scrapy is considered unknown.
            ("2.0.0", "TWISTED_REACTOR", "None", False),
            (
                "2.0.0",
                "TWISTED_REACTOR",
                '"twisted.internet.asyncioreactor.AsyncioSelectorReactor"',
                False,
            ),
            # If a Scrapy version is known, SCP17 is still triggered or not as
            # usual for settings for which we do not know a history of default
            # value changes, but we do know their default value.
            (
                "2.13.0",
                "TELNETCONSOLE_USERNAME",
                '"scrapy"',
                True,
            ),
            (
                "2.13.0",
                "TELNETCONSOLE_USERNAME",
                '"username"',
                False,
            ),
        )
    ),
    *(
        (
            [
                File("[settings]\na=a", path="scrapy.cfg"),
                File(requirements, path="requirements.txt"),
                File('TELNETCONSOLE_USERNAME = "scrapy"', path=path),
            ],
            (
                *default_issues(path),
                *(
                    Issue(
                        "SCP13 incomplete requirements freeze", path="requirements.txt"
                    )
                    for _ in range(1)
                    if not isinstance(requirements, bytes)
                ),
                Issue(
                    "SCP17 redundant setting value",
                    column=len("TELNETCONSOLE_USERNAME") + 3,
                    path=path,
                ),
            ),
            {},
        )
        for path in ["a.py"]
        for requirements in (
            # Invalid or non-frozen requirements do not prevent SCP17 for
            # settings for which SCP17 reporting does not depend on the version
            # of Scrapy.
            "",
            "# scrapy==2.13.0",
            "scrapy>=2.13.0",
            "scrapy>=2.13.0,<2.14.0",
            "scrapy!",
            "scrapy!=2.13.0  # foo",
            b"\xff\xfe\x00\x00",
        )
    ),
    # Setting module detection and checking
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
                *(
                    Issue(
                        "SCP27 unknown setting",
                        line=line,
                        path=path,
                    )
                    for line in range(1, 3)
                    if is_setting_like
                ),
            ),
            {},
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
            {},
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
                        Issue("SCP17 redundant setting value", column=17, path=path),
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
                        Issue("SCP17 redundant setting value", column=23, path=path),
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
)


@cases(CASES)
def test(
    input: File | list[File], expected: Issue | list[Issue] | None, flake8_options
):
    check_project(input, expected, flake8_options)
