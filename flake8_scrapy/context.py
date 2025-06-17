from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

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

    @classmethod
    def from_file(cls, file: Flake8File):
        root = cls.root_from_file(file)
        return cls(
            root,
            cls.setting_module_import_paths_from_root(root),
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
