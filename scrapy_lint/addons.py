from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scrapy_lint.versions import UnknownFutureVersion, UnknownUnsupportedVersion

if TYPE_CHECKING:
    from packaging.version import Version

    from scrapy_lint.context import Project


class VersionedSettings:  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        settings: set[str] | None = None,
        history: dict[
            Version | UnknownUnsupportedVersion | UnknownFutureVersion, set[str]
        ]
        | None = None,
    ):
        if settings is None:
            assert history
            self.all_time_settings: set[str] = set.intersection(*history.values())
        else:
            self.all_time_settings = settings
        self.history = history

    def __getitem__(self, version: Version) -> set[str]:
        if self.history is None:
            return self.all_time_settings
        applicable_versions = [
            v
            for v in self.history
            if not isinstance(v, UnknownUnsupportedVersion)
            and not isinstance(v, UnknownFutureVersion)
            and v <= version
        ]
        assert applicable_versions
        latest_applicable = max(applicable_versions)
        return self.history[latest_applicable]


@dataclass
class Addon:
    package: str
    settings: VersionedSettings

    def get_settings(self, project: Project) -> set[str]:
        if self.package not in project.frozen_requirements:
            return self.settings.all_time_settings
        version = project.frozen_requirements[self.package]
        return self.settings[version]
