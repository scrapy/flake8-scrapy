from __future__ import annotations

from tests.helpers import check_project
from tests.settings import SETTING_VALUE_CHECK_TEMPLATES, SafeDict, zip_with_template

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases

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
                        (
                            "FEEDS",
                            '{f: {"format": "json", "batch_item_count": 0, "indent": 0, "fields": foo}}',
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
                    ExpectedIssue(
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
                            ExpectedIssue(
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
)


@cases(CASES)
def test(
    files: File | list[File],
    expected: ExpectedIssue | list[ExpectedIssue] | None,
    options,
):
    check_project(files, expected, options)
