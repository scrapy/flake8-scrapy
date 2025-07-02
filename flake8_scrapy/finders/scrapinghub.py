from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from flake8_scrapy.issues import Issue

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.context import Context


class ScrapinghubIssueFinder:
    def __init__(self, context: Context):
        self.context = context

    def in_scrapinghub_file(self) -> bool:
        if not self.context.project.root:
            return False
        return self.context.file.path == self.context.project.root / "scrapinghub.yml"

    def check(self) -> Generator[Issue, None, None]:
        assert self.context.file.lines is not None
        content = "\n".join(self.context.file.lines)
        yaml_parser = YAML(typ="safe")
        try:
            data = yaml_parser.load(content)
        except YAMLError:
            return
        if not isinstance(data, dict):
            return
        if self._has_image_key(data):
            return
        if "stack" not in data and not self._has_stacks_default(data):
            yield Issue(18, "no root stack")
        if "requirements" not in data:
            yield Issue(21, "no root requirements")
        yield from self.check_keys(data)

    def check_keys(
        self, data: dict, is_root: bool = True
    ) -> Generator[Issue, None, None]:
        for key, value in data.items():
            if key == "stack":
                if not is_root:
                    yield Issue(19, "non-root stack")
                if not self._is_frozen_stack(value):
                    yield Issue(20, "stack not frozen")
            elif key == "requirements":
                if not is_root:
                    yield Issue(22, "non-root requirements")
                yield from self._check_requirements_structure(value)
            elif key == "stacks" and is_root:
                if not isinstance(value, dict):
                    yield Issue(28, "invalid scrapinghub.yml")
                else:
                    for stack_value in value.values():
                        yield Issue(19, "non-root stack")
                        if not self._is_frozen_stack(stack_value):
                            yield Issue(20, "stack not frozen")
            if isinstance(value, dict):
                yield from self.check_keys(value, is_root=False)

    def _is_frozen_stack(self, stack: str) -> bool:
        return isinstance(stack, str) and bool(re.search(r"-\d{8}$", stack))

    def _check_requirements_structure(
        self, requirements_value
    ) -> Generator[Issue, None, None]:
        if not isinstance(requirements_value, dict):
            yield Issue(28, "invalid scrapinghub.yml")
            return

        if "file" not in requirements_value:
            yield Issue(23, "no requirements.file")
            return

        file_value = requirements_value["file"]

        if not isinstance(file_value, str) or not file_value.strip():
            yield Issue(24, "invalid requirements.file")
            return

        if self.context.project.root:
            requirements_path = self.context.project.root / file_value
            if not requirements_path.exists():
                yield Issue(25, "unexisting requirements.file")
            elif (
                self.context.project.requirements_file_path
                and requirements_path != self.context.project.requirements_file_path
            ):
                yield Issue(26, "requirements.file mismatch")

    def _has_image_key(self, data: dict) -> bool:
        for key, value in data.items():
            if key == "image":
                return True
            if isinstance(value, dict) and self._has_image_key(value):
                return True
        return False

    def _has_stacks_default(self, data: dict) -> bool:
        return (
            "stacks" in data
            and isinstance(data["stacks"], dict)
            and "default" in data["stacks"]
        )
