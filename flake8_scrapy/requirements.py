from collections.abc import Generator, Iterable
from typing import cast

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name


def iter_requirement_lines(
    lines: Iterable[str],
) -> Generator[tuple[int, str, Requirement], None, None]:
    for line_number, line in enumerate(lines, start=1):
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#"):
            continue
        if "#" in clean_line:
            clean_line = clean_line.split("#", 1)[0].strip()
        try:
            requirement = Requirement(clean_line)
        except InvalidRequirement:
            continue
        canonical_name = cast("str", canonicalize_name(requirement.name))
        yield line_number, canonical_name, requirement
