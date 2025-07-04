from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Issue:
    code: int
    summary: str
    detail: str | None = None
    line: int = 1
    column: int = 0

    def __init__(self, code, summary, detail=None, line=None, column=None, node=None):  # noqa: PLR0913
        if node is not None:
            node_line = getattr(node, "lineno", None)
            node_col = getattr(node, "col_offset", None)
            if line is None:
                line = node_line
            if column is None:
                column = node_col
        self.code = code
        self.summary = summary
        self.detail = detail
        self.line = line if line is not None else 1
        self.column = column if column is not None else 0

    def __iter__(self):
        message = f"SCP{self.code:02} {self.summary}"
        if self.detail:
            message += f": {self.detail}"
        return iter([self.line, self.column, message])
