#!/usr/bin/env python3

import json
import re
import urllib.request
from pathlib import Path
from subprocess import run


def get_latest_version(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    with urllib.request.urlopen(url) as response:  # noqa: S310
        if response.status != 200:  # noqa: PLR2004
            raise Exception(f"Error fetching data: HTTP {response.status}")
        data = json.load(response)
        return data["info"]["version"]


def main():
    latest_flake = get_latest_version("flake8")
    readme = Path(__file__).parent.parent / "README.rst"
    old_text = readme.read_text()
    new_text = re.sub(
        r'rev: "\d+\.\d+\.\d+"',
        f'rev: "{latest_flake}"',
        old_text,
    )
    if old_text == new_text:
        return
    with readme.open("w", encoding="utf-8") as f:
        f.write(new_text)
    run(["git", "add", readme], check=True)  # noqa: S603,S607


if __name__ == "__main__":
    main()
