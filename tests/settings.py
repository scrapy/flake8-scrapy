from __future__ import annotations

from itertools import cycle
from typing import TYPE_CHECKING, overload

from tests import ExpectedIssue

if TYPE_CHECKING:
    from collections.abc import Sequence

# (template, setting column, value column - setting length)
SETTING_VALUE_CHECK_TEMPLATES = (
    ("settings['{setting}'] = {value}", 9, 15),
    ("BaseSettings({{'{setting}': {value}}})", 14, 18),
    ("settings.set(name='{setting}', value={value})", 18, 28),
    ("settings.setdefault('{setting}', {value}, 'addon')", 20, 24),
    ("settings.Settings(dict({setting}={value}))", 23, 24),
    ("crawler.settings.__setitem__('{setting}', {value})", 29, 33),
    (
        "scrapy.settings.overridden_settings(settings={{'{setting}': {value}}})",
        46,
        50,
    ),
)


class SafeDict(dict):
    """Allows to use str.format_map() with missing keys. e.g.
    SETTING_VALUE_CHECK_TEMPLATES can be used with a setting only, without a
    value."""

    def __missing__(self, key):
        return "{" + key + "}"


@overload
def zip_with_template(
    a: tuple[tuple[str], ...],
    b: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str, str], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str], ...],
) -> tuple[tuple[str, int, str], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, int, str, str], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str, str, int], ...],
) -> tuple[tuple[str, int, str, str, str, int], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str | None, str, str, int], ...],
) -> tuple[tuple[str, int, str, str | None, str, str, int], ...]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str, Sequence[ExpectedIssue] | ExpectedIssue | None], ...],
) -> tuple[
    tuple[str, int, str, str, Sequence[ExpectedIssue] | ExpectedIssue | None],
    ...,
]: ...


@overload
def zip_with_template(
    a: tuple[tuple[str, int], ...],
    b: tuple[tuple[str, str, Sequence[tuple[str, int]]], ...],
) -> tuple[tuple[str, int, str, str, Sequence[tuple[str, int]]], ...]: ...


def zip_with_template(a, b):
    return tuple((*ta, *tb) for ta, tb in zip(cycle(a), b))


def default_issues(
    path: str | None = None,
    exclude: int | set[int] | None = None,
) -> Sequence[ExpectedIssue]:
    exclude = {exclude} if isinstance(exclude, int) else exclude or set()
    return [
        ExpectedIssue(message=message, path=path)
        for message in (
            "SCP08 no project USER_AGENT",
            "SCP09 robots.txt ignored by default",
            "SCP10 incomplete project throttling",
            "SCP34 missing changing setting: FEED_EXPORT_ENCODING changes from None to 'utf-8' in a future version of scrapy",
        )
        if not any(message.startswith(f"SCP{code:02} ") for code in exclude)
    ]
