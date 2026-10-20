"""
A path this repository's own configuration names has to be there.

Four things tell a machine what to install, what to run, and what to read: the
GitHub workflows, the pre-commit manifest, ``requirements-dev.txt``, and
``llms.txt``. Between them they named twenty-three paths that had left with the
bricks when the monorepo was split, and nothing said so:

* ``ci.yml`` looped over two folders' ``requirements-*.txt`` — one of them
  ``sprezzature-vision``, a brick that merged into ``sprezzature-accessibility``
  in October. ``shopt -s nullglob`` turns a glob that matches nothing into
  nothing at all, so the step printed its name, installed none of what it
  announced, and went green;
* ``requirements-dev.txt`` told the reader to install
  ``sprezzature/scripts/requirements.txt`` for a full local environment, a file
  no clone has had for weeks;
* three of its own packages existed for ``tests/eval/``, which the split left
  behind as an empty directory. CI installed them on every job of every push to
  run nothing;
* ``llms.txt`` — the index a model reads first — linked eighteen scripts at
  paths inside the skill folders, from before each brick took its code to its
  own package, and a Montserrat font directory the three-Roboto rule replaced.

So the two shapes of the same defect: a *missing* path, which reads as "the
step did nothing because there was nothing to do", and an *empty* directory,
which reads as "the suite passed". Both look exactly like success.

Scope: what this repository can check about itself. Paths inside sibling
checkouts are a different question — the siblings may not be cloned here, and
`test_ci_reads_what_it_is_told.py` is where that is asked.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The files that tell a machine what to install and run. Prose is included on
#: purpose: a comment that points at a file which is gone misleads the next
#: reader exactly as much as a command that does.
CONFIGURATION: tuple[str, ...] = (
    ".github/workflows/*.yml",
    ".pre-commit-hooks.yaml",
    "requirements-dev.txt",
    # The index a model reads first, and the one where this went furthest:
    # nineteen of its links pointed at files the bundle no longer contained —
    # eighteen scripts that had moved into their bricks' own packages, and a
    # Montserrat font directory the three-Roboto rule replaced. A dead link in
    # a human README is an annoyance; here it is an instruction to open a file
    # that is not there.
    "llms.txt",
)

#: Repository-relative path, by its first segment. Anchored on the directories
#: this repository actually has at its root, so a bare word like ``figures`` or
#: a package name is not mistaken for a file.
_PATH = re.compile(
    r"\b(?:sprezzature(?:-[a-z-]+)?|tests|scripts|web|assets|docs)"
    r"(?:/[\w*.-]+)+"
)

#: Children that do not make a directory non-empty: build leftovers, and the
#: dotfiles a tool drops. ``tests/eval/`` held nothing but ``__pycache__`` and
#: still satisfied ``is_dir()``.
_NOT_CONTENT = ("__pycache__",)


def _configuration_files() -> list[Path]:
    """Every file in :data:`CONFIGURATION`, globs expanded."""
    out: list[Path] = []
    for pattern in CONFIGURATION:
        out.extend(sorted(REPO_ROOT.glob(pattern)))
    return out


def _named_paths(path: Path) -> list[str]:
    """Repository-relative paths one configuration file names.

    URLs go first: ``github.com/warith-harchaoui/sprezzature-figures`` is a
    remote, not a directory here. Then ``\\.`` — these files carry regular
    expressions, and ``scripts/build_triggers\\.py`` is the same path as
    ``scripts/build_triggers.py``.
    """
    text = re.sub(r"https?://\S+", " ", path.read_text(encoding="utf-8"))
    text = text.replace("\\.", ".")
    found = {m.rstrip(".,;:)`'\"").rstrip("/") for m in _PATH.findall(text)}
    return sorted(f for f in found if "/" in f)


def _complaint(named: str, target: Path) -> str | None:
    """What is wrong with `named`, or ``None`` if nothing is."""
    if "*" in named:
        if not list(REPO_ROOT.glob(named)):
            return (
                f"{named} matches nothing. A glob that matches nothing is not "
                f"an empty install, it is a silent one."
            )
        return None
    if not target.exists():
        return f"{named} is not there."
    if target.is_dir() and not any(
        c for c in target.iterdir() if c.name not in _NOT_CONTENT and not c.name.startswith(".")
    ):
        return (
            f"{named} is an empty directory. Whatever it was named for is "
            f"gone, and a suite with no tests in it passes."
        )
    return None


def test_there_is_configuration_to_read() -> None:
    """The globs above must still match, or the test below checks nothing."""
    found = _configuration_files()
    assert len(found) >= 4, [p.name for p in found]


@pytest.mark.parametrize(
    "config", _configuration_files(), ids=lambda p: p.relative_to(REPO_ROOT).as_posix()
)
def test_every_path_the_configuration_names_is_there(config: Path) -> None:
    """Named and absent, or named and empty — both read as success."""
    complaints = [
        f"{config.relative_to(REPO_ROOT)}: {complaint}"
        for named in _named_paths(config)
        if (complaint := _complaint(named, REPO_ROOT / named)) is not None
    ]
    assert not complaints, "\n".join(complaints)
