"""
A brick whose Dockerfile copies its whole tree keeps its history and notes out.

``COPY . .`` sends whatever ``docker build`` was given as its context, and
without a ``.dockerignore`` that is everything in the checkout: the ``.git``
history and the gitignored ``.private/`` notes. sprezzature-maps baked 703 MB of
history and 412 MB of private notes into an image layer that way, and eight
other bricks had the same Dockerfile and no ignore file either. Nothing failed:
the image built, ran and served.

The check reads every sibling checkout's Dockerfile, and where it copies ``.``
asks for a ``.dockerignore`` that names both.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = sorted(
    p
    for p in REPO_ROOT.parent.glob("sprezzature-*")
    if (p / "Dockerfile").is_file() and (p / "pyproject.toml").is_file()
)
MUST_IGNORE = (".git", ".private")


@pytest.mark.parametrize("brick", SIBLINGS, ids=lambda p: p.name)
def test_a_whole_tree_copy_leaves_history_and_notes_out(brick: Path) -> None:
    dockerfile = (brick / "Dockerfile").read_text(encoding="utf-8")
    if not re.search(r"^COPY\s+\.\s", dockerfile, re.M):
        pytest.skip("the Dockerfile copies named paths only")
    ignore = brick / ".dockerignore"
    assert ignore.is_file(), f"{brick.name}: COPY . . with no .dockerignore"
    lines = {
        line.strip().rstrip("/")
        for line in ignore.read_text(encoding="utf-8").splitlines()
    }
    missing = [name for name in MUST_IGNORE if name not in lines]
    assert not missing, f"{brick.name}/.dockerignore leaves out {missing}"


def test_the_siblings_are_there() -> None:
    if not SIBLINGS:
        pytest.skip("no sibling checkouts; run scripts/fetch_siblings.sh")
    assert len(SIBLINGS) >= 9
