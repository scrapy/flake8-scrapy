from collections.abc import Sequence

from . import NO_ISSUE, ExpectedIssue, File, cases, iter_issues
from .helpers import check_project


def issue(message, path="scrapinghub.yml", **kwargs):
    return ExpectedIssue(message, path=path, **kwargs)


LATEST_KNOWN_STACK = "scrapy:2.12-20241202"


def default_issues(path: str = "requirements.txt") -> Sequence[ExpectedIssue]:
    return (
        ExpectedIssue(
            message="SCP13 incomplete requirements freeze",
            path=path,
        ),
        ExpectedIssue(
            message="SCP24 missing stack requirements: aiohttp, "
            "awscli, boto, boto3, jinja2, monkeylearn, pillow, pyyaml, "
            "requests, scrapinghub, scrapinghub-entrypoint-scrapy, "
            "scrapy-deltafetch, scrapy-dotpersistence, scrapy-magicfields, "
            "scrapy-pagestorage, scrapy-querycleaner, "
            "scrapy-splitvariants, scrapy-zyte-smartproxy, spidermon, "
            "urllib3",
            path=path,
        ),
    )


CASES = [
    # Config content
    *(
        (
            (
                File(config, "scrapinghub.yml"),
                File("", "scrapy.cfg"),
                File("", "requirements.txt"),
            ),
            (
                *default_issues(),
                *iter_issues(issues),
            ),
            {},
        )
        for config, issues in (
            *(
                (config, NO_ISSUE)
                for config in (
                    "\n".join(
                        [
                            "requirements:",
                            "  file: requirements.txt",
                            f"stack: {LATEST_KNOWN_STACK}",
                        ],
                    ),
                    "image: custom:latest",
                    "\n".join(
                        [
                            "image: custom:latest",
                            "projects:",
                            "  default:",
                            "    stack: scrapy:2.12",
                            "    requirements:",
                            "      file: requirements.txt",
                        ],
                    ),
                    "\n".join(
                        [
                            "projects:",
                            "  default:",
                            "    image: custom:latest",
                            "    stack: scrapy:2.12",
                            "    requirements:",
                            "      file: requirements.txt",
                        ],
                    ),
                )
            ),
            # SCP18 no root stack
            *(
                (config, issue("SCP18 no root stack"))
                for config in (
                    "\n".join(["requirements:", "  file: requirements.txt"]),
                )
            ),
            # SCP19 non-root stack
            (
                "\n".join(
                    [
                        "requirements:",
                        "  file: requirements.txt",
                        "projects:",
                        "  default:",
                        f"    stack: {LATEST_KNOWN_STACK}",
                    ],
                ),
                (
                    issue("SCP18 no root stack"),
                    issue("SCP19 non-root stack", line=5, column=4),
                ),
            ),
            (
                "\n".join(
                    [
                        "requirements:",
                        "  file: requirements.txt",
                        "stacks:",
                        f"  default: {LATEST_KNOWN_STACK}",
                    ],
                ),
                issue("SCP19 non-root stack", line=4, column=2),
            ),
            (
                "\n".join(
                    [
                        "requirements:",
                        "  file: requirements.txt",
                        "stacks:",
                        f"  prod: {LATEST_KNOWN_STACK}",
                        f"  dev: {LATEST_KNOWN_STACK}",
                    ],
                ),
                (
                    issue("SCP18 no root stack"),
                    issue("SCP19 non-root stack", line=4, column=2),
                    issue("SCP19 non-root stack", line=5, column=2),
                ),
            ),
            # SCP20 stack not frozen
            *(
                (
                    (f"{config}\nrequirements:\n  file: requirements.txt"),
                    issue("SCP20 stack not frozen", column=7),
                )
                for config in (
                    "stack: scrapy:2.12",
                    "stack: scrapy:latest",
                    "stack: scrapy:2.12-rc1",
                )
            ),
            (
                "\n".join(
                    [
                        "project: 12345",
                        "stack: foo",
                        "requirements:",
                        "  file: requirements.txt",
                    ],
                ),
                issue("SCP20 stack not frozen", line=2, column=7),
            ),
            (
                "\n".join(
                    [
                        "requirements:",
                        "  file: requirements.txt",
                        "stacks:",
                        "  default: scrapy:2.12",
                        "  prod: scrapy:2.11",
                    ],
                ),
                (
                    issue("SCP19 non-root stack", line=4, column=2),
                    issue("SCP19 non-root stack", line=5, column=2),
                    issue("SCP20 stack not frozen", line=4, column=11),
                    issue("SCP20 stack not frozen", line=5, column=8),
                ),
            ),
            # SCP21 no root requirements
            *(
                (config, issue("SCP21 no root requirements"))
                for config in (
                    "\n".join([f"stack: {LATEST_KNOWN_STACK}", "project: 12345"]),
                )
            ),
            # SCP22 non-root requirements
            *(
                (config, issue("SCP22 non-root requirements", line=6, column=4))
                for config in (
                    "\n".join(
                        [
                            f"stack: {LATEST_KNOWN_STACK}",
                            "requirements:",
                            "  file: requirements.txt",
                            "projects:",
                            "  default:",
                            "    requirements:",
                            "      file: requirements.txt",
                        ],
                    ),
                )
            ),
            # SCP23 no requirements.file
            *(
                (
                    config,
                    issue(
                        "SCP23 invalid scrapinghub.yml: no requirements.file key",
                        line=3,
                        column=2,
                    ),
                )
                for config in (
                    "\n".join(
                        [
                            f"stack: {LATEST_KNOWN_STACK}",
                            "requirements:",
                            "  eggs:",
                            "  - a.egg",
                        ],
                    ),
                )
            ),
            # SCP24 invalid requirements.file
            *(
                (
                    "\n".join(
                        [
                            f"stack: {LATEST_KNOWN_STACK}",
                            "requirements:",
                            f"  file: {value}",
                        ],
                    ),
                    issue(f"SCP23 invalid scrapinghub.yml: {detail}", line=3, column=8),
                )
                for value, detail in (
                    ("", "non-str requirements.file"),
                    ("123", "non-str requirements.file"),
                    ('""', "empty requirements.file"),
                )
            ),
            # SCP25 unexisting requirements.file
            *(
                (
                    "\n".join(
                        [
                            f"stack: {LATEST_KNOWN_STACK}",
                            "requirements:",
                            f"  file: {path}",
                        ],
                    ),
                    issue("SCP25 unexisting requirements.file", line=3, column=8),
                )
                for path in (
                    "missing-requirements.txt",
                    "nonexistent/requirements.txt",
                )
            ),
            # Multiple issues
            (
                "\n".join(
                    [
                        "projects:",
                        "  default:",
                        "    id: 12345",
                        "    stack: '2.12'",
                        "    requirements:",
                        "      eggs:",
                        "      - a.egg:",
                    ],
                ),
                (
                    issue("SCP18 no root stack"),
                    issue("SCP19 non-root stack", line=4, column=4),
                    issue("SCP20 stack not frozen", line=4, column=11),
                    issue("SCP21 no root requirements"),
                    issue("SCP22 non-root requirements", line=5, column=4),
                    issue(
                        "SCP23 invalid scrapinghub.yml: no requirements.file key",
                        line=6,
                        column=6,
                    ),
                ),
            ),
            # SCP23 invalid scrapinghub.yml
            (
                "invalid: yaml: content:",
                issue(
                    "SCP23 invalid scrapinghub.yml: mapping values are not allowed here\n"
                    '  in "<unicode string>", line 1, column 14:\n'
                    "    invalid: yaml: content:\n"
                    "                 ^ (line: 1)",
                ),
            ),
            (
                "- not a dict",
                issue("SCP23 invalid scrapinghub.yml: non-mapping root data structure"),
            ),
            (
                "just a string",
                issue("SCP23 invalid scrapinghub.yml: non-mapping root data structure"),
            ),
            (
                "123",
                issue("SCP23 invalid scrapinghub.yml: non-mapping root data structure"),
            ),
            (
                "true",
                issue("SCP23 invalid scrapinghub.yml: non-mapping root data structure"),
            ),
            (
                "null",
                issue("SCP23 invalid scrapinghub.yml: non-mapping root data structure"),
            ),
            (
                "\n".join(
                    [
                        f"stack: {LATEST_KNOWN_STACK}",
                        "requirements: yes",
                    ],
                ),
                issue(
                    "SCP23 invalid scrapinghub.yml: non-mapping requirements",
                    line=2,
                    column=14,
                ),
            ),
            (
                "\n".join(
                    [
                        "requirements:",
                        "  file: requirements.txt",
                        f"stacks: {LATEST_KNOWN_STACK}",
                    ],
                ),
                [
                    issue("SCP18 no root stack"),
                    issue(
                        "SCP23 invalid scrapinghub.yml: non-mapping stacks",
                        line=3,
                        column=8,
                    ),
                ],
            ),
            (
                "\n".join(
                    [
                        "stack: 2.8",
                        "projects:",
                        "  default:",
                        "    stack: 3",
                        "requirements:",
                        "  file: requirements.txt",
                    ],
                ),
                [
                    issue("SCP19 non-root stack", line=4, column=4),
                    issue(
                        "SCP23 invalid scrapinghub.yml: non-str stack",
                        line=1,
                        column=7,
                    ),
                    issue(
                        "SCP23 invalid scrapinghub.yml: non-str stack",
                        line=4,
                        column=11,
                    ),
                ],
            ),
        )
    ),
    # Test case without requirements.txt file for SCP25
    *(
        (
            (
                File(config, "scrapinghub.yml"),
                File("", "scrapy.cfg"),
            ),
            issues,
            {},
        )
        for config, issues in (
            (
                "\n".join(
                    [
                        f"stack: {LATEST_KNOWN_STACK}",
                        "requirements:",
                        "  file: requirements.txt",
                    ],
                ),
                issue("SCP25 unexisting requirements.file", line=3, column=8),
            ),
        )
    ),
    # Only a root scrapinghub.yml file is checked
    *(
        (
            (File("project: 12345", path), File("", "scrapy.cfg")),
            issues,
            {},
        )
        for path, issues in (
            (
                "scrapinghub.yml",
                (issue("SCP18 no root stack"), issue("SCP21 no root requirements")),
            ),
            *(
                (path, NO_ISSUE)
                for path in (
                    "not-scrapinghub.yml",
                    "subdir/scrapinghub.yml",
                )
            ),
        )
    ),
    # SCP26 requirements.file mismatch
    (
        (
            File(
                "\n".join(
                    [
                        f"stack: {LATEST_KNOWN_STACK}",
                        "requirements:",
                        "  file: requirements.txt",
                    ],
                ),
                "scrapinghub.yml",
            ),
            File("", "scrapy.cfg"),
            File("", "requirements-dev.txt"),
            File("", "requirements.txt"),
        ),
        (
            *default_issues("requirements-dev.txt"),
            issue("SCP26 requirements.file mismatch", line=3, column=8),
        ),
        {"requirements_file": "requirements-dev.txt"},
    ),
    (
        (
            File(
                "\n".join(
                    [
                        f"stack: {LATEST_KNOWN_STACK}",
                        "requirements:",
                        "  file: requirements-dev.txt",
                    ],
                ),
                "scrapinghub.yml",
            ),
            File("", "scrapy.cfg"),
            File("", "requirements-dev.txt"),
        ),
        (*default_issues("requirements-dev.txt"),),
        {"requirements_file": "requirements-dev.txt"},
    ),
]


@cases(CASES)
def test(files, expected, options):
    check_project(files, expected, options)
