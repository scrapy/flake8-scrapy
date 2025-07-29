from __future__ import annotations

import re
from ast import Call, Constant, Dict, Lambda, List, Set, Tuple, UnaryOp, USub, expr
from typing import TYPE_CHECKING, Protocol

from packaging.version import Version

from scrapy_lint.ast import is_dict, iter_dict
from scrapy_lint.data.settings import FEEDS_KEY_VERSION_ADDED
from scrapy_lint.finders.settings.types import (
    check_import_path_need,
    has_feed_uri_params,
    is_import_path,
    is_path_obj,
)
from scrapy_lint.issues import (
    INVALID_SETTING_VALUE,
    NO_CONTACT_INFO,
    SETTING_NEEDS_UPGRADE,
    UNNEEDED_PATH_STRING,
    UNSUPPORTED_PATH_OBJECT,
    Issue,
    Pos,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from scrapy_lint.context import Context


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


def check_download_slots(node: expr, **_) -> Generator[Issue]:
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


def check_feed_uri(
    node: expr,
    allow_none: bool = True,
    path_obj_support: bool | None = True,
    unsupported_path_obj_detail: str | None = None,
    **_,
) -> Generator[Issue]:
    if is_dict(node) or isinstance(node, (Lambda, List, Set, Tuple)):
        return
    pos = Pos.from_node(node)
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
        yield Issue(INVALID_SETTING_VALUE, pos)
        return
    unneeded_str = Issue(UNNEEDED_PATH_STRING, pos)
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


def check_feed_class_list(
    param: str,
    value: expr,
    context: Context,
) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Constant, Dict, Lambda)):
        detail = f"{param!r} must be a list"
        yield Issue(INVALID_SETTING_VALUE, pos, detail)
        return
    if not isinstance(value, (List, Set, Tuple)):
        return
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


def check_feed_fields(param: str, value: expr, **_kwargs) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, Constant):
        if value.value is not None:
            detail = f"{param!r} must be a list or a dict"
            yield Issue(INVALID_SETTING_VALUE, pos, detail)
        return
    if isinstance(value, (List, Set, Tuple)):
        for index, elt in enumerate(value.elts):
            if isinstance(elt, Constant) and not isinstance(elt.value, str):
                detail = f"{param}[{index}] ({elt.value!r}) must be a string"
                pos_elt = Pos.from_node(elt)
                yield Issue(INVALID_SETTING_VALUE, pos_elt, detail)
        return
    if not is_dict(value):
        return
    assert isinstance(value, (Call, Dict))
    for elt_key, elt_value in iter_dict(value):
        if isinstance(elt_key, Constant) and not isinstance(
            elt_key.value,
            str,
        ):
            pos_key = Pos.from_node(elt_key)
            detail = (
                f"{param!r} keys must be strings, not "
                f"{type(elt_key.value).__name__} "
                f"({elt_key.value!r})"
            )
            yield Issue(INVALID_SETTING_VALUE, pos_key, detail)
        if not (
            isinstance(elt_value, Constant)
            and not isinstance(
                elt_value.value,
                str,
            )
        ):
            continue
        pos_value = Pos.from_node(elt_value)
        if isinstance(elt_key, Constant) and isinstance(
            elt_key.value,
            str,
        ):
            detail = (
                f"{param}[{elt_key.value!r}] ({elt_value.value!r}) must be a string"
            )
            yield Issue(INVALID_SETTING_VALUE, pos_value, detail)
        else:
            detail = (
                f"{param!r} dict values must be strings, not "
                f"{type(elt_value.value).__name__} "
                f"({elt_value.value!r})"
            )
            yield Issue(INVALID_SETTING_VALUE, pos_value, detail)


def check_item_export_kwargs(param: str, value: expr, **_kwargs) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Constant, Lambda, List, Set, Tuple)):
        detail = f"{param!r} must be a dict"
        yield Issue(INVALID_SETTING_VALUE, pos, detail)
        return
    if not is_dict(value):
        return
    assert isinstance(value, (Call, Dict))
    for key_elt, _ in iter_dict(value):
        if isinstance(key_elt, Constant) and not isinstance(
            key_elt.value,
            str,
        ):
            detail = (
                f"{param!r} keys must be strings, not "
                f"{type(key_elt.value).__name__} ({key_elt.value!r})"
            )
            yield Issue(INVALID_SETTING_VALUE, pos, detail)


def check_feed_obj_list(param: str, value: expr, context: Context) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
        isinstance(value, Constant)
        and not isinstance(value.value, str)
        and value.value is not None
    ):
        detail = f"{param!r} must be a Python object or its import path as a string"
        yield Issue(INVALID_SETTING_VALUE, pos, detail)
        return
    if not (isinstance(value, Constant) and isinstance(value.value, str)):
        return
    if is_import_path(value.value):
        yield from check_import_path_need(value, context.project)
        return
    detail = f"{param!r} ({value.value!r}) does not look like a valid import path"
    yield Issue(INVALID_SETTING_VALUE, pos, detail)


class FieldChecker(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(
        self, param: str, value: expr, *, context: Context
    ) -> Generator[Issue]: ...


def check_feed_format(param: str, value: expr, **_kwargs) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
        isinstance(value, Constant) and not isinstance(value.value, str)
    ):
        yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be a string")


def check_feed_bool(param: str, value: expr, **_kwargs) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
        isinstance(value, Constant) and not isinstance(value.value, bool)
    ):
        yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be a boolean")


def check_feed_int(param: str, value: expr, **_kwargs) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
        isinstance(value, Constant) and not isinstance(value.value, int)
    ):
        yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be an integer")
    elif (
        isinstance(value, Constant) and isinstance(value.value, int) and value.value < 0
    ) or (isinstance(value, UnaryOp) and isinstance(value.op, USub)):
        yield Issue(INVALID_SETTING_VALUE, pos, f"{param!r} must be >= 0")


def check_feed_encoding(param: str, value: expr, **_kwargs) -> Generator[Issue]:
    pos = Pos.from_node(value)
    if isinstance(value, (Dict, Lambda, List, Set, Tuple)) or (
        isinstance(value, Constant)
        and not isinstance(value.value, str)
        and value.value is not None
    ):
        yield Issue(
            INVALID_SETTING_VALUE,
            pos,
            f"{param!r} must be a string or None",
        )


FEED_CONFIG_CHECKERS: dict[str, FieldChecker] = {
    "fields": check_feed_fields,
    "item_classes": check_feed_class_list,
    "item_export_kwargs": check_item_export_kwargs,
    "item_filter": check_feed_obj_list,
    "postprocessing": check_feed_class_list,
    "uri_params": check_feed_obj_list,
    "format": check_feed_format,
    "overwrite": check_feed_bool,
    "store_empty": check_feed_bool,
    "batch_item_count": check_feed_int,
    "indent": check_feed_int,
    "encoding": check_feed_encoding,
}


def check_feed_config(node: Call | Dict, context: Context) -> Generator[Issue]:
    scrapy_version = context.project.frozen_requirements.get("scrapy")
    for key, value in iter_dict(node):
        if not isinstance(key, Constant):
            continue
        param = key.value
        assert isinstance(param, str)
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
        if param in FEED_CONFIG_CHECKERS:
            yield from FEED_CONFIG_CHECKERS[param](param, value, context=context)
            return
        yield Issue(
            INVALID_SETTING_VALUE,
            Pos.from_node(key),
            "unknown feed config key",
        )


def check_feeds(node: expr, context: Context, **_) -> Generator[Issue]:
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


def check_user_agent(node: expr, **_) -> Generator[Issue]:
    if not isinstance(node, Constant):
        return
    issue = Issue(NO_CONTACT_INFO, Pos.from_node(node))
    if node.value is None:
        yield issue
        return
    if not isinstance(node.value, str):
        return  # type error, reported elsewhere
    if not node.value:
        yield issue
        return
    if (
        any(s in node.value for s in INVALID_UA_SUBSTRINGS)
        or any(re.search(p, node.value) for p in INVALID_UA_PATTERNS)
        or not any(re.search(p, node.value) for p in REQUIRED_UA_PATTERNS)
    ):
        yield issue


class ValueChecker(Protocol):  # pylint: disable=too-few-public-methods
    def __call__(self, node: expr, *, context: Context) -> Generator[Issue]: ...


VALUE_CHECKERS: dict[str, ValueChecker] = {
    "DOWNLOAD_SLOTS": check_download_slots,
    "FEED_URI": check_feed_uri,
    "FEEDS": check_feeds,
    "USER_AGENT": check_user_agent,
}
