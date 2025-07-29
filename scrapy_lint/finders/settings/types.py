from __future__ import annotations

import json
import re
from ast import Call, Constant, Dict, Lambda, List, Set, Tuple, expr
from collections.abc import Generator, Iterable
from functools import partial
from typing import TYPE_CHECKING, Protocol

from packaging.version import Version

from scrapy_lint.ast import is_dict, iter_dict
from scrapy_lint.issues import (
    INVALID_SETTING_VALUE,
    UNNEEDED_IMPORT_PATH,
    UNNEEDED_PATH_STRING,
    UNSUPPORTED_PATH_OBJECT,
    Issue,
    Pos,
)
from scrapy_lint.settings import (
    UNKNOWN_SETTING_VALUE,
    UNKNOWN_UNSUPPORTED_VERSION,
    Setting,
    SettingType,
    UnknownUnsupportedVersion,
)

if TYPE_CHECKING:
    from scrapy_lint.context import Project


def check_import_path_need(
    node: Constant,
    project: Project,
    allowed: set[str] | None = None,
) -> Generator[Issue]:
    frozen_version = project.frozen_requirements.get("scrapy")
    if not frozen_version or frozen_version < Version("2.4.0"):
        return
    allowed = allowed or set()
    if node.value not in allowed:
        yield Issue(UNNEEDED_IMPORT_PATH, Pos.from_node(node))


def has_feed_uri_params(value: str) -> bool:
    return bool(re.search(r"%\([^)]+\)[sdifouxXeEgGcr]", value))


def is_import_path(value: str, **_) -> bool:
    if not value:
        return False
    parts = value.split(".")
    return bool(parts and all(part.isidentifier() for part in parts) and len(parts) > 1)


def is_path_obj(node: Call) -> bool:
    return getattr(node.func, "id", None) in {
        "Path",
        "PurePath",
        "PurePosixPath",
        "PureWindowsPath",
        "PosixPath",
        "WindowsPath",
    }


def is_getbool_compatible(node: expr, **_) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    return node.value in {
        True,
        "1",
        "True",
        "true",
        False,
        "0",
        "False",
        "false",
        None,
    }


def is_getint_compatible(node: expr, **_) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    try:
        int(node.value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return True


def is_getfloat_compatible(node: expr, **_) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    try:
        float(node.value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return True


def is_getlist_compatible(node: expr, **_) -> bool:
    if not isinstance(node, Constant):
        return True
    value = node.value
    if not value:
        return True
    if isinstance(value, (bytes, bytearray)):
        return False
    return isinstance(value, Iterable)


def check_getdict_compatible(node: expr, **_) -> Generator[Issue]:
    if isinstance(node, Lambda):
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node), "must be a dict")
        return
    if not isinstance(node, Constant) or node.value is None:
        return
    value = node.value
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as e:
            detail = f"invalid JSON: {e}"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node), detail)
            return
    try:
        dict(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        detail = f"must be a dict, not {type(value).__name__} ({value!r})"
        if isinstance(node.value, str):
            detail = f"invalid JSON: {detail}"
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node), detail)


def check_getwithbase_compatible(node: expr) -> Generator[Issue]:
    # All callers already handle Dict nodes.
    # If we ever handle dict here, we should also check that keys are strings.
    if not isinstance(node, Constant) or node.value is None:
        return
    if not isinstance(node.value, str):
        detail = f"must be a dict, not {type(node.value).__name__}"
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node), detail)
        return
    try:
        data = json.loads(node.value)
    except ValueError as e:
        detail = f"invalid JSON: {e}"
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node), detail)
        return
    if not isinstance(data, dict):
        detail = f"invalid JSON: must be a dict, not {type(data).__name__} ({data!r})"
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node), detail)


def is_getdictorlist_compatible(node: expr, **_) -> bool:
    if not isinstance(node, Constant):
        return True
    value = node.value
    return value is None or isinstance(value, str)


def is_opt_str(node: expr, **_) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    value = node.value
    return value is None or isinstance(value, str)


def is_str(node: expr, **_) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    return isinstance(node.value, str)


def is_log_level(node: expr, **_) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    value = node.value
    if isinstance(value, int):
        return True
    if not isinstance(value, str):
        return False
    return value in {
        "CRITICAL",
        "FATAL",
        "ERROR",
        "WARNING",
        "WARN",
        "INFO",
        "DEBUG",
        "NOTSET",
        "critical",
        "fatal",
        "error",
        "warning",
        "warn",
        "info",
        "debug",
        "notset",
    }


def is_enum_str(node: expr, setting: Setting, **_) -> bool:
    assert setting.values
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    return node.value in setting.values


def is_opt_int(node: expr, **kwargs) -> bool:
    if isinstance(node, Constant) and node.value is None:
        return True
    return is_getint_compatible(node, **kwargs)


class IsTypeFunction(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(self, node: expr, *, setting: Setting) -> bool: ...


class TypeChecker(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(
        self,
        node: expr,
        *,
        setting: Setting,
        project: Project,
    ) -> Generator[Issue]: ...


def check_type(is_type: IsTypeFunction) -> TypeChecker:
    def wrapper(node: expr, *, setting: Setting, **_) -> Generator[Issue]:
        if not is_type(node, setting=setting):
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node))

    return wrapper


def check_import_path(node: Constant, project: Project) -> Generator[Issue]:
    if not isinstance(node.value, str):
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node))
        return
    if not is_import_path(node.value):
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node))
        return
    yield from check_import_path_need(node, project)


def check_based_comp_prio(
    node: expr,
    *,
    setting: Setting,
    project: Project,
    **_,
) -> Generator[Issue]:
    yield from check_getwithbase_compatible(node)
    if not is_dict(node):
        return
    assert isinstance(node, (Call, Dict))
    for key, value in iter_dict(node):
        if isinstance(key, Constant):
            if not isinstance(key.value, str):
                detail = f"keys must be strings, not {type(key.value).__name__} ({key.value!r})"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
            elif not is_import_path(key.value):
                detail = f"{key.value!r} does not look like an import path"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
            else:
                default_value = setting.base.get_default_value(project)
                if default_value is not UNKNOWN_SETTING_VALUE:
                    base_import_paths = set(default_value.keys())
                    yield from check_import_path_need(key, project, base_import_paths)
        if isinstance(value, (Dict, Lambda, List, Set, Tuple)):
            detail = "dict values must be integers or None"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)
        elif (
            isinstance(value, Constant)
            and value.value is not None
            and not isinstance(value.value, int)
        ):
            detail = f"dict values must be integers or None, not {type(value.value).__name__} ({value.value!r})"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)


def check_based_obj_dict(node: expr, *, project: Project, **_) -> Generator[Issue]:
    yield from check_getwithbase_compatible(node)
    if not is_dict(node):
        return
    assert isinstance(node, (Call, Dict))
    for key, value in iter_dict(node):
        if isinstance(key, Constant) and not isinstance(key.value, str):
            detail = (
                f"keys must be strings, not {type(key.value).__name__} ({key.value!r})"
            )
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
        if isinstance(value, Constant) and value.value is not None:
            if not isinstance(value.value, str):
                detail = (
                    f"values must be Python objects or their import paths as strings, not "
                    f"{type(value.value).__name__} ({value.value!r})"
                )
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)
            elif not is_import_path(value.value):
                detail = f"{value.value!r} does not look like an import path"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)
            else:
                yield from check_import_path_need(value, project)


def check_comp_prio(node: expr, project: Project, **_) -> Generator[Issue]:
    yield from check_getdict_compatible(node)
    if not is_dict(node):
        return
    assert isinstance(node, (Call, Dict))
    for key, value in iter_dict(node):
        if isinstance(key, Constant):
            component = key.value
            if not isinstance(component, str):
                detail = f"keys must be components, not {type(component).__name__} ({component!r})"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
            elif not is_import_path(component):
                detail = f"{component!r} does not look like an import path"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
            else:
                yield from check_import_path_need(key, project)
        if isinstance(value, (Dict, Lambda, List, Set, Tuple)):
            detail = "dict values must be integers"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)
        elif isinstance(value, Constant) and not isinstance(value.value, int):
            detail = f"dict values must be integers, not {type(value.value).__name__} ({value.value!r})"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)


def check_obj(
    node: expr,
    *,
    allow_none: bool = False,
    project: Project,
    **_,
) -> Generator[Issue]:
    issue = Issue(INVALID_SETTING_VALUE, Pos.from_node(node))
    if is_dict(node) or isinstance(node, (List, Set, Tuple)):
        yield issue
        return
    if not isinstance(node, Constant):
        return
    if node.value is None:
        if not allow_none:
            yield issue
        return
    yield from check_import_path(node, project)


PATH_SUPPORT_VERSIONS: dict[str, Version | UnknownUnsupportedVersion] = {
    "FEED_TEMPDIR": Version("2.8.0"),
    "FILES_STORE": Version("2.9.0"),
    "HTTPCACHE_DIR": Version("2.8.0"),
    "IMAGES_STORE": Version("2.9.0"),
    "JOBDIR": Version("2.8.0"),
    "LOG_FILE": UNKNOWN_UNSUPPORTED_VERSION,
    "TEMPLATES_DIR": Version("2.8.0"),
}


def check_opt_path(
    node: expr,
    *,
    setting: Setting,
    project: Project,
    **_,
) -> Generator[Issue]:
    pos = Pos.from_node(node)
    invalid = Issue(INVALID_SETTING_VALUE, pos)
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        yield invalid
        return
    if isinstance(node, Call):
        if not is_path_obj(node):
            return
        is_path_obj_ = True
    elif isinstance(node, Constant):
        if node.value is None:
            return
        if not isinstance(node.value, str):
            yield invalid
            return
        is_path_obj_ = False
    else:
        return
    version = project.frozen_requirements.get(setting.package)
    assert setting.name in PATH_SUPPORT_VERSIONS
    path_support_version = PATH_SUPPORT_VERSIONS[setting.name]
    if isinstance(path_support_version, UnknownUnsupportedVersion):
        supports_path_obj = True
    elif version is None:
        return
    else:
        supports_path_obj = version >= path_support_version
    if is_path_obj_ and not supports_path_obj:
        detail = f"requires Scrapy {path_support_version}+"
        yield Issue(UNSUPPORTED_PATH_OBJECT, pos, detail)
    elif not is_path_obj_ and supports_path_obj:
        yield Issue(UNNEEDED_PATH_STRING, pos)


def check_periodic_log_config_key(key) -> str | None:
    if not isinstance(key.value, str):
        return f"keys must be 'include' or 'exclude', not {type(key.value).__name__} ({key.value!r})"
    if key.value not in {"include", "exclude"}:
        return f"keys must be 'include' or 'exclude', not {key.value!r}"
    return None


def check_periodic_log_config_value(value) -> str | None:
    if isinstance(value, (Constant, Dict, Lambda)):
        return "dict values must be lists of stat name substrings"
    return None


def check_periodic_log_config_item(item) -> str | None:
    if isinstance(item, (Dict, Lambda, List, Set, Tuple)):
        return "include/exclude list items must be strings"
    if not isinstance(item, Constant):
        return None
    if not isinstance(item.value, str):
        return "include/exclude list items must be strings"
    return None


def check_periodic_log_config(node: expr, **_) -> Generator[Issue]:
    detail = "must be True or a dict"
    issue = Issue(INVALID_SETTING_VALUE, Pos.from_node(node), detail)
    if isinstance(node, (Lambda, List, Set, Tuple)):
        yield issue
        return
    if isinstance(node, Constant):
        if node.value is not None and node.value is not True:
            yield issue
        return
    if not is_dict(node):
        return
    assert isinstance(node, (Call, Dict))
    for key, value in iter_dict(node):
        if isinstance(key, Constant):
            key_detail = check_periodic_log_config_key(key)
            if key_detail:
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), key_detail)
        value_detail = check_periodic_log_config_value(value)
        if value_detail:
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), value_detail)
            continue
        if not isinstance(value, (List, Set, Tuple)):
            continue
        for item in value.elts:
            item_detail = check_periodic_log_config_item(item)
            if item_detail:
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(item), item_detail)


TYPE_CHECKERS: dict[SettingType, TypeChecker] = {
    **{
        setting_type: check_type(is_type)
        for setting_type, is_type in (
            (SettingType.BOOL, is_getbool_compatible),
            (SettingType.DICT_OR_LIST, is_getdictorlist_compatible),
            (SettingType.ENUM_STR, is_enum_str),
            (SettingType.FLOAT, is_getfloat_compatible),
            (SettingType.INT, is_getint_compatible),
            (SettingType.LIST, is_getlist_compatible),
            (SettingType.LOG_LEVEL, is_log_level),
            (SettingType.OPT_INT, is_opt_int),
            (SettingType.OPT_STR, is_opt_str),
            (SettingType.STR, is_str),
        )
    },
    SettingType.BASED_COMP_PRIO_DICT: check_based_comp_prio,
    SettingType.BASED_OBJ_DICT: check_based_obj_dict,
    SettingType.COMP_PRIO_DICT: check_comp_prio,
    SettingType.DICT: check_getdict_compatible,
    SettingType.OBJ: check_obj,
    SettingType.OPT_OBJ: partial(check_obj, allow_none=True),
    SettingType.OPT_PATH: check_opt_path,
    SettingType.PERIODIC_LOG_CONFIG: check_periodic_log_config,
}
