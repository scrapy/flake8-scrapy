from __future__ import annotations

import ast
from ast import (
    AST,
    Assign,
    Attribute,
    Call,
    ClassDef,
    Compare,
    Constant,
    Del,
    Dict,
    FunctionDef,
    GeneratorExp,
    Import,
    ImportFrom,
    In,
    Lambda,
    Load,
    Module,
    Name,
    NodeVisitor,
    NotIn,
    Store,
    Subscript,
    alias,
    expr,
    keyword,
)
from ast import walk as iter_nodes
from contextlib import suppress
from difflib import SequenceMatcher
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from packaging.version import Version

from scrapy_lint.ast import (
    definition_column,
    extract_literal_value,
    import_column,
    is_dict,
    iter_dict,
)
from scrapy_lint.data.addons import ADDONS
from scrapy_lint.data.packages import PACKAGES
from scrapy_lint.data.settings import (
    MAX_AUTOMATIC_SUGGESTIONS,
    MIN_AUTOMATIC_SUGGESTION_SCORE,
    PREDEFINED_SUGGESTIONS,
    SETTINGS,
)
from scrapy_lint.issues import (
    BASE_SETTING_USE,
    DEPRECATED_SETTING,
    IMPORTED_SETTING,
    IMPROPER_SETTING_DEFINITION,
    INCOMPLETE_PROJECT_THROTTLING,
    LOW_PROJECT_THROTTLING,
    MISSING_CHANGING_SETTING,
    MISSING_SETTING_REQUIREMENT,
    NO_OP_SETTING_UPDATE,
    NO_PROJECT_USER_AGENT,
    NON_PICKLABLE_SETTING,
    REDEFINED_SETTING,
    REDUNDANT_SETTING_VALUE,
    REMOVED_SETTING,
    ROBOTS_TXT_IGNORED_BY_DEFAULT,
    SETTING_NEEDS_UPGRADE,
    UNKNOWN_SETTING,
    UNNEEDED_SETTING_GET,
    WRONG_SETTING_METHOD,
    ZYTE_RAW_PARAMS,
    Issue,
    Pos,
)
from scrapy_lint.settings import (
    MAX_DEFAULT_VALUE_HISTORY,
    SETTING_GETTERS,
    SETTING_METHODS,
    SETTING_SETTERS,
    SETTING_TYPE_GETTERS,
    SETTING_UPDATER_TYPES,
    SETTING_UPDATERS,
    UNKNOWN_SETTING_VALUE,
    Setting,
    UnknownSettingValue,
    getbool,
)
from scrapy_lint.utils import extend_sys_path
from scrapy_lint.versions import (
    UNKNOWN_FUTURE_VERSION,
    UNKNOWN_UNSUPPORTED_VERSION,
    UnknownUnsupportedVersion,
)

from .types import TYPE_CHECKERS
from .values import VALUE_CHECKERS

if TYPE_CHECKING:
    from collections.abc import Generator

    from scrapy_lint.context import Context

LineNumber = int
IssueNode = Union[Constant, Name, keyword, ClassDef, FunctionDef, Import, ImportFrom]


class SettingChecker:
    def __init__(self, context: Context) -> None:
        self.context = context
        self.project = context.project
        self.additional_known_settings = set(context.options.get("known-settings", []))
        self.in_update_pre_crawler_settings = False
        self.in_update_settings = False

    def is_known_setting(self, name: str) -> bool:
        return name in SETTINGS or name in self.additional_known_settings

    def is_supported_setting(self, name: str) -> bool:
        if not self.project.packages or name not in SETTINGS:
            return True
        setting = SETTINGS[name]
        if setting.package not in self.project.frozen_requirements or (
            not setting.versioning.added_in and not setting.versioning.deprecated_in
        ):
            return setting.package in self.project.packages
        deprecated_in = setting.versioning.deprecated_in
        if isinstance(deprecated_in, UnknownUnsupportedVersion):
            deprecated_in = PACKAGES[setting.package].lowest_supported_version
            assert deprecated_in
        package_version = self.project.frozen_requirements[setting.package]
        return (
            not setting.versioning.added_in
            or package_version >= setting.versioning.added_in
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

    def check_known_name(self, name: str, pos: Pos) -> Generator[Issue]:
        yield from self.check_special_names(name, pos)
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        package = setting.package
        yield from self.check_setting_requirement(setting, pos)
        if package not in self.project.frozen_requirements:
            return
        yield from self.check_setting_versioning(setting, pos)

    def check_special_names(self, name: str, pos: Pos) -> Generator[Issue]:
        if name.endswith("_BASE"):
            yield Issue(BASE_SETTING_USE, pos)
        elif name == "ZYTE_API_DEFAULT_PARAMS":
            yield Issue(ZYTE_RAW_PARAMS, pos)

    def check_setting_requirement(self, setting, pos: Pos) -> Generator[Issue]:
        package = setting.package
        if (
            package not in self.project.frozen_requirements
            and self.project.packages
            and package not in self.project.packages
        ):
            yield Issue(MISSING_SETTING_REQUIREMENT, pos, package)

    def check_setting_versioning(self, setting, pos: Pos) -> Generator[Issue]:
        package = setting.package
        added_in = setting.versioning.added_in
        deprecated_in = setting.versioning.deprecated_in
        removed_in = setting.versioning.removed_in
        if not deprecated_in and not added_in:
            return
        version = self.project.frozen_requirements[package]
        if added_in and version < added_in:
            yield Issue(SETTING_NEEDS_UPGRADE, pos, f"added in {package} {added_in}")
            return
        if not deprecated_in:
            return
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
            issue = REMOVED_SETTING
        else:
            issue = DEPRECATED_SETTING
        if setting.versioning.sunset_guidance:
            detail += f"; {setting.versioning.sunset_guidance}"
        yield Issue(issue, pos, detail)

    def check_dict(self, node: expr) -> Generator[Issue]:
        if not is_dict(node):
            return
        assert isinstance(node, (Call, Dict))
        for key, value in iter_dict(node):
            if not isinstance(key, Constant):
                continue
            yield from self.check_name(key)
            yield from self.check_update(key)
            if isinstance(key.value, str):
                yield from self.check_value(key.value, value)

    def check_name(
        self,
        node: Constant
        | Name
        | keyword
        | ClassDef
        | FunctionDef
        | tuple[Import | ImportFrom, alias],
    ) -> Generator[Issue]:
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
        pos = Pos.from_node(resolved_node, column)
        if not self.is_known_setting(name):
            detail = None
            if suggestions := self.suggest_names(name):
                detail = f"did you mean: {', '.join(suggestions)}?"
            yield Issue(UNKNOWN_SETTING, pos, detail)
            return
        yield from self.check_known_name(name, pos)

    def check_update(self, node: keyword | Constant) -> Generator[Issue]:
        name = node.value if isinstance(node, Constant) else node.arg
        if not isinstance(name, str) or name not in SETTINGS:
            return
        setting = SETTINGS[name]
        if setting.is_pre_crawler and not self.in_update_pre_crawler_settings:
            yield Issue(NO_OP_SETTING_UPDATE, Pos.from_node(node))

    def check_method(self, name_node: Constant, call: Call) -> Generator[Issue]:
        func = call.func
        assert isinstance(func, Attribute)
        name = name_node.value
        assert isinstance(name, str)
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        name_pos = Pos.from_node(name_node)
        if (
            func.attr in SETTING_UPDATERS
            and setting.is_pre_crawler
            and not self.in_update_pre_crawler_settings
        ):
            yield Issue(NO_OP_SETTING_UPDATE, name_pos)
        yield from self.check_wrong_setting_method(setting, call, name_pos)

    def check_wrong_setting_method(
        self,
        setting: Setting,
        call: Call,
        name_pos: Pos,
    ) -> Generator[Issue]:
        func = call.func
        assert isinstance(func, Attribute)
        if (
            setting.type is not None
            and func.attr in SETTING_UPDATER_TYPES
            and setting.type not in SETTING_UPDATER_TYPES[func.attr]
        ):
            yield Issue(WRONG_SETTING_METHOD, name_pos)
        if func.attr not in SETTING_GETTERS or setting.type is None:
            return
        assert func.end_col_offset is not None
        column = func.end_col_offset - len(func.attr)
        pos = Pos.from_node(func, column)
        if setting.type in SETTING_TYPE_GETTERS:
            expected = SETTING_TYPE_GETTERS[setting.type]
            if func.attr != expected and (
                expected != "getwithbase" or not self.in_update_settings
            ):
                yield Issue(WRONG_SETTING_METHOD, pos, f"use {expected}()")
        elif func.attr not in {"get", "__getitem__"}:
            has_default = False
            if len(call.args) > 1:
                has_default = True
            else:
                for kw in call.keywords:
                    if kw.arg == "default":
                        has_default = True
                        break
            if has_default:
                yield Issue(WRONG_SETTING_METHOD, pos, "use get()")
            else:
                yield Issue(WRONG_SETTING_METHOD, pos, "use []")

    def check_subscript(self, name: str, node: Subscript) -> Generator[Issue]:
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        if (
            isinstance(node.ctx, Load)
            and setting.type is not None
            and setting.type in SETTING_TYPE_GETTERS
            and (
                SETTING_TYPE_GETTERS[setting.type] != "getwithbase"
                or not self.in_update_settings
            )
        ):
            assert isinstance(node.value, Name)
            column = node.value.col_offset + len(node.value.id)
            expected = SETTING_TYPE_GETTERS[setting.type]
            pos = Pos.from_node(node, column)
            yield Issue(WRONG_SETTING_METHOD, pos, f"use {expected}()")
        if (
            isinstance(node.ctx, (Store, Del))
            and setting.is_pre_crawler
            and not self.in_update_pre_crawler_settings
        ):
            column = getattr(node.slice, "col_offset", node.col_offset + 1)
            yield Issue(NO_OP_SETTING_UPDATE, Pos.from_node(node, column))

    def is_materializer_call(self, parent):
        if not isinstance(parent, Call):
            return False
        func = parent.func
        return isinstance(func, Name) and func.id in {"list", "tuple", "set"}

    def check_non_picklable(self, node, parent=None):
        if isinstance(node, Lambda) or (
            isinstance(node, GeneratorExp) and not self.is_materializer_call(parent)
        ):
            yield Issue(NON_PICKLABLE_SETTING, Pos.from_node(node))
        for child in ast.iter_child_nodes(node):
            yield from self.check_non_picklable(child, node)

    def check_value(self, name: str, node: expr) -> Generator[Issue]:
        if name in VALUE_CHECKERS:
            yield from VALUE_CHECKERS[name](node, context=self.context)

        yield from self.check_non_picklable(node)

        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        if setting.type is not None:
            yield from TYPE_CHECKERS[setting.type](
                node,
                setting=setting,
                project=self.project,
            )


class SettingIssueFinder:
    NON_METHOD_SETTINGS_CALLABLES = ("BaseSettings", "Settings", "overridden_settings")

    def __init__(self, setting_checker: SettingChecker):
        self.setting_checker = setting_checker

    def __call__(
        self,
        node: AST,
    ) -> Generator[Issue]:
        if isinstance(node, Call):
            yield from self.find_call_issues(node)
            return
        if isinstance(node, Assign):
            yield from self.find_assign_issues(node)
            return
        if isinstance(node, Subscript):
            yield from self.find_subscript_issues(node)
            return
        if isinstance(node, Compare):
            yield from self.find_compare_issues(node)
            return
        if isinstance(node, FunctionDef):
            if node.name == "update_pre_crawler_settings":
                self.setting_checker.in_update_pre_crawler_settings = True
            elif node.name == "update_settings":
                self.setting_checker.in_update_settings = True
            return

    def post_visit(self, node: Call | Compare | FunctionDef | Subscript) -> None:
        if isinstance(node, FunctionDef):
            if node.name == "update_pre_crawler_settings":
                self.setting_checker.in_update_pre_crawler_settings = False
            elif node.name == "update_settings":
                self.setting_checker.in_update_settings = False

    def find_call_issues(self, node: Call) -> Generator[Issue]:
        if self.looks_like_setting_method(node.func):
            yield from self.check_method_call(node)
            return

        if self.looks_like_settings_callable(node.func):
            yield from self.check_settings_callable(node)
            return

    def check_method_call(self, node: Call) -> Generator[Issue]:
        """Handle issues for calls that look like setting methods."""
        default_arg_index = 1
        assert isinstance(node.func, Attribute)
        name: Constant | None = None
        value_or_default: expr | None = None
        if node.args and isinstance(node.args[0], Constant):
            name = node.args[0]
        if len(node.args) >= (default_arg_index + 1):
            value_or_default = node.args[default_arg_index]
        else:
            for kw in node.keywords:
                if not node.args and kw.arg == "name":
                    if not isinstance(kw.value, Constant):
                        return
                    name = kw.value
                elif kw.arg in {"value", "default"}:
                    value_or_default = kw.value
        if not name:
            return
        yield from self.setting_checker.check_name(name)
        yield from self.setting_checker.check_method(name, node)
        if node.func.attr in SETTING_SETTERS:
            if isinstance(name.value, str) and value_or_default:
                yield from self.setting_checker.check_value(
                    name.value,
                    value_or_default,
                )
        elif node.func.attr == "get" and (
            value_or_default is None
            or (
                isinstance(value_or_default, Constant)
                and value_or_default.value is None
            )
        ):
            assert isinstance(node.func.value.end_lineno, int)
            assert isinstance(node.func.value.end_col_offset, int)
            pos = Pos(
                node.func.value.end_lineno,
                node.func.value.end_col_offset + 1,
            )
            yield Issue(UNNEEDED_SETTING_GET, pos)

    def check_settings_callable(self, node: Call) -> Generator[Issue]:
        """Handle issues for calls that look like settings callables."""
        if node.args:
            yield from self.setting_checker.check_dict(node.args[0])
            return
        for kw in node.keywords:
            if kw.arg in ("values", "settings"):
                yield from self.setting_checker.check_dict(kw.value)
                return

    def find_assign_issues(self, node: Assign) -> Generator[Issue]:
        for target in node.targets:
            if (
                isinstance(target, Subscript)
                and self.looks_like_settings_variable(target.value)
                and self.looks_like_setting_constant(target.slice)
            ):
                assert isinstance(target.slice, Constant)
                assert isinstance(target.slice.value, str)
                yield from self.setting_checker.check_value(
                    target.slice.value,
                    node.value,
                )

    def looks_like_setting_method(self, func: expr) -> bool:
        if not isinstance(func, Attribute):
            return False
        if not self.looks_like_settings_variable(func.value):
            return False
        return func.attr in SETTING_METHODS

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

    def find_compare_issues(self, node: Compare) -> Generator[Issue]:
        if (
            node.ops
            and isinstance(node.ops[0], (In, NotIn))
            and isinstance(node.left, Constant)
            and self.looks_like_settings_variable(node.comparators[0])
        ):
            yield from self.setting_checker.check_name(node.left)

    def find_subscript_issues(self, node: Subscript) -> Generator[Issue]:
        if not self.looks_like_settings_variable(
            node.value,
        ) or not self.looks_like_setting_constant(node.slice):
            return
        if isinstance(node.slice, Constant) and isinstance(node.slice.value, str):
            yield from self.setting_checker.check_name(node.slice)
            yield from self.setting_checker.check_subscript(node.slice.value, node)

    def looks_like_settings_variable(self, value: expr) -> bool:
        while isinstance(value, Attribute):
            if value.attr == "settings":
                return True
            value = value.value
        return isinstance(value, Name) and value.id == "settings"

    def looks_like_setting_constant(self, value: expr) -> bool:
        return isinstance(value, Constant) and isinstance(value.value, str)


class SettingModuleIssueFinder(NodeVisitor):
    def __init__(self, context: Context, file: Path, setting_checker: SettingChecker):
        super().__init__()
        self.context = context
        self.file = file.absolute()
        self.issues: list[Issue] = []
        self.setting_checker = setting_checker

    def in_setting_module(self) -> bool:
        for import_path in self.context.project.setting_module_import_paths:
            assert self.context.project.root is not None
            with extend_sys_path(self.context.project.root):
                spec = find_spec(import_path)
            if not spec or not spec.origin:
                continue
            module_path = Path(spec.origin).absolute()
            if module_path == self.file:
                return True
        return False

    def check(self, tree: Module) -> Generator[Issue]:
        self.visit(tree)
        yield from self.issues

    def visit_Module(self, node: Module) -> None:  # pylint: disable=invalid-name
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
        self,
        node: Assign,
        seen: dict[str, LineNumber],
    ) -> dict[str, LineNumber]:
        for target in node.targets:
            if not (isinstance(target, Name) and target.id.isupper()):
                continue
            name = target.id
            pos = Pos.from_node(node)
            if name in seen:
                detail = f"seen first at line {seen[name]}"
                self.issues.append(Issue(REDEFINED_SETTING, pos, detail))
                continue
            seen[name] = pos.line
        return seen

    def check_import_statement(self, node: Import | ImportFrom) -> None:
        for import_alias in node.names:
            name = import_alias.asname if import_alias.asname else import_alias.name
            if not (name and name.isupper()):
                continue
            pos = Pos.from_node(node, import_column(node, import_alias))
            self.issues.append(Issue(IMPORTED_SETTING, pos))
            for issue in self.setting_checker.check_name((node, import_alias)):
                self.issues.append(issue)

    def check_all_nodes_issues(self, node: Module) -> None:
        processor = SettingsModuleSettingsProcessor(self.context, self.setting_checker)
        for child in iter_nodes(node):
            if isinstance(child, Assign):
                issue_generator = processor.process_assignment(child)
                self.issues.extend(issue_generator)
            elif isinstance(child, (ClassDef, FunctionDef)):
                if not child.name.isupper():
                    continue
                pos = Pos.from_node(child, definition_column(child))
                self.issues.append(Issue(IMPROPER_SETTING_DEFINITION, pos))
                issue_generator = self.setting_checker.check_name(child)
                self.issues.extend(issue_generator)
            elif isinstance(child, (Import, ImportFrom)):
                processor.process_import(child)
        self.issues.extend(processor.iter_issues())


class SettingsModuleSettingsProcessor:
    def __init__(self, context: Context, setting_checker: SettingChecker):
        self.context = context
        self.seen_settings: set[str] = set()
        self.robotstxt_obey_values: list[tuple[bool, int, int]] = []
        self.redundant_values: list[tuple[str, int, int]] = []
        self.setting_checker = setting_checker
        self.imports: dict[str, str] = {}
        self.addon_settings: set[str] = set()

    def process_assignment(self, assignment: Assign) -> Generator[Issue]:
        for target in assignment.targets:
            if not (isinstance(target, Name) and target.id.isupper()):
                continue
            yield from self.setting_checker.check_name(target)
            name = target.id
            self.seen_settings.add(name)
            if name == "ADDONS":
                self.process_addons(assignment)
            yield from self.process_setting(name, assignment)

    def resolve_import_path(self, node) -> str:
        """Recursively resolve the import path for a Name or Attribute node, using self.imports for base names."""
        if isinstance(node, Name):
            return self.imports.get(node.id, node.id)
        assert isinstance(node, Attribute)
        base = self.resolve_import_path(node.value)
        return f"{base}.{node.attr}"

    def process_addons(self, assignment: Assign) -> None:
        if not is_dict(assignment.value):
            return
        assert isinstance(assignment.value, (Call, Dict))
        for key, _ in iter_dict(assignment.value):
            import_path = None
            if (
                isinstance(key, Name)
                and key.id in self.imports
                and self.imports[key.id] in ADDONS
            ):
                import_path = self.imports[key.id]
            elif isinstance(key, Constant) and isinstance(key.value, str):
                import_path = key.value
            elif isinstance(key, Attribute):
                import_path = self.resolve_import_path(key)
            if import_path not in ADDONS:
                continue
            addon_settings = ADDONS[import_path].get_settings(self.context.project)
            self.addon_settings |= addon_settings

    def process_setting(self, name: str, assignment: Assign) -> Generator[Issue]:
        if name == "ROBOTSTXT_OBEY":
            self.process_robotstxt(assignment)
        self.check_redundant_values(name, assignment)
        yield from self.check_throttling(name, assignment)
        yield from self.setting_checker.check_value(name, assignment.value)

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
                (name, assignment.value.lineno, assignment.value.col_offset),
            )

    def check_throttling(self, name: str, assignment: Assign) -> Generator[Issue]:
        if name not in {"CONCURRENT_REQUESTS_PER_DOMAIN", "DOWNLOAD_DELAY"}:
            return
        if not isinstance(assignment.value, Constant):
            return
        value = assignment.value.value
        if not isinstance(value, (int, float)):
            return
        if (name == "CONCURRENT_REQUESTS_PER_DOMAIN" and value > 1) or (
            name == "DOWNLOAD_DELAY" and value < 1.0
        ):
            pos = Pos.from_node(assignment.value)
            yield Issue(LOW_PROJECT_THROTTLING, pos)

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

    def iter_issues(self) -> Generator[Issue]:
        yield from self.validate_user_agent()
        yield from self.validate_robotstxt()
        yield from self.validate_throttling()
        yield from self.validate_missing_changing_settings()
        yield from self.validate_redundant_values()

    def validate_user_agent(self) -> Generator[Issue]:
        if "USER_AGENT" not in self.seen_settings:
            yield Issue(NO_PROJECT_USER_AGENT)

    def validate_robotstxt(self) -> Generator[Issue]:
        if not self.robotstxt_obey_values:
            yield Issue(ROBOTS_TXT_IGNORED_BY_DEFAULT)
        elif all(not value for value, *_ in self.robotstxt_obey_values):
            _, line, column = self.robotstxt_obey_values[0]
            yield Issue(ROBOTS_TXT_IGNORED_BY_DEFAULT, Pos(line, column))

    def validate_throttling(self) -> Generator[Issue]:
        if not all(
            setting in self.seen_settings
            for setting in (
                "CONCURRENT_REQUESTS_PER_DOMAIN",
                "DOWNLOAD_DELAY",
            )
        ):
            yield Issue(INCOMPLETE_PROJECT_THROTTLING)

    def validate_missing_changing_settings(self) -> Generator[Issue]:
        for name, setting in SETTINGS.items():
            if (
                name in self.seen_settings
                or name.endswith("_BASE")
                or name in self.addon_settings
            ):
                continue
            default = setting.default_value
            if isinstance(default, UnknownSettingValue):
                continue
            if not default or not default.history:
                continue
            history = default.history
            assert len(history) == MAX_DEFAULT_VALUE_HISTORY
            assert UNKNOWN_UNSUPPORTED_VERSION in history
            old_value = history[UNKNOWN_UNSUPPORTED_VERSION]
            if UNKNOWN_FUTURE_VERSION in history:
                new_value = history[UNKNOWN_FUTURE_VERSION]
                detail = (
                    f"{name} changes from {old_value!r} to {new_value!r} in a "
                    f"future version of {setting.package}"
                )
                issue = Issue(MISSING_CHANGING_SETTING, detail=detail)
                yield issue
                continue
            requirements = self.context.project.frozen_requirements
            if not requirements or setting.package not in requirements:
                continue
            project_version = requirements[setting.package]
            change_version, new_value = next(iter(history.items()))  # pylint: disable=stop-iteration-return
            assert isinstance(change_version, Version)
            if project_version >= change_version:
                continue
            detail = (
                f"{name} changes from {old_value!r} to {new_value!r} in "
                f"{setting.package} {change_version}"
            )
            issue = Issue(MISSING_CHANGING_SETTING, detail=detail)
            yield issue

    def validate_redundant_values(self) -> Generator[Issue]:
        for name, line, column in self.redundant_values:
            if self.is_changing_setting(name):
                continue
            yield Issue(REDUNDANT_SETTING_VALUE, Pos(line, column))

    def is_changing_setting(self, name: str) -> bool:
        assert name in SETTINGS
        setting = SETTINGS[name]
        default = setting.default_value
        assert not isinstance(default, UnknownSettingValue)
        if not default or not default.history:
            return False
        history = default.history
        assert len(history) == MAX_DEFAULT_VALUE_HISTORY
        assert UNKNOWN_UNSUPPORTED_VERSION in history
        assert UNKNOWN_FUTURE_VERSION not in history
        requirements = self.context.project.frozen_requirements
        assert setting.package in requirements
        project_version = requirements[setting.package]
        change_version = next(
            iter(k for k in history if k != UNKNOWN_UNSUPPORTED_VERSION),
        )
        assert isinstance(change_version, Version)
        return project_version < change_version

    def process_import(self, node: Import | ImportFrom) -> None:
        if isinstance(node, Import):
            for import_alias in node.names:
                name = import_alias.asname if import_alias.asname else import_alias.name
                self.imports[name] = import_alias.name
        elif isinstance(node, ImportFrom):
            for import_alias in node.names:
                name = import_alias.asname if import_alias.asname else import_alias.name
                self.imports[name] = f"{node.module}.{import_alias.name}"
