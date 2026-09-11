"""
test_package_skill — the zip that the Claude skill-import form accepts.

What this checks
----------------
``scripts/package_skill.py`` exists because a 30.5 MB
``sprezzature-figures.zip`` was refused with "Zip file uncompressed size
exceeds 30MB", and because the 74 MB it unpacked to was showcase renders
with no generator code behind them. The tests below pin both halves of
that fix:

* every shipped skill's payload stays under the import ceiling, with
  the figures skill — the only one anywhere near it — checked explicitly;
* rendered showcase folders and tooling caches never enter a payload;
* a skill listed in ``EXTRACTED_CODE`` refuses to package when its
  standalone repo is absent, rather than quietly shipping prose alone;
* the archive extracts to ``<skill>/SKILL.md`` and the strict YAML
  validator still accepts what comes out.

The heavy end-to-end check — unzip, then run all 127 generators with no
``PYTHONPATH`` and no install — is not automated here: it needs the
standalone repo checked out beside the monorepo, which CI does not have.
The layout that makes it work is asserted instead, file by file.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from package_skill import (
    EXCLUDED_NAMES,
    EXTRACTED_CODE,
    MAX_UNCOMPRESSED_BYTES,
    SHOWCASE_DIRS,
    _default_code_root,
    build,
    plan_payload,
)
from skills_manifest import SHIPPED_SKILLS
from validate_skill import validate_skill

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def _code_root(skill: str) -> Path | None:
    """The standalone repo for `skill`, or None when it is not checked out."""
    return _default_code_root(skill, REPO_ROOT)


def _requires_code(skill: str) -> None:
    """Skip when `skill` needs a standalone repo that is not present."""
    if skill in EXTRACTED_CODE and _code_root(skill) is None:
        pytest.skip(f"{skill}: standalone repo not checked out beside the monorepo")


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_payload_fits_the_import_limit(skill: str) -> None:
    """Every skill packages to less than 30 MB uncompressed."""
    _requires_code(skill)
    entries = plan_payload(skill, REPO_ROOT, _code_root(skill))
    total: int = sum(entry.size for entry in entries)
    assert total <= MAX_UNCOMPRESSED_BYTES, (
        f"{skill}: {total / 1e6:.1f} MB uncompressed, over the limit"
    )


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_payload_carries_no_renders_or_caches(skill: str) -> None:
    """Showcase folders and tooling caches stay out of every payload."""
    _requires_code(skill)
    banned: frozenset[str] = SHOWCASE_DIRS | EXCLUDED_NAMES
    offenders: list[str] = [
        entry.arc.as_posix()
        for entry in plan_payload(skill, REPO_ROOT, _code_root(skill))
        if banned & set(entry.arc.parts)
    ]
    assert not offenders, f"{skill}: {offenders[:5]}"


def test_figures_ships_its_generators() -> None:
    """
    The figures payload carries runnable generators, not just prose.

    The 30.5 MB zip that triggered this module had 128 gallery PNGs and
    no ``make_*.py`` at all, because the monorepo dropped the scripts
    when the standalone repo was split out.
    """
    skill: str = "sprezzature-figures"
    _requires_code(skill)
    arcs: set[str] = {
        entry.arc.as_posix() for entry in plan_payload(skill, REPO_ROOT, _code_root(skill))
    }

    generators: set[str] = {a for a in arcs if "/make_" in a and a.endswith(".py")}
    assert len(generators) > 100, f"only {len(generators)} generators packaged"

    # The import layout that lets `python <skill>/scripts/make_bar.py`
    # run with no PYTHONPATH: font module inside scripts/, faces in the
    # sibling folder fonts.py resolves to. See EXTRACTED_CODE.
    assert f"{skill}/scripts/sprezzature_figures/__init__.py" in arcs
    assert f"{skill}/scripts/sprezzature_figures/fonts.py" in arcs
    assert any(
        a.startswith(f"{skill}/scripts/sprezzature_figures_fonts/") and a.endswith(".woff2")
        for a in arcs
    ), "no WOFF2 faces packaged; generated SVGs would lose their type"
    assert not any(a.endswith(".ttf") for a in arcs), "TTFs are raster-only ballast"


def test_missing_standalone_repo_is_an_error(tmp_path: Path) -> None:
    """Packaging fails loudly rather than shipping a skill with no code."""
    skill: str = next(iter(EXTRACTED_CODE))
    with pytest.raises(FileNotFoundError, match="nothing behind it|--code-from"):
        plan_payload(skill, REPO_ROOT, tmp_path)


@pytest.mark.parametrize("skill", SHIPPED_SKILLS)
def test_archive_extracts_to_a_valid_skill(skill: str, tmp_path: Path) -> None:
    """The written zip unpacks to ``<skill>/SKILL.md`` and validates."""
    _requires_code(skill)
    archive, _ = build(skill, REPO_ROOT, tmp_path / "out", _code_root(skill))
    assert archive is not None

    extracted: Path = tmp_path / "x"
    with zipfile.ZipFile(archive) as zf:
        names: list[str] = zf.namelist()
        assert all(n.startswith(f"{skill}/") for n in names), "skill must be the root"
        zf.extractall(extracted)

    assert validate_skill(extracted / skill) == []
