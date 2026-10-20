"""
test_cli_help — a command whose ``--help`` nobody runs is a command nobody starts.

A console script that cannot even print its help is broken before argument
parsing: a missing extra imported at module load, a ``prog=`` naming a module,
an entry point pointing at a function that moved. All three have happened here,
and all three are caught by running the command with ``--help`` once.

Why this file asks a different question than it used to
------------------------------------------------------
It ran ``<script> --help`` as a subprocess, over a hand-kept ``SCRIPTS`` list.
The list emptied one brick at a time as each took its code to its own package,
each removal correct and annotated — "its own suite checks their --help there" —
until nothing was left but two tests over ``[]``, which pytest reports as "got
empty parameter set", and a reader takes for a pass. The import they shared,
``from _argparse import SKILL_VERSION``, would not even resolve any more: the
monorepo keeps no copy of that helper.

Running the commands is the bricks' job now — it needs their dependencies
installed, which this repository deliberately does not do. What belongs here is
the question only this repository can ask: **did the check arrive where it was
sent?** The comments asserted a delegation and nothing verified it, so for
four bricks it had not happened: ui, colors, ux-laws and maps, eighteen
registered commands between them and not one invoked by a test. They were
listed here for an afternoon, in a two-sided exemption table — a brick outside
it had to exercise ``--help``, a brick inside it had to still be missing one,
so closing a gap forced its own exemption out. All four closed the same day,
each with a ``tests/test_every_command_can_start.py`` beside the commands it
runs, and the table went with them: a list of nothing needs no machinery, and
parametrising over an empty one is the vacuity this whole file is about. If a
new gap appears, the answer is the test, not a line here.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent

#: A test that runs something with a help flag. Deliberately loose — it looks
#: for the flag as a literal, not for a particular way of invoking it, because
#: the bricks do this through subprocess, Click's CliRunner and argparse's
#: ``parse_args`` alike, and which one they chose is not this test's business.
_EXERCISES_HELP = re.compile(r"""["'](?:--help|-h)["']""")

def _suite(brick: str) -> list[Path] | None:
    """A brick's test files, or None when it is not checked out beside us."""
    root = SIBLINGS / brick
    if not (root / "pyproject.toml").is_file():
        return None
    tests = root / "tests"
    if not tests.is_dir():
        return []
    return sorted(p for p in tests.rglob("*.py") if "__pycache__" not in p.parts)


def _exercises_help(brick: str) -> bool | None:
    """Does `brick`'s own suite run anything with a help flag?"""
    suite = _suite(brick)
    if suite is None:
        return None
    return any(
        _EXERCISES_HELP.search(p.read_text(encoding="utf-8", errors="replace"))
        for p in suite
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_the_brick_runs_a_command_with_help_somewhere(brick: str) -> None:
    """Otherwise a command that cannot start is a command nothing starts."""
    found = _exercises_help(brick)
    if found is None:
        pytest.skip(f"{brick} is not checked out beside this repository")
    assert found, (
        f"{brick} registers console scripts and its suite never runs one with "
        f"--help. A command that dies at import — a missing extra, a renamed "
        f"entry point — exits non-zero before parsing anything, and nothing "
        f"there would say so. The nine have one each; add it to {brick} too, "
        f"beside the commands it runs."
    )
