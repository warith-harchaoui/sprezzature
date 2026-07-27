"""
test_helper_sync — the per-skill shared helpers must not drift.

Each skill is self-contained: the shared helpers are duplicated verbatim into
every ``front-*/scripts/`` so a skill installs and runs on its own. That
duplication is only safe if the copies stay in lockstep — this test makes any
drift a red build.

Every shared helper is **byte-identical** across all its copies: they carry no
skill-specific text (the module docstrings were made skill-neutral in v0.26.1),
so the strongest, simplest guarantee applies. (``_lang.py`` also has a
byte-identical guard in ``test_bodytext.py``; keeping it here too is harmless
belt-and-suspenders.)

Author
------
Project maintainers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Shared helpers duplicated across skills — every copy must match to the byte.
SHARED_HELPERS = ("_argparse.py", "_click.py", "_lang.py", "_vocab.py")


@pytest.mark.parametrize("helper", SHARED_HELPERS)
def test_helper_copies_are_byte_identical(helper: str) -> None:
    """Every copy of a shared helper must be byte-for-byte identical.

    Fails the moment one copy is edited without propagating the exact bytes to
    the others. The helpers are intentionally skill-neutral, so there is no
    legitimate per-copy difference — not even in a docstring.
    """
    copies = sorted(REPO_ROOT.glob(f"front-*/scripts/{helper}"))
    assert len(copies) >= 2, f"expected several {helper} copies, found {len(copies)}"

    canonical = copies[0].read_bytes()
    drifted = [
        str(p.relative_to(REPO_ROOT))
        for p in copies[1:]
        if p.read_bytes() != canonical
    ]
    assert not drifted, (
        f"{helper} copies drifted from {copies[0].relative_to(REPO_ROOT)}: {drifted}. "
        "Edit one, then propagate the exact bytes to every copy."
    )
