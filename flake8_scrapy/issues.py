from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Pos:
    line: int = 1
    column: int = 0

    def __iter__(self):
        return iter([self.line, self.column])

    @classmethod
    def from_node(cls, node, column: int | None = None, /) -> Pos:
        line = getattr(node, "lineno", 1)
        column = getattr(node, "col_offset", 1) if column is None else column
        assert column is not None
        return cls(line=line, column=column)


@dataclass
class Issue:
    code: int
    summary: str
    detail: str | None = None
    line: int = 1
    column: int = 0

    def __init__(
        self,
        id: tuple[int, str],
        pos: Pos | None = None,
        /,
        detail: str | None = None,
    ):
        self.code, self.summary = id
        self.pos = pos or Pos()
        self.detail = detail

    def __iter__(self):
        message = f"SCP{self.code:02} {self.summary}"
        if self.detail:
            message += f": {self.detail}"
        return iter([*self.pos, message])


DISALLOWED_DOMAIN = (1, "disallowed domain")
URL_IN_ALLOWED_DOMAINS = (2, "URL in allowed_domains")
IMPROPER_RESPONSE_URL_JOIN = (3, "improper response URL join")
IMPROPER_RESPONSE_SELECTOR = (4, "improper response selector")
LAMBDA_CALLBACK = (5, "lambda callback")
IMPROPER_FIRST_MATCH_EXTRACTION = (6, "improper first match extraction")
REDEFINED_SETTING = (7, "redefined setting")
NO_PROJECT_USER_AGENT = (8, "no project USER_AGENT")
ROBOTS_TXT_IGNORED_BY_DEFAULT = (9, "robots.txt ignored by default")
INCOMPLETE_PROJECT_THROTTLING = (10, "incomplete project throttling")
IMPROPER_SETTING_DEFINITION = (11, "improper setting definition")
IMPORTED_SETTING = (12, "imported setting")
PARTIAL_FREEZE = (13, "incomplete requirements freeze")
UNSUPPORTED_REQUIREMENT = (14, "unsupported requirement")
INSECURE_REQUIREMENT = (15, "insecure requirement")
UNMAINTAINED_REQUIREMENT = (16, "unmaintained requirement")
REDUNDANT_SETTING_VALUE = (17, "redundant setting value")
NO_ROOT_STACK = (18, "no root stack")
NON_ROOT_STACK = (19, "non-root stack")
STACK_NOT_FROZEN = (20, "stack not frozen")
NO_ROOT_REQUIREMENTS = (21, "no root requirements")
NON_ROOT_REQUIREMENTS = (22, "non-root requirements")
INVALID_SCRAPINGHUB_YML = (23, "invalid scrapinghub.yml")
MISSING_STACK_REQUIREMENTS = (24, "missing stack requirements")
UNEXISTING_REQUIREMENTS_FILE = (25, "unexisting requirements.file")
REQUIREMENTS_FILE_MISMATCH = (26, "requirements.file mismatch")
UNKNOWN_SETTING = (27, "unknown setting")
DEPRECATED_SETTING = (28, "deprecated setting")
SETTING_NEEDS_UPGRADE = (29, "setting needs upgrade")
REMOVED_SETTING = (30, "removed setting")
MISSING_SETTING_REQUIREMENT = (31, "missing setting requirement")
WRONG_SETTING_METHOD = (32, "wrong setting method")
BASE_SETTING_USE = (33, "base setting use")
MISSING_CHANGING_SETTING = (34, "missing changing setting")
NO_OP_SETTING_UPDATE = (35, "no-op setting update")
INVALID_SETTING_VALUE = (36, "invalid setting value")
NON_PICKLABLE_SETTING = (37, "unpicklable setting value")
LOW_PROJECT_THROTTLING = (38, "low project throttling")
NO_CONTACT_INFO = (39, "no contact info")
