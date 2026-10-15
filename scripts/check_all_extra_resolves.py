#!/usr/bin/env python3
"""
check_all_extra_resolves — do the ``all`` extra's floors exist on PyPI?

``tests/test_all_extra_is_the_suite.py`` checks the half that is decidable
offline: that the extra names the suite exactly, and that each floor matches
the sibling checkout sitting next to this repository. It says so in its own
docstring, and it is right to: a network call in CI would make the build flaky.

But that leaves a gap, and the gap has opened twice. A floor can name a version
that exists **only on a laptop**. ``sprezzature[all]`` then fails to resolve for
everyone, while every test in this repository stays green, because the sibling
checkout the test compares against is exactly the unpublished thing. The last
time, the extra floored ``sprezzature-figures`` at 2.5.0 and ``sprezzature-maps``
at 0.15.0 when PyPI held 2.4.0 and 0.12.0 -- the one command that installs the
whole suite could not run, and nothing in the repository could tell.

So this is the release-time half: it asks PyPI. Run it before tagging the
umbrella, after the sibling packages have been published. It is a script and
not a test on purpose -- it needs the network, and CI does not have it.

Usage
-----
::

    python scripts/check_all_extra_resolves.py

Exits 0 when every floor is published, 1 otherwise, naming what is missing.

Author
------
Warith HARCHAOUI <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 30


def _floors() -> list[tuple[str, str]]:
    """Each requirement in the ``all`` extra, as ``(package, floor)``."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"^all = \[(.*?)^\]", text, re.MULTILINE | re.DOTALL)
    if not match:
        sys.exit("error: pyproject.toml has no `all` extra")
    return re.findall(r'"([A-Za-z0-9_.-]+)\s*>=\s*([\d.]+)"', match.group(1))


def _published(package: str) -> tuple[set[str], str] | None:
    """Every version PyPI holds for a package, plus the one it calls latest."""
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{package}/json", timeout=TIMEOUT
        ) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    # A version key with an empty file list is a release whose files were all
    # yanked or deleted: present in the index, not installable.
    return {v for v, files in data["releases"].items() if files}, data["info"]["version"]


def main() -> int:
    stale: list[str] = []
    for package, floor in _floors():
        found = _published(package)
        if found is None:
            stale.append(f"{package}: not on PyPI at all (floor {floor})")
            print(f"!!  {package:28s} floor {floor:9s} NOT ON PYPI")
            continue
        versions, latest = found
        if floor in versions:
            print(f"ok  {package:28s} floor {floor:9s} latest {latest}")
        else:
            stale.append(f"{package}: floor {floor} is not published (latest {latest})")
            print(f"!!  {package:28s} floor {floor:9s} NOT PUBLISHED (latest {latest})")

    if stale:
        print(
            "\n`pip install sprezzature[all]` cannot resolve:\n  " + "\n  ".join(stale)
            + "\n\nPublish those versions first, or lower the floors to versions "
            "that exist. A floor naming a version only this machine has is the "
            "failure every test here is blind to.",
            file=sys.stderr,
        )
        return 1

    print("\nevery floor in the `all` extra resolves on PyPI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
