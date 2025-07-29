from __future__ import annotations

import ast
from ast import NodeVisitor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:  # Python < 3.11
    import tomli as tomllib
from pathspec import GitIgnoreSpec

from scrapy_lint.issues import Issue

from .context import Context, Project
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
        lambda_callback_issue_finder = LambdaCallbackIssueFinder()
        setting_issue_finder = SettingIssueFinder(setting_checker)

        self.finders: dict[str, Sequence[IssueFinder]] = {
            "Assign": [
                lambda_callback_issue_finder,
                OldSelectorIssueFinder(),
                setting_issue_finder,
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
            ],
            "Call": [
                find_get_first_by_index_issues,
                lambda_callback_issue_finder,
                RequestIssueFinder(),
                setting_issue_finder,
                find_url_join_issues,
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
        root = Path().cwd()
        options = self.load_options(root)
        requirements_file: Path | None = self.resolve_requirements_file(options)
        project = Project(root, requirements_file)
        self.context = Context(project, options)
        self.files = self.resolve_files(root, paths, requirements_file)
        self.requirements_file = requirements_file
        self.setting_checker = SettingChecker(self.context)
        self.ignores: set[int] = {int(code[3:]) for code in options.get("ignore", [])}
        self.per_file_ignores: dict[Path, set[int]] = {
            (root / file).resolve(): {int(code[3:]) for code in codes}
            for file, codes in options.get("per-file-ignores", {}).items()
        }
        self.root = root

    @classmethod
    def resolve_requirements_file(
        cls,
        options: dict[str, Any],
    ) -> Path | None:
        requirements_file: Path | None
        path_str = options.get("requirements_file")
        if path_str is not None:
            requirements_file = Path(path_str).resolve()
            if requirements_file.exists():
                return requirements_file

        # Check scrapinghub.yml for requirements file
        scrapinghub_file = Path("scrapinghub.yml")
        yaml_parser = YAML(typ="safe")
        if scrapinghub_file.exists():
            try:
                with scrapinghub_file.open(encoding="utf-8") as f:
                    data = yaml_parser.load(f)
            except (UnicodeDecodeError, YAMLError):
                pass
            else:
                try:
                    requirements_file_name = data.get("requirements", {}).get(
                        "file",
                        "",
                    )
                except AttributeError:
                    pass
                else:
                    if requirements_file_name and isinstance(
                        requirements_file_name,
                        str,
                    ):
                        scrapinghub_requirements_file = Path(requirements_file_name)
                        if scrapinghub_requirements_file.exists():
                            return scrapinghub_requirements_file.resolve()

        # Fall back to requirements.txt
        requirements_file = Path("requirements.txt")
        if requirements_file.exists():
            return requirements_file.resolve()

        return None

    @classmethod
    def load_options(cls, root: Path) -> dict[str, Any]:
        pyproject_path = root / "pyproject.toml"
        if not pyproject_path.exists():
            return {}
        try:
            pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid pyproject.toml: {e}") from None
        return pyproject.get("tool", {}).get("scrapy-lint", {})

    @classmethod
    def resolve_files(
        cls,
        root: Path,
        paths: Sequence[Path],
        requirements_path: Path | None,
    ) -> Sequence[Path]:
        files = set()
        spec = None
        gitignore = root / ".gitignore"
        if gitignore.exists():
            spec = GitIgnoreSpec.from_lines(
                gitignore.read_text(encoding="utf-8").splitlines(),
            )
        for path in paths:
            if path.is_file():
                files.add(path)
                continue
            if path.resolve() == root:
                zyte_config_path = root / "scrapinghub.yml"
                if zyte_config_path.exists():
                    files.add(zyte_config_path)
                if requirements_path and requirements_path.exists():
                    files.add(requirements_path)
            for python_file_path in path.glob("**/*.py"):
                if spec is None or not spec.match_file(
                    python_file_path.relative_to(root),
                ):
                    files.add(python_file_path)
        return sorted(files)

    def lint(self) -> Generator[Issue]:
        for file in self.files:
            absolute_file = file.resolve()
            for issue in self.lint_file(absolute_file):
                if self.is_ignored(issue, absolute_file):
                    continue
                issue.file = absolute_file.relative_to(self.root)
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
        elif self.requirements_file is not None and file == self.requirements_file:
            yield from RequirementsIssueFinder(self.context).lint(file)

    def lint_python_file(self, file: Path) -> Generator[Issue]:
        try:
            with file.open("r", encoding="utf-8") as f:
                source = f.read()
        except UnicodeDecodeError as e:
            raise ValueError(
                f"Could not read {file.relative_to(self.root)}: {e}",
            ) from None
        tree = ast.parse(source, filename=str(file))
        setting_module_finder = SettingModuleIssueFinder(
            self.context,
            file,
            self.setting_checker,
        )
        if setting_module_finder.in_setting_module():
            yield from setting_module_finder.check(tree)
        finder = PythonIssueFinder(self.setting_checker)
        finder.visit(tree)
        yield from finder.issues
