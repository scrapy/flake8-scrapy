from __future__ import annotations

from packaging.version import Version

from tests.helpers import check_project

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases, iter_issues
from .settings import default_issues
from .test_settings import SETTING_VALUE_CHECK_TEMPLATES, SafeDict, zip_with_template

CASES: Cases = (
    # Checks bassed on requirements and setting values
    *(
        (
            (
                File("", path="scrapy.cfg"),
                File(requirements, path="requirements.txt"),
                File(f"settings[{name!r}] = {value}", path=path),
            ),
            (
                ExpectedIssue(
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
                        ExpectedIssue(
                            "SCP15 insecure requirement: scrapy 2.11.2 implements "
                            "security fixes",
                            path="requirements.txt",
                        ),
                        *(
                            ExpectedIssue(
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
                ExpectedIssue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
                ExpectedIssue(
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
                    ExpectedIssue(
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
                ExpectedIssue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
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
                    ExpectedIssue(
                        "SCP17 redundant setting value",
                        column=18,
                        path=path,
                    ),
                    ExpectedIssue(
                        "SCP41 unneeded import path",
                        column=18,
                        path=path,
                    ),
                ),
            ),
            (
                ("scrapy==2.12.0",),
                "",
                ExpectedIssue(
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
                ExpectedIssue(
                    "SCP41 unneeded import path",
                    column=18,
                    path=path,
                ),
            ),
            (
                ("scrapy==2.12.0",),
                'TWISTED_REACTOR = "custom.reactor"',
                ExpectedIssue(
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
                    ExpectedIssue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
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
                    ExpectedIssue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                    ExpectedIssue(
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
                    ExpectedIssue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    ExpectedIssue("SCP33 base setting use", path=path),
                    ExpectedIssue(
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
                    ExpectedIssue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                    ExpectedIssue("SCP41 unneeded import path", column=20, path=path),
                ),
            ),
            (
                ("scrapy==2.12.0",),
                'SPIDER_CONTRACTS = {"scrapy.contracts.default.MetadataContract": None}',
                (
                    ExpectedIssue(
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
                    ExpectedIssue(
                        (
                            "SCP15 insecure requirement: scrapy 2.11.2 "
                            "implements security fixes"
                        ),
                        path="requirements.txt",
                    ),
                    ExpectedIssue(
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
                    ExpectedIssue(
                        (
                            "SCP34 missing changing setting: TWISTED_REACTOR "
                            "changes from None to "
                            "'twisted.internet.asyncioreactor.AsyncioSelectorReactor' "
                            "in scrapy 2.13.0"
                        ),
                        path=path,
                    ),
                    ExpectedIssue("SCP41 unneeded import path", column=22, path=path),
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
                ExpectedIssue(
                    "SCP13 incomplete requirements freeze",
                    path="requirements.txt",
                ),
                *(
                    ExpectedIssue(message, path="requirements.txt")
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
                        ExpectedIssue(
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
                    ExpectedIssue(
                        "SCP13 incomplete requirements freeze",
                        path="requirements.txt",
                    )
                    for _ in range(1)
                    if not isinstance(requirements, bytes)
                ),
                ExpectedIssue(
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
    # SCP27 unknown setting: recommend known-settings even when
    # dependency versions need to be taken into account (assume they are met)
    (
        (
            File("", path="scrapy.cfg"),
            File("scrapy", path="requirements.txt"),
            File("settings['SETING']", path="a.py"),
        ),
        (
            ExpectedIssue(
                message="SCP13 incomplete requirements freeze",
                line=1,
                column=0,
                path="requirements.txt",
            ),
            ExpectedIssue(
                "SCP27 unknown setting: did you mean: SETTING?",
                column=9,
                path="a.py",
            ),
        ),
        {
            "known-settings": "SETTING",
        },
    ),
)


@cases(CASES)
def test(
    input_: File | list[File],
    expected: ExpectedIssue | list[ExpectedIssue] | None,
    flake8_options,
):
    check_project(input_, expected, flake8_options)
