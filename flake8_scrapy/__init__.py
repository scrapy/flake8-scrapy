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
            "Subscript": [
                ExtractThenIndexIssueFinder(),
                setting_issue_finder,
            ],
        }

    def find_issues_visitor(self, visitor, node):
        """Find issues for the provided visitor"""
        for finder in self.finders[visitor]:
            issues = finder.find_issues(node)
            if issues:
                self.issues.extend(list(issues))
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.find_issues_visitor("Assign", node)

    def visit_Call(self, node):
        self.find_issues_visitor("Call", node)

    def visit_Subscript(self, node):
        self.find_issues_visitor("Subscript", node)


class ScrapyStyleChecker:
    options = None
    name = "flake8-scrapy"
    version = __version__
    requirements_file_path: ClassVar[str] = ""

    @classmethod
    def add_options(cls, parser):
        parser.add_option(
            "--scrapy-requirements-file",
            default="",
            help="Path of the project requirements file",
            parse_from_config=True,
        )

    @classmethod
    def parse_options(cls, options):
        cls.requirements_file_path = options.scrapy_requirements_file or getattr(
            options, "requirements_file", ""
        )

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
            setting_checker = SettingChecker()
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
