"""
The one check nothing was doing: does this package still build?

The monorepo's `[tool.setuptools]` names every skill folder it ships. When
`sprezzature-vision` was merged into `sprezzature-accessibility` on
2026-10-17, the folder went and three lines naming it stayed — so `python -m
build` failed with `package directory 'sprezzature-vision' does not exist`,
and had done for two days.

Nothing caught it because nothing built. The tests pass against the source
tree, the audit reads sibling checkouts, and the wheel is only made just
before a release — which is exactly when a two-day-old packaging break is
most expensive to discover.

This asks the question cheaply: every folder the packaging claims to ship has
to exist. The full `python -m build` is the honest version and is too slow for
every run; the claim it would catch is this one.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 — tomllib landed in 3.11
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PACKAGE_DIR: dict[str, str] = (
    PYPROJECT.get("tool", {}).get("setuptools", {}).get("package-dir", {})
)
PACKAGES: list[str] = (
    PYPROJECT.get("tool", {}).get("setuptools", {}).get("packages", [])
)


def test_the_packaging_declares_something() -> None:
    """An empty table would make the checks below pass by testing nothing."""
    assert PACKAGES, "no packages declared — did the build backend change?"


def _tracked(folder: str) -> list[str]:
    """The git-tracked files under a folder."""
    import subprocess

    done = subprocess.run(
        ["git", "ls-files", folder],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return [line for line in done.stdout.splitlines() if line.strip()]


@pytest.mark.parametrize("name,folder", sorted(PACKAGE_DIR.items()))
def test_every_mapped_folder_ships_something(name: str, folder: str) -> None:
    """A mapped folder has to hold *tracked* files, not merely exist.

    "Does the directory exist" is the obvious check and it is the wrong one.
    When `sprezzature-vision` was merged into `sprezzature-accessibility`, the
    folder stayed behind on disk holding a `.DS_Store` and a `__pycache__` —
    so it existed, and a first version of this test passed. The build still
    failed, because a build works from *tracked* files and there were none:
    `package directory 'sprezzature-vision' does not exist`.

    The two questions look identical from a working tree and differ exactly
    where it matters.
    """
    assert (ROOT / folder).is_dir(), f"`{name}` maps to `{folder}/`, which is gone"
    assert _tracked(folder), (
        f"`{name}` maps to `{folder}/`, which holds nothing git tracks. It "
        f"exists here and not in a build, so `python -m build` fails on it — "
        f"days after whatever emptied it, at release time."
    )


@pytest.mark.parametrize("package", sorted(PACKAGES))
def test_every_declared_package_resolves(package: str) -> None:
    """Either it is mapped to a folder, or it is a real directory path."""
    if package in PACKAGE_DIR:
        return  # covered by the test above
    assert (ROOT / Path(*package.split("."))).is_dir(), package


def test_every_shipped_skill_is_one_the_suite_still_has() -> None:
    """The reverse direction, which the mapping check cannot see.

    A skill folder present on disk but absent from the packaging ships
    nothing — the quieter half of the same drift, and the one that produces a
    wheel missing a skill rather than a build that fails loudly.
    """
    shipped = {folder for folder in PACKAGE_DIR.values()}
    on_disk = {
        p.name
        for p in ROOT.glob("sprezzature-*")
        if p.is_dir() and (p / "SKILL.md").is_file()
    }
    missing = on_disk - shipped
    assert not missing, f"skills on disk but not packaged: {sorted(missing)}"
