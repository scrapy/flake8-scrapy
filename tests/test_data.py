from __future__ import annotations

from packaging.utils import canonicalize_name

from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.data.settings import SETTINGS
from flake8_scrapy.settings import SettingType


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


def test_enum_setting_values():
    for name, data in SETTINGS.items():
        if data.type != SettingType.ENUM_STR:
            continue
        assert data.values, f"Enum setting {name} has no values"
