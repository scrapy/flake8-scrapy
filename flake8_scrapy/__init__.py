from __future__ import annotations

from ast import AST, NodeVisitor
from typing import TYPE_CHECKING

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
from .finders.requests import RequestIssueFinder
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
    import argparse
    from collections.abc import Sequence

    from flake8_scrapy.issues import Issue


class PythonIssueFinder(NodeVisitor):
    def __init__(self, setting_checker: SettingChecker):
        super().__init__()
        self.issues: list[Issue] = []
        lambda_callback_issue_finder = LambdaCallbackIssueFinder()
        setting_issue_finder = SettingIssueFinder(setting_checker)

        self.finders: dict[str, Sequence] = {
            "Assign": [
                lambda_callback_issue_finder,
                OldSelectorIssueFinder(),
                setting_issue_finder,
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
            ],
            "Call": [
                GetFirstByIndexIssueFinder(),
                lambda_callback_issue_finder,
                RequestIssueFinder(),
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


class ScrapyFlake8Plugin:
    options = None
    name = "flake8-scrapy"
    version = __version__
    flake8_options: argparse.Namespace

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
    def parse_options(cls, options: argparse.Namespace):
        cls.flake8_options = options

    def __init__(
        self, tree: AST | None, filename: str, lines: Sequence[str] | None = None
    ):
        self.tree = tree
        self.context = Context.from_flake8_params(
            tree=tree,
            file_path=filename,
            lines=lines,
            options=self.flake8_options,
        )

    def run(self):
        for issue in self.run_checks():
            yield (*issue, self.__class__)

    def run_checks(self):
        if self.tree:
            setting_checker = SettingChecker(self.context)
            setting_module_finder = SettingModuleIssueFinder(
                self.context, setting_checker
            )
            if setting_module_finder.in_setting_module():
                yield from setting_module_finder.check()
            finder = PythonIssueFinder(setting_checker)
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
