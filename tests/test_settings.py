from __future__ import annotations

from collections.abc import Sequence

from scrapy_lint.finders.settings.types import TYPE_CHECKERS
from scrapy_lint.settings import SettingType
from tests.helpers import check_project

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases, iter_issues
from .settings import SETTING_VALUE_CHECK_TEMPLATES, SafeDict, zip_with_template


def test_type_checkers():
    for setting_type in SettingType:
        assert setting_type in TYPE_CHECKERS, (
            f"{setting_type} is missing from SETTING_TYPE_CHECKERS"
        )


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
            (
                "settings['FOO']",
                ExpectedIssue("SCP27 unknown setting", column=9, path=path),
            ),
            (
                "self.settings['FOO']",
                ExpectedIssue("SCP27 unknown setting", column=14, path=path),
            ),
            (
                "crawler.settings['FOO']",
                ExpectedIssue("SCP27 unknown setting", column=17, path=path),
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
                ExpectedIssue("SCP27 unknown setting", column=9, path=path),
            ),
            # even if the value is not supported for setting value checks,
            (
                "settings['FOO'] = bar",
                ExpectedIssue("SCP27 unknown setting", column=9, path=path),
            ),
            # and even on attributes.
            (
                "self.settings['FOO'] = 'bar'",
                ExpectedIssue("SCP27 unknown setting", column=14, path=path),
            ),
            # BaseSetting methods that have a setting name as a parameter
            # trigger setting name checks,
            *(
                (
                    f"settings.{method_name}('FOO')",
                    (
                        ExpectedIssue(
                            "SCP27 unknown setting",
                            column=len(method_name) + 10,
                            path=path,
                        ),
                        *(
                            ExpectedIssue(
                                "SCP40 unneeded setting get",
                                column=9,
                                path=path,
                            )
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
                        ExpectedIssue(
                            "SCP27 unknown setting",
                            column=13 + column_offset,
                            path=path,
                        ),
                        *(
                            ExpectedIssue(
                                "SCP40 unneeded setting get",
                                column=9,
                                path=path,
                            )
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
                    f"{callable_}({{'FOO': 'bar'}})",
                    ExpectedIssue(
                        "SCP27 unknown setting",
                        column=len(callable_) + 2,
                        path=path,
                    ),
                )
                for callable_ in (
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
                    ExpectedIssue(
                        "SCP27 unknown setting",
                        column=9 + column_offset,
                        path=path,
                    ),
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
                ExpectedIssue("SCP27 unknown setting", column=14, path=path),
            ),
            (
                "Settings(foo(FOO='bar'))",
                NO_ISSUE,
            ),
            # and checking all keys in the dict.
            (
                'Settings({"DOWNLOAD_DELAY": 5.0, "BAR": "baz"})',
                ExpectedIssue("SCP27 unknown setting", column=33, path=path),
            ),
            (
                "Settings(dict(DOWNLOAD_DELAY=5.0, BAR='baz'))",
                ExpectedIssue("SCP27 unknown setting", column=34, path=path),
            ),
            # "`FOO" in settings` triggers setting name checks,
            (
                "'FOO' in settings",
                ExpectedIssue("SCP27 unknown setting", path=path),
            ),
            # also when not is involved,
            (
                "'FOO' not in settings",
                ExpectedIssue("SCP27 unknown setting", path=path),
            ),
            # even for attributes,
            (
                "'FOO' in self.settings",
                ExpectedIssue("SCP27 unknown setting", path=path),
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
                    ExpectedIssue(
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
                    ExpectedIssue(
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
                        ExpectedIssue("SCP27 unknown setting", column=9, path=path)
                        if issue is True
                        else ExpectedIssue(
                            f"SCP27 unknown setting: did you mean: {issue}?",
                            column=9,
                            path=path,
                        )
                        if isinstance(issue, str)
                        else ExpectedIssue(
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
                ExpectedIssue(
                    "SCP32 wrong setting method: use getbool()",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: keyword argument
            (
                "settings.get(name='RETRY_TIMES')",
                (
                    ExpectedIssue(
                        "SCP32 wrong setting method: use getint()",
                        column=9,
                        path=path,
                    ),
                    ExpectedIssue("SCP40 unneeded setting get", column=9, path=path),
                ),
            ),
            # SCP32 wrong setting method: subscript
            (
                "settings['DOWNLOAD_DELAY']",
                ExpectedIssue(
                    "SCP32 wrong setting method: use getfloat()",
                    column=8,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: subscript recommendation
            (
                "settings.getint('DEFAULT_DROPITEM_LOG_LEVEL')",
                ExpectedIssue(
                    "SCP32 wrong setting method: use []",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: get() recommendation due to positional default
            (
                "settings.getint('DEFAULT_DROPITEM_LOG_LEVEL', 5)",
                ExpectedIssue(
                    "SCP32 wrong setting method: use get()",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: get() recommendation due to keyword default
            (
                "settings.getint('DEFAULT_DROPITEM_LOG_LEVEL', default=5)",
                ExpectedIssue(
                    "SCP32 wrong setting method: use get()",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: list
            (
                "settings.add_to_list('LOG_SHORT_NAMES', 'foo')",
                ExpectedIssue("SCP32 wrong setting method", column=21, path=path),
            ),
            (
                "settings.add_to_list('LOG_VERSIONS', 'foo')",
                NO_ISSUE,
            ),
            # SCP32 wrong setting method: component priority dict
            (
                "settings.replace_in_component_priority_dict('DOWNLOAD_HANDLERS', Old, New)",
                ExpectedIssue("SCP32 wrong setting method", column=44, path=path),
            ),
            (
                "settings.replace_in_component_priority_dict('DOWNLOADER_MIDDLEWARES', Old, New)",
                NO_ISSUE,
            ),
            # SCP32 wrong setting method: component priority dict, based
            (
                "settings.getdict('DOWNLOADER_MIDDLEWARES')",
                ExpectedIssue(
                    "SCP32 wrong setting method: use getwithbase()",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: regular dict, based
            (
                "settings.getdict('DOWNLOAD_HANDLERS')",
                ExpectedIssue(
                    "SCP32 wrong setting method: use getwithbase()",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: component priority dict, not based
            (
                "settings.getwithbase('ADDONS')",
                ExpectedIssue(
                    "SCP32 wrong setting method: use getdict()",
                    column=9,
                    path=path,
                ),
            ),
            # SCP32 wrong setting method: regular dict, not based
            (
                "settings.getwithbase('DOWNLOAD_SLOTS')",
                ExpectedIssue(
                    "SCP32 wrong setting method: use getdict()",
                    column=9,
                    path=path,
                ),
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
            # SCP32 wrong setting method: ast.Attribute in load context
            (
                "foo = self.settings['LOG_ENABLED']",
                ExpectedIssue(
                    "SCP32 wrong setting method: use getbool()",
                    column=11,
                    path=path,
                ),
            ),
            # SCP33 base setting use
            (
                "settings['DOWNLOAD_HANDLERS_BASE']",
                ExpectedIssue("SCP33 base setting use", column=9, path=path),
            ),
            (
                "settings['FOO_BASE']",
                ExpectedIssue("SCP27 unknown setting", column=9, path=path),
            ),
            # SCP35 no-op setting update
            *(
                (
                    template.format_map(SafeDict(setting=setting, value=value)),
                    (
                        ExpectedIssue(
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
                    ExpectedIssue(
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
                    ExpectedIssue(
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
                    ),
                ),
                ExpectedIssue(
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
                    ),
                ),
                NO_ISSUE,
            ),
            # SCP40 unneeded setting get
            *(
                (
                    code,
                    ExpectedIssue("SCP40 unneeded setting get", column=9, path=path),
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
            # SCP46 raw Zyte API params
            (
                "settings['ZYTE_API_DEFAULT_PARAMS'] = {'foo': 'bar'}",
                ExpectedIssue("SCP46 raw Zyte API params", column=9, path=path),
            ),
        )
    ),
    # known-settings silences SCP27
    (
        [File("settings['FOO']", path="a.py")],
        NO_ISSUE,
        {"known-settings": ["FOO", "BAR"]},
    ),
    # and extends automatic suggestions.
    (
        [File("settings['FOOBAR']", path="a.py")],
        ExpectedIssue(
            "SCP27 unknown setting: did you mean: FOO_BAR?",
            column=9,
            path="a.py",
        ),
        {"known-settings": ["FOO_BAR"]},
    ),
    # SCP32 wrong setting method: do not trigger when not using getwithbase()
    # in update_settings()
    (
        (
            File(
                "\n".join(
                    (
                        "from scrapy import Spider",
                        "",
                        "class MySpider(Spider):",
                        "    name = 'my_spider'",
                        "",
                        "    @classmethod",
                        "    def update_settings(cls, settings):",
                        "        super().update_settings(settings)",
                        '        dm = settings["DOWNLOADER_MIDDLEWARES"]',
                        '        dm["custom.Middleware"] = 500',
                    ),
                ),
                path="a.py",
            ),
        ),
        NO_ISSUE,
        {},
    ),
    (
        (
            File(
                "\n".join(
                    (
                        "from scrapy import Spider",
                        "",
                        "class MySpider(Spider):",
                        "    name = 'my_spider'",
                        "",
                        "    @classmethod",
                        "    def update_settings(cls, settings):",
                        "        super().update_settings(settings)",
                        '        dm = settings.get("DOWNLOADER_MIDDLEWARES")',
                        '        dm["custom.Middleware"] = 500',
                    ),
                ),
                path="a.py",
            ),
        ),
        ExpectedIssue("SCP40 unneeded setting get", line=9, column=22, path="a.py"),
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
