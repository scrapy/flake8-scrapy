from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.version import InvalidVersion, Version

from scrapy_lint.data.packages import PACKAGES
from scrapy_lint.issues import (
    INSECURE_REQUIREMENT,
    MISSING_STACK_REQUIREMENTS,
    PARTIAL_FREEZE,
    UNMAINTAINED_REQUIREMENT,
    UNSUPPORTED_REQUIREMENT,
    Issue,
    Pos,
)
from scrapy_lint.requirements import iter_requirement_lines

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from packaging.requirements import Requirement

    from scrapy_lint.context import Context


class RequirementsIssueFinder:
    REQUIRED_DEPENDENCIES = frozenset(
        {
            "cryptography",
            "cssselect",
            "lxml",
            "parsel",
            "protego",
            "pyopenssl",
            "queuelib",
            "service-identity",
            "twisted",
            "w3lib",
            "zope-interface",
        },
    )
    SCRAPY_CLOUD_STACK_DEPENDENCIES = frozenset(
        {
            "aiohttp",
            "awscli",
            "boto",
            "boto3",
            "jinja2",
            "monkeylearn",
            "pillow",
            "pyyaml",
            "requests",
            "scrapinghub",
            "scrapinghub-entrypoint-scrapy",
            "scrapy-deltafetch",
            "scrapy-dotpersistence",
            "scrapy-magicfields",
            "scrapy-pagestorage",
            "scrapy-querycleaner",
            "scrapy-splitvariants",
            "scrapy-zyte-smartproxy",
            "spidermon",
            "urllib3",
        },
    )

    def __init__(self, context: Context):
        self.context = context

    def lint(self, file: Path) -> Generator[Issue]:
        packages: set[str] = set()
        try:
            requirements_text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return
        for line_number, name, requirement in iter_requirement_lines(
            requirements_text.splitlines(),
        ):
            packages.add(name)
            if name not in PACKAGES:
                continue
            yield from self.check_package_name(name, line_number)
            version = self.requirement_version(requirement)
            if version is None:
                continue
            yield from self.check_package_version(name, version, line_number)
        missing_deps = self.REQUIRED_DEPENDENCIES - packages
        if missing_deps or not packages:
            yield Issue(PARTIAL_FREEZE)
        yield from self.check_scrapy_cloud_stack_requirements(packages)

    @staticmethod
    def requirement_version(requirement: Requirement) -> Version | None:
        if not requirement.specifier or len(requirement.specifier) != 1:
            return None
        spec = next(iter(requirement.specifier))
        if spec.operator != "==":
            return None
        try:
            return Version(spec.version)
        except InvalidVersion:
            return None

    def check_package_name(self, name: str, line: int) -> Generator[Issue]:
        package = PACKAGES[name]
        if package.replacements:
            replacement = (
                package.replacements[0]
                if len(package.replacements) == 1
                else f"one of: {', '.join(package.replacements)}"
            )
            detail = f"replace with {replacement}"
            yield Issue(UNMAINTAINED_REQUIREMENT, Pos(line), detail)

    def check_package_version(
        self,
        name: str,
        version: Version,
        line: int,
    ) -> Generator[Issue]:
        package = PACKAGES[name]
        pos = Pos(line)
        if (
            package.lowest_supported_version
            and version < package.lowest_supported_version
        ):
            detail = (
                f"scrapy-lint only supports {name} {package.lowest_supported_version}+"
            )
            yield Issue(UNSUPPORTED_REQUIREMENT, pos, detail)
        if package.lowest_safe_version and version < package.lowest_safe_version:
            detail = f"{name} {package.lowest_safe_version} implements security fixes"
            yield Issue(INSECURE_REQUIREMENT, pos, detail)

    def check_scrapy_cloud_stack_requirements(
        self,
        packages: set[str],
    ) -> Generator[Issue]:
        if (
            not self.context.project.root
            or not (self.context.project.root / "scrapinghub.yml").exists()
        ):
            return
        missing = self.SCRAPY_CLOUD_STACK_DEPENDENCIES - packages
        if not missing:
            return
        detail = ", ".join(sorted(missing))
        yield Issue(MISSING_STACK_REQUIREMENTS, detail=detail)
