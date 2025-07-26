from __future__ import annotations

import ast
from collections.abc import Sequence
from itertools import cycle
from typing import overload

from packaging.version import Version

from flake8_scrapy.finders.settings import TYPE_CHECKERS
from flake8_scrapy.settings import SettingType
from tests.helpers import check_project

from . import NO_ISSUE, Cases, File, Issue, cases, iter_issues
from .test_requirements import (
    SCRAPY_ANCIENT_VERSION,
    SCRAPY_FUTURE_VERSION,
    SCRAPY_HIGHEST_KNOWN,
    SCRAPY_LOWEST_SUPPORTED,
)


def test_type_checkers():
    for setting_type in SettingType:
        assert setting_type in TYPE_CHECKERS, (
            f"{setting_type} is missing from SETTING_TYPE_CHECKERS"
        )


FALSE_BOOLS = ("False", "'false'", "0")
TRUE_BOOLS = ("True", "'true'", "1")

# (template, setting column, value column - setting length)
SETTING_VALUE_CHECK_TEMPLATES = (
    ("settings['{setting}'] = {value}", 9, 15),
    ("BaseSettings({{'{setting}': {value}}})", 14, 18),
    ("settings.set(name='{setting}', value={value})", 18, 28),
    ("settings.setdefault('{setting}', {value}, 'addon')", 20, 24),
    ("settings.Settings(dict({setting}={value}))", 23, 24),
    ("crawler.settings.__setitem__('{setting}', {value})", 29, 33),
    (
        "scrapy.settings.overridden_settings(settings={{'{setting}': {value}}})",
        46,
        50,
    ),
)


class SafeDict(dict):
    """Allows to use str.format_map() with missing keys. e.g.
    SETTING_VALUE_CHECK_TEMPLATES can be used with a setting only, without a
    value."""

    def __missing__(self, key):
        return "{" + key + "}"


@overload
def zip_with_template(
    a: tuple[tuple[str], ...], b: tuple[tuple[str, str], ...]
) -> tuple[tuple[str, str, str], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...], b: tuple[tuple[str], ...]
) -> tuple[tuple[str, int, str], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...], b: tuple[tuple[str, str], ...]
) -> tuple[tuple[str, int, str, str], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...], b: tuple[tuple[str, str, str, int], ...]
) -> tuple[tuple[str, int, str, str, str, int], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...], b: tuple[tuple[str, str | None, str, str, int], ...]
) -> tuple[tuple[str, int, str, str | None, str, str, int], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str, Sequence[Issue] | Issue | None], ...],
) -> tuple[tuple[str, int, str, str, Sequence[Issue] | Issue | None], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str, Sequence[tuple[str, int]]], ...],
) -> tuple[tuple[str, int, str, str, Sequence[tuple[str, int]]], ...]: ...


def zip_with_template(a, b):
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
    # Python file checks
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
                    (
                        Issue(
                            "SCP27 unknown setting",
                            column=len(method_name) + 10,
                            path=path,
                        ),
                        *(
                            Issue("SCP40 unneeded setting get", column=8, path=path)
                            for _ in range(1)
                            if method_name == "get"
                        ),
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
                    (
                        Issue(
                            "SCP27 unknown setting",
                            column=13 + column_offset,
                            path=path,
                        ),
                        *(
                            Issue("SCP40 unneeded setting get", column=8, path=path)
                            for _ in range(1)
                            if not has_default
                        ),
                    ),
                )
                for params, column_offset, has_default in (
                    ("name='FOO'", 5, False),
                    ("'FOO', foo", 0, True),
                    ("'FOO', default=foo", 0, True),
                    ("name='FOO', default=foo", 5, True),
                    ("default=foo, name='FOO'", 18, True),
                    # and even if parameters do not match the expected function
                    # signature, since the similarities could suggest that it
                    # is still about a setting name.
                    ("'FOO', foo, bar", 0, True),
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
            (
                "Settings({foo: 'bar'})",
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
                'Settings({"DOWNLOAD_DELAY": 5.0, "BAR": "baz"})',
                Issue("SCP27 unknown setting", column=33, path=path),
            ),
            (
                "Settings(dict(DOWNLOAD_DELAY=5.0, BAR='baz'))",
                Issue("SCP27 unknown setting", column=34, path=path),
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
            # BaseSetting setter methods trigger setting value checks,
            *(
                (
                    f"settings.{method_name}('BOT_NAME', None)",
                    Issue(
                        "SCP36 invalid setting value",
                        column=len(method_name) + 22,
                        path=path,
                    ),
                )
                for method_name in (
                    "__setitem__",
                    "set",
                    "setdefault",
                )
            ),
            # regardless of parameter syntax used.
            *(
                (
                    f"settings.set({params})",
                    Issue(
                        "SCP36 invalid setting value",
                        column=13 + column_offset,
                        path=path,
                    ),
                )
                for params, column_offset in (
                    ("'BOT_NAME', value=None", 18),
                    ("name='BOT_NAME', value=None", 23),
                    ("value=None, name='BOT_NAME'", 6),
                )
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
                (
                    Issue(
                        "SCP32 wrong setting method: use getint()", column=9, path=path
                    ),
                    Issue("SCP40 unneeded setting get", column=8, path=path),
                ),
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
            # SCP32 wrong setting method: get() recommendation due to positional default
            (
                "settings.getint('DEFAULT_DROPITEM_LOG_LEVEL', 5)",
                Issue("SCP32 wrong setting method: use get()", column=9, path=path),
            ),
            # SCP32 wrong setting method: get() recommendation due to keyword default
            (
                "settings.getint('DEFAULT_DROPITEM_LOG_LEVEL', default=5)",
                Issue("SCP32 wrong setting method: use get()", column=9, path=path),
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
                    (
                        Issue(
                            "SCP35 no-op setting update",
                            column=column,
                            path=path,
                        ),
                        *iter_issues(issues),
                    ),
                )
                for template, column, setting, value, issues in zip_with_template(
                    (
                        *(
                            (template, setting_column)
                            for template, setting_column, _ in SETTING_VALUE_CHECK_TEMPLATES[
                                :13
                            ]
                        ),
                    ),
                    (
                        ("ADDONS", "{'my.addons.Addon': 100}", NO_ISSUE),
                        ("ASYNCIO_EVENT_LOOP", "'uvloop.Loop'", NO_ISSUE),
                        ("COMMANDS_MODULE", "'my_project.commands'", NO_ISSUE),
                        (
                            "DNS_RESOLVER",
                            "'scrapy.resolver.CachingHostnameResolver'",
                            NO_ISSUE,
                        ),
                        ("DNS_TIMEOUT", "120", NO_ISSUE),
                        ("DNSCACHE_ENABLED", "False", NO_ISSUE),
                        ("DNSCACHE_SIZE", "20_000", NO_ISSUE),
                        ("FORCE_CRAWLER_PROCESS", "True", NO_ISSUE),
                        ("REACTOR_THREADPOOL_MAXSIZE", "50", NO_ISSUE),
                        ("SPIDER_LOADER_CLASS", "CustomSpiderLoader", NO_ISSUE),
                        ("SPIDER_LOADER_WARN_ONLY", "True", NO_ISSUE),
                        ("SPIDER_MODULES", "['my_project.spiders_module']", NO_ISSUE),
                        (
                            "TWISTED_REACTOR",
                            "'twisted.internet.pollreactor.PollReactor'",
                            NO_ISSUE,
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
                for template, column, setting, value in zip_with_template(
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
                for template, column, setting in zip_with_template(
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
            # SCP40 unneeded setting get
            *(
                (
                    code,
                    Issue("SCP40 unneeded setting get", column=8, path=path),
                )
                for code in (
                    "settings.get('DOWNLOADER')",
                    "settings.get('DOWNLOADER', None)",
                    "settings.get('DOWNLOADER', default=None)",
                    "settings.get(name='DOWNLOADER', default=None)",
                )
            ),
            *(
                (code, NO_ISSUE)
                for code in (
                    "settings['DOWNLOADER']",
                    "settings.get('DOWNLOADER', foo)",
                )
            ),
            # Setting value checks
            *(
                (
                    template.format_map(SafeDict(setting=setting, value=value)),
                    NO_ISSUE,
                )
                for template, setting, value in zip_with_template(
                    (
                        *(
                            (template,)
                            for template, _, _ in SETTING_VALUE_CHECK_TEMPLATES
                        ),
                    ),
                    (
                        # SCP36 invalid setting value (valid values)
                        ("AWS_ACCESS_KEY_ID", "foo"),
                        ("AWS_ACCESS_KEY_ID", "foo()"),
                        ("AWS_ACCESS_KEY_ID", '"AKIAIOSFODNN7EXAMPLE"'),
                        ("AWS_ACCESS_KEY_ID", "None"),
                        ("BOT_NAME", "foo"),
                        ("BOT_NAME", "foo()"),
                        ("BOT_NAME", '"mybot"'),
                        ("BOT_NAME", '"mybot"'),
                        ("CONCURRENT_REQUESTS", "foo"),
                        ("CONCURRENT_REQUESTS", "foo()"),
                        ("CONCURRENT_REQUESTS", '"1"'),
                        ("CONCURRENT_REQUESTS", 'b"1"'),
                        ("CONCURRENT_REQUESTS", "1.0"),
                        ("CONCURRENT_REQUESTS", "1"),
                        ("CONCURRENT_REQUESTS", "True"),
                        ("DEFAULT_ITEM_CLASS", "foo"),
                        ("DEFAULT_ITEM_CLASS", "foo()"),
                        ("DEFAULT_ITEM_CLASS", "MyItem"),
                        ("DEFAULT_REQUEST_HEADERS", "foo"),
                        ("DEFAULT_REQUEST_HEADERS", "foo()"),
                        ("DEFAULT_REQUEST_HEADERS", "None"),
                        ("DEFAULT_REQUEST_HEADERS", "{}"),
                        ("DEFAULT_REQUEST_HEADERS", "'{}'"),
                        ("DEFAULT_REQUEST_HEADERS", "{a: b}"),
                        ("DEFAULT_REQUEST_HEADERS", "[(a, b)]"),
                        ("DEFAULT_REQUEST_HEADERS", '\'[["a", "b"]]\''),
                        ("DEFAULT_REQUEST_HEADERS", "{'Foo': 'Bar'}"),
                        (
                            "DEFAULT_REQUEST_HEADERS",
                            "{1: 'keys do not have to be str'}",
                        ),
                        ("DOWNLOAD_HANDLERS", "foo"),
                        ("DOWNLOAD_HANDLERS", "foo()"),
                        ("DOWNLOAD_HANDLERS", "None"),
                        ("DOWNLOAD_HANDLERS", "{}"),
                        ("DOWNLOAD_HANDLERS", "'{}'"),
                        ("DOWNLOAD_HANDLERS", "{a: b}"),
                        ("DOWNLOAD_HANDLERS", "{'http': None}"),
                        ("DOWNLOAD_HANDLERS", "{'websocket': WebSocketHandler}"),
                        ("DOWNLOAD_HANDLERS", "dict(http=None)"),
                        ("DOWNLOAD_HANDLERS", "dict(websocket=WebSocketHandler)"),
                        ("DOWNLOAD_SLOTS", "foo"),
                        ("DOWNLOAD_SLOTS", "foo()"),
                        ("DOWNLOAD_SLOTS", '"{}"'),
                        ("DOWNLOAD_SLOTS", "{a: b}"),
                        ("DOWNLOAD_SLOTS", "{a: {b: c}}"),
                        ("DOWNLOAD_SLOTS", '{"toscrape.com": {"concurrency": 1}}'),
                        ("DOWNLOAD_SLOTS", '{"toscrape.com": {"delay": 0.0}}'),
                        (
                            "DOWNLOAD_SLOTS",
                            '{"toscrape.com": {"randomize_delay": True}}',
                        ),
                        ("DOWNLOAD_SLOTS", '{"toscrape.com": {}}'),
                        ("DOWNLOAD_SLOTS", '\'{"toscrape.com": {"concurrency": 1}}\''),
                        ("DOWNLOAD_SLOTS", "{}"),
                        ("DOWNLOAD_SLOTS", "[]"),
                        ("DOWNLOAD_SLOTS", '"[]"'),
                        ("DOWNLOAD_SLOTS", "None"),
                        ("DOWNLOADER_CLIENT_TLS_METHOD", "foo"),
                        ("DOWNLOADER_CLIENT_TLS_METHOD", "foo()"),
                        ("DOWNLOADER_CLIENT_TLS_METHOD", '"TLS"'),
                        ("DOWNLOADER_CLIENT_TLS_METHOD", '"TLSv1.2"'),
                        ("DOWNLOADER_MIDDLEWARES", "foo"),
                        ("DOWNLOADER_MIDDLEWARES", "foo()"),
                        ("DOWNLOADER_MIDDLEWARES", "{}"),
                        ("DOWNLOADER_MIDDLEWARES", "'{}'"),
                        ("DOWNLOADER_MIDDLEWARES", "{a: b}"),
                        ("DOWNLOADER_MIDDLEWARES", "{Foo: 100}"),
                        ("DOWNLOADER_MIDDLEWARES", "{'foo.Foo': 100}"),
                        ("FEED_EXPORT_FIELDS", "foo"),
                        ("FEED_EXPORT_FIELDS", "foo()"),
                        ("FEED_EXPORT_FIELDS", '"foo"'),
                        ("FEED_EXPORT_FIELDS", "()"),
                        ("FEED_EXPORT_FIELDS", "[]"),
                        ("FEED_EXPORT_FIELDS", "{}"),
                        ("FEED_EXPORT_FIELDS", "None"),
                        ("FEED_EXPORT_INDENT", '"2"'),
                        ("FEED_EXPORT_INDENT", "0"),
                        ("FEED_EXPORT_INDENT", "1"),
                        ("FEED_EXPORT_INDENT", "None"),
                        ("FEED_EXPORT_INDENT", "True"),
                        ("FEED_URI", "foo"),
                        ("FEED_URI", "foo()"),
                        ("FEED_URI", "Path(foo)"),
                        ("FEED_URI", "Path(foo())"),
                        ("FEED_URI", "Path()"),  # Bad, but not Scrapy-specific
                        ("FEED_URI", "Path(1)"),  # Bad, but not Scrapy-specific
                        ("FEED_URI_PARAMS", "foo"),
                        ("FEED_URI_PARAMS", "foo()"),
                        ("FEED_URI_PARAMS", '"myproject.utils.get_uri_params"'),
                        ("FEED_URI_PARAMS", "None"),
                        ("FEED_URI_PARAMS", "uri_params"),
                        ("FEED_URI_PARAMS", "my_project.feeds.uri_params"),
                        ("FEEDS", "foo"),
                        ("FEEDS", "foo()"),
                        ("FEEDS", '"{}"'),
                        ("FEEDS", "[]"),
                        ("FEEDS", '"[]"'),
                        ("FEEDS", "None"),
                        (
                            "FEEDS",
                            '{f: {"format": "csv", "fields": ["name", "price"], "encoding": "utf-8"}}',
                        ),
                        (
                            "FEEDS",
                            '{f: {"format": "json", "batch_item_count": 0, "indent": 0, "fields": None}}',
                        ),
                        ("FEEDS", '{f: {"format": "json"}}'),
                        (
                            "FEEDS",
                            '{f:{"item_classes":[ProductItem],"item_filter":MyFilter,"uri_params":get_uri_params,}}',
                        ),
                        (
                            "FEEDS",
                            '{f: {"format": "xml", "batch_item_count": 100, "encoding": None, "fields": {"name": "product_name", "price": "product_price"}, "item_classes": ["myproject.items.ProductItem"], "item_filter": "myproject.filters.MyFilter", "indent": 2, "item_export_kwargs": {"root_element": "products"}, "overwrite": True, "store_empty": False, "uri_params": "myproject.utils.get_uri_params"}}',
                        ),
                        ("FEEDS", '\'{"output.json": {"format": "json"}}\''),
                        ("FEEDS", "{}"),
                        ("FEEDS", "{a: b}"),
                        ("FEEDS", "{a: {b: c}}"),
                        ("JOBDIR", "foo"),
                        ("JOBDIR", "foo()"),
                        ("JOBDIR", '"/tmp/foo"'),
                        ("JOBDIR", 'Path("/tmp/foo")'),
                        ("JOBDIR", "None"),
                        ("LOG_LEVEL", "foo"),
                        ("LOG_LEVEL", "foo()"),
                        ("LOG_LEVEL", '"debug"'),
                        ("LOG_LEVEL", '"INFO"'),
                        ("LOG_LEVEL", "0"),
                        ("LOG_LEVEL", "20"),
                        ("LOG_LEVEL", "25"),
                        ("LOG_VERSIONS", "foo"),
                        ("LOG_VERSIONS", "foo()"),
                        ("LOG_VERSIONS", '"foo,bar"'),
                        ("LOG_VERSIONS", '"foo"'),
                        ("LOG_VERSIONS", '["foo", "bar"]'),
                        ("LOG_VERSIONS", '["foo"]'),
                        ("LOG_VERSIONS", "b''"),
                        ("LOG_VERSIONS", "()"),
                        ("LOG_VERSIONS", "[]"),
                        ("LOG_VERSIONS", "{}"),
                        ("LOG_VERSIONS", "range(2)"),
                        ("LOG_VERSIONS", "set()"),
                        ("LOG_VERSIONS", "None"),
                        ("LOGSTATS_INTERVAL", "foo"),
                        ("LOGSTATS_INTERVAL", "foo()"),
                        ("LOGSTATS_INTERVAL", '"1.0"'),
                        ("LOGSTATS_INTERVAL", 'b"1.0"'),
                        ("LOGSTATS_INTERVAL", "1.0"),
                        ("LOGSTATS_INTERVAL", "1"),
                        ("LOGSTATS_INTERVAL", "True"),
                        ("PERIODIC_LOG_DELTA", "foo"),
                        ("PERIODIC_LOG_DELTA", "foo()"),
                        ("PERIODIC_LOG_DELTA", "None"),
                        ("PERIODIC_LOG_DELTA", "True"),
                        ("PERIODIC_LOG_DELTA", "{}"),
                        ("PERIODIC_LOG_DELTA", "{a: [b, c]}"),
                        ("PERIODIC_LOG_DELTA", '{"exclude": foo}'),
                        (
                            "PERIODIC_LOG_DELTA",
                            '{"exclude": ["downloader/response_count"]}',
                        ),
                        ("PERIODIC_LOG_DELTA", '{"exclude": []}'),
                        (
                            "PERIODIC_LOG_DELTA",
                            '{"include": ["stats"], "exclude": ["other"]}',
                        ),
                        ("PERIODIC_LOG_DELTA", '{"include": ["stats"]}'),
                        ("PERIODIC_LOG_DELTA", '{"include": []}'),
                        ("SCHEDULER", "foo"),
                        ("SCHEDULER", "foo()"),
                        ("SCHEDULER", "CustomScheduler"),
                        ("SCHEDULER", "my_project.schedulers.CustomScheduler"),
                        ("SPIDER_CONTRACTS", "foo"),
                        ("SPIDER_CONTRACTS", "foo()"),
                        ("SPIDER_CONTRACTS", '"{}"'),
                        ("SPIDER_CONTRACTS", "{}"),
                        ("SPIDER_CONTRACTS", "None"),
                        # Unknown setting type
                        ("SERVICE_ROOT", "foo"),
                        ("SERVICE_ROOT", "foo()"),
                        # SCP37 unpicklable setting value (valid values)
                        ("LOG_VERSIONS", "list((k for k in deps))"),
                        # SCP39 no contact info (valid values)
                        *(
                            ("USER_AGENT", value)
                            for value in (
                                "foo",
                                "foo()",
                                '"https://jane.doe.example"',
                                '"Jane Doe (https://jane.doe.example)"',
                                '"Jane Doe (+https://jane.doe.example)"',
                                '"jane.doe@example.com"',
                                '"Jane Doe (jane.doe@example.com)"',
                                '"Jane Doe (+mailto:jane.doe@example.com)"',
                                '"+1 555-9292"',
                                '"Jane Doe (+1 (555) 92.92))"',
                                '"Jane Doe (+tel:+15559292"',
                            )
                        ),
                        # SCP42 unneeded path string (valid values)
                        #
                        # FEED_URI supports Path since Scrapy 2.0.0+.
                        ("FEED_URI", 'Path("output.jsonl")'),
                        # URI params require a string, though:
                        # https://github.com/scrapy/scrapy/issues/6425
                        ("FEED_URI", '"output-%(time)s.jsonl"'),
                        ("FEED_URI", '"file:///home/user/output-%(time)s.jsonl"'),
                        # The value of LOG_FILE is directly passed to the
                        # Python API, and should support Path objects on Python
                        # 3.6+.
                        ("LOG_FILE", 'Path("scrapy.log")'),
                        # FEED_URI and LOG_FILE can be None
                        ("FEED_URI", "None"),
                        ("LOG_FILE", "None"),
                    ),
                )
            ),
            *(
                (
                    template.format_map(SafeDict(setting=setting, value=value)),
                    Issue(
                        issue,
                        column=template_column + len(setting) + value_offset,
                        path=path,
                    ),
                )
                for template, template_column, issue, setting, value, value_offset in zip_with_template(
                    (
                        *(
                            (template, value_column)
                            for template, _, value_column in SETTING_VALUE_CHECK_TEMPLATES
                        ),
                    ),
                    (
                        *(
                            ("SCP36 invalid setting value", setting, value, 0)
                            for setting, value in (
                                ("AUTOTHROTTLE_ENABLED", "'foo'"),
                                ("AUTOTHROTTLE_ENABLED", "{}"),
                                ("AWS_ACCESS_KEY_ID", "[]"),
                                ("BOT_NAME", "None"),
                                ("BOT_NAME", "[]"),
                                ("CONCURRENT_REQUESTS", "None"),
                                ("CONCURRENT_REQUESTS", "{}"),
                                ("DEFAULT_ITEM_CLASS", "None"),
                                ("DEFAULT_ITEM_CLASS", "[]"),
                                ("DEFAULT_ITEM_CLASS", '""'),
                                ("DEFAULT_ITEM_CLASS", '"mymodule"'),
                                ("DOWNLOADER_CLIENT_TLS_METHOD", "'TLSv1.3'"),
                                ("DOWNLOADER_CLIENT_TLS_METHOD", "None"),
                                ("DOWNLOADER_CLIENT_TLS_METHOD", "{}"),
                                ("FEED_EXPORT_FIELDS", "0"),
                                ("FEED_EXPORT_INDENT", '"not_int"'),
                                ("FEED_URI", "{}"),
                                ("FEED_URI_PARAMS", '"invalid"'),
                                ("FEED_URI_PARAMS", "123"),
                                ("FEED_URI_PARAMS", "[]"),
                                ("JOBDIR", "1"),
                                ("JOBDIR", "[]"),
                                ("LOG_LEVEL", "'FOO'"),
                                ("LOG_LEVEL", "None"),
                                ("LOG_LEVEL", "{}"),
                                ("LOG_VERSIONS", "b'foo,bar'"),
                                ("LOGSTATS_INTERVAL", "None"),
                                ("LOGSTATS_INTERVAL", "{}"),
                                ("SCHEDULER", "123"),
                            )
                        ),
                        *(
                            ("SCP36 invalid setting value", setting, value, column)
                            for setting, value, column in (
                                ("FEEDS", "{1: {}}", 1),
                                ("FEEDS", "{None: {}}", 1),
                            )
                        ),
                        *(
                            (
                                f"SCP36 invalid setting value: {detail}",
                                setting,
                                value,
                                column,
                            )
                            for setting, value, column, detail in (
                                (
                                    "DEFAULT_REQUEST_HEADERS",
                                    "'invalid json'",
                                    0,
                                    "invalid JSON: Expecting value: line 1 column 1 (char 0)",
                                ),
                                (
                                    "DEFAULT_REQUEST_HEADERS",
                                    "'[\"non-dict-compatible list\"]'",
                                    0,
                                    "invalid JSON: must be a dict, not list (['non-dict-compatible list'])",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    "42",
                                    0,
                                    "must be a dict, not int",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    "'invalid json'",
                                    0,
                                    "invalid JSON: Expecting value: line 1 column 1 (char 0)",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    "'[]'",
                                    0,
                                    "invalid JSON: must be a dict, not list ([])",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    "{1: foo}",
                                    1,
                                    "keys must be strings, not int (1)",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    '{"a": "not an import path"}',
                                    6,
                                    "'not an import path' does not look like an import path",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    '{"a": 1}',
                                    6,
                                    "values must be Python objects or their import paths as strings, not int (1)",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    "dict(a=1)",
                                    7,
                                    "values must be Python objects or their import paths as strings, not int (1)",
                                ),
                                (
                                    "DOWNLOAD_HANDLERS",
                                    'dict(a="not an import path")',
                                    7,
                                    "'not an import path' does not look like an import path",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '"not_a_dict"',
                                    0,
                                    "invalid JSON: Expecting value: line 1 column 1 (char 0)",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    "{1: {}}",
                                    1,
                                    (
                                        "DOWNLOAD_SLOTS keys must be download "
                                        "slot IDs as strings"
                                    ),
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": []}',
                                    17,
                                    (
                                        "DOWNLOAD_SLOTS values must be "
                                        "dicts of download slot parameters"
                                    ),
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": {"foo": "bar"}}',
                                    18,
                                    "unknown download slot parameter",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": {"concurrency": -1}}',
                                    33,
                                    "concurrency must be >= 1",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": {"concurrency": 0}}',
                                    33,
                                    "concurrency must be >= 1",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": {"concurrency": 1.5}}',
                                    33,
                                    "concurrency must be an integer",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": {"delay": -1}}',
                                    27,
                                    "delay must be >= 0",
                                ),
                                (
                                    "DOWNLOAD_SLOTS",
                                    '{"toscrape.com": {"randomize_delay": 1}}',
                                    37,
                                    "randomize_delay must be a boolean",
                                ),
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    "1",
                                    0,
                                    "must be a dict, not int",
                                ),
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    "{1: 100}",
                                    1,
                                    "keys must be strings, not int (1)",
                                ),
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    "'{1: 100}'",
                                    0,
                                    "invalid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
                                ),
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    "{'module': 100}",
                                    1,
                                    "'module' does not look like an import path",
                                ),
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    "{Foo: []}",
                                    6,
                                    "dict values must be integers or None",
                                ),
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    "{Foo: 'bar'}",
                                    6,
                                    "dict values must be integers or None, not str ('bar')",
                                ),
                                (
                                    "FEEDS",
                                    '"not_a_dict"',
                                    0,
                                    "invalid JSON: Expecting value: line 1 column 1 (char 0)",
                                ),
                                *(
                                    (
                                        "FEEDS",
                                        value,
                                        4,
                                        "FEEDS dict values must be dicts of "
                                        "feed configurations",
                                    )
                                    for value in (
                                        '{f: "not_a_dict"}',
                                        "{f: 123}",
                                        "{f: []}",
                                        '{f: "[]"}',
                                    )
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"foo": "bar"}}',
                                    5,
                                    "unknown feed config key",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"format": 123}}',
                                    15,
                                    "'format' must be a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"format": {}}}',
                                    15,
                                    "'format' must be a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"batch_item_count": -1}}',
                                    25,
                                    "'batch_item_count' must be >= 0",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"batch_item_count": "not_int"}}',
                                    25,
                                    "'batch_item_count' must be an integer",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"batch_item_count": {}}}',
                                    25,
                                    "'batch_item_count' must be an integer",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"encoding": 123}}',
                                    17,
                                    "'encoding' must be a string or None",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"encoding": {}}}',
                                    17,
                                    "'encoding' must be a string or None",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"fields": ""}}',
                                    15,
                                    "'fields' must be a list or a dict",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"fields": [123]}}',
                                    16,
                                    "fields[0] (123) must be a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"fields": {1: ["foo", "bar"]}}}',
                                    16,
                                    "'fields' keys must be strings, not int (1)",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"fields": {"key": 123}}}',
                                    23,
                                    "fields['key'] (123) must be a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_classes": "not_list"}}',
                                    21,
                                    "'item_classes' must be a list",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_classes": [[]]}}',
                                    22,
                                    "item_classes[0] is neither a Python object of the expected type nor its import path as a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_classes": [1]}}',
                                    22,
                                    "item_classes[0] (1) is neither a Python object of the expected type nor its import path as a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_classes": ["foo"]}}',
                                    22,
                                    "item_classes[0] ('foo') does not look like a valid import path",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_filter": "foo"}}',
                                    20,
                                    "'item_filter' ('foo') does not look like a valid import path",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"indent": -1}}',
                                    15,
                                    "'indent' must be >= 0",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"indent": "not_int"}}',
                                    15,
                                    "'indent' must be an integer",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_export_kwargs": "not_dict"}}',
                                    27,
                                    "'item_export_kwargs' must be a dict",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"item_export_kwargs": {1: "key is invalid"}}}',
                                    27,
                                    "'item_export_kwargs' keys must be strings, not int (1)",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"overwrite": "not_bool"}}',
                                    18,
                                    "'overwrite' must be a boolean",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"overwrite": {}}}',
                                    18,
                                    "'overwrite' must be a boolean",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"store_empty": "not_bool"}}',
                                    20,
                                    "'store_empty' must be a boolean",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"uri_params": "foo"}}',
                                    19,
                                    "'uri_params' ('foo') does not look like "
                                    "a valid import path",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"uri_params": {}}}',
                                    19,
                                    "'uri_params' must be a Python object or "
                                    "its import path as a string",
                                ),
                                (
                                    "FEEDS",
                                    '{f: {"postprocessing": ["foo"]}}',
                                    24,
                                    "postprocessing[0] ('foo') does not look "
                                    "like a valid import path",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    "False",
                                    0,
                                    "must be True or a dict",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    '"foo"',
                                    0,
                                    "must be True or a dict",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    "[]",
                                    0,
                                    "must be True or a dict",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    "{1: []}",
                                    1,
                                    "keys must be 'include' or 'exclude', not int (1)",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    '{"foo": []}',
                                    1,
                                    "keys must be 'include' or 'exclude', not 'foo'",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    '{"include": "not_a_list"}',
                                    12,
                                    "dict values must be lists of stat name substrings",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    '{"include": [123]}',
                                    13,
                                    "include/exclude list items must be strings",
                                ),
                                (
                                    "PERIODIC_LOG_DELTA",
                                    '{"include": [{}]}',
                                    13,
                                    "include/exclude list items must be strings",
                                ),
                            )
                        ),
                        *(
                            ("SCP37 unpicklable setting value", setting, value, 0)
                            for setting, value in (
                                ("FEED_URI_PARAMS", "lambda params, spider: {}"),
                                ("LOG_VERSIONS", "(k for k in deps)"),
                            )
                        ),
                        *(
                            ("SCP37 unpicklable setting value", setting, value, column)
                            for setting, value, column in (
                                (
                                    "FEEDS",
                                    '{f:{"item_classes": (cls for cls in item_classes)}}',
                                    20,
                                ),
                            )
                        ),
                        # SCP39 no contact info
                        *(
                            ("SCP39 no contact info", "USER_AGENT", value, 0)
                            for value in (
                                "None",
                                "''",
                                "'foo'",
                                "'my_project (+http://www.yourdomain.com)'",
                                "'Scrapy/2.11.2 (+https://scrapy.org)'",
                                "'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'",
                                "'Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0'",
                            )
                        ),
                        *(
                            ("SCP36 invalid setting value", "USER_AGENT", value, 0)
                            for value in ("5559292",)
                        ),
                        # SCP42 unneeded path string
                        ("SCP42 unneeded path string", "FEED_URI", "'output.jsonl'", 0),
                        (
                            "SCP42 unneeded path string",
                            "FEED_URI",
                            "'file:///home/user/output.jsonl'",
                            0,
                        ),
                        ("SCP42 unneeded path string", "LOG_FILE", "'scrapy.log'", 0),
                    ),
                )
            ),
            *(
                (
                    template.format_map(SafeDict(setting=setting, value=value)),
                    (
                        *(
                            Issue(
                                msg,
                                column=template_column + len(setting) + col,
                                path=path,
                            )
                            for msg, col in value_issues
                        ),
                    ),
                )
                for template, template_column, setting, value, value_issues in zip_with_template(
                    (
                        *(
                            (template, value_column)
                            for template, _, value_column in SETTING_VALUE_CHECK_TEMPLATES
                        ),
                    ),
                    (
                        (
                            "DOWNLOAD_SLOTS",
                            "lambda: foo",
                            (
                                ("SCP36 invalid setting value: must be a dict", 0),
                                ("SCP37 unpicklable setting value", 0),
                            ),
                        ),
                        (
                            "FEEDS",
                            (
                                '{"item_classes": [ProductItem], '
                                '"item_filter": MyFilter, '
                                '"uri_params": get_uri_params}'
                            ),
                            (
                                (
                                    (
                                        "SCP36 invalid setting value: FEEDS "
                                        "dict values must be dicts of feed "
                                        "configurations"
                                    ),
                                    17,
                                ),
                                ("SCP42 unneeded path string", 1),
                                ("SCP42 unneeded path string", 32),
                                ("SCP42 unneeded path string", 57),
                            ),
                        ),
                        (
                            "FEEDS",
                            '{f: {"fields": {1: 2}}}',
                            (
                                (
                                    "SCP36 invalid setting value: 'fields' "
                                    "keys must be strings, not int (1)",
                                    16,
                                ),
                                (
                                    "SCP36 invalid setting value: 'fields' "
                                    "dict values must be strings, not int (2)",
                                    19,
                                ),
                            ),
                        ),
                    ),
                )
            ),
        )
    ),
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
                File(code, path=path),
            ],
            (
                *default_issues(path),
                *iter_issues(issues),
            ),
            {},
        )
        for path in ["a.py"]
        for code, issues in (
            # Baseline
            ("BOT_NAME = 'a'", NO_ISSUE),
            # Non-setting-module specific checks for Python files also apply
            (
                "settings['FOO']",
                Issue("SCP27 unknown setting", column=9, path=path),
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
                        Issue(
                            "SCP17 redundant setting value",
                            line=1,
                            column=len(name) + 3,
                            path=path,
                        ),
                        *iter_issues(issues),
                    ),
                )
                for name, value, issues in (
                    *(
                        (
                            "DOWNLOAD_DELAY",
                            value,
                            Issue("SCP38 low project throttling", column=17, path=path),
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
            # Setting value checks for pre-crawler settings
            (
                "ADDONS = '{}'",
                Issue("SCP17 redundant setting value", column=9, path=path),
            ),
            (
                "ADDONS = {}",
                Issue("SCP17 redundant setting value", column=9, path=path),
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
                    Issue(
                        f"SCP36 invalid setting value: {detail}",
                        column=9 + offset,
                        path=path,
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
            (
                *default_issues(path, exclude=exclude),
                *iter_issues(issues),
            ),
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
            *((f"ROBOTSTXT_OBEY = {value}", 9, ()) for value in TRUE_BOOLS),
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
            ("ROBOTSTXT_OBEY = foo", 9, ()),
            (
                "ROBOTSTXT_OBEY = 'foo'",
                9,
                (Issue("SCP36 invalid setting value", column=17, path=path),),
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
                        Issue(
                            "SCP10 incomplete project throttling", column=0, path=path
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
                    Issue("SCP10 incomplete project throttling", path=path),
                )
                for value in TRUE_BOOLS
            ),
            (
                "AUTOTHROTTLE_ENABLED = foo",
                10,
                Issue("SCP10 incomplete project throttling", path=path),
            ),
            (
                "AUTOTHROTTLE_ENABLED = 'foo'",
                10,
                (
                    Issue("SCP10 incomplete project throttling", path=path),
                    Issue("SCP36 invalid setting value", column=23, path=path),
                ),
            ),
            *(
                (
                    f"AUTOTHROTTLE_ENABLED = {value}",
                    10,
                    (
                        Issue("SCP10 incomplete project throttling", path=path),
                        Issue("SCP17 redundant setting value", column=23, path=path),
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
                    Issue("SCP38 low project throttling", column=33, path=path),
                    Issue("SCP38 low project throttling", line=2, column=17, path=path),
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
                    Issue("SCP36 invalid setting value", column=33, path=path),
                    Issue("SCP36 invalid setting value", line=2, column=17, path=path),
                ),
            ),
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
    # Checks bassed on requirements and setting values
    *(
        (
            (
                File("", path="scrapy.cfg"),
                File(requirements, path="requirements.txt"),
                File(f"settings[{name!r}] = {value}", path=path),
            ),
            (
                Issue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
                *iter_issues(issues),
            ),
            {},
        )
        for path in ("a.py",)
        for requirements, name, value, issues in (
            # SCP36 invalid setting value: FEEDS keys
            *(
                (
                    f"scrapy=={version}",
                    "FEEDS",
                    value,
                    (
                        Issue(
                            "SCP15 insecure requirement: scrapy 2.11.2 implements "
                            "security fixes",
                            path="requirements.txt",
                        ),
                        *(
                            Issue(
                                f"SCP29 setting needs upgrade: {key!r} "
                                f"requires Scrapy {versions[1]}+",
                                column=25,
                                path=path,
                            )
                            for _ in range(1)
                            if has_issue
                        ),
                    ),
                )
                for key, versions, value in (
                    (
                        "batch_item_count",
                        ("2.2.0", "2.3.0"),
                        '{f: {"batch_item_count": 100}}',
                    ),
                    (
                        "item_export_kwargs",
                        ("2.3.0", "2.4.0"),
                        '{f: {"item_export_kwargs": {}}}',
                    ),
                    ("overwrite", ("2.3.0", "2.4.0"), '{f: {"overwrite": False}}'),
                    (
                        "item_classes",
                        ("2.5.0", "2.6.0"),
                        '{f: {"item_classes": [MyItem]}}',
                    ),
                    (
                        "item_filter",
                        ("2.5.0", "2.6.0"),
                        '{f: {"item_filter": MyFilter}}',
                    ),
                    (
                        "postprocessing",
                        ("2.5.0", "2.6.0"),
                        '{f: {"postprocessing": []}}',
                    ),
                )
                for version, has_issue in zip(versions, (True, False))
            ),
        )
    ),
    *(
        (
            [
                File("", path="scrapy.cfg"),
                File(requirements, path="requirements.txt"),
                File(code, path=path),
            ],
            (
                Issue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
                Issue(
                    "SCP15 insecure requirement: scrapy 2.11.2 implements security fixes",
                    path="requirements.txt",
                ),
                *iter_issues(issues),
            ),
            {},
        )
        for path in ["a.py"]
        for requirements, code, issues in (
            *(
                (
                    requirements,
                    template.format_map(SafeDict(setting=setting, value=value)),
                    Issue(
                        issue,
                        column=template_column + len(setting) + value_offset,
                        path=path,
                    )
                    if issue
                    else NO_ISSUE,
                )
                for template, template_column, requirements, issue, setting, value, value_offset in zip_with_template(
                    (
                        *(
                            (template, value_column)
                            for template, _, value_column in SETTING_VALUE_CHECK_TEMPLATES
                        ),
                    ),
                    (
                        # SCP41 unneeded import path
                        *(
                            (requirements, NO_ISSUE, settings, value, 0)
                            for requirements in ("scrapy==2.3.0", "scrapy==2.4.0")
                            for settings, value in (
                                # Object
                                ("DEFAULT_ITEM_CLASS", "MyItem"),
                                # Optional object
                                ("FEED_URI_PARAMS", "feed_uri_params"),
                                # Based object dict
                                (
                                    "FEED_EXPORTERS",
                                    '{"json": None, "csv": MyCSVExporter}',
                                ),
                                (
                                    "FEED_EXPORTERS",
                                    "dict(json=None, csv=MyCSVExporter)",
                                ),
                                # Based component priority dict
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    '{Foo: 0, Bar: 1000, "scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware": None}',
                                ),
                                # Special settings.
                                (
                                    "FEEDS",
                                    '{foo: {"uri_params": None}}',
                                ),
                                (
                                    "FEEDS",
                                    '{foo: {"uri_params": uri_params}}',
                                ),
                            )
                        ),
                        *(
                            (requirements, issues, settings, value, value_offset)
                            for requirements, issues in (
                                ("scrapy==2.3.0", NO_ISSUE),
                                ("scrapy==2.4.0", "SCP41 unneeded import path"),
                            )
                            for settings, value, value_offset in (
                                # Callable.
                                ("DEFAULT_ITEM_CLASS", "'my_project.items.MyItem'", 0),
                                # Optional callable.
                                ("FEED_URI_PARAMS", "'custom.feed_uri_params'", 0),
                                # Based object dict
                                ("FEED_EXPORTERS", '{"csv": "custom.CSVExporter"}', 8),
                                ("FEED_EXPORTERS", 'dict(csv="custom.CSVExporter")', 9),
                                # Based component priority dict
                                (
                                    "DOWNLOADER_MIDDLEWARES",
                                    '{"custom.Middleware": 42}',
                                    1,
                                ),
                                # Special settings.
                                (
                                    "FEEDS",
                                    '{foo: {"uri_params": "custom.uri_params"}}',
                                    21,
                                ),
                            )
                        ),
                        *(
                            (requirements, issues, settings, value, value_offset)
                            for requirements, settings, value, value_offset, issues in (
                                # Special settings.
                                (
                                    "scrapy==2.6.0",
                                    "FEEDS",
                                    '{foo: {"item_classes": [MyItem]}}',
                                    0,
                                    NO_ISSUE,
                                ),
                                (
                                    "scrapy==2.6.0",
                                    "FEEDS",
                                    '{foo: {"item_filter": MyFilter}}',
                                    0,
                                    NO_ISSUE,
                                ),
                                (
                                    "scrapy==2.6.0",
                                    "FEEDS",
                                    '{foo: {"postprocessing": [MyPlugin]}}',
                                    0,
                                    NO_ISSUE,
                                ),
                                (
                                    "scrapy==2.6.0",
                                    "FEEDS",
                                    '{foo: {"item_classes": ["custom.Item"]}}',
                                    24,
                                    "SCP41 unneeded import path",
                                ),
                                (
                                    "scrapy==2.6.0",
                                    "FEEDS",
                                    '{foo: {"item_filter": "custom.Filter"}}',
                                    22,
                                    "SCP41 unneeded import path",
                                ),
                                (
                                    "scrapy==2.6.0",
                                    "FEEDS",
                                    '{foo: {"postprocessing": ["custom.Plugin"]}}',
                                    26,
                                    "SCP41 unneeded import path",
                                ),
                                # Unknown base key
                                (
                                    "scrapy==2.4.0",
                                    "DOWNLOADER_MIDDLEWARES",
                                    '{"custom.Middleware": 42}',
                                    1,
                                    "SCP41 unneeded import path",
                                ),
                            )
                        ),
                        # SCP42 unneeded path string
                        # SCP43 unsupported Path object
                        *(
                            (f"scrapy=={version}", issues, setting, value, 0)
                            for setting, old_version, new_version in (
                                ("HTTPCACHE_DIR", "2.7.1", "2.8.0"),
                                ("TEMPLATES_DIR", "2.7.1", "2.8.0"),
                                ("FEED_TEMPDIR", "2.7.1", "2.8.0"),
                                ("JOBDIR", "2.7.1", "2.8.0"),
                                ("FILES_STORE", "2.8.0", "2.9.0"),
                                ("IMAGES_STORE", "2.8.0", "2.9.0"),
                            )
                            for value, version, issues in (
                                ("'path'", old_version, NO_ISSUE),
                                (
                                    "Path('path')",
                                    old_version,
                                    f"SCP43 unsupported Path object: requires Scrapy {new_version}+",
                                ),
                                ("'path'", new_version, "SCP42 unneeded path string"),
                                ("Path('path')", new_version, NO_ISSUE),
                            )
                        ),
                        *(
                            (f"scrapy=={version}", issues, "FEEDS", value, 1)
                            for old_version, new_version in (("2.5.1", "2.6.0"),)
                            for value, version, issues in (
                                # No path support, no URI params
                                (
                                    "{'output.json': {'format': 'json'}}",
                                    old_version,
                                    NO_ISSUE,
                                ),
                                (
                                    "{'file:///home/user/output.json': {'format': 'json'}}",
                                    old_version,
                                    NO_ISSUE,
                                ),
                                (
                                    "{Path('output.json'): {'format': 'json'}}",
                                    old_version,
                                    "SCP43 unsupported Path object: requires Scrapy 2.6.0+",
                                ),
                                # Path support, no URI params
                                (
                                    "{'output.json': {'format': 'json'}}",
                                    new_version,
                                    "SCP42 unneeded path string",
                                ),
                                (
                                    "{'file:///home/user/output.json': {'format': 'json'}}",
                                    new_version,
                                    "SCP42 unneeded path string",
                                ),
                                (
                                    "{Path('output.json'): {'format': 'json'}}",
                                    new_version,
                                    NO_ISSUE,
                                ),
                                # No path support, URI params
                                (
                                    "{'output-%(time)s.json': {'format': 'json'}}",
                                    old_version,
                                    NO_ISSUE,
                                ),
                                (
                                    "{'file:///home/user/output-%(time)s.json': {'format': 'json'}}",
                                    old_version,
                                    NO_ISSUE,
                                ),
                                (
                                    "{Path('output-%(time)s.json'): {'format': 'json'}}",
                                    old_version,
                                    "SCP43 unsupported Path object: requires Scrapy 2.6.0+",
                                ),
                                # Path support, URI params
                                (
                                    "{'output-%(time)s.json': {'format': 'json'}}",
                                    new_version,
                                    NO_ISSUE,
                                ),
                                (
                                    "{'file:///home/user/output-%(time)s.json': {'format': 'json'}}",
                                    new_version,
                                    NO_ISSUE,
                                ),
                                (
                                    "{Path('output-%(time)s.json'): {'format': 'json'}}",
                                    new_version,
                                    "SCP43 unsupported Path object: has URI params",
                                ),
                            )
                        ),
                    ),
                )
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
                *default_issues(path),
                Issue("SCP13 incomplete requirements freeze", path="requirements.txt"),
                *iter_issues(issues),
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
                (
                    Issue(
                        "SCP17 redundant setting value",
                        column=18,
                        path=path,
                    ),
                    Issue(
                        "SCP41 unneeded import path",
                        column=18,
                        path=path,
                    ),
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
                Issue(
                    "SCP41 unneeded import path",
                    column=18,
                    path=path,
                ),
            ),
            (
                ("scrapy==2.12.0",),
                'TWISTED_REACTOR = "custom.reactor"',
                Issue(
                    "SCP41 unneeded import path",
                    column=18,
                    path=path,
                ),
            ),
            # SCP41 unneeded import path (non-based component priority dict)
            (
                ("scrapy==2.10.0",),
                "ADDONS = {ScrapyPoetAddon: 300}",
                (
                    Issue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                ),
            ),
            (
                ("scrapy==2.10.0",),
                'ADDONS = {"scrapy_poet.addons.Addon": 300}',
                (
                    Issue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                    Issue(
                        "SCP41 unneeded import path",
                        column=10,
                        path=path,
                    ),
                ),
            ),
            # SCP41 unneeded import path (base setting)
            (
                ("scrapy==2.4.0",),
                'EXTENSIONS_BASE = {"custom.Extension": 42}',
                (
                    Issue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    Issue("SCP33 base setting use", path=path),
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                ),
            ),
            # SCP41 unneeded import path: added base key
            (
                ("scrapy==2.11.2",),
                'SPIDER_CONTRACTS = {"scrapy.contracts.default.MetadataContract": None}',
                (
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                    Issue("SCP41 unneeded import path", column=20, path=path),
                ),
            ),
            (
                ("scrapy==2.12.0",),
                'SPIDER_CONTRACTS = {"scrapy.contracts.default.MetadataContract": None}',
                (
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                ),
            ),
            # SCP41 unneeded import path: removed base key
            (
                ("scrapy==2.11.1",),
                'SPIDER_MIDDLEWARES = {"scrapy.spidermiddlewares.offsite.OffsiteMiddleware": 10}',
                (
                    Issue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                ),
            ),
            (
                ("scrapy==2.11.2",),
                'SPIDER_MIDDLEWARES = {"scrapy.spidermiddlewares.offsite.OffsiteMiddleware": 10}',
                (
                    Issue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                    Issue("SCP41 unneeded import path", column=22, path=path),
                ),
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
