from __future__ import annotations

from ast import AST, NodeVisitor
from typing import TYPE_CHECKING, ClassVar

from .context import Context
from .finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from .finders.oldstyle import (
    ExtractThenIndexIssueFinder,
    GetFirstByIndexIssueFinder,
    OldSelectorIssueFinder,
    UrlJoinIssueFinder,
)
from .finders.requirements import RequirementsIssueFinder
from .finders.scrapinghub import ScrapinghubIssueFinder
from .finders.settings import (
    SettingChecker,
    SettingIssueFinder,
    SettingModuleIssueFinder,
)
from .finders.unsupported import LambdaCallbackIssueFinder

__version__ = "0.0.2"

if TYPE_CHECKING:
    from collections.abc import Sequence

    from flake8_scrapy.issues import Issue


class ScrapyStyleIssueFinder(NodeVisitor):
    def __init__(self, setting_checker: SettingChecker):
        super().__init__()
        self.issues: list[Issue] = []
        lambda_callback_issue_finder = LambdaCallbackIssueFinder()
        setting_issue_finder = SettingIssueFinder(setting_checker)

        self.finders: dict[str, Sequence] = {
            "Assign": [
                lambda_callback_issue_finder,
                OldSelectorIssueFinder(),
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
            ],
            "Call": [
                GetFirstByIndexIssueFinder(),
                lambda_callback_issue_finder,
                setting_issue_finder,
                UrlJoinIssueFinder(),
            ],
            "Compare": [
                setting_issue_finder,
            ],
            "FunctionDef": [
                setting_issue_finder,
            ],
            "Subscript": [
                ExtractThenIndexIssueFinder(),
                setting_issue_finder,
            ],
        }
        self.post_visitors = {
            "FunctionDef": (setting_issue_finder,),
        }

    def find_issues_visitor(self, visitor, node):
        """Find issues for the provided visitor"""
        for finder in self.finders[visitor]:
            issues = finder.find_issues(node)
            if issues:
                self.issues.extend(list(issues))
        self.generic_visit(node)
        for finder in self.post_visitors.get(visitor, ()):
            finder.post_visit(node)

    def visit(self, node):
        node_type = type(node).__name__
        if node_type in self.finders:
            self.find_issues_visitor(node_type, node)
        else:
            super().visit(node)


class ScrapyStyleChecker:
    options = None
    name = "flake8-scrapy"
    version = __version__
    requirements_file_path: ClassVar[str] = ""
    known_settings: ClassVar[set[str]] = set()

    @classmethod
    def add_options(cls, parser):
        parser.add_option(
            "--scrapy-requirements-file",
            default="",
            help="Path of the project requirements file",
            parse_from_config=True,
        )
        parser.add_option(
            "--scrapy-known-settings",
            default="",
            help="Comma-separated list of additional known settings (do not trigger SCP27)",
            parse_from_config=True,
        )

    @classmethod
    def parse_options(cls, options):
        cls.requirements_file_path = options.scrapy_requirements_file or getattr(
            options, "requirements_file", ""
        )
        known = getattr(options, "scrapy_known_settings", "")
        if known:
            cls.known_settings = {s.strip() for s in known.split(",") if s.strip()}
        else:
            cls.known_settings = set()

    def __init__(
        self, tree: AST | None, filename: str, lines: Sequence[str] | None = None
    ):
        self.tree = tree
        self.context = Context.from_flake8_params(
            tree, filename, lines, self.requirements_file_path
        )

    def run(self):
        for issue in self.run_checks():
            yield (*issue, self.__class__)

    def run_checks(self):
        if self.tree:
            setting_checker = SettingChecker(
                self.context, additional_known_settings=self.known_settings
            )
            setting_module_finder = SettingModuleIssueFinder(
                self.context, setting_checker
            )
            if setting_module_finder.in_setting_module():
                yield from setting_module_finder.check()
            finder = ScrapyStyleIssueFinder(setting_checker)
            finder.visit(self.tree)
            yield from finder.issues
            return

        requirements_finder = RequirementsIssueFinder(self.context)
        if requirements_finder.in_requirements_file():
            yield from requirements_finder.check()
            return

        scrapinghub_finder = ScrapinghubIssueFinder(self.context)
        if scrapinghub_finder.in_scrapinghub_file():
            yield from scrapinghub_finder.check()
            return
