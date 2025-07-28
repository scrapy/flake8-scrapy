from __future__ import annotations

from packaging.utils import canonicalize_name
from packaging.version import Version

from scrapy_lint.data.packages import PACKAGES
from scrapy_lint.data.settings import SETTINGS
from scrapy_lint.finders.settings.types import PATH_SUPPORT_VERSIONS
from scrapy_lint.settings import (
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


def test_default_value_history():
    for data in SETTINGS.values():
        assert isinstance(data.name, str)
        default_value = data.default_value
        if isinstance(default_value, UnknownSettingValue):
            continue
        history = default_value.value_history
        if not history:
            continue
        assert UNKNOWN_UNSUPPORTED_VERSION in history
        # The following is an expectation of the check for “changing settings”,
        # i.e. SCP34. SCP34 logic needs to be updated to support more than 2
        # default value history entries in non-base settings.
        assert len(history) == 2 or data.name.endswith("_BASE")


def test_enum_setting_values():
    for name, data in SETTINGS.items():
        if data.type != SettingType.ENUM_STR:
            continue
        assert data.values, f"Enum setting {name} has no values"


def test_path_support():
    for name, data in SETTINGS.items():
        if data.type is not SettingType.OPT_PATH:
            assert name not in PATH_SUPPORT_VERSIONS
        else:
            assert name in PATH_SUPPORT_VERSIONS


def test_sunset_guidance():
    for data in SETTINGS.values():
        if not data.versioning.deprecated_in:
            assert not data.versioning.sunset_guidance


def test_versions():
    for data in SETTINGS.values():
        if data.versioning.removed_in:
            # Any setting with a removed_in version is expected to have a
            # lower deprecated_in version as well. If that ever changes, we
            # need to review any existing code that relies on this assumption.
            assert data.versioning.deprecated_in
            if isinstance(data.versioning.deprecated_in, UnknownUnsupportedVersion):
                assert data.versioning.deprecated_in is UNKNOWN_UNSUPPORTED_VERSION
                assert PACKAGES[data.package].lowest_supported_version
                assert (
                    PACKAGES[data.package].lowest_supported_version  # type: ignore[operator]
                    < data.versioning.removed_in
                )
            else:
                assert isinstance(data.versioning.deprecated_in, Version)
                assert data.versioning.deprecated_in < data.versioning.removed_in
