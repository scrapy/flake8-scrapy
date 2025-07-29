from __future__ import annotations

from collections import defaultdict
from configparser import ConfigParser
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any

from packaging.version import Version

from scrapy_lint.requirements import iter_requirement_lines

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from packaging.requirements import Requirement


@dataclass
class Project:
    root: Path
    requirements_file_path: Path | None = None

    @cached_property
    def setting_module_import_paths(self) -> Sequence[str]:
        config_file = self.root / "scrapy.cfg"
        config = ConfigParser()
        config.read(config_file)
        if "settings" not in config:
            return ()
        return tuple(config["settings"].values())

    @cached_property
    def _requirements(self) -> dict[str, list[Requirement]]:
        content = self.requirements_text
        if content is None:
            return {}
        result = defaultdict(list)
        for _, name, requirement in iter_requirement_lines(content.splitlines()):
            result[name].append(requirement)
        return result

    @cached_property
    def frozen_requirements(self) -> dict[str, Version]:
        result = {}
        for name, requirements in self._requirements.items():
            for requirement in requirements:
                if len(requirement.specifier) != 1:
                    continue
                spec = next(iter(requirement.specifier))
                if spec.operator != "==":
                    continue
                result[name] = Version(spec.version)
        return result

    @cached_property
    def requirements_text(self) -> str | None:
        if not self.requirements_file_path or not self.requirements_file_path.exists():
            return None

        try:
            return self.requirements_file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    @cached_property
    def packages(self) -> set[str]:
        return set(self._requirements)


@dataclass
class Context:
    project: Project
    options: dict[str, Any]
