from __future__ import annotations

import ast
import json
import re
from ast import (
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
    List,
    Load,
    Module,
    Name,
    NodeVisitor,
    NotIn,
    Set,
    Store,
    Subscript,
    Tuple,
    UnaryOp,
    USub,
    alias,
    expr,
    keyword,
)
from ast import walk as iter_nodes
from collections.abc import Generator, Iterable
from contextlib import suppress
from difflib import SequenceMatcher
from functools import partial
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Union

from packaging.version import Version

from flake8_scrapy.ast import extract_literal_value, is_dict, iter_dict
from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.data.settings import (
    FEEDS_KEY_VERSION_ADDED,
    MAX_AUTOMATIC_SUGGESTIONS,
    MIN_AUTOMATIC_SUGGESTION_SCORE,
    PREDEFINED_SUGGESTIONS,
    SETTINGS,
)
from flake8_scrapy.issues import (
    BASE_SETTING_USE,
    DEPRECATED_SETTING,
    IMPORTED_SETTING,
    IMPROPER_SETTING_DEFINITION,
    INCOMPLETE_PROJECT_THROTTLING,
    INVALID_SETTING_VALUE,
    LOW_PROJECT_THROTTLING,
    MISSING_CHANGING_SETTING,
    MISSING_SETTING_REQUIREMENT,
    NO_CONTACT_INFO,
    NO_OP_SETTING_UPDATE,
    NO_PROJECT_USER_AGENT,
    NON_PICKLABLE_SETTING,
    REDEFINED_SETTING,
    REDUNDANT_SETTING_VALUE,
    REMOVED_SETTING,
    ROBOTS_TXT_IGNORED_BY_DEFAULT,
    SETTING_NEEDS_UPGRADE,
    UNKNOWN_SETTING,
    UNNEEDED_IMPORT_PATH,
    UNNEEDED_PATH_STRING,
    UNNEEDED_SETTING_GET,
    UNSUPPORTED_PATH_OBJECT,
    WRONG_SETTING_METHOD,
    Issue,
    Pos,
)
from flake8_scrapy.settings import (
    SETTING_GETTERS,
    SETTING_METHODS,
    SETTING_SETTERS,
    SETTING_TYPE_GETTERS,
    SETTING_UPDATER_TYPES,
    SETTING_UPDATERS,
    UNKNOWN_FUTURE_VERSION,
    UNKNOWN_SETTING_VALUE,
    UNKNOWN_UNSUPPORTED_VERSION,
    Setting,
    SettingType,
    UnknownSettingValue,
    UnknownUnsupportedVersion,
    getbool,
)
from flake8_scrapy.utils import extend_sys_path

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context, Project
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


def is_getbool_compatible(node: expr, **kwargs) -> bool:
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


def is_getint_compatible(node: expr, **kwargs) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    try:
        int(node.value)
    except (TypeError, ValueError):
        return False
    else:
        return True


def is_getfloat_compatible(node: expr, **kwargs) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    try:
        float(node.value)
    except (TypeError, ValueError):
        return False
    else:
        return True


def is_getlist_compatible(node: expr, **kwargs) -> bool:
    if not isinstance(node, Constant):
        return True
    value = node.value
    if not value:
        return True
    if isinstance(value, (bytes, bytearray)):
        return False
    return isinstance(value, Iterable)


def check_getdict_compatible(node: expr, **kwargs) -> Generator[Issue]:
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
        dict(value)
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


def is_getdictorlist_compatible(node: expr, **kwargs) -> bool:
    if not isinstance(node, Constant):
        return True
    value = node.value
    return value is None or isinstance(value, str)


def is_opt_str(node: expr, **kwargs) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    value = node.value
    return value is None or isinstance(value, str)


def is_str(node: expr, **kwargs) -> bool:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return False
    if not isinstance(node, Constant):
        return True
    return isinstance(node.value, str)


def is_import_path(value: str, **kwargs) -> bool:
    if not value:
        return False
    parts = value.split(".")
    return bool(parts and all(part.isidentifier() for part in parts) and len(parts) > 1)


def is_log_level(node: expr, **kwargs) -> bool:
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


def is_enum_str(node: expr, setting: Setting, **kwargs) -> bool:
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


INVALID_UA_SUBSTRINGS = (
    "(+http://www.yourdomain.com)",
    "(+https://scrapy.org)",
)
INVALID_UA_PATTERNS = (
    r"Mozilla/\d+\.\d+",
    r"Chrome/\d+\.\d+",
    r"Safari/\d+\.\d+",
    r"Firefox/\d+\.\d+",
    r"AppleWebKit/\d+\.\d+",
    r"Gecko/\d+",
)
REQUIRED_UA_PATTERNS = (
    # URL
    r"https?://[a-zA-Z0-9.-]+|www\.[a-zA-Z0-9.-]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    # email
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    # international phone number
    r"\+\d{1,3}[\s\-\.]?\(?\d+\)?([\s\-\.]?\d+)+",
)


def check_download_slots(node: expr, **kwargs) -> Generator[Issue]:
    if not is_dict(node):
        return
    assert isinstance(node, (Call, Dict))
    for key, value in iter_dict(node):
        if isinstance(key, Constant) and not isinstance(key.value, str):
            detail = "DOWNLOAD_SLOTS keys must be download slot IDs as strings"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail=detail)
        if isinstance(value, (Constant, Lambda, List, Set, Tuple)):
            detail = "DOWNLOAD_SLOTS values must be dicts of download slot parameters"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail=detail)
        elif is_dict(value):
            assert isinstance(value, (Call, Dict))
            yield from check_slot_config(value)


def check_slot_config(node: Call | Dict) -> Generator[Issue]:
    for key, value in iter_dict(node):
        if not isinstance(key, Constant):
            continue
        param = key.value
        value_pos = Pos.from_node(value)
        if param == "concurrency":
            if isinstance(value, Constant):
                if not isinstance(value.value, int):
                    detail = "concurrency must be an integer"
                    yield Issue(INVALID_SETTING_VALUE, value_pos, detail=detail)
                elif value.value < 1:
                    detail = "concurrency must be >= 1"
                    yield Issue(INVALID_SETTING_VALUE, value_pos, detail=detail)
            elif isinstance(value, UnaryOp) and isinstance(value.op, USub):
                detail = "concurrency must be >= 1"
                yield Issue(INVALID_SETTING_VALUE, value_pos, detail=detail)
        elif param == "delay":
            if (
                isinstance(value, UnaryOp)
                and isinstance(value.op, USub)
                and isinstance(value.operand, Constant)
                and isinstance(value.operand.value, (int, float))
                and value.operand.value > 0
            ):
                detail = "delay must be >= 0"
                yield Issue(INVALID_SETTING_VALUE, value_pos, detail=detail)
        elif param == "randomize_delay":
            if isinstance(value, Constant) and not isinstance(value.value, bool):
                detail = "randomize_delay must be a boolean"
                yield Issue(INVALID_SETTING_VALUE, value_pos, detail=detail)
        else:
            detail = "unknown download slot parameter"
            key_pos = Pos.from_node(key)
            yield Issue(INVALID_SETTING_VALUE, key_pos, detail=detail)


def has_feed_uri_params(value: str) -> bool:
    return bool(re.search(r"%\([^)]+\)[sdifouxXeEgGcr]", value))


def is_path_obj(node: Call) -> bool:
    return getattr(node.func, "id", None) in {
        "Path",
        "PurePath",
        "PurePosixPath",
        "PureWindowsPath",
        "PosixPath",
        "WindowsPath",
    }


def check_feed_uri(
    node: expr,
    allow_none: bool = True,
    path_obj_support: bool | None = True,
    unsupported_path_obj_detail: str | None = None,
    **kwargs,
) -> Generator[Issue]:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return  # Already reported as bad type
    pos = Pos.from_node(node)
    invalid = Issue(INVALID_SETTING_VALUE, pos)
    unneeded_str = Issue(UNNEEDED_PATH_STRING, pos)
    if isinstance(node, Call):
        if not (
            is_path_obj(node) and node.args and isinstance(node.args[0], Constant)
        ) or not isinstance(node.args[0].value, str):
            pass
        elif path_obj_support is False:
            assert unsupported_path_obj_detail is not None
            yield Issue(UNSUPPORTED_PATH_OBJECT, pos, unsupported_path_obj_detail)
        elif has_feed_uri_params(node.args[0].value):
            yield Issue(UNSUPPORTED_PATH_OBJECT, pos, "has URI params")
        return
    if not isinstance(node, Constant) or (allow_none and node.value is None):
        return
    if not isinstance(node.value, str):
        yield invalid
        return
    try:
        protocol, path = node.value.split("://", 1)
    except ValueError:
        if path_obj_support is not False and not has_feed_uri_params(node.value):
            yield unneeded_str
    else:
        if (
            protocol == "file"
            and path_obj_support is not False
            and not has_feed_uri_params(path)
        ):
            yield unneeded_str


def check_feeds(node: expr, context: Context, **kwargs) -> Generator[Issue]:
    if not is_dict(node):
        return
    assert isinstance(node, (Call, Dict))
    version = context.project.frozen_requirements.get("scrapy")
    path_obj_support = None if version is None else version >= Version("2.6.0")
    for key, value in iter_dict(node):
        yield from check_feed_uri(
            key,
            allow_none=False,
            path_obj_support=path_obj_support,
            unsupported_path_obj_detail="requires Scrapy 2.6.0+",
            context=context,
        )
        if isinstance(value, (Constant, Lambda, List, Set, Tuple)):
            detail = "FEEDS dict values must be dicts of feed configurations"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)
        elif is_dict(value):
            assert isinstance(value, (Call, Dict))
            yield from check_feed_config(value, context)


def check_feed_config(node: Call | Dict, context: Context) -> Generator[Issue]:  # noqa: PLR0912, PLR0915
    scrapy_version = context.project.frozen_requirements.get("scrapy")
    for key, value in iter_dict(node):
        if not isinstance(key, Constant):
            continue
        param = key.value
        if (
            param in FEEDS_KEY_VERSION_ADDED
            and scrapy_version
            and scrapy_version < FEEDS_KEY_VERSION_ADDED[param]
        ):
            yield Issue(
                SETTING_NEEDS_UPGRADE,
                Pos.from_node(key),
                f"{param!r} requires Scrapy {FEEDS_KEY_VERSION_ADDED[param]}+",
            )
        pos = Pos.from_node(value)
        if param == "format":
            if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
                isinstance(value, Constant) and not isinstance(value.value, str)
            ):
                yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be a string")
        elif param in {"overwrite", "store_empty"}:
            if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
                isinstance(value, Constant) and not isinstance(value.value, bool)
            ):
                yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be a boolean")
        elif param in {"batch_item_count", "indent"}:
            if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
                isinstance(value, Constant) and not isinstance(value.value, int)
            ):
                yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be an integer")
            elif (
                isinstance(value, Constant)
                and isinstance(value.value, int)
                and value.value < 0
            ) or (isinstance(value, UnaryOp) and isinstance(value.op, USub)):
                yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be >= 0")
        elif param == "encoding":
            if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
                isinstance(value, Constant)
                and not isinstance(value.value, str)
                and value.value is not None
            ):
                yield Issue(
                    INVALID_SETTING_VALUE, pos, f"{param!r} must be a string or None"
                )
        elif param in {"item_filter", "uri_params"}:
            if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
                isinstance(value, Constant)
                and not isinstance(value.value, str)
                and value.value is not None
            ):
                detail = (
                    f"{param!r} must be a Python object or its import path as a string"
                )
                yield Issue(INVALID_SETTING_VALUE, pos, detail)
            elif isinstance(value, Constant) and isinstance(value.value, str):
                if not is_import_path(value.value):
                    detail = (
                        f"{param!r} ({value.value!r}) does not look like a "
                        f"valid import path"
                    )
                    yield Issue(INVALID_SETTING_VALUE, pos, detail)
                else:
                    yield from check_import_path_need(value, context.project)
        elif param == "item_export_kwargs":
            if isinstance(value, (Constant, Lambda, List, Set, Tuple)):
                detail = f"{param!r} must be a dict"
                yield Issue(INVALID_SETTING_VALUE, pos, detail)
            elif is_dict(value):
                assert isinstance(value, (Call, Dict))
                for key_elt, _ in iter_dict(value):
                    if isinstance(key_elt, Constant) and not isinstance(
                        key_elt.value, str
                    ):
                        detail = (
                            f"{param!r} keys must be strings, not "
                            f"{type(key_elt.value).__name__} ({key_elt.value!r})"
                        )
                        yield Issue(INVALID_SETTING_VALUE, pos, detail)
        elif param in {"item_classes", "postprocessing"}:
            if isinstance(value, (Constant, Dict, Lambda)):
                detail = f"{param!r} must be a list"
                yield Issue(INVALID_SETTING_VALUE, pos, detail)
            elif isinstance(value, (List, Set, Tuple)):
                for index, elt in enumerate(value.elts):
                    pos_elt = Pos.from_node(elt)
                    if isinstance(elt, (Dict, Lambda, List, Set, Tuple)):
                        detail = (
                            f"{param}[{index}] is neither a Python object of "
                            f"the expected type nor its import path as a "
                            f"string"
                        )
                        yield Issue(INVALID_SETTING_VALUE, pos_elt, detail)
                    elif isinstance(elt, Constant) and not isinstance(elt.value, str):
                        detail = (
                            f"{param}[{index}] ({elt.value!r}) is neither a "
                            f"Python object of the expected type nor its "
                            f"import path as a string"
                        )
                        yield Issue(INVALID_SETTING_VALUE, pos_elt, detail)
                    elif isinstance(elt, Constant) and isinstance(elt.value, str):
                        if not is_import_path(elt.value):
                            detail = (
                                f"{param}[{index}] ({elt.value!r}) does not "
                                f"look like a valid import path"
                            )
                            yield Issue(INVALID_SETTING_VALUE, pos_elt, detail)
                        else:
                            yield from check_import_path_need(elt, context.project)
        elif param == "fields":
            if isinstance(value, Constant):
                if value.value is not None:
                    detail = f"{param!r} must be a list or a dict"
                    yield Issue(INVALID_SETTING_VALUE, pos, detail)
            elif isinstance(value, (List, Set, Tuple)):
                for index, elt in enumerate(value.elts):
                    if isinstance(elt, Constant) and not isinstance(elt.value, str):
                        detail = f"{param}[{index}] ({elt.value!r}) must be a string"
                        pos_elt = Pos.from_node(elt)
                        yield Issue(INVALID_SETTING_VALUE, pos_elt, detail)
            elif is_dict(value):
                assert isinstance(value, (Call, Dict))
                for elt_key, elt_value in iter_dict(value):
                    if isinstance(elt_key, Constant) and not isinstance(
                        elt_key.value, str
                    ):
                        pos_key = Pos.from_node(elt_key)
                        detail = (
                            f"{param!r} keys must be strings, not "
                            f"{type(elt_key.value).__name__} "
                            f"({elt_key.value!r})"
                        )
                        yield Issue(INVALID_SETTING_VALUE, pos_key, detail)
                    if isinstance(elt_value, Constant) and not isinstance(
                        elt_value.value, str
                    ):
                        pos_value = Pos.from_node(elt_value)
                        if isinstance(elt_key, Constant) and isinstance(
                            elt_key.value, str
                        ):
                            detail = (
                                f"{param}[{elt_key.value!r}] "
                                f"({elt_value.value!r}) must be a string"
                            )
                            yield Issue(INVALID_SETTING_VALUE, pos_value, detail)
                        else:
                            detail = (
                                f"{param!r} dict values must be strings, not "
                                f"{type(elt_value.value).__name__} "
                                f"({elt_value.value!r})"
                            )
                            yield Issue(INVALID_SETTING_VALUE, pos_value, detail)
        else:
            yield Issue(
                INVALID_SETTING_VALUE,
                Pos.from_node(key),
                "unknown feed config key",
            )


def check_periodic_log_config(node: expr, **kwargs) -> Generator[Issue]:  # noqa: PLR0912
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
            if not isinstance(key.value, str):
                detail = (
                    f"keys must be 'include' or 'exclude', not "
                    f"{type(key.value).__name__} ({key.value!r})"
                )
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
            elif key.value not in {"include", "exclude"}:
                detail = f"keys must be 'include' or 'exclude', not {key.value!r}"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(key), detail)
        if isinstance(value, (Constant, Dict, Lambda)):
            detail = "dict values must be lists of stat name substrings"
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(value), detail)
        if not isinstance(value, (List, Set, Tuple)):
            continue
        for item in value.elts:
            if isinstance(item, (Dict, Lambda, List, Set, Tuple)):
                detail = "include/exclude list items must be strings"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(item), detail)
            if not isinstance(item, Constant):
                continue
            if not isinstance(item.value, str):
                detail = "include/exclude list items must be strings"
                yield Issue(INVALID_SETTING_VALUE, Pos.from_node(item), detail)


def check_user_agent(node: expr, **kwargs) -> Generator[Issue]:
    if isinstance(node, Constant) and (
        node.value is None
        or (
            isinstance(node.value, str)
            and (
                not node.value
                or (
                    any(s in node.value for s in INVALID_UA_SUBSTRINGS)
                    or any(re.search(p, node.value) for p in INVALID_UA_PATTERNS)
                    or not any(re.search(p, node.value) for p in REQUIRED_UA_PATTERNS)
                )
            )
        )
    ):
        yield Issue(NO_CONTACT_INFO, Pos.from_node(node))


class ValueChecker(Protocol):
    def __call__(self, node: expr, *, context: Context) -> Generator[Issue]: ...


VALUE_CHECKERS: dict[str, ValueChecker] = {
    "DOWNLOAD_SLOTS": check_download_slots,
    "FEED_URI": check_feed_uri,
    "FEEDS": check_feeds,
    "USER_AGENT": check_user_agent,
}


class IsTypeFunction(Protocol):
    def __call__(self, node: expr, *, setting: Setting) -> bool: ...


class TypeChecker(Protocol):
    def __call__(
        self, node: expr, *, setting: Setting, project: Project
    ) -> Generator[Issue]: ...


def check_type(is_type: IsTypeFunction) -> TypeChecker:
    def wrapper(node: expr, *, setting: Setting, **kwargs) -> Generator[Issue]:
        if not is_type(node, setting=setting):
            yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node))

    return wrapper


def check_import_path_need(
    node: Constant, project: Project, allowed: set[str] | None = None
) -> Generator[Issue]:
    frozen_version = project.frozen_requirements.get("scrapy")
    if not frozen_version or frozen_version < Version("2.4.0"):
        return
    allowed = allowed or set()
    if node.value not in allowed:
        yield Issue(UNNEEDED_IMPORT_PATH, Pos.from_node(node))


def check_import_path(node: Constant, project: Project) -> Generator[Issue]:
    if not isinstance(node.value, str):
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node))
        return
    if not is_import_path(node.value):
        yield Issue(INVALID_SETTING_VALUE, Pos.from_node(node))
        return
    yield from check_import_path_need(node, project)


def check_based_comp_prio(
    node: expr, *, setting: Setting, project: Project, **kwargs
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


def check_based_obj_dict(node: expr, *, project: Project, **kwargs) -> Generator[Issue]:
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


def check_comp_prio(node: expr, project: Project, **kwargs) -> Generator[Issue]:
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
    setting: Setting,
    project: Project,
    **kwargs,
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
    **kwargs,
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
        yield Issue(UNSUPPORTED_PATH_OBJECT, pos)
    elif not is_path_obj_ and supports_path_obj:
        yield Issue(UNNEEDED_PATH_STRING, pos)


TYPE_CHECKERS: dict[SettingType, TypeChecker] = {
    **{
        type: check_type(is_type)
        for type, is_type in (
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


class SettingChecker:
    def __init__(self, context: Context):
        self.context = context
        self.project = context.project
        known_settings = getattr(context.flake8_options, "scrapy_known_settings", "")
        self.additional_known_settings = {
            s.strip() for s in known_settings.split(",") if s.strip()
        }
        self.allow_pre_crawler_settings = False

    def is_known_setting(self, name: str) -> bool:
        return name in SETTINGS or name in self.additional_known_settings

    def is_supported_setting(self, setting: str) -> bool:
        if not self.project.packages:
            return True
        assert setting in SETTINGS
        setting_info = SETTINGS[setting]
        if setting_info.package not in self.project.frozen_requirements or (
            not setting_info.added_in and not setting_info.deprecated_in
        ):
            return setting_info.package in self.project.packages
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

    def check_known_name(  # noqa: PLR0911, PLR0912
        self, name: str, pos: Pos
    ) -> Generator[Issue]:
        if name.endswith("_BASE"):
            yield Issue(BASE_SETTING_USE, pos)
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        package = setting.package
        if package not in self.project.frozen_requirements:
            if self.project.frozen_requirements:
                yield Issue(MISSING_SETTING_REQUIREMENT, pos, package)
            return
        added_in = setting.added_in
        deprecated_in = setting.deprecated_in
        removed_in = setting.removed_in
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
        if setting.sunset_guidance:
            detail += f"; {setting.sunset_guidance}"
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
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        if setting.is_pre_crawler and not self.allow_pre_crawler_settings:
            yield Issue(NO_OP_SETTING_UPDATE, Pos.from_node(node))

    def check_method(self, name_node: Constant, call: Call) -> Generator[Issue]:
        func = call.func
        assert isinstance(func, Attribute)
        name = name_node.value
        if name not in SETTINGS:
            return
        setting = SETTINGS[name]
        name_pos = Pos.from_node(name_node)
        if (
            func.attr in SETTING_UPDATERS
            and setting.is_pre_crawler
            and not self.allow_pre_crawler_settings
        ):
            yield Issue(NO_OP_SETTING_UPDATE, name_pos)
        yield from self.check_wrong_setting_method(setting, call, name_pos)

    def check_wrong_setting_method(
        self, setting: Setting, call: Call, name_pos: Pos
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
        assert isinstance(func.value, Name)
        column = func.col_offset + len(func.value.id) + 1  # +1 for the dot
        pos = Pos.from_node(func, column)
        if setting.type in SETTING_TYPE_GETTERS:
            expected = SETTING_TYPE_GETTERS[setting.type]
            if func.attr != expected:
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
        ):
            assert isinstance(node.value, Name)
            column = node.value.col_offset + len(node.value.id)
            expected = SETTING_TYPE_GETTERS[setting.type]
            pos = Pos.from_node(node, column)
            yield Issue(WRONG_SETTING_METHOD, pos, f"use {expected}()")
        if (
            isinstance(node.ctx, (Store, Del))
            and setting.is_pre_crawler
            and not self.allow_pre_crawler_settings
        ):
            column = getattr(node.slice, "col_offset", node.col_offset + 1)
            yield Issue(NO_OP_SETTING_UPDATE, Pos.from_node(node, column))

    def is_materializer_call(self, parent, child):
        if not isinstance(parent, Call):
            return False
        func = parent.func
        return isinstance(func, Name) and func.id in {"list", "tuple", "set"}

    def check_non_picklable(self, node, parent=None):
        if isinstance(node, Lambda) or (
            isinstance(node, GeneratorExp)
            and not self.is_materializer_call(parent, node)
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
                node, setting=setting, project=self.project
            )


class SettingIssueFinder:
    NON_METHOD_SETTINGS_CALLABLES = ("BaseSettings", "Settings", "overridden_settings")

    def __init__(self, setting_checker: SettingChecker):
        self.setting_checker = setting_checker

    def find_issues(
        self, node: Assign | Call | Compare | FunctionDef | Subscript
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
                self.setting_checker.allow_pre_crawler_settings = True
            return

    def post_visit(self, node: Call | Compare | FunctionDef | Subscript) -> None:
        if isinstance(node, FunctionDef):
            if node.name == "update_pre_crawler_settings":
                self.setting_checker.allow_pre_crawler_settings = False
            return

    def find_call_issues(self, node: Call) -> Generator[Issue]:  # noqa: PLR0912
        if self.looks_like_setting_method(node.func):
            assert isinstance(node.func, Attribute)
            name: Constant | None = None
            value_or_default: expr | None = None
            if node.args and isinstance(node.args[0], Constant):
                name = node.args[0]
            if len(node.args) >= 2:  # noqa: PLR2004
                value_or_default = node.args[1]
            else:
                for keyword in node.keywords:
                    if not node.args and keyword.arg == "name":
                        if not isinstance(keyword.value, Constant):
                            return
                        name = keyword.value
                    elif keyword.arg in {"value", "default"}:
                        value_or_default = keyword.value
            if not name:
                return
            yield from self.setting_checker.check_name(name)
            yield from self.setting_checker.check_method(name, node)
            if node.func.attr in SETTING_SETTERS:
                if isinstance(name.value, str) and value_or_default:
                    yield from self.setting_checker.check_value(
                        name.value, value_or_default
                    )
            elif node.func.attr == "get" and (
                value_or_default is None
                or (
                    isinstance(value_or_default, Constant)
                    and value_or_default.value is None
                )
            ):
                pos = Pos.from_node(
                    node.func.value.end_lineno,
                    node.func.value.end_col_offset,
                )
                yield Issue(UNNEEDED_SETTING_GET, pos)
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

    def find_assign_issues(self, node: Assign) -> Generator[Issue]:
        for target in node.targets:
            if (
                isinstance(target, Subscript)
                and self.looks_like_settings_variable(target.value)
                and self.looks_like_setting_constant(target.slice)
            ):
                assert isinstance(target.slice, Constant)
                yield from self.setting_checker.check_value(
                    target.slice.value, node.value
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
            node.value
        ) or not self.looks_like_setting_constant(node.slice):
            return
        if isinstance(node.slice, Constant):
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

    def check(self) -> Generator[Issue]:
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
                processor.process_assignment(child)
            elif isinstance(child, (ClassDef, FunctionDef)):
                if not child.name.isupper():
                    continue
                pos = Pos.from_node(child, definition_column(child))
                self.issues.append(Issue(IMPROPER_SETTING_DEFINITION, pos))
                for issue in self.setting_checker.check_name(child):
                    self.issues.append(issue)
        self.issues.extend(processor.get_issues())


class SettingsModuleSettingsProcessor:
    def __init__(self, context: Context, setting_checker: SettingChecker):
        self.context = context
        self.seen_settings: set[str] = set()
        self.robotstxt_obey_values: list[tuple[bool, int, int]] = []
        self.redundant_values: list[tuple[str, int, int]] = []
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

    def process_setting(self, name: str, assignment: Assign) -> None:
        if name == "ROBOTSTXT_OBEY":
            self.process_robotstxt(assignment)
        self.check_redundant_values(name, assignment)
        self.check_throttling(name, assignment)
        for issue in self.setting_checker.check_value(name, assignment.value):
            self.issues.append(issue)

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
                (name, assignment.value.lineno, assignment.value.col_offset)
            )

    def check_throttling(self, name: str, assignment: Assign) -> None:
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
            self.issues.append(Issue(LOW_PROJECT_THROTTLING, pos))

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
        self.validate_missing_changing_settings()
        self.validate_redundant_values()
        return self.issues

    def validate_user_agent(self) -> None:
        if "USER_AGENT" not in self.seen_settings:
            self.issues.append(Issue(NO_PROJECT_USER_AGENT))

    def validate_robotstxt(self) -> None:
        if not self.robotstxt_obey_values:
            self.issues.append(Issue(ROBOTS_TXT_IGNORED_BY_DEFAULT))
        elif all(not value for value, *_ in self.robotstxt_obey_values):
            _, line, column = self.robotstxt_obey_values[0]
            self.issues.append(Issue(ROBOTS_TXT_IGNORED_BY_DEFAULT, Pos(line, column)))

    def validate_throttling(self) -> None:
        if not all(
            setting in self.seen_settings
            for setting in (
                "CONCURRENT_REQUESTS_PER_DOMAIN",
                "DOWNLOAD_DELAY",
            )
        ):
            self.issues.append(Issue(INCOMPLETE_PROJECT_THROTTLING))

    def validate_missing_changing_settings(self) -> None:
        for name, setting in SETTINGS.items():
            if name in self.seen_settings or name.endswith("_BASE"):
                continue
            default = setting.default_value
            if isinstance(default, UnknownSettingValue):
                continue
            if not default or not default.value_history:
                continue
            history = default.value_history
            assert len(history) == 2  # noqa: PLR2004
            assert UNKNOWN_UNSUPPORTED_VERSION in history
            old_value = history[UNKNOWN_UNSUPPORTED_VERSION]
            if UNKNOWN_FUTURE_VERSION in history:
                new_value = history[UNKNOWN_FUTURE_VERSION]
                detail = (
                    f"{name} changes from {old_value!r} to {new_value!r} in a "
                    f"future version of {setting.package}"
                )
                issue = Issue(MISSING_CHANGING_SETTING, detail=detail)
                self.issues.append(issue)
                continue
            requirements = self.context.project.frozen_requirements
            if not requirements or setting.package not in requirements:
                continue
            project_version = requirements[setting.package]
            change_version, new_value = next(
                iter(
                    (k, v)
                    for k, v in history.items()
                    if k != UNKNOWN_UNSUPPORTED_VERSION
                )
            )
            assert isinstance(change_version, Version)
            if project_version >= change_version:
                continue
            detail = (
                f"{name} changes from {old_value!r} to {new_value!r} in "
                f"{setting.package} {change_version}"
            )
            issue = Issue(MISSING_CHANGING_SETTING, detail=detail)
            self.issues.append(issue)

    def validate_redundant_values(self) -> None:
        for name, line, column in self.redundant_values:
            if self.is_changing_setting(name):
                continue
            self.issues.append(Issue(REDUNDANT_SETTING_VALUE, Pos(line, column)))

    def is_changing_setting(self, name: str) -> bool:
        assert name in SETTINGS
        setting = SETTINGS[name]
        default = setting.default_value
        assert not isinstance(default, UnknownSettingValue)
        if not default or not default.value_history:
            return False
        history = default.value_history
        assert len(history) == 2  # noqa: PLR2004
        assert UNKNOWN_UNSUPPORTED_VERSION in history
        assert UNKNOWN_FUTURE_VERSION not in history
        requirements = self.context.project.frozen_requirements
        assert setting.package in requirements
        project_version = requirements[setting.package]
        change_version = next(
            iter(k for k in history if k != UNKNOWN_UNSUPPORTED_VERSION)
        )
        assert isinstance(change_version, Version)
        return project_version < change_version
