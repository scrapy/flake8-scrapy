from ast import Assign, Module, Name, NodeVisitor
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

        # Check for redefinitions at the top level of the module
        for child in node.body:
            if not isinstance(child, Assign):
                continue
            for target in child.targets:
                if not (isinstance(target, Name) and target.id.isupper()):
                    continue
                name = target.id
                if name in top_level_seen:
                    self.issues.append(
                        Issue(
                            7,
                            "redefined setting",
                            detail=f"seen first at line {top_level_seen[name]}",
                            line=child.lineno,
                            column=child.col_offset,
                        )
                    )
                    continue
                top_level_seen[name] = child.lineno
