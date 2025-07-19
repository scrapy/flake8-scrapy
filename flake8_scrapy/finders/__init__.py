from abc import abstractmethod
from collections.abc import Generator

from flake8_scrapy.issues import Issue


class IssueFinder:
    @abstractmethod
    def find_issues(self, node) -> Generator[Issue, None, None]:
        pass
