"""
Nothing here imports a standard-library module younger than the Python floor.

``pyproject.toml`` says this project supports Python 3.10, and the CI matrix
runs 3.10, 3.11 and 3.12 to mean it. A module that arrived in 3.11 therefore
imports fine on a developer's 3.13, fine on two thirds of the matrix, and
fails collection on the third — which is where it was found, after a push,
rather than before one.

``tomllib`` is the one that bit: three guards written on the same afternoon
each opened with a bare ``import tomllib``, and all three were an
``ImportError`` on 3.10. The repository already knew — two older test files
carry the ``tomli`` fallback and ``requirements-dev.txt`` declares
``tomli; python_version < '3.11'`` — so this was not a missing piece of
knowledge. It was knowledge that lived in two files and not in a check.

Only the standard library, and only the modules this project might plausibly
reach for. A third-party import is a dependency question, which
``requirements-dev.txt`` and a clean install already answer.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Standard-library module -> the Python version that first shipped it.
#: Short on purpose: a long list of modules nobody here imports would make
#: the guard look thorough and check nothing.
ARRIVED_IN: dict[str, tuple[int, int]] = {
    "tomllib": (3, 11),
    "graphlib": (3, 9),
    "zoneinfo": (3, 9),
    "importlib.resources": (3, 9),
}


def _floor() -> tuple[int, int]:
    """The oldest Python this project claims to support."""
    body = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    found = re.search(r'requires-python\s*=\s*"[^0-9]*(\d+)\.(\d+)', body)
    assert found, "pyproject.toml declares no requires-python"
    return int(found.group(1)), int(found.group(2))


def _python_files() -> list[Path]:
    return sorted(
        path
        for folder in ("tests", "scripts", "sprezzature")
        for path in (REPO_ROOT / folder).rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _unguarded_imports(source: str) -> set[str]:
    """Module names imported at the top level, outside any ``try``.

    An import inside ``try: … except ModuleNotFoundError`` is the fallback
    this guard exists to ask for, so it does not count. One inside a function
    does not either: it runs only when that path is taken, and the caller has
    decided it is reachable.
    """
    tree = ast.parse(source)
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def test_no_file_imports_a_module_younger_than_the_floor() -> None:
    """A guard written on 3.13 has to collect on the oldest version too."""
    major, minor = _floor()
    too_young = {
        name: version
        for name, version in ARRIVED_IN.items()
        if version > (major, minor)
    }
    assert too_young, (
        f"this project's floor is {major}.{minor} and every module in "
        f"ARRIVED_IN predates it, so this check examines nothing. Either the "
        f"floor moved up — in which case shorten the table — or the table "
        f"stopped describing anything."
    )

    offenders: dict[str, list[str]] = {}
    for path in _python_files():
        imported = _unguarded_imports(path.read_text(encoding="utf-8", errors="replace"))
        late = sorted(imported & set(too_young))
        if late:
            offenders[str(path.relative_to(REPO_ROOT))] = late
    assert not offenders, (
        f"these import a module the {major}.{minor} floor does not have, "
        f"unguarded: {offenders}. Wrap it in "
        f"`try: import x / except ModuleNotFoundError: import y as x`, which "
        f"is what the rest of this repository does for tomllib."
    )


def test_the_guarded_form_is_not_flagged() -> None:
    """The fallback the repository already uses has to pass this.

    Without it the check could be satisfied by deleting every import, and a
    rule nobody can satisfy is a rule somebody deletes.
    """
    guarded = (
        "try:\n"
        "    import tomllib\n"
        "except ModuleNotFoundError:\n"
        "    import tomli as tomllib\n"
    )
    assert "tomllib" not in _unguarded_imports(guarded)
    assert "tomllib" in _unguarded_imports("import tomllib\n")


def test_there_are_files_to_read() -> None:
    """A glob that stopped matching would make the check above vacuous."""
    files = _python_files()
    assert len(files) >= 50, f"read {len(files)} Python files from this repository"
