from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from flake8_scrapy.issues import Issue


class IssueFinder:
    @abstractmethod
    def find_issues(self, node) -> Generator[Issue]:
        pass
