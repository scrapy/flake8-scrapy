from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packaging.version import Version

    from scrapy_lint.context import Project


class UnknownFutureVersion:  # pylint: disable=too-few-public-methods
    pass


class UnknownSettingValue:  # pylint: disable=too-few-public-methods
    pass


class UnknownUnsupportedVersion:  # pylint: disable=too-few-public-methods
    pass


UNKNOWN_FUTURE_VERSION = UnknownFutureVersion()
UNKNOWN_SETTING_VALUE = UnknownSettingValue()
UNKNOWN_UNSUPPORTED_VERSION = UnknownUnsupportedVersion()

# Methods of the Settings class that read a setting value.
SETTING_GETTERS = {
    "__getitem__",
    "get",
    "getbool",
    "getint",
    "getfloat",
    "getlist",
    "getdict",
    "getdictorlist",
    "getwithbase",
}
# Methods of the Settings class that set an entire setting value.
SETTING_SETTERS = {
    "__setitem__",
    "set",
    "setdefault",
}
# Methods of the Settings class that delete or change a setting value.
SETTING_UPDATERS = {
    *SETTING_SETTERS,
    "__delitem__",
    "add_to_list",
    "delete",
    "pop",
    "remove_from_list",
    "replace_in_component_priority_dict",
    "set_in_component_priority_dict",
    "setdefault_in_component_priority_dict",
}
# Methods of the Settings class that get a setting name as parameter.
SETTING_METHODS = {
    *SETTING_GETTERS,
    *SETTING_UPDATERS,
    "__contains__",
    "__init__",
    "getpriority",
}


# https://github.com/scrapy/scrapy/blob/2.13.2/scrapy/settings/__init__.py#L152-L180
def getbool(value: Any) -> bool:
    try:
        return bool(int(value))
    except ValueError:
        pass
    if value in ("True", "true"):
        return True
    if value in ("False", "false"):
        return False
    raise ValueError


class SettingType(Enum):
    BASED_COMP_PRIO_DICT = "based_comp_prio_dict"
    BOOL = "bool"
    COMP_PRIO_DICT = "comp_prio_dict"
    DICT = "dict"
    DICT_OR_LIST = "dict_or_list"
    ENUM_STR = "enum_str"
    FLOAT = "float"
    INT = "int"
    LIST = "list"
    LOG_LEVEL = "log_level"
    OPT_INT = "opt_int"
    OPT_PATH = "opt_path"
    OPT_STR = "opt_str"
    PERIODIC_LOG_CONFIG = "periodic_log_config"
    STR = "str"
    # OBJ stands for a Python object (e.g. class, function, module) or its
    # import path.
    OBJ = "obj"
    OPT_OBJ = "opt_obj"  # Can be None
    BASED_OBJ_DICT = "based_obj_dict"  # Values are objects, import paths or None


# Missing types use the `get` method.
SETTING_TYPE_GETTERS = {
    SettingType.BOOL: "getbool",
    SettingType.INT: "getint",
    SettingType.FLOAT: "getfloat",
    SettingType.LIST: "getlist",
    SettingType.DICT: "getdict",
    SettingType.COMP_PRIO_DICT: "getdict",
    SettingType.DICT_OR_LIST: "getdictorlist",
    SettingType.BASED_OBJ_DICT: "getwithbase",
    SettingType.BASED_COMP_PRIO_DICT: "getwithbase",
}
SETTING_UPDATER_TYPES = {
    "add_to_list": {SettingType.LIST},
    "remove_from_list": {SettingType.LIST},
    "replace_in_component_priority_dict": {
        SettingType.COMP_PRIO_DICT,
        SettingType.BASED_COMP_PRIO_DICT,
    },
    "set_in_component_priority_dict": {
        SettingType.COMP_PRIO_DICT,
        SettingType.BASED_COMP_PRIO_DICT,
    },
    "setdefault_in_component_priority_dict": {
        SettingType.COMP_PRIO_DICT,
        SettingType.BASED_COMP_PRIO_DICT,
    },
}


@dataclass
class VersionedValue:
    def __init__(
        self,
        value: Any = UNKNOWN_SETTING_VALUE,
        history: dict[Version | UnknownUnsupportedVersion | UnknownFutureVersion, Any]
        | None = None,
    ):
        self.all_time_value = value
        self.value_history = history or {}

    def __getitem__(self, version: Version) -> Any:
        if not self.value_history:
            return self.all_time_value
        applicable_versions = [
            v
            for v in self.value_history
            if not isinstance(v, UnknownUnsupportedVersion)
            and not isinstance(v, UnknownFutureVersion)
            and v <= version
        ]
        if not applicable_versions:
            assert UNKNOWN_UNSUPPORTED_VERSION in self.value_history
            return self.value_history[UNKNOWN_UNSUPPORTED_VERSION]
        latest_applicable = max(applicable_versions)
        return self.value_history[latest_applicable]


@dataclass
class Versioning:
    added_in: Version | None = None
    deprecated_in: Version | UnknownUnsupportedVersion | None = None
    removed_in: Version | None = None
    sunset_guidance: str | None = None


@dataclass
class Setting:
    name: str | None = None
    type: SettingType | None = None
    values: tuple[Any, ...] | None = None
    default_value: VersionedValue | UnknownSettingValue = field(
        default_factory=lambda: UNKNOWN_SETTING_VALUE,
    )
    is_pre_crawler: bool = False

    package: str = "scrapy"
    versioning: Versioning = field(default_factory=Versioning)

    @property
    def base(self) -> Setting:
        from scrapy_lint.data.settings import SETTINGS  # noqa: PLC0415

        return SETTINGS[f"{self.name}_BASE"]

    def get_default_value(self, project: Project) -> Any:
        if self.default_value is UNKNOWN_SETTING_VALUE:
            return UNKNOWN_SETTING_VALUE
        assert isinstance(self.default_value, VersionedValue)
        versioned_value = self.default_value
        if self.package not in project.frozen_requirements:
            return versioned_value.all_time_value
        version = project.frozen_requirements[self.package]
        return versioned_value[version]

    def parse(self, value: Any) -> Any:
        if self.type == SettingType.BOOL:
            return getbool(value)
        if self.type == SettingType.INT:
            return int(value)
        if self.type == SettingType.FLOAT:
            return float(value)
        if self.type == SettingType.STR:
            return str(value)
        if self.type in {
            SettingType.DICT,
            SettingType.BASED_OBJ_DICT,
            SettingType.COMP_PRIO_DICT,
            SettingType.BASED_COMP_PRIO_DICT,
        } and isinstance(value, str):
            return json.loads(value)
        return value
