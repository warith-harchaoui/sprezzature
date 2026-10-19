"""
A skill that says "invoked as `X …`" has to mean a command somebody can type.

Each of the nine ``SKILL.md`` files opens with a note pointing the reader at
the standalone package and naming how its tools are run. That sentence is the
agentic contract: a model reads it and runs what it says.

Two of them named a command that **nothing installed**. ``sprezzature-colors``
only ever put ``sprezzature-colors-contrast`` and its three siblings on the
PATH, and ``sprezzature-ux-laws`` only put ``sprezzature-ux-laws-audit``
there. Both became real on 2026-10-19, when those packages got their unified
front doors; before that an agent following the skill ran a command that did
not exist, and found out at the shell.

This is the same defect each package already guards *inside itself*
(``test_console_scripts_exist.py``: "every command the help text names has to
be a command you can run"). It could not catch this one, because the claim is
made here and the entry points are declared there. A guard belongs where it
can see both — which is this repository, the only place that holds all nine
skills and knows which package each belongs to.

Offline by construction: the sibling checkouts' ``pyproject.toml`` files are
read, not PyPI. When a sibling is absent the check skips rather than passes,
because a silent skip that looks like a pass is the failure this suite keeps
paying for.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent

#: The sentence every skill note carries, e.g. ``invoked as `make-map …```.
#: Backticked names only: prose that merely mentions a tool is not a claim
#: that it is on the PATH.
_INVOKED_RE = re.compile(r"invoked as (.+?)\.\s", re.S)

#: Each backticked run inside that sentence whose first word looks like a
#: **console script**, which in this suite means one of exactly two naming
#: conventions: ``make-…`` or ``sprezzature-…``. The first word only, because
#: a sentence writes the invocation as ``make-site <tool>``.
#:
#: Narrowed from "every backticked lowercase word". That version read the
#: sub-command names a sentence lists — ``lint``, ``alt``, ``text-spacing`` —
#: as console-script claims and failed on a skill that was telling the truth.
#: A sub-command named in prose is not a promise that it is on the PATH; the
#: promise is about the command you type first.
_NAME_RE = re.compile(r"`((?:make|sprezzature)-[a-z0-9-]*)(?:[^`]*)`")

_SCRIPTS_SECTION_RE = re.compile(
    r"^\[project\.scripts\]\s*$(.*?)(?=^\[|\Z)", re.M | re.S
)
_SCRIPT_ENTRY_RE = re.compile(r'^\s*([A-Za-z0-9._-]+)\s*=', re.M)


def _skills() -> list[Path]:
    """Every shipped ``SKILL.md`` in this repository."""
    return sorted(REPO_ROOT.glob("sprezzature-*/SKILL.md"))


def _declared_commands(package_dir: Path) -> set[str] | None:
    """Console scripts the sibling checkout declares, or ``None`` if absent."""
    pyproject = package_dir / "pyproject.toml"
    if not pyproject.is_file():
        return None
    section = _SCRIPTS_SECTION_RE.search(pyproject.read_text(encoding="utf-8"))
    if section is None:
        return set()
    return set(_SCRIPT_ENTRY_RE.findall(section.group(1)))


def _claimed_commands(skill: Path) -> set[str]:
    """Command names the skill's invocation sentence promises."""
    sentence = _INVOKED_RE.search(skill.read_text(encoding="utf-8"))
    if sentence is None:
        return set()
    claimed = set(_NAME_RE.findall(sentence.group(1)))
    # Suffix shorthands like `-html`, `-icons` continue the previous name and
    # are not commands on their own; the regex already excludes them by
    # requiring a leading letter.
    return claimed


def test_there_are_skills_to_check() -> None:
    """A glob that stops matching would make every test below vacuous."""
    assert len(_skills()) >= 8, [s.parent.name for s in _skills()]


@pytest.mark.parametrize("skill", _skills(), ids=lambda p: p.parent.name)
def test_every_command_a_skill_names_is_a_console_script(skill: Path) -> None:
    """The contract's commands exist in the package that ships them."""
    package = skill.parent.name
    declared = _declared_commands(SIBLINGS / package)
    if declared is None:
        pytest.skip(f"{package} is not checked out beside this repository")

    claimed = _claimed_commands(skill)
    assert claimed, f"{package}/SKILL.md has no 'invoked as' sentence to check"

    missing = sorted(c for c in claimed if c not in declared)
    assert not missing, (
        f"{package}/SKILL.md tells an agent to run {missing}, which "
        f"{package}/pyproject.toml does not install. Declared: "
        f"{sorted(declared)}"
    )


@pytest.mark.parametrize("skill", _skills(), ids=lambda p: p.parent.name)
def test_the_all_extra_floors_the_version_that_has_those_commands(
    skill: Path,
) -> None:
    """Naming a command is not enough if `all` can resolve to an older release.

    ``sprezzature-colors>=1.0.1`` satisfied the resolver while installing a
    release with no ``sprezzature-colors`` command in it. The floor has to be
    at least the version the sibling currently declares those commands at.
    """
    package = skill.parent.name
    sibling = SIBLINGS / package / "pyproject.toml"
    if not sibling.is_file():
        pytest.skip(f"{package} is not checked out beside this repository")

    version = re.search(
        r'^version\s*=\s*"([^"]+)"', sibling.read_text(encoding="utf-8"), re.M
    )
    assert version, f"{package} declares no version"

    ours = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor = re.search(
        rf'"{re.escape(package)}(?:\[[^\]]*\])?>=([0-9][0-9.]*)"', ours
    )
    if floor is None:
        pytest.skip(f"{package} is not in the `all` extra")

    def key(v: str) -> tuple[int, ...]:
        return tuple(int(part) for part in v.split("."))

    assert key(floor.group(1)) <= key(version.group(1)), (
        f"`all` floors {package} at {floor.group(1)}, which is ahead of the "
        f"{version.group(1)} the checkout declares — the extra cannot resolve"
    )
