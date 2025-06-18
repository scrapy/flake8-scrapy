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
from .finders.setting_modules import SettingModuleIssueFinder
from .finders.unsupported import LambdaCallbackIssueFinder

__version__ = "0.0.2"

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence


class ScrapyStyleIssueFinder(NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issues = []
        lambda_callback_issue_finder = LambdaCallbackIssueFinder()
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
                UrlJoinIssueFinder(),
            ],
            "Subscript": [
                ExtractThenIndexIssueFinder(),
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
        context = Context.from_flake8_params(
            tree, filename, lines, self.requirements_file_path
        )
        self.requirements_finder = RequirementsIssueFinder(context)
        self.scrapinghub_finder = ScrapinghubIssueFinder(context)
        self.setting_module_finder = SettingModuleIssueFinder(context)

    def run(self):
        for issue in self.run_checks():
            yield (*issue, self.__class__)

    def run_checks(self):
        if self.setting_module_finder.in_setting_module():
            yield from self.setting_module_finder.check()
        elif self.tree:
            yield from self.check_code()
        elif self.requirements_finder.in_requirements_file():
            yield from self.requirements_finder.check()
        elif self.scrapinghub_finder.in_scrapinghub_file():
            yield from self.scrapinghub_finder.check()

    def check_code(self) -> Generator[tuple[str, int, int], None, None]:
        finder = ScrapyStyleIssueFinder()
        assert self.tree is not None
        finder.visit(self.tree)
        yield from finder.issues
