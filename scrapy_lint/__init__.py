from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

from .linter import Linter

if TYPE_CHECKING:
    from collections.abc import Generator

    from .issues import Issue


def get_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "paths",
        type=Path,
        nargs="*",
        default=[Path().cwd()],
        metavar="FILES",
    )
    return parser


def lint() -> Generator[Issue]:
    parser = get_parser()
    args = parser.parse_args()
    linter = Linter.from_args(args)
    yield from linter.lint()


def main() -> None:
    try:
        found_issues = False
        for issue in lint():
            found_issues = True
            print(issue)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    else:
        if found_issues:
            sys.exit(1)
