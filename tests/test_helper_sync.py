"""
test_helper_sync — the duplicated shared helpers must not drift.

Five small helpers (``_argparse.py``, ``_click.py``, ``_lang.py``,
``_vocab.py``, ``_vtt.py``) are copied into every brick on purpose: a skill has
to install and run on its own, including from a downloaded zip with nothing but
the standard library, so it cannot import a shared package from a sibling. That
duplication is a deliberate exception to "don't repeat yourself", and it is only
safe while the copies stay identical.

Why this used to check nothing
------------------------------
It globbed ``sprezzature-*/scripts/<helper>`` **in this repository** and skipped
when it found fewer than two copies. After the split it finds none, so all four
cases skipped — with an honest reason that named the right tool,
``scripts/sync_helpers.py``, and left out that nothing runs it. Helper drift is
silent by nature: every copy keeps working, and the bug is that two of them now
disagree. The one check that catches it ran nowhere.

So it runs the real thing: ``sync_helpers.py`` against the sibling checkouts,
which returns non-zero on drift and prints which copies disagree and with what.
``SKILL_VERSION`` is the one line that legitimately differs — each brick sets it
to its own release — and the script already ignores it when comparing.

Author
------
Project maintainers.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent
SYNC = REPO_ROOT / "scripts" / "sync_helpers.py"


def _checkouts() -> list[str]:
    """The bricks checked out beside this repository."""
    return [b for b in SHIPPED_SKILLS if (SIBLINGS / b / "pyproject.toml").is_file()]


def test_the_sync_script_is_there() -> None:
    """It is the only thing that can answer the question below."""
    assert SYNC.is_file(), f"{SYNC} is missing; helper drift is unchecked"


def test_no_shared_helper_has_drifted() -> None:
    """One canonical copy, propagated; any disagreement is a red build.

    Runs the reporter rather than re-implementing it: the comparison has a
    subtlety — ``SKILL_VERSION`` differs per brick on purpose — and two
    implementations of that rule would drift from each other the way the helpers
    themselves are being guarded against.
    """
    checkouts = _checkouts()
    if not checkouts:
        pytest.skip(
            "no brick is checked out beside this repository; "
            "run scripts/fetch_siblings.sh to check the helpers for drift"
        )
    proc = subprocess.run(
        [sys.executable, str(SYNC), "--home", str(SIBLINGS)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"a shared helper has drifted across the {len(checkouts)} bricks here. "
        f"Edit the canonical copy named below, then propagate with "
        f"`python3 scripts/sync_helpers.py --apply`:\n{proc.stdout}\n{proc.stderr}"
    )


def test_the_report_actually_compared_something() -> None:
    """A run that found one copy of everything would pass and mean nothing.

    ``sync_helpers.py`` prints "N copy — nothing to compare" for a helper it
    cannot cross-check, and exits 0 — correct for the script, useless as a gate.
    This is the same vacuity the file had before: the check present, the subject
    absent, the result green.
    """
    if not _checkouts():
        pytest.skip("no brick is checked out beside this repository")
    proc = subprocess.run(
        [sys.executable, str(SYNC), "--home", str(SIBLINGS)],
        capture_output=True,
        text=True,
    )
    uncompared = [
        line.strip()
        for line in proc.stdout.splitlines()
        if "nothing to compare" in line
    ]
    assert not uncompared, (
        "sync_helpers.py could not cross-check these, so their copies are "
        "unguarded:\n  " + "\n  ".join(uncompared)
    )
