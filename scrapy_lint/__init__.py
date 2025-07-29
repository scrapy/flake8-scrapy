from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

from .linter import Linter

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

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


def lint(args: Sequence[str]) -> Generator[Issue]:
    parser = get_parser()
    parsed_args = parser.parse_args(args)
    linter = Linter.from_args(parsed_args)
    yield from linter.lint()


def main(args: Sequence[str] | None = None) -> None:
    args = args if args is not None else sys.argv[1:]
    try:
        found_issues = False
        for issue in lint(args):
            found_issues = True
            print(issue)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    else:
        if found_issues:
            sys.exit(1)
