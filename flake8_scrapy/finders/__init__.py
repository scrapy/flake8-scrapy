from abc import abstractmethod
from collections.abc import Generator


class IssueFinder:
    msg_code = ""
    msg_info = ""

    @property
    def message(self):
        return f"{self.msg_code} {self.msg_info}"

    @abstractmethod
    def find_issues(self, node) -> Generator[tuple[int, int, str], None, None]:
        pass
