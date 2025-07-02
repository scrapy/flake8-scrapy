from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML, CommentedMap
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
        yaml_parser = YAML(typ="rt")
        try:
            data = yaml_parser.load(content)
        except YAMLError as e:
            yield Issue(28, "invalid scrapinghub.yml", detail=str(e))
            return
        if not isinstance(data, CommentedMap):
            yield Issue(
                28, "invalid scrapinghub.yml", detail="non-mapping root data structure"
            )
            return
        if self._has_image_key(data):
            return
        if "stack" not in data and not self._has_stacks_default(data):
            yield Issue(18, "no root stack")
        if "requirements" not in data:
            yield Issue(21, "no root requirements")
        yield from self.check_keys(data)

    def check_keys(
        self, data: CommentedMap, is_root: bool = True
    ) -> Generator[Issue, None, None]:
        for key, value in data.items():
            if key == "stack":
                if not is_root:
                    line, column = self._get_key_position(data, key)
                    yield Issue(19, "non-root stack", line=line, column=column)
                yield from self._check_stack_value(data, key)
            elif key == "requirements":
                if not is_root:
                    line, column = self._get_key_position(data, key)
                    yield Issue(22, "non-root requirements", line=line, column=column)
                line, column = self._get_value_position(data, key)
                yield from self._check_requirements_value(value, line, column)
            elif key == "stacks" and is_root:
                if not isinstance(value, CommentedMap):
                    line, column = self._get_value_position(data, key)
                    yield Issue(
                        28,
                        "invalid scrapinghub.yml",
                        detail="non-mapping stacks",
                        line=line,
                        column=column,
                    )
                else:
                    for stack_key in value:
                        line, column = self._get_key_position(value, stack_key)
                        yield Issue(19, "non-root stack", line=line, column=column)
                        yield from self._check_stack_value(value, stack_key)
            if isinstance(value, CommentedMap):
                yield from self.check_keys(value, is_root=False)

    def _get_key_position(self, data: CommentedMap, key: str) -> tuple[int, int]:
        line_info = data.lc.key(key)
        return line_info[0] + 1, line_info[1]

    def _get_value_position(self, data: CommentedMap, key: str) -> tuple[int, int]:
        line_info = data.lc.value(key)
        return line_info[0] + 1, line_info[1]

    def _is_frozen_stack(self, stack: str) -> bool:
        return isinstance(stack, str) and bool(re.search(r"-\d{8}$", stack))

    def _check_stack_value(
        self, data: CommentedMap, key: str
    ) -> Generator[Issue, None, None]:
        value = data[key]
        line, column = self._get_value_position(data, key)
        if not isinstance(value, str):
            yield Issue(
                28,
                "invalid scrapinghub.yml",
                detail="non-str stack",
                line=line,
                column=column,
            )
            return
        if not re.search(r"-\d{8}$", value):
            yield Issue(20, "stack not frozen", line=line, column=column)

    def _check_requirements_value(
        self, requirements_value: Any, line: int, column: int
    ) -> Generator[Issue, None, None]:
        if not isinstance(requirements_value, CommentedMap):
            yield Issue(
                28,
                "invalid scrapinghub.yml",
                detail="non-mapping requirements",
                line=line,
                column=column,
            )
            return

        if "file" not in requirements_value:
            yield Issue(23, "no requirements.file", line=line, column=column)
            return

        file_value = requirements_value["file"]
        line, column = self._get_value_position(requirements_value, "file")
        if not isinstance(file_value, str) or not file_value.strip():
            yield Issue(24, "invalid requirements.file", line=line, column=column)
            return

        if self.context.project.root:
            requirements_path = self.context.project.root / file_value
            if not requirements_path.exists():
                yield Issue(
                    25, "unexisting requirements.file", line=line, column=column
                )
            elif (
                self.context.project.requirements_file_path
                and requirements_path != self.context.project.requirements_file_path
            ):
                yield Issue(26, "requirements.file mismatch", line=line, column=column)

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
