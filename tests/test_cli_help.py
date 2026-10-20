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
sent?** The comments asserted a delegation; nothing verified it, and for four
bricks it had not happened.

The exemption list below is therefore two-sided. A brick outside it must
exercise ``--help`` somewhere in its suite; a brick inside it must still be
missing one — so the day somebody writes that test, this fails until the
exemption is removed. An exemption that cannot expire is how a list like this
rots into a TODO nobody reads.

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

#: Bricks with no ``--help`` smoke test in their own suite, measured
#: 2026-10-20. Every one of them registers console scripts, so every one of
#: them can break the way described above without its suite noticing. Listed
#: rather than fixed from here: the test belongs beside the commands it runs,
#: in each brick's repository, where the dependencies to run them exist.
KNOWN_GAPS: dict[str, str] = {
    "sprezzature-ui": "registers 5 commands; no test invokes one",
    "sprezzature-colors": "registers 7 commands; no test invokes one",
    "sprezzature-ux-laws": "registers 3 commands; no test invokes one",
    "sprezzature-maps": "registers 3 commands; no test invokes one",
}


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


def test_every_exemption_names_a_brick_that_ships() -> None:
    """A gap listed for a brick that no longer exists hides nothing."""
    unknown = sorted(set(KNOWN_GAPS) - set(SHIPPED_SKILLS))
    assert not unknown, f"{unknown} are exempted here and not in SKILLS.txt"


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_the_brick_runs_a_command_with_help_somewhere(brick: str) -> None:
    """Otherwise a command that cannot start is a command nothing starts."""
    found = _exercises_help(brick)
    if found is None:
        pytest.skip(f"{brick} is not checked out beside this repository")
    if brick in KNOWN_GAPS:
        pytest.skip(f"{brick}: {KNOWN_GAPS[brick]}")
    assert found, (
        f"{brick} registers console scripts and its suite never runs one with "
        f"--help. A command that dies at import — a missing extra, a renamed "
        f"entry point — exits non-zero before parsing anything, and nothing "
        f"there would say so. Add the smoke test, or list the brick in "
        f"KNOWN_GAPS here with a reason."
    )


@pytest.mark.parametrize("brick", sorted(KNOWN_GAPS))
def test_a_closed_gap_leaves_the_exemption_list(brick: str) -> None:
    """The half that makes the list above shrink instead of settling."""
    found = _exercises_help(brick)
    if found is None:
        pytest.skip(f"{brick} is not checked out beside this repository")
    assert not found, (
        f"{brick} now exercises --help in its own suite. Remove it from "
        f"KNOWN_GAPS: an exemption that outlives the gap it describes is a "
        f"line of documentation that has started lying."
    )
