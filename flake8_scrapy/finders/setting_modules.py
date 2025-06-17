from ast import Assign, Constant, Module, Name, NodeVisitor
from ast import walk as iter_nodes
from collections.abc import Generator
from contextlib import suppress
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

from flake8_scrapy.context import Context
from flake8_scrapy.issues import Issue
from flake8_scrapy.settings import getbool
from flake8_scrapy.utils import extend_sys_path

if TYPE_CHECKING:
    from flake8_scrapy.typing import LineNumber


class SettingModuleIssueFinder(NodeVisitor):
    def __init__(self, context: Context):
        super().__init__()
        self.context = context
        self.issues: list[Issue] = []

    def in_setting_module(self) -> bool:
        for import_path in self.context.project.setting_module_import_paths:
            assert self.context.project.root is not None
            with extend_sys_path(self.context.project.root):
                spec = find_spec(import_path)
            if not spec or not spec.origin:
                continue
            module_path = Path(spec.origin).resolve()
            if module_path == self.context.file.path:
                return True
        return False

    def check(self) -> Generator[Issue, None, None]:
        assert self.context.file.tree is not None
        self.visit(self.context.file.tree)
        yield from self.issues

    def visit_Module(self, node: Module) -> None:
        self.check_body_level_issues(node)
        self.check_all_nodes_issues(node)

    def check_body_level_issues(self, node: Module) -> None:
        seen: dict[str, LineNumber] = {}
        for child in node.body:
            if not isinstance(child, Assign):
                continue
            for target in child.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                if name in seen:
                    self.issues.append(
                        Issue(
                            7,
                            "redefined setting",
                            detail=f"seen first at line {seen[name]}",
                            line=child.lineno,
                            column=child.col_offset,
                        )
                    )
                    continue
                seen[name] = child.lineno

    def check_all_nodes_issues(self, node: Module) -> None:
        seen: set[str] = set()
        robotstxt_obey_values = []
        for child in iter_nodes(node):
            if not isinstance(child, Assign):
                continue
            for target in child.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                if name == "ROBOTSTXT_OBEY":
                    value = True
                    col_offset = child.col_offset
                    if isinstance(child.value, Constant):
                        col_offset = child.value.col_offset
                        # If the value is not a valid boolean, assume True to
                        # avoid reporting the setting as being disabled, and
                        # instead let a check about wrong setting values handle
                        # it.
                        with suppress(ValueError):
                            value = getbool(child.value.value)
                    robotstxt_obey_values.append((value, child.lineno, col_offset))
                seen.add(name)

        if "USER_AGENT" not in seen:
            self.issues.append(Issue(8, "no project USER_AGENT"))

        if not robotstxt_obey_values:
            self.issues.append(Issue(9, "robots.txt ignored by default"))
        elif all(not value for value, *_ in robotstxt_obey_values):
            _, line, column = robotstxt_obey_values[0]
            self.issues.append(
                Issue(9, "robots.txt ignored by default", line=line, column=column)
            )
