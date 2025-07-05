from __future__ import annotations

from ast import (
    Assign,
    Attribute,
    Call,
    ClassDef,
    Compare,
    Constant,
    Dict,
    FunctionDef,
    Import,
    ImportFrom,
    In,
    Module,
    Name,
    NodeVisitor,
    NotIn,
    Subscript,
    alias,
    expr,
    keyword,
)
from ast import walk as iter_nodes
from collections.abc import Generator
from contextlib import suppress
from difflib import SequenceMatcher
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from flake8_scrapy.ast import extract_literal_value
from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.data.settings import (
    MAX_AUTOMATIC_SUGGESTIONS,
    MIN_AUTOMATIC_SUGGESTION_SCORE,
    PREDEFINED_SUGGESTIONS,
    SETTINGS,
)
from flake8_scrapy.issues import Issue
from flake8_scrapy.settings import (
    UNKNOWN_SETTING_VALUE,
    UnknownUnsupportedVersion,
    getbool,
)
from flake8_scrapy.utils import extend_sys_path

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context
    from flake8_scrapy.typing import LineNumber

IssueNode = Union[Constant, Name, keyword, ClassDef, FunctionDef, Import, ImportFrom]


def definition_column(node: ClassDef | FunctionDef) -> int:
    offset = len("class ") if isinstance(node, ClassDef) else len("def ")
    return node.col_offset + offset


def import_column(node: Import | ImportFrom, alias: alias) -> int:
    if alias.asname:
        # For "from foo import BAR as BAZ" or "import foo as BAR", point to "BAZ"/"BAR"
        # Need to find position of alias name after " as "
        if hasattr(alias, "col_offset"):
            return alias.col_offset + len(alias.name) + 4  # " as " is 4 chars
        # Python 3.9 compatibility: alias objects don't have col_offset
        return node.col_offset
    # For "from foo import FOO" or "import FOO", point to "FOO"
    if hasattr(alias, "col_offset"):
        return alias.col_offset
    # Python 3.9 compatibility: alias objects don't have col_offset
    return node.col_offset


class SettingChecker:
    def __init__(self, context: Context, additional_known_settings: set[str]):
        self.project = context.project
        self.additional_known_settings = additional_known_settings

    def is_known_setting(self, name: str) -> bool:
        return name in SETTINGS or name in self.additional_known_settings

    def is_supported_setting(self, setting: str) -> bool:
        if not self.project.requirements:
            return True
        assert setting in SETTINGS
        setting_info = SETTINGS[setting]
        if setting_info.package not in self.project.frozen_requirements or (
            not setting_info.added_in and not setting_info.deprecated_in
        ):
            return setting_info.package in self.project.requirements
        deprecated_in = setting_info.deprecated_in
        if isinstance(deprecated_in, UnknownUnsupportedVersion):
            deprecated_in = PACKAGES[setting_info.package].lowest_supported_version
            assert deprecated_in
        package_version = self.project.frozen_requirements[setting_info.package]
        return (
            not setting_info.added_in or package_version >= setting_info.added_in
        ) and (not deprecated_in or package_version < deprecated_in)

    def suggest_names(self, unknown_name: str) -> list[str]:
        if unknown_name in PREDEFINED_SUGGESTIONS:
            return [
                setting
                for setting in PREDEFINED_SUGGESTIONS[unknown_name]
                if self.is_supported_setting(setting)
            ]
        matches = []
        for candidate in self.additional_known_settings | set(SETTINGS):
            if (
                candidate.endswith("_BASE") and not unknown_name.endswith("_BASE")
            ) or not self.is_supported_setting(candidate):
                continue
            ratio = SequenceMatcher(None, unknown_name, candidate).ratio()
            if ratio >= MIN_AUTOMATIC_SUGGESTION_SCORE:
                matches.append((candidate, ratio))
        matches.sort(key=lambda x: (-x[1], x[0]))
        return [m[0] for m in matches[:MAX_AUTOMATIC_SUGGESTIONS]]

    def check_known_name(
        self, name: str, resolved_node: IssueNode, column: int
    ) -> Generator[Issue, None, None]:
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        added_in = setting.added_in
        deprecated_in = setting.deprecated_in
        removed_in = setting.removed_in
        if not deprecated_in and not added_in:
            return
        package = setting.package
        if package not in self.project.frozen_requirements:
            return
        version = self.project.frozen_requirements[package]
        if added_in and version < added_in:
            detail = f"added in {package} {added_in}"
            yield Issue(
                29,
                "setting needs upgrade",
                detail=detail,
                node=resolved_node,
                column=column,
            )
            return
        assert deprecated_in
        if isinstance(deprecated_in, UnknownUnsupportedVersion):
            deprecated_in = PACKAGES[package].lowest_supported_version
            assert deprecated_in
            if version < deprecated_in:
                return
            detail = f"deprecated in {package} {deprecated_in} or lower"
        else:
            if version < deprecated_in:
                return
            detail = f"deprecated in {package} {deprecated_in}"
        if removed_in and version >= removed_in:
            detail += f", removed in {removed_in}"
            code, message = 30, "removed setting"
        else:
            code, message = 28, "deprecated setting"
        if setting.sunset_guidance:
            detail += f"; {setting.sunset_guidance}"
        yield Issue(
            code,
            message,
            detail=detail,
            node=resolved_node,
            column=column,
        )

    def check_dict(self, node: expr) -> Generator[Issue, None, None]:
        if not isinstance(node, (Call, Dict)):
            return
        if isinstance(node, Call):
            if not isinstance(node.func, Name) or node.func.id != "dict":
                return
            for keyword in node.keywords:
                yield from self.check_name(keyword)
            return
        assert isinstance(node, Dict)
        for key in node.keys:
            if isinstance(key, Constant):
                yield from self.check_name(key)

    def check_name(
        self,
        node: Constant
        | Name
        | keyword
        | ClassDef
        | FunctionDef
        | tuple[Import | ImportFrom, alias],
    ) -> Generator[Issue, None, None]:
        resolved_node: IssueNode
        name: Any
        if isinstance(node, tuple):
            resolved_node, import_alias = node
            name = import_alias.asname if import_alias.asname else import_alias.name
        else:
            resolved_node = node
            import_alias = None
            name = (
                resolved_node.value
                if isinstance(resolved_node, Constant)
                else resolved_node.id
                if isinstance(resolved_node, Name)
                else resolved_node.arg
                if isinstance(resolved_node, keyword)
                else resolved_node.name
            )
        if not isinstance(name, str):
            return  # Not a string, so not a setting name
        if isinstance(resolved_node, (Import, ImportFrom)):
            assert import_alias
            column = import_column(resolved_node, import_alias)
        elif isinstance(resolved_node, (ClassDef, FunctionDef)):
            column = definition_column(resolved_node)
        else:
            column = resolved_node.col_offset
        if not self.is_known_setting(name):
            detail = None
            if suggestions := self.suggest_names(name):
                detail = f"did you mean: {', '.join(suggestions)}?"
            yield Issue(
                27,
                "unknown setting",
                detail=detail,
                node=resolved_node,
                column=column,
            )
            return
        yield from self.check_known_name(name, resolved_node, column)


class SettingIssueFinder:
    NON_METHOD_SETTINGS_CALLABLES = ("BaseSettings", "Settings", "overridden_settings")

    def __init__(self, setting_checker: SettingChecker):
        self.setting_checker = setting_checker

    def find_issues(
        self, node: Call | Compare | Subscript
    ) -> Generator[Issue, None, None]:
        if isinstance(node, Call):
            yield from self.find_call_issues(node)
            return
        if isinstance(node, Subscript):
            yield from self.find_subscript_issues(node)
            return
        if isinstance(node, Compare):
            yield from self.find_compare_issues(node)
            return

    def find_call_issues(self, node: Call) -> Generator[Issue, None, None]:
        if self.looks_like_setting_method(node.func):
            if node.args:
                if isinstance(node.args[0], Constant):
                    yield from self.setting_checker.check_name(node.args[0])
                return
            for keyword in node.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, Constant):
                    yield from self.setting_checker.check_name(keyword.value)
                    return
            return

        if self.looks_like_settings_callable(node.func):
            if node.args:
                yield from self.setting_checker.check_dict(node.args[0])
                return
            for keyword in node.keywords:
                if keyword.arg in ("values", "settings"):
                    yield from self.setting_checker.check_dict(keyword.value)
                    return
            return

    def looks_like_setting_method(self, func: expr) -> bool:
        if not isinstance(func, Attribute):
            return False
        if not self.looks_like_settings_variable(func.value):
            return False
        return func.attr in (
            "__contains__",
            "__delitem__",
            "__getitem__",
            "__init__",
            "__setitem__",
            "add_to_list",
            "delete",
            "get",
            "getbool",
            "getint",
            "getfloat",
            "getlist",
            "getdict",
            "getdictorlist",
            "getpriority",
            "getwithbase",
            "pop",
            "remove_from_list",
            "replace_in_component_priority_dict",
            "set",
            "set_in_component_priority_dict",
            "setdefault",
            "setdefault_in_component_priority_dict",
        )

    def looks_like_settings_callable(self, func: expr) -> bool:
        if not isinstance(func, (Attribute, Name)):
            return False
        if isinstance(func, Name):
            return func.id in self.NON_METHOD_SETTINGS_CALLABLES
        assert isinstance(func, Attribute)
        return func.attr in self.NON_METHOD_SETTINGS_CALLABLES or (
            func.attr in ("setdict", "update")
            and self.looks_like_settings_variable(func.value)
        )

    def find_compare_issues(self, node: Compare) -> Generator[Issue, None, None]:
        if (
            node.ops
            and isinstance(node.ops[0], (In, NotIn))
            and isinstance(node.left, Constant)
            and self.looks_like_settings_variable(node.comparators[0])
        ):
            yield from self.setting_checker.check_name(node.left)

    def find_subscript_issues(self, node: Subscript) -> Generator[Issue, None, None]:
        if not self.looks_like_settings_variable(
            node.value
        ) or not self.looks_like_setting_constant(node.slice):
            return
        if isinstance(node.slice, Constant):
            yield from self.setting_checker.check_name(node.slice)

    def looks_like_settings_variable(self, value: expr) -> bool:
        while isinstance(value, Attribute):
            if value.attr == "settings":
                return True
            value = value.value
        return isinstance(value, Name) and value.id == "settings"

    def looks_like_setting_constant(self, value: expr) -> bool:
        return isinstance(value, Constant) and isinstance(value.value, str)


class SettingModuleIssueFinder(NodeVisitor):
    def __init__(self, context: Context, setting_checker: SettingChecker):
        super().__init__()
        self.context = context
        self.issues: list[Issue] = []
        self.setting_checker = setting_checker

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
            if isinstance(child, Assign):
                seen = self.check_assignment_redefinition(child, seen)
            elif isinstance(child, (ImportFrom, Import)):
                self.check_import_statement(child)

    def check_assignment_redefinition(
        self, node: Assign, seen: dict[str, LineNumber]
    ) -> dict[str, LineNumber]:
        for target in node.targets:
            if not (isinstance(target, Name) and target.id.isupper()):
                continue
            name = target.id
            if name in seen:
                self.issues.append(
                    Issue(
                        7,
                        "redefined setting",
                        detail=f"seen first at line {seen[name]}",
                        node=node,
                    )
                )
                continue
            seen[name] = node.lineno
        return seen

    def check_import_statement(self, node: Import | ImportFrom) -> None:
        for import_alias in node.names:
            name = import_alias.asname if import_alias.asname else import_alias.name
            if not (name and name.isupper()):
                continue
            self.issues.append(
                Issue(
                    12,
                    "imported setting",
                    node=node,
                    column=import_column(node, import_alias),
                )
            )
            for issue in self.setting_checker.check_name((node, import_alias)):
                self.issues.append(issue)

    def check_all_nodes_issues(self, node: Module) -> None:
        processor = SettingsModuleSettingsProcessor(self.context, self.setting_checker)
        for child in iter_nodes(node):
            if isinstance(child, Assign):
                processor.process_assignment(child)
            elif isinstance(child, (ClassDef, FunctionDef)):
                if not child.name.isupper():
                    continue
                self.issues.append(
                    Issue(
                        11,
                        "improper setting definition",
                        node=child,
                        column=definition_column(child),
                    )
                )
                for issue in self.setting_checker.check_name(child):
                    self.issues.append(issue)

        self.issues.extend(processor.get_issues())


class SettingsModuleSettingsProcessor:
    def __init__(self, context: Context, setting_checker: SettingChecker):
        self.context = context
        self.seen_settings: set[str] = set()
        self.autothrottle_enabled = False
        self.robotstxt_obey_values: list[tuple[bool, int, int]] = []
        self.redundant_values: list[tuple[int, int]] = []
        self.issues: list[Issue] = []
        self.setting_checker = setting_checker

    def process_assignment(self, assignment: Assign) -> None:
        for target in assignment.targets:
            if not (isinstance(target, Name) and target.id.isupper()):
                continue
            for issue in self.setting_checker.check_name(target):
                self.issues.append(issue)
            name = target.id
            self.seen_settings.add(name)
            self.process_setting(name, assignment)

    def process_setting(self, name: str, child: Assign) -> None:
        if name == "AUTOTHROTTLE_ENABLED":
            self.process_autothrottle(child)
        elif name == "ROBOTSTXT_OBEY":
            self.process_robotstxt(child)
        self.check_redundant_values(name, child)

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
        self.validate_redundant_values()
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

    def check_redundant_values(self, name: str, assignment: Assign) -> None:
        if name not in SETTINGS:
            return
        setting_info = SETTINGS[name]
        default_value = setting_info.get_default_value(self.context.project)
        if default_value is UNKNOWN_SETTING_VALUE:
            return
        setting_value, is_literal = extract_literal_value(assignment.value)
        if not is_literal:
            return
        try:
            parsed_value = setting_info.parse(setting_value)
        except (ValueError, TypeError):
            return
        if parsed_value == default_value:
            self.redundant_values.append(
                (assignment.value.lineno, assignment.value.col_offset)
            )

    def validate_redundant_values(self) -> None:
        for line, column in self.redundant_values:
            self.issues.append(
                Issue(17, "redundant setting value", line=line, column=column)
            )
