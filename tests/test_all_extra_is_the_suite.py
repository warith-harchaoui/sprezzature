"""
The ``all`` extra is a promise that ``pip install sprezzature[all]`` gives you
every tool the skills call. It is a hand-written list, and it went wrong in
both directions on the way to the first publication: it floored
``sprezzature-figures`` at a release predating the ``redraw`` command its own
skill documents, and it named two packages that were not on PyPI at all, so
the extra could not resolve.

Nothing in the repository connected the list to the packages the suite
actually has. ``scripts/check_wheels.py`` already knows them — it builds and
installs each one — so that is the source of truth here.

This cannot check PyPI: CI is offline and a network call would make the build
flaky. It checks the half that is decidable locally — that the extra names the
suite, exactly. Whether those versions exist is what ``check_wheels.py`` and
the publication step answer.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_wheels import PACKAGES  # noqa: E402

#: Every sibling tool package: what `check_wheels` builds, less this repo.
TOOL_PACKAGES = frozenset(PACKAGES) - {"sprezzature"}

_ALL_EXTRA_RE = re.compile(r"^all = \[(.*?)\]", re.MULTILINE | re.DOTALL)
_REQUIREMENT_RE = re.compile(r'"([A-Za-z0-9_.-]+)\s*(?:[<>=!~]=?[^"]*)?"')


def _all_extra() -> dict[str, str]:
    """Map each requirement in the ``all`` extra to the raw string declaring it."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = _ALL_EXTRA_RE.search(text)
    assert match, "pyproject.toml has no `all` extra"
    body = match.group(1)
    return {m.group(1): m.group(0) for m in _REQUIREMENT_RE.finditer(body)}


def test_all_extra_names_every_tool_package() -> None:
    """A new tool package must join the extra, or `[all]` quietly omits it."""
    missing = sorted(TOOL_PACKAGES - set(_all_extra()))
    assert not missing, (
        "these suite packages are not in the `all` extra, so "
        f"`pip install sprezzature[all]` would not install them: {missing}"
    )


def test_all_extra_names_nothing_else() -> None:
    """And nothing the suite does not publish — an extra that cannot resolve."""
    extra = set(_all_extra())
    unknown = sorted(extra - TOOL_PACKAGES)
    assert not unknown, (
        f"the `all` extra requires {unknown}, which check_wheels.py does not "
        "know how to build. Either add the repository to its PACKAGES table or "
        "drop the requirement: an extra naming a package nobody publishes "
        "fails to resolve at install time, not at build time."
    )


def test_every_requirement_carries_a_floor() -> None:
    """An unpinned requirement resolves to whatever is oldest-compatible."""
    unfloored = sorted(name for name, raw in _all_extra().items() if ">=" not in raw)
    assert not unfloored, (
        f"no minimum version on {unfloored}. The extra floored "
        "sprezzature-figures at 2.0.0 while the skill it ships documented "
        "commands that arrived in 2.2.0; a floor is how that stays honest."
    )
