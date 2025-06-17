from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Issue:
    code: int
    summary: str
    detail: str | None = None
    line: int = 1
    column: int = 0

    def __iter__(self):
        message = f"SCP{self.code:02} {self.summary}"
        if self.detail:
            message += f": {self.detail}"
        return iter([self.line, self.column, message])
