from __future__ import annotations

from packaging.utils import canonicalize_name
from packaging.version import Version

from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.data.settings import SETTINGS
from flake8_scrapy.settings import (
    UNKNOWN_UNSUPPORTED_VERSION,
    SettingType,
    UnknownSettingValue,
    UnknownUnsupportedVersion,
)


def test_canonical_package_names():
    for name, data in SETTINGS.items():
        actual = data.package
        expected = canonicalize_name(actual)
        assert actual == expected, (
            f"Setting {name} uses non-canonical package name '{actual}', should be '{expected}'"
        )
    for actual in PACKAGES:
        expected = canonicalize_name(actual)
        assert actual == expected, (
            f"Package name {actual} is not canonical, should be '{expected}'"
        )


def test_default_value_history_oldest_known_value():
    for data in SETTINGS.values():
        default_value = data.default_value
        if isinstance(default_value, UnknownSettingValue):
            continue
        history = default_value.value_history
        if not history:
            continue
        assert UNKNOWN_UNSUPPORTED_VERSION in history


def test_enum_setting_values():
    for name, data in SETTINGS.items():
        if data.type != SettingType.ENUM_STR:
            continue
        assert data.values, f"Enum setting {name} has no values"


def test_sunset_guidance():
    for data in SETTINGS.values():
        if not data.deprecated_in:
            assert not data.sunset_guidance


def test_versions():
    for data in SETTINGS.values():
        if data.removed_in:
            # Any setting with a removed_in version is expected to have a
            # lower deprecated_in version as well. If that ever changes, we
            # need to review any existing code that relies on this assumption.
            assert data.deprecated_in
            if isinstance(data.deprecated_in, UnknownUnsupportedVersion):
                assert data.deprecated_in is UNKNOWN_UNSUPPORTED_VERSION
                assert PACKAGES[data.package].lowest_supported_version is not None
                assert PACKAGES[data.package].lowest_supported_version < data.removed_in  # type: ignore[operator]
            else:
                assert isinstance(data.deprecated_in, Version)
                assert data.deprecated_in < data.removed_in
