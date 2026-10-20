"""
A skill that hands out ``python -m <module>`` must not be hiding a command.

``python -m sprezzature_colors_scripts.simulate_cvd`` works. That is the
trouble with it: nothing fails, so nothing says that the brick registers
``sprezzature-colors-cvd`` for the same entry point and has done for releases.
Three skills went further and wrote the absence down —

* ``sprezzature-ux-laws``: "It registers no console script, so it runs as
  ``python -m sprezzature_ux_laws_scripts.audit_laws_of_ux``";
* ``sprezzature-colors``, about itself: "The package registers no console
  scripts: every entry below runs as ``python -m …``" — seven of them;
* ``sprezzature-accessibility``, about its neighbour: "the ``sprezzature-colors``
  package ships no console script, only these importable modules".

An agent reads that and takes the longer road, which needs the internal package
name — a name the brick is free to change, and did when ``scripts/`` became
``sprezzature_<brick>_scripts``. The command is the part the brick promises.

A fallback is different, and allowed: "``sprezzature-accessibility-lint``, or
``python -m …`` if the console script is not on ``$PATH``" names the command
first and the module as a remedy. What this refuses is the module presented as
the way in.

Asked from here because the answer is in the bricks' own
``[project.scripts]`` — nine files this repository can read at once and each
brick can only read one of. Each case skips when its sibling is not checked
out; ``scripts/fetch_siblings.sh`` is what puts them there, in CI and on a
machine that has only this clone.

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

#: ``python -m`` against one of this suite's script packages.
_INVOCATION = re.compile(r"python3? -m (sprezzature_\w+_scripts\.[\w.]+)")

#: A line that offers the module *after* the command, as a remedy for a
#: scripts directory that is not on ``$PATH``. Naming both is right.
_FALLBACK = re.compile(r"[Ff]alls back|fallback|not on `?\$PATH|\(none; run as")

#: Prose that asserts the absence of what the brick registers. Caught
#: separately from the invocations because the sentence outlives them: every
#: ``python -m`` can be corrected and the claim still sit there, now contradicted
#: by the lines under it.
_DENIAL = re.compile(
    r"(?:registers?|ships?|exposes?|has)\s+no\s+console\s+scripts?", re.I
)


def _commands_by_module() -> dict[str, str]:
    """Module to the command its brick registers for it, across the siblings."""
    out: dict[str, str] = {}
    for brick in SHIPPED_SKILLS:
        pyproject = SIBLINGS / brick / "pyproject.toml"
        if not pyproject.is_file():
            continue
        block = re.search(
            r"^\[project\.scripts\]\n(.*?)(?=^\[|\Z)",
            pyproject.read_text(encoding="utf-8"),
            re.M | re.S,
        )
        if block is None:
            continue
        for name, module in re.findall(
            r'^([\w.-]+)\s*=\s*"([\w.]+):\w+"', block.group(1), re.M
        ):
            out.setdefault(module, name)
    return out


def _shipped_prose() -> list[Path]:
    """Every Markdown file a skill ships: the contract and its references."""
    out: list[Path] = []
    for brick in SHIPPED_SKILLS:
        out.extend(
            f
            for f in sorted((REPO_ROOT / brick).rglob("*.md"))
            if "__pycache__" not in f.parts
        )
    return out


def test_there_is_prose_to_read() -> None:
    """A glob that stopped matching would make the cases below vacuous."""
    found = _shipped_prose()
    assert len(found) >= 40, len(found)


@pytest.mark.parametrize(
    "doc", _shipped_prose(), ids=lambda p: p.relative_to(Path(__file__).resolve().parent.parent).as_posix()
)
def test_no_shipped_line_routes_around_a_registered_command(doc: Path) -> None:
    """``python -m`` where a command exists works, and that is the problem."""
    known = _commands_by_module()
    if not known:
        pytest.skip("no sibling is checked out beside this repository")

    offences: list[str] = []
    for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        if _FALLBACK.search(line):
            continue
        for module in _INVOCATION.findall(line):
            command = known.get(module)
            if command is not None:
                offences.append(f"line {number}: `python -m {module}` → `{command}`")
    assert not offences, (
        f"{doc.relative_to(REPO_ROOT)} sends the reader through the module when "
        f"the brick registers a command for it:\n  " + "\n  ".join(offences)
    )


@pytest.mark.parametrize(
    "doc", _shipped_prose(), ids=lambda p: p.relative_to(Path(__file__).resolve().parent.parent).as_posix()
)
def test_no_shipped_line_says_a_brick_registers_nothing(doc: Path) -> None:
    """The sentence outlives the invocations it was written to justify."""
    known = set(_commands_by_module().values())
    if not known:
        pytest.skip("no sibling is checked out beside this repository")

    offences = [
        f"line {number}: {line.strip()[:120]}"
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1)
        if _DENIAL.search(line)
    ]
    assert not offences, (
        f"{doc.relative_to(REPO_ROOT)} states that a package registers no "
        f"console script. Between them the nine bricks register "
        f"{len(known)}:\n  " + "\n  ".join(offences)
    )
