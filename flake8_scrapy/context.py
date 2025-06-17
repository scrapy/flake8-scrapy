from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Sequence


@dataclass
class Flake8File:
    tree: AST | None
    path: Path
    lines: Sequence[str] | None = None

    @classmethod
    def from_params(
        cls, tree: AST | None, file_path: str, lines: Sequence[str] | None = None
    ):
        return cls(tree, Path(file_path).resolve(), lines)


@dataclass
class Project:
    root: Path | None
    setting_module_import_paths: Sequence[str]
    requirements_file_path: Path | None = None

    @classmethod
    def from_file(cls, file: Flake8File):
        root = cls.root_from_file(file)
        return cls(
            root,
            cls.setting_module_import_paths_from_root(root),
            cls.find_requirements_file_path(root),
        )

    @staticmethod
    def root_from_file(file: Flake8File) -> Path | None:
        for parent in [file.path, *list(file.path.parents)]:
            if (parent / "scrapy.cfg").exists():
                return parent
        return None

    @staticmethod
    def setting_module_import_paths_from_root(root: Path | None) -> Sequence[str]:
        if not root:
            return ()
        config_file = root / "scrapy.cfg"
        config = ConfigParser()
        config.read(config_file)
        if "settings" not in config:
            return ()
        return tuple(config["settings"].values())

    @staticmethod
    def find_requirements_file_path(root: Path | None) -> Path | None:
        if not root:
            return None
        requirements_file = root / "requirements.txt"
        if requirements_file.exists():
            return requirements_file.resolve()
        return None

    @cached_property
    def requirements(self) -> dict[str, Version]:
        if not self.requirements_file_path or not self.requirements_file_path.exists():
            return {}

        try:
            content = self.requirements_file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return {}

        versions = {}
        for line in content.splitlines():
            line = line.strip()  # noqa: PLW2901
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()  # noqa: PLW2901
            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                continue
            # Only process if it's a frozen dependency (==version)
            if len(requirement.specifier) != 1:
                continue
            spec = next(iter(requirement.specifier))
            if spec.operator != "==":
                continue
            canonical_name = cast("str", canonicalize_name(requirement.name))
            versions[canonical_name] = Version(spec.version)
        return versions


@dataclass
class Context:
    file: Flake8File
    project: Project

    @classmethod
    def from_flake8_params(
        cls,
        tree: AST | None,
        file_path: str,
        lines: Sequence[str] | None = None,
    ):
        file = Flake8File.from_params(tree, file_path, lines)
        project = Project.from_file(file)
        return cls(file, project)
