from ast import Assign, Module, Name, NodeVisitor
from ast import walk as iter_nodes
from collections.abc import Generator
from importlib.util import find_spec
from pathlib import Path

from flake8_scrapy.context import Context
from flake8_scrapy.issues import Issue
from flake8_scrapy.utils import extend_sys_path


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
        # setting name: line number
        top_level_seen: dict[str, int] = {}
        all_seen: set[str] = set()

        # First pass: Check for redefinitions at the top level of the module
        for statement in node.body:
            if not isinstance(statement, Assign):
                continue
            for target in statement.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                if name in top_level_seen:
                    self.issues.append(
                        Issue(
                            7,
                            "redefined setting",
                            detail=f"seen first at line {top_level_seen[name]}",
                            line=statement.lineno,
                            column=statement.col_offset,
                        )
                    )
                    continue
                top_level_seen[name] = statement.lineno

        # Second pass: collect all settings and check specific values
        for child_node in iter_nodes(node):
            if not isinstance(child_node, Assign):
                continue
            for target in child_node.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                all_seen.add(name)

        if "USER_AGENT" not in all_seen:
            self.issues.append(Issue(8, "no project USER_AGENT"))
