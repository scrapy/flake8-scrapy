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
        processor = SettingsProcessor()
        for child in iter_nodes(node):
            if isinstance(child, Assign):
                processor.process_assignment(child)
        self.issues.extend(processor.get_issues())


class SettingsProcessor:
    def __init__(self):
        self.seen_settings: set[str] = set()
        self.autothrottle_enabled = False
        self.robotstxt_obey_values: list[tuple[bool, int, int]] = []
        self.issues: list[Issue] = []

    def process_assignment(self, assignment: Assign) -> None:
        for target in assignment.targets:
            if not (isinstance(target, Name) and target.id.isupper()):
                continue
            name = target.id
            self.seen_settings.add(name)
            self.process_setting(name, assignment)

    def process_setting(self, name: str, child: Assign) -> None:
        if name == "AUTOTHROTTLE_ENABLED":
            self.process_autothrottle(child)
        elif name == "ROBOTSTXT_OBEY":
            self.process_robotstxt(child)

    def process_autothrottle(self, child: Assign) -> None:
        if not isinstance(child.value, Constant):
            self.autothrottle_enabled = True
        else:
            try:
                value = getbool(child.value.value)
            except ValueError:
                # If the value is not a valid boolean, assume True
                # to avoid reporting the setting as being disabled,
                # and instead let a check about wrong setting
                # values handle it.
                self.autothrottle_enabled = True
            else:
                # Unlike with ROBOTSTXT_OBEY, we do not keep track
                # of the line and column here because SCP10 can be
                # silenced even if AUTOTHROTTLE_ENABLED is set to
                # False by defining other concurrency settings, so
                # a specific False value is not *the* reason why
                # SCP10 triggers.
                self.autothrottle_enabled = value

    def process_robotstxt(self, child: Assign) -> None:
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
        self.robotstxt_obey_values.append((value, child.lineno, col_offset))

    def get_issues(self) -> list[Issue]:
        self.validate_user_agent()
        self.validate_robotstxt()
        self.validate_throttling()
        return self.issues

    def validate_user_agent(self) -> None:
        if "USER_AGENT" not in self.seen_settings:
            self.issues.append(Issue(8, "no project USER_AGENT"))

    def validate_robotstxt(self) -> None:
        if not self.robotstxt_obey_values:
            self.issues.append(Issue(9, "robots.txt ignored by default"))
        elif all(not value for value, *_ in self.robotstxt_obey_values):
            _, line, column = self.robotstxt_obey_values[0]
            self.issues.append(
                Issue(9, "robots.txt ignored by default", line=line, column=column)
            )

    def validate_throttling(self) -> None:
        if not self.autothrottle_enabled and not all(
            setting in self.seen_settings
            for setting in (
                "CONCURRENT_REQUESTS",
                "CONCURRENT_REQUESTS_PER_DOMAIN",
                "DOWNLOAD_DELAY",
            )
        ):
            self.issues.append(Issue(10, "incomplete project throttling"))
