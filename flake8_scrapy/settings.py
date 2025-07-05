from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packaging.version import Version

    from flake8_scrapy.context import Project


class UnknownFutureVersion:
    pass


class UnknownSettingValue:
    pass


class UnknownUnsupportedVersion:
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
# Methods of the Settings class that get a setting name as parameter.
SETTING_METHODS = {
    "__contains__",
    "__delitem__",
    "__init__",
    "__setitem__",
    "add_to_list",
    "delete",
    *SETTING_GETTERS,
    "getpriority",
    "pop",
    "remove_from_list",
    "replace_in_component_priority_dict",
    "set",
    "set_in_component_priority_dict",
    "setdefault",
    "setdefault_in_component_priority_dict",
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
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    LIST = "list"
    DICT = "dict"
    DICT_OR_LIST = "dict_or_list"
    BASED_DICT = "based_dict"
    OPT_STR = "opt_str"
    STR = "str"
    CLS = "cls"
    PATH = "path"
    OPT_PATH = "opt_path"
    LOG_LEVEL = "log_level"
    ENUM_STR = "enum_str"
    PERIODIC_LOG_CONFIG = "periodic_log_config"
    OPT_CALLABLE = "opt_callable"
    OPT_INT = "opt_int"


# Missing types use the `get` method.
SETTING_TYPE_GETTERS = {
    SettingType.BOOL: "getbool",
    SettingType.INT: "getint",
    SettingType.FLOAT: "getfloat",
    SettingType.LIST: "getlist",
    SettingType.DICT: "getdict",
    SettingType.DICT_OR_LIST: "getdictorlist",
    SettingType.BASED_DICT: "getwithbase",
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
class Setting:
    added_in: Version | None = None
    deprecated_in: Version | UnknownUnsupportedVersion | None = None
    removed_in: Version | None = None
    type: SettingType | None = None
    package: str = "scrapy"
    values: tuple[Any, ...] | None = None
    sunset_guidance: str | None = None
    default_value: VersionedValue | UnknownSettingValue = field(
        default_factory=lambda: UNKNOWN_SETTING_VALUE
    )

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
        return value
