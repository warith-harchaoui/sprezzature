"""
Shared: a package may not promise a Python its dependencies cannot deliver.

``requires-python`` is a promise to anyone running ``pip install``. A
dependency's ``requires-python`` is the same promise one level down, and it
binds just as hard: if ``wallet-helper`` cannot be installed on 3.14, nothing
requiring it can be either, whatever the manifest says.

The question that decides, and the two that do not
--------------------------------------------------
It took three readings to get right, and the two cheap ones each produced a
confident and false accusation:

1. **The floor's window.** Says nothing: a resolver takes the newest release
   that fits, not the oldest. This reading accused ``sprezzature-figures`` of
   promising two Pythons it could not deliver, over a ``dowhy`` floor capped
   at ``<3.12`` — and a later ``dowhy`` lifts the bound.
2. **The newest release's window.** Right for a *ceiling* — if even the newest
   excludes 3.14, nothing works — and wrong in the mirror: on 3.10 a resolver
   installs an old ``numpy``, not today's. This reading flagged six bricks,
   all of them healthy.
3. **Reachability.** For each Python a manifest claims, does *some* release
   its specifier accepts admit that Python? That is the one. With it, the
   eleven bricks measured on 2026-11-02 are sound, and the one real defect —
   ``sprezzature-accessibility`` claiming 3.14 over a ``wallet-helper`` that
   has never published a release reaching it — still shows.

A wrong measurement does not produce silence. It produces certainty.

Why this file is duplicated
---------------------------
It is copied into each brick on purpose, like the skill helpers: a brick's
tests have to run from its own checkout with nothing but its dev
dependencies, so they cannot import a shared package from a sibling. The
duplication is safe only while the copies stay identical, which
``sprezzature/scripts/sync_helpers.py`` is what keeps true — edit the
canonical copy in ``sprezzature-accessibility`` and propagate.

Reading the manifest without a parser
-------------------------------------
Deliberately regex, not ``tomllib``. ``tomllib`` landed in 3.11 and several of
these packages floor at **3.10**, so importing it fails at *collection* on the
oldest interpreter in the matrix — green on a developer's 3.13, red on the
runner, with a ``ModuleNotFoundError`` naming no test. Measured the hard way
on 2026-11-02. The two shapes needed here are a quoted scalar and a flat array
of strings, and neither needs a parser.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

#: The minor versions a promise is checked against. 3.14 is the one that
#: exists and that several ``*-helper`` packages stop short of; 3.15 is here
#: so a ceiling moving up is noticed before the interpreter ships.
CANDIDATES: tuple[str, ...] = ("3.10", "3.11", "3.12", "3.13", "3.14", "3.15")

_REQUIRES_PYTHON = re.compile(r'^requires-python\s*=\s*"([^"]+)"', re.M)
_DEPENDENCIES = re.compile(r"^dependencies\s*=\s*\[(.*?)^\]", re.S | re.M)


def promise(manifest: Path) -> str:
    """The ``requires-python`` string the manifest declares."""
    found = _REQUIRES_PYTHON.search(manifest.read_text(encoding="utf-8"))
    assert found, f"{manifest} declares no requires-python"
    return found.group(1)


def dependency_names(manifest: Path) -> list[str]:
    """The base dependencies, names only, in declaration order."""
    block = _DEPENDENCIES.search(manifest.read_text(encoding="utf-8"))
    assert block, f"{manifest} has no [project] dependencies array"
    # Comments inside the array quote specifiers too ("it was \">=1.0\""), so
    # they go before anything is read as a dependency.
    body = re.sub(r"#[^\n]*", "", block.group(1))
    return [
        re.split(r"[<>=~\[; !]", m.group(1))[0].strip()
        for m in re.finditer(r'"([^"]+)"', body)
    ]


def admits(specifier: str, version: str) -> bool:
    """Whether a ``requires-python`` string admits this minor version.

    ``packaging`` is imported here rather than at module scope so that an
    environment without it fails one assertion instead of a whole collection.
    It arrives with pytest (``packaging>=22``), so it is there wherever these
    tests run.
    """
    from packaging.specifiers import SpecifierSet

    if not specifier:
        return True
    return SpecifierSet(specifier).contains(f"{version}.0")


def overreach(
    manifest: Path, measured: dict[str, tuple[str, ...]], version: str
) -> list[str]:
    """Dependencies that cannot be installed on a Python the manifest claims.

    Empty when the manifest does not claim that version — there is nothing to
    keep — and empty when every dependency reaches it.
    """
    if not admits(promise(manifest), version):
        return []
    names = dependency_names(manifest)
    return sorted(
        f"{name} (reaches {', '.join(reach) or 'nothing'})"
        for name, reach in measured.items()
        if name in names and version not in reach
    )
