from __future__ import annotations

import ast
import warnings
from ast import NodeVisitor
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pathspec import GitIgnoreSpec

from scrapy_lint.issues import Issue

from .context import Context, Project
from .errors import InputFileError
from .finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from .finders.oldstyle import (
    OldSelectorIssueFinder,
    find_extract_then_index_issues,
    find_get_first_by_index_issues,
    find_url_join_issues,
)
from .finders.requests import RequestIssueFinder
from .finders.requirements import RequirementsIssueFinder
from .finders.settings import (
    SettingChecker,
    SettingIssueFinder,
    SettingModuleIssueFinder,
)
from .finders.unsupported import LambdaCallbackIssueFinder
from .finders.zyte import ZyteCloudConfigIssueFinder

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Generator, Sequence

    from .issues import Issue


class IssueFinder(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(self, node: ast.AST) -> Generator[Issue]: ...


class PythonIssueFinder(NodeVisitor):
    def __init__(self, setting_checker: SettingChecker):
        super().__init__()
        self.issues: list[Issue] = []
        domain_issue_finder = UnreachableDomainIssueFinder()
        lambda_callback_issue_finder = LambdaCallbackIssueFinder()
        setting_issue_finder = SettingIssueFinder(setting_checker)

        self.finders: dict[str, Sequence[IssueFinder]] = {
            "Assign": [
                lambda_callback_issue_finder,
                OldSelectorIssueFinder(),
                setting_issue_finder,
                domain_issue_finder,
                UrlInAllowedDomainsIssueFinder(),
            ],
            "Call": [
                find_get_first_by_index_issues,
                lambda_callback_issue_finder,
                RequestIssueFinder(),
                setting_issue_finder,
                find_url_join_issues,
            ],
            "ClassDef": [
                domain_issue_finder,
            ],
            "Compare": [
                setting_issue_finder,
            ],
            "FunctionDef": [
                setting_issue_finder,
            ],
            "Subscript": [
                find_extract_then_index_issues,
                setting_issue_finder,
            ],
        }
        self.post_visitors = {
            "FunctionDef": (setting_issue_finder,),
        }

    def find_issues_visitor(self, visitor, node):
        """Find issues for the provided visitor"""
        for finder in self.finders[visitor]:
            issues = finder(node)
            if issues:
                self.issues.extend(list(issues))
        self.generic_visit(node)
        for finder in self.post_visitors.get(visitor, ()):
            assert hasattr(finder, "post_visit")
            finder.post_visit(node)

    def visit(self, node):
        node_type = type(node).__name__
        if node_type in self.finders:
            self.find_issues_visitor(node_type, node)
        else:
            super().visit(node)


class Linter:
    @classmethod
    def from_args(cls, args: Namespace) -> Linter:
        return cls(args.paths)

    def __init__(self, paths: Sequence[Path]) -> None:
        self.project = Project(Path().cwd())
        self.context = Context(self.project)
        self.files = self.resolve_files(self.project, paths)
        self.setting_checker = SettingChecker(self.context)
        self.ignores: set[int] = {
            int(code[3:]) for code in self.project.scrapy_lint_options.get("ignore", [])
        }
        self.per_file_ignores: dict[Path, set[int]] = {
            (self.project.path / file).resolve(): {int(code[3:]) for code in codes}
            for file, codes in self.project.scrapy_lint_options.get(
                "per-file-ignores", {}
            ).items()
        }

    @classmethod
    def resolve_files(
        cls,
        project: Project,
        paths: Sequence[Path],
    ) -> Sequence[Path]:
        files = set()
        spec = None
        gitignore = project.path / ".gitignore"
        if gitignore.exists():
            spec = GitIgnoreSpec.from_lines(
                gitignore.read_text(encoding="utf-8").splitlines(),
            )
        for path in paths:
            if path.is_file():
                files.add(path)
                continue
            if path.resolve() == project.path:
                zyte_config_path = project.path / "scrapinghub.yml"
                if zyte_config_path.exists():
                    files.add(zyte_config_path)
                if project.requirements_file and project.requirements_file.exists():
                    files.add(project.requirements_file)
            for python_file_path in path.glob("**/*.py"):
                if spec is None or not spec.match_file(
                    python_file_path.relative_to(project.path),
                ):
                    files.add(python_file_path)
        return sorted(files)

    def lint(self) -> Generator[Issue]:
        for file in self.files:
            absolute_file = file.resolve()
            for issue in self.lint_file(absolute_file):
                if self.is_ignored(issue, absolute_file):
                    continue
                issue.file = absolute_file.relative_to(self.project.path)
                yield issue

    def is_ignored(self, issue: Issue, file: Path) -> bool:
        return issue.code in self.ignores or (
            file in self.per_file_ignores and issue.code in self.per_file_ignores[file]
        )

    def lint_file(self, file: Path) -> Generator[Issue]:
        if file.suffix == ".py":
            yield from self.lint_python_file(file)
        elif file.name == "scrapinghub.yml":
            yield from ZyteCloudConfigIssueFinder(self.context).lint(file)
        elif (
            self.project.requirements_file is not None
            and file == self.project.requirements_file
        ):
            yield from RequirementsIssueFinder(self.context).lint(file)

    def lint_python_file(self, file: Path) -> Generator[Issue]:
        try:
            with file.open("r", encoding="utf-8") as f:
                source = f.read()
        except UnicodeDecodeError as e:
            raise InputFileError(str(e), file) from None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                tree = ast.parse(source, filename=str(file))
            except SyntaxError as e:
                raise InputFileError(str(e), file) from None
        setting_module_finder = SettingModuleIssueFinder(
            self.context,
            file,
            self.setting_checker,
        )
        if file in self.context.project.setting_module_paths:
            yield from setting_module_finder.check(tree)
        finder = PythonIssueFinder(self.setting_checker)
        finder.visit(tree)
        yield from finder.issues
