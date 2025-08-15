from __future__ import annotations

from collections import defaultdict
from configparser import ConfigParser
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packaging.version import Version
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:  # Python < 3.11
    import tomli as tomllib

from scrapy_lint.errors import InputFileError
from scrapy_lint.requirements import iter_requirement_lines

if TYPE_CHECKING:
    from packaging.requirements import Requirement


@dataclass
class Project:
    path: Path

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
    def scrapy_lint_options(self) -> dict[str, Any]:
        pyproject_path = self.path / "pyproject.toml"
        if not pyproject_path.exists():
            return {}
        try:
            pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
            raise InputFileError(str(e), pyproject_path) from None
        return pyproject.get("tool", {}).get("scrapy-lint", {})

    @cached_property
    def packages(self) -> set[str]:
        return set(self._requirements)

    @cached_property
    def requirements_file(self) -> Path | None:
        requirements_file: Path | None
        path_str = self.scrapy_lint_options.get("requirements_file")
        if path_str is not None:
            requirements_file = Path(path_str).resolve()
            if requirements_file.exists():
                return requirements_file

        # Check scrapinghub.yml for requirements file
        if self.scrapy_cloud_config:
            try:
                requirements_file_name = self.scrapy_cloud_config.get(
                    "requirements", {}
                ).get(
                    "file",
                    "",
                )
            except AttributeError:
                pass
            else:
                if requirements_file_name and isinstance(
                    requirements_file_name,
                    str,
                ):
                    scrapinghub_requirements_file = Path(requirements_file_name)
                    if scrapinghub_requirements_file.exists():
                        return scrapinghub_requirements_file.resolve()

        # Fall back to requirements.txt
        requirements_file = Path("requirements.txt")
        if requirements_file.exists():
            return requirements_file.resolve()

        return None

    @cached_property
    def requirements_text(self) -> str | None:
        if not self.requirements_file or not self.requirements_file.exists():
            return None

        try:
            return self.requirements_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    @cached_property
    def scrapy_cloud_config(self) -> dict[str, Any] | None:
        config_file = self.path / "scrapinghub.yml"
        if not config_file.exists():
            return None
        yaml_parser = YAML(typ="safe")
        try:
            with config_file.open(encoding="utf-8") as f:
                return yaml_parser.load(f)
        except (UnicodeDecodeError, YAMLError):
            return None

    @cached_property
    def setting_module_paths(self) -> set[Path]:
        config_file = self.path / "scrapy.cfg"
        config = ConfigParser()
        config.read(config_file)
        if "settings" not in config:
            return set()
        result = set()
        for module_path in config["settings"].values():
            parts = module_path.split(".")
            pkg_path = self.path.joinpath(*parts, "__init__.py")
            if pkg_path.exists():
                result.add(pkg_path)
                continue
            mod_path = self.path.joinpath(*parts[:-1], f"{parts[-1]}.py")
            if mod_path.exists():
                result.add(mod_path)
        return result

    @cached_property
    def _requirements(self) -> dict[str, list[Requirement]]:
        content = self.requirements_text
        if content is None:
            return {}
        result = defaultdict(list)
        for _, name, requirement in iter_requirement_lines(content.splitlines()):
            result[name].append(requirement)
        return result


@dataclass
class Context:
    project: Project

    @property
    def options(self) -> dict[str, Any]:
        return self.project.scrapy_lint_options
