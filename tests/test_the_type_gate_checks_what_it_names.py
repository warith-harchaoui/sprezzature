"""
``run_mypy.sh`` type-checks every directory it names that holds Python.

The gate loops over three targets: the skills' ``scripts/`` dirs, this
repository's own ``scripts/``, and ``sprezzature-cli/src``. It skips a target
with no Python in it, which is right -- the eight skill ``scripts/`` dirs are
empty shells left by the monorepo split, and mypy fails outright on a directory
with no ``.py`` files.

The skip was decided by ``find "$dir" -maxdepth 1 -name '*.py'``, and
``sprezzature-cli`` keeps its modules one level down, under
``src/sprezzature_cli/``. So the loop named that package, read it as empty, and
skipped it. The gate reported ``1 dir(s) type-check clean`` and that sentence
was true about the one directory it had checked out of the two that held code.

A guard that silently narrows its own scope is the expensive kind, because its
output looks identical either way. This test reads the live branch of the loop
-- ``--list`` prints it -- and compares it against the targets that actually
hold Python, so the two can only disagree out loud.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
GATE: Path = REPO_ROOT / "scripts" / "run_mypy.sh"

#: The targets the loop names, spelled as the script spells them. A glob here
#: and a glob there have to stay in step; the test below is what notices.
TARGET_GLOBS: tuple[str, ...] = ("sprezzature-*/scripts", "scripts", "sprezzature-cli/src")


def _listed() -> set[str]:
    """What the gate says it would check."""
    out = subprocess.run(
        ["bash", str(GATE), "--list"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120, check=True,
    )
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def _holds_python() -> set[str]:
    """Every named target that holds a ``.py`` file at any depth."""
    found: set[str] = set()
    for pattern in TARGET_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_dir() and any(path.rglob("*.py")):
                found.add(str(path.relative_to(REPO_ROOT)))
    return found


def test_the_gate_checks_every_target_that_holds_python() -> None:
    """Nothing the loop names and that holds code is skipped."""
    missed = _holds_python() - _listed()
    assert not missed, (
        f"run_mypy.sh names {sorted(missed)} and skips it, so those files are "
        f"type-checked by nothing. The gate still exits 0 and reports the "
        f"directories it did check, which is why this is a test and not a "
        f"thing anyone would notice."
    )


def test_the_gate_checks_more_than_one_directory() -> None:
    """A floor, so the loop cannot quietly shrink to a single target.

    Not an exact set: a brick that ships deterministic scripts again should
    widen this gate without editing a test. One directory means the loop is
    down to this repository's own ``scripts/``, which is how it was found.
    """
    listed = _listed()
    assert len(listed) >= 2, (
        f"run_mypy.sh would check {sorted(listed)} — one directory. The loop "
        f"names three targets; at least this repository's scripts/ and "
        f"sprezzature-cli/src hold Python."
    )
    assert "sprezzature-cli/src" in listed, (
        "sprezzature-cli/src holds the CLI package and the gate names it; it "
        "is checked by nothing else in this repository."
    )
