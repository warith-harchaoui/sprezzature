"""
This package may not promise a Python its dependencies cannot deliver.

``requires-python`` is a promise to anyone running ``pip install``, and a
dependency's is the same promise one level down. If a dependency has never
published a release reaching 3.14, nothing requiring it can be installed
there — whatever this manifest says.

The defect this guards was real and found elsewhere: on 2026-11-02
``sprezzature-accessibility`` claimed ``>=3.10`` with no upper bound over a
``wallet-helper`` that stops at 3.13. It had survived because the check
existed in two bricks out of eleven, and the one brick where an inherited
ceiling actually bit was one of the nine without it. A check that exists in
two places holds where it happens to be.

This package's own promise carries an upper bound, and it is inherited
rather than chosen: at least one dependency below stops short of 3.14.

The reasoning — and the two cheaper readings that each produced a confident
false accusation — is in :mod:`_pywindow`, shared verbatim across the suite.

Author
------
Project maintainers.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _pywindow import CANDIDATES, admits, dependency_names, overreach, promise

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "pyproject.toml"

#: Every base dependency, and the Python minors **at least one accepted
#: release** can be installed on.
#:
#: Reachability, not the floor's window and not the newest release's: see
#: :mod:`_pywindow` for why those two each accused a healthy package.
#: Measured against the simple index on 2026-11-02; re-measure when a floor or
#: a dependency moves.
MEASURED: dict[str, tuple[str, ...]] = {
    'sprezzature-accessibility': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-audio': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-cli-gui': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-colors': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-figures': ('3.10', '3.11', '3.12', '3.13'),
    'sprezzature-maps': ('3.10', '3.11', '3.12', '3.13'),
    'sprezzature-publish': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-ui': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-ux-laws': ('3.10', '3.11', '3.12', '3.13', '3.14', '3.15'),
    'sprezzature-video': ('3.10', '3.11', '3.12', '3.13'),
}


def test_there_are_dependencies_to_check() -> None:
    """Non-vacuity: an empty manifest would make every assertion below hold."""
    assert len(dependency_names(MANIFEST)) >= 8


def test_every_base_dependency_has_a_measured_window() -> None:
    """A new dependency has to be measured, not assumed.

    This is the half that rots: the comparison is only as complete as the
    table, and a dependency added without a reading would be invisible to it.
    """
    names = set(dependency_names(MANIFEST))
    unmeasured = sorted(names - set(MEASURED))
    assert not unmeasured, (
        "these base dependencies have no recorded reachability, so the check "
        f"below silently skips them: {', '.join(unmeasured)}"
    )
    stale = sorted(set(MEASURED) - names)
    assert not stale, f"recorded and no longer required: {', '.join(stale)}"


@pytest.mark.parametrize("version", CANDIDATES)
def test_the_promise_is_not_wider_than_the_graph(version: str) -> None:
    """For every Python this package claims, every dependency must reach it."""
    broken = overreach(MANIFEST, MEASURED, version)
    assert not broken, (
        f"requires-python = {promise(MANIFEST)!r} claims Python {version}, and "
        f"these cannot be installed there: {', '.join(broken)}.\n"
        "  Either narrow the promise, or raise the dependency to one that "
        "reaches further — the promise is what a reader acts on."
    )


def test_the_reader_itself_is_right() -> None:
    """Sabotage, inline: a check built on a broken specifier reader would pass
    every assertion above and mean nothing."""
    assert admits(">=3.10", "3.14")
    assert not admits("<3.14,>=3.10", "3.14")
    assert admits(promise(MANIFEST), "3.12")
