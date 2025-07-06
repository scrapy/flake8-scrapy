from __future__ import annotations

import ast
from collections.abc import Sequence
from itertools import cycle

from packaging.version import Version

from tests.helpers import check_project

from . import NO_ISSUE, Cases, File, Issue, cases
from .test_requirements import (
    SCRAPY_ANCIENT_VERSION,
    SCRAPY_FUTURE_VERSION,
    SCRAPY_HIGHEST_KNOWN,
    SCRAPY_LOWEST_SUPPORTED,
)

FALSE_BOOLS = ("False", "'false'", "0")
TRUE_UNKNOWN_OR_INVALID_BOOLS = ("True", "'true'", "1", "foo", "'foo'")


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def zip_uneven_cycle(a, b):
    if len(a) >= len(b):
        return tuple((*ta, *tb) for ta, tb in zip(a, cycle(b)))
    return tuple((*ta, *tb) for ta, tb in zip(cycle(a), b))


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
            "SCP34 missing changing setting: FEED_EXPORT_ENCODING changes from None to 'utf-8' in a future version of scrapy",
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
            *(
                (code, NO_ISSUE)
                for code in (
                    "FOO = 'bar'",
                    "class FOO:\n    pass",
                    "def FOO():\n    pass",
                    "import FOO",
                )
            ),
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
            # ignoring unparseable functions,
            (
                "foo()({'FOO': 'bar'})",
                NO_ISSUE,
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
            # ignoring unknown kwargs,
            (
                "Settings(foo={'FOO': 'bar'})",
                NO_ISSUE,
            ),
            # ignoring non-str keys,
            (
                "Settings({1: 'bar'})",
                NO_ISSUE,
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
            (
                "Settings(foo(FOO='bar'))",
                NO_ISSUE,
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
                    ("TIMEOUT", ("DOWNLOAD_TIMEOUT", "TIMEOUT_LIMIT")),
                )
            ),
            # SCP31 missing setting requirement: nothing is reported if there
            # are no requirements.
            (
                "settings['SCRAPY_POET_CACHE']",
                NO_ISSUE,
            ),
            # SCP32 wrong setting method: positional argument
            (
                "settings.getint('LOG_ENABLED')",
                Issue("SCP32 wrong setting method: use getbool()", column=9, path=path),
            ),
            # SCP32 wrong setting method: keyword argument
            (
                "settings.get(name='RETRY_TIMES')",
                Issue("SCP32 wrong setting method: use getint()", column=9, path=path),
            ),
            # SCP32 wrong setting method: subscript
            (
                "settings['DOWNLOAD_DELAY']",
                Issue(
                    "SCP32 wrong setting method: use getfloat()", column=8, path=path
                ),
            ),
            # SCP32 wrong setting method: subscript recommendation
            (
                "settings.getint('DEFAULT_DROPITEM_LOG_LEVEL')",
                Issue("SCP32 wrong setting method: use []", column=9, path=path),
            ),
            # SCP32 wrong setting method: list
            (
                "settings.add_to_list('LOG_SHORT_NAMES', 'foo')",
                Issue("SCP32 wrong setting method", column=21, path=path),
            ),
            (
                "settings.add_to_list('LOG_VERSIONS', 'foo')",
                NO_ISSUE,
            ),
            # SCP32 wrong setting method: component priority dict
            (
                "settings.replace_in_component_priority_dict('DOWNLOAD_HANDLERS', Old, New)",
                Issue("SCP32 wrong setting method", column=44, path=path),
            ),
            (
                "settings.replace_in_component_priority_dict('DOWNLOADER_MIDDLEWARES', Old, New)",
                NO_ISSUE,
            ),
            # SCP32 wrong setting method: component priority dict, based
            (
                "settings.getdict('DOWNLOADER_MIDDLEWARES')",
                Issue(
                    "SCP32 wrong setting method: use getwithbase()", column=9, path=path
                ),
            ),
            # SCP32 wrong setting method: regular dict, based
            (
                "settings.getdict('DOWNLOAD_HANDLERS')",
                Issue(
                    "SCP32 wrong setting method: use getwithbase()", column=9, path=path
                ),
            ),
            # SCP32 wrong setting method: component priority dict, not based
            (
                "settings.getwithbase('ADDONS')",
                Issue("SCP32 wrong setting method: use getdict()", column=9, path=path),
            ),
            # SCP32 wrong setting method: regular dict, not based
            (
                "settings.getwithbase('DOWNLOAD_SLOTS')",
                Issue("SCP32 wrong setting method: use getdict()", column=9, path=path),
            ),
            # SCP32 wrong setting method: non-getter setting method
            (
                "settings.__contains__('DEFAULT_DROPITEM_LOG_LEVEL')",
                NO_ISSUE,
            ),
            # SCP32 wrong setting method: setting with unknown type
            (
                "settings.getdict('DEBUG')",
                NO_ISSUE,
            ),
            # SCP33 base setting use
            (
                "settings['DOWNLOAD_HANDLERS_BASE']",
                Issue("SCP33 base setting use", column=9, path=path),
            ),
            (
                "settings['FOO_BASE']",
                Issue("SCP27 unknown setting", column=9, path=path),
            ),
            # SCP35 no-op setting update
            *(
                (
                    template.format_map(SafeDict(setting=setting, value=value)),
                    Issue(
                        "SCP35 no-op setting update",
                        column=column,
                        path=path,
                    ),
                )
                for template, column, setting, value in zip_uneven_cycle(
                    (
                        ("settings.delete('{setting}')", 16),
                        ("settings.pop(name='{setting}')", 18),
                        ("settings.set(name='{setting}', value={value})", 18),
                        ("settings.setdefault('{setting}', {value}, 'addon')", 20),
                        ("settings['{setting}'] = {value}", 9),
                        ("del self.settings['{setting}']", 18),
                        ("settings.__delitem__('{setting}')", 21),
                        ("crawler.settings.__setitem__('{setting}', {value})", 29),
                        ("BaseSettings({{'{setting}': {value}}})", 14),
                        ("settings.Settings(dict({setting}={value}))", 23),
                        (
                            "scrapy.settings.overridden_settings(settings={{'{setting}': {value}}})",
                            46,
                        ),
                    ),
                    (
                        ("ADDONS", "{'my.addons.Addon': 100}"),
                        ("ASYNCIO_EVENT_LOOP", "'uvloop.Loop'"),
                        ("COMMANDS_MODULE", "'my_project.commands'"),
                        ("DNS_RESOLVER", "'scrapy.resolver.CachingHostnameResolver'"),
                        ("DNS_TIMEOUT", "120"),
                        ("DNSCACHE_ENABLED", "False"),
                        ("DNSCACHE_SIZE", "20_000"),
                        ("FORCE_CRAWLER_PROCESS", "True"),
                        ("REACTOR_THREADPOOL_MAXSIZE", "50"),
                        ("SPIDER_LOADER_CLASS", "CustomSpiderLoader"),
                        ("SPIDER_LOADER_WARN_ONLY", "True"),
                        ("SPIDER_MODULES", "['my_project.spiders_module']"),
                        (
                            "TWISTED_REACTOR",
                            "'twisted.internet.pollreactor.PollReactor'",
                        ),
                    ),
                )
            ),
            *(
                (
                    template.format_map(SafeDict(setting=setting, value=value)),
                    Issue(
                        "SCP35 no-op setting update",
                        column=column,
                        path=path,
                    ),
                )
                for template, column, setting, value in zip_uneven_cycle(
                    (
                        ("settings.add_to_list('{setting}', {value})", 21),
                        (
                            "settings.remove_from_list(name='{setting}', item={value})",
                            31,
                        ),
                    ),
                    (
                        ("SPIDER_MODULES", "'myspiders'"),
                        ("SPIDER_MODULES", "'myproject.spiders'"),
                    ),
                )
            ),
            *(
                (
                    template.format_map(SafeDict(setting=setting)),
                    Issue(
                        "SCP35 no-op setting update",
                        column=column,
                        path=path,
                    ),
                )
                for template, column, setting in zip_uneven_cycle(
                    (
                        (
                            "settings.replace_in_component_priority_dict('{setting}', Old, New, 200)",
                            44,
                        ),
                        (
                            "settings.set_in_component_priority_dict(name='{setting}', cls=MyAddon, priority=300)",
                            45,
                        ),
                        (
                            "settings.setdefault_in_component_priority_dict('{setting}', Addon)",
                            47,
                        ),
                    ),
                    (("ADDONS",),),
                )
            ),
            (
                "\n".join(
                    (
                        "class MyAddon:",
                        "    def update_settings(self, settings):",
                        "        settings.add_to_list('SPIDER_MODULES', 'addon.spiders')",
                    )
                ),
                Issue(
                    "SCP35 no-op setting update",
                    line=3,
                    column=29,
                    path=path,
                ),
            ),
            (
                "\n".join(
                    (
                        "class MyAddon:",
                        "    def update_pre_crawler_settings(cls, settings):",
                        "        settings.add_to_list('SPIDER_MODULES', 'addon.spiders')",
                    )
                ),
                NO_ISSUE,
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
            # Non-setting-module specific checks for Python files also apply
            (
                "settings.get('FOO')",
                Issue("SCP27 unknown setting", column=13, path=path),
            ),
            # Setting name checks work with module-specific setting syntax
            *(
                (
                    code,
                    (
                        Issue("SCP27 unknown setting", column=column, path=path),
                        *extra_issues,
                    ),
                )
                for code, column, extra_issues in (
                    ("FOO = 'bar'", 0, ()),
                    (
                        "class FOO:\n    pass",
                        6,
                        (
                            Issue(
                                "SCP11 improper setting definition", column=6, path=path
                            ),
                        ),
                    ),
                    (
                        "def FOO():\n    pass",
                        4,
                        (
                            Issue(
                                "SCP11 improper setting definition", column=4, path=path
                            ),
                        ),
                    ),
                    (
                        "import FOO",
                        7 if ALIAS_HAS_COL_OFFSET else 0,
                        (
                            Issue(
                                "SCP12 imported setting",
                                column=7 if ALIAS_HAS_COL_OFFSET else 0,
                                path=path,
                            ),
                        ),
                    ),
                )
            ),
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
            # SCP11 improper setting definition
            *(
                (
                    "\n".join(lines),
                    Issue(
                        "SCP11 improper setting definition", column=column, path=path
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
                    Issue(
                        "SCP12 imported setting",
                        column=column if ALIAS_HAS_COL_OFFSET else 0,
                        path=path,
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
                    Issue(
                        "SCP12 imported setting",
                        column=16 if ALIAS_HAS_COL_OFFSET else 0,
                        path=path,
                    ),
                    Issue(
                        "SCP12 imported setting",
                        column=26 if ALIAS_HAS_COL_OFFSET else 0,
                        path=path,
                    ),
                ],
            ),
            (
                "import foo, BOT_NAME",
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
            # SCP35 no-op setting update
            (
                "SPIDER_MODULES = ['myproject.spiders']",
                NO_ISSUE,
            ),
            (
                "settings['SPIDER_MODULES'] = ['myproject.spiders']",
                Issue("SCP35 no-op setting update", column=9, path=path),
            ),
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
            # SCP34 missing changing setting: FEED_EXPORT_ENCODING
            ("FEED_EXPORT_ENCODING = 'utf-8'", 34, ()),
            ("FEED_EXPORT_ENCODING = None", 34, ()),
            ("FEED_EXPORT_ENCODING = 'foo'", 34, ()),
        )
    ),
    # Checks bassed on requirements and setting names
    *(
        (
            (
                File("", path="scrapy.cfg"),
                File("\n".join(requirements), path="requirements.txt"),
                File(f"settings[{setting_name!r}]", path=path),
            ),
            (
                Issue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
                *(
                    (issues,)
                    if isinstance(issues, Issue)
                    else issues
                    if isinstance(issues, Sequence)
                    else ()
                ),
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
                        Issue(
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
                            (
                                (),
                                "TIMEOUT",
                                (
                                    "DOWNLOAD_TIMEOUT",
                                    "TIMEOUT_LIMIT",
                                ),
                            ),
                            (
                                ("scrapy",),
                                "TIMEOUT",
                                ("DOWNLOAD_TIMEOUT",),
                            ),
                            (
                                ("scrapy", "scrapyrt"),
                                "TIMEOUT",
                                (
                                    "DOWNLOAD_TIMEOUT",
                                    "TIMEOUT_LIMIT",
                                ),
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
                            Issue(
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
                            Issue(
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
                Issue(
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
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    Issue(
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
                Issue(
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
                Issue(
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
                    Issue(
                        "SCP14 unsupported requirement: flake8-scrapy only supports scrapy 2.0.1+",
                        path="requirements.txt",
                    ),
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    Issue(
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
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    Issue(
                        "SCP28 deprecated setting: deprecated in scrapy 2.0.1 or lower; use SCHEDULER_DEBUG instead",
                        path=path,
                        column=column,
                    ),
                    Issue(
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
                    Issue(
                        "SCP14 unsupported requirement: flake8-scrapy only supports scrapy 2.0.1+",
                        path="requirements.txt",
                    ),
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    Issue(
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
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                ),
            ),
            (
                ("scrapy==2.6.3",),
                "REQUEST_FINGERPRINTER_IMPLEMENTATION",
                (
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    Issue(
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
                    Issue(
                        "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                        path="requirements.txt",
                    ),
                    Issue(
                        "SCP30 removed setting: deprecated in scrapy 2.0.1 or "
                        "lower, removed in 2.1.0; use SCHEDULER_DEBUG instead",
                        path=path,
                        column=column,
                    ),
                    Issue(
                        "SCP32 wrong setting method: use getbool()",
                        path=path,
                        column=column - 1,
                    ),
                ),
            ),
            # SCP31 missing setting requirement
            (
                (f"scrapy=={SCRAPY_HIGHEST_KNOWN}",),
                "SCRAPY_POET_CACHE",
                Issue(
                    "SCP31 missing setting requirement: scrapy-poet",
                    path=path,
                    column=column,
                ),
            ),
        )
    ),
    # Checks based on requirements and code in a settings module
    *(
        (
            (
                File("[settings]\na=a", path="scrapy.cfg"),
                File("\n".join(requirements), path="requirements.txt"),
                File(code, path=path),
            ),
            (
                *(
                    issues
                    if isinstance(issues, Sequence)
                    else (issues,)
                    if issues
                    else ()
                ),
                *default_issues(path),
                Issue("SCP13 incomplete requirements freeze", path="requirements.txt"),
            ),
            {},
        )
        for path in ("a.py",)
        for requirements, code, issues in (
            # Baseline
            (
                (),
                "",
                NO_ISSUE,
            ),
            # SCP34 missing changing setting
            (
                ("scrapy==2.13.0",),
                "",
                NO_ISSUE,
            ),
            (
                ("scrapy==2.13.0",),
                "TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'",
                Issue(
                    "SCP17 redundant setting value",
                    column=18,
                    path=path,
                ),
            ),
            (
                ("scrapy==2.12.0",),
                "",
                Issue(
                    "SCP34 missing changing setting: TWISTED_REACTOR changes "
                    "from None to "
                    "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                    "in scrapy 2.13.0",
                    path=path,
                ),
            ),
            (
                ("scrapy==2.12.0",),
                "TWISTED_REACTOR = None",
                NO_ISSUE,
            ),
            (
                ("scrapy==2.12.0",),
                'TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"',
                NO_ISSUE,
            ),
            (
                ("scrapy==2.12.0",),
                'TWISTED_REACTOR = "custom.reactor"',
                NO_ISSUE,
            ),
        )
    ),
    # SCP17 redundant setting value
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
                            "SCP14 unsupported requirement: flake8-scrapy only supports scrapy 2.0.1+",
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
    # scrapy_known_settings silences SCP27
    (
        [File("settings['FOO']", path="a.py")],
        NO_ISSUE,
        {"scrapy_known_settings": "FOO,BAR"},
    ),
    # and extends automatic suggestions.
    (
        [File("settings['FOOBAR']", path="a.py")],
        Issue(
            "SCP27 unknown setting: did you mean: FOO_BAR?",
            column=9,
            path="a.py",
        ),
        {"scrapy_known_settings": "FOO_BAR"},
    ),
)


@cases(CASES)
def test(
    input: File | list[File], expected: Issue | list[Issue] | None, flake8_options
):
    check_project(input, expected, flake8_options)
