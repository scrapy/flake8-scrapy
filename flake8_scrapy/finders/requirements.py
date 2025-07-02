from __future__ import annotations

from typing import TYPE_CHECKING

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.issues import Issue

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context


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
        }
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
        }
    )

    def __init__(self, context: Context):
        self.context = context

    def in_requirements_file(self) -> bool:
        if not self.context.project.requirements_file_path:
            return False
        return self.context.file.path == self.context.project.requirements_file_path

    def check(self) -> Generator[Issue, None, None]:
        packages: set[str] = set()
        assert self.context.file.lines is not None
        for line_number, line in enumerate(self.context.file.lines, start=1):
            line = line.strip()  # noqa: PLW2901
            if not line or line.startswith("#"):
                continue
            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                continue
            name = canonicalize_name(requirement.name)
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
            yield Issue(13, "incomplete requirements freeze")
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

    def check_package_name(self, name: str, line: int) -> Generator[Issue, None, None]:
        package = PACKAGES[name]
        if package.replacements:
            replacement = (
                package.replacements[0]
                if len(package.replacements) == 1
                else f"one of: {', '.join(package.replacements)}"
            )
            yield Issue(
                16, "unmaintained requirement", f"replace with {replacement}", line=line
            )

    def check_package_version(
        self, name: str, version: Version, line: int
    ) -> Generator[Issue, None, None]:
        package = PACKAGES[name]
        if (
            package.lowest_supported_version
            and version < package.lowest_supported_version
        ):
            yield Issue(
                14,
                "unsupported requirement",
                f"scrapy-flake8 only supports {name}>={package.lowest_supported_version}+",
                line=line,
            )
        if package.lowest_safe_version and version < package.lowest_safe_version:
            yield Issue(
                15,
                "insecure requirement",
                f"{name} {package.lowest_safe_version} implements security fixes",
                line=line,
            )

    def check_scrapy_cloud_stack_requirements(
        self, packages: set[str]
    ) -> Generator[Issue, None, None]:
        if (
            not self.context.project.root
            or not (self.context.project.root / "scrapinghub.yml").exists()
        ):
            return
        missing = self.SCRAPY_CLOUD_STACK_DEPENDENCIES - packages
        if not missing:
            return
        detail = f"missing packages: {', '.join(sorted(missing))}"
        yield Issue(24, "missing stack requirements", detail)
