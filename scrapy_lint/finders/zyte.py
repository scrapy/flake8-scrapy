from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML, CommentedMap
from ruamel.yaml.error import YAMLError

from scrapy_lint.issues import (
    INVALID_SCRAPINGHUB_YML,
    NO_ROOT_REQUIREMENTS,
    NO_ROOT_STACK,
    NON_ROOT_REQUIREMENTS,
    NON_ROOT_STACK,
    REQUIREMENTS_FILE_MISMATCH,
    STACK_NOT_FROZEN,
    UNEXISTING_REQUIREMENTS_FILE,
    Issue,
    Pos,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from scrapy_lint.context import Context


class ZyteCloudConfigIssueFinder:
    def __init__(self, context: Context):
        self.context = context

    def lint(self, file: Path) -> Generator[Issue]:
        yaml_parser = YAML(typ="rt")
        try:
            data = yaml_parser.load(file.read_text(encoding="utf-8"))
        except YAMLError as e:
            yield Issue(INVALID_SCRAPINGHUB_YML, detail=str(e))
            return
        if not isinstance(data, CommentedMap):
            detail = "non-mapping root data structure"
            yield Issue(INVALID_SCRAPINGHUB_YML, detail=detail)
            return
        if self._has_image_key(data):
            return
        if "stack" not in data and not self._has_stacks_default(data):
            yield Issue(NO_ROOT_STACK)
        if "requirements" not in data:
            yield Issue(NO_ROOT_REQUIREMENTS)
        yield from self.check_keys(data)

    def check_keys(self, data: CommentedMap, is_root: bool = True) -> Generator[Issue]:
        for key, value in data.items():
            if key == "stack":
                if not is_root:
                    yield Issue(NON_ROOT_STACK, self._get_key_position(data, key))
                yield from self._check_stack_value(data, key)
            elif key == "requirements":
                if not is_root:
                    pos = self._get_key_position(data, key)
                    yield Issue(NON_ROOT_REQUIREMENTS, pos)
                pos = self._get_value_position(data, key)
                yield from self._check_requirements_value(value, pos)
            elif key == "stacks" and is_root:
                if not isinstance(value, CommentedMap):
                    pos = self._get_value_position(data, key)
                    yield Issue(INVALID_SCRAPINGHUB_YML, pos, "non-mapping stacks")
                else:
                    for stack_key in value:
                        pos = self._get_key_position(value, stack_key)
                        yield Issue(NON_ROOT_STACK, pos)
                        yield from self._check_stack_value(value, stack_key)
            if isinstance(value, CommentedMap):
                yield from self.check_keys(value, is_root=False)

    def _get_key_position(self, data: CommentedMap, key: str) -> Pos:
        line_info = data.lc.key(key)
        return Pos(line_info[0] + 1, line_info[1])

    def _get_value_position(self, data: CommentedMap, key: str) -> Pos:
        line_info = data.lc.value(key)
        return Pos(line_info[0] + 1, line_info[1])

    def _check_stack_value(self, data: CommentedMap, key: str) -> Generator[Issue]:
        value = data[key]
        pos = self._get_value_position(data, key)
        if not isinstance(value, str):
            yield Issue(INVALID_SCRAPINGHUB_YML, pos, "non-str stack")
            return
        if not re.search(r"-\d{8}$", value):
            yield Issue(STACK_NOT_FROZEN, pos)

    def _check_requirements_value(
        self,
        requirements_value: Any,
        pos: Pos,
    ) -> Generator[Issue]:
        if not isinstance(requirements_value, CommentedMap):
            yield Issue(INVALID_SCRAPINGHUB_YML, pos, "non-mapping requirements")
            return

        if "file" not in requirements_value:
            yield Issue(INVALID_SCRAPINGHUB_YML, pos, "no requirements.file key")
            return

        file_value = requirements_value["file"]
        pos = self._get_value_position(requirements_value, "file")
        if not isinstance(file_value, str):
            yield Issue(INVALID_SCRAPINGHUB_YML, pos, "non-str requirements.file")
            return
        if not file_value.strip():
            yield Issue(INVALID_SCRAPINGHUB_YML, pos, "empty requirements.file")
            return

        if self.context.project.root:
            requirements_path = self.context.project.root / file_value
            if not requirements_path.exists():
                yield Issue(UNEXISTING_REQUIREMENTS_FILE, pos)
            elif (
                self.context.project.requirements_file_path
                and requirements_path != self.context.project.requirements_file_path
            ):
                yield Issue(REQUIREMENTS_FILE_MISMATCH, pos)

    def _has_image_key(self, data: CommentedMap) -> bool:
        for key, value in data.items():
            if key == "image":
                return True
            if isinstance(value, CommentedMap) and self._has_image_key(value):
                return True
        return False

    def _has_stacks_default(self, data: CommentedMap) -> bool:
        return (
            "stacks" in data
            and isinstance(data["stacks"], CommentedMap)
            and "default" in data["stacks"]
        )
