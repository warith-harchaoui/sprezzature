"""
test_version_consistency — the release version is single-valued across the repo.

The version is hand-maintained in three kinds of place:

* the ``metadata.version`` field of every ``sprezzature-*/SKILL.md`` (9 skills),
* the ``SKILL_VERSION`` literal in each skill's ``scripts/_argparse.py`` and
  ``scripts/_click.py`` copies,
* ``sprezzature-cli/pyproject.toml``'s ``project.version``,
* the repo-root ``pyproject.toml`` and ``sprezzature/__init__.py`` — the
  version of the ``sprezzature`` distribution itself. This pair was outside
  the sweep until 1.2.0, which is the worst place for a gap: it is the number
  PyPI shows and the one ``pip install sprezzature==`` resolves against.

A release bumps all of them. With that many hand-edited sources, a missed one is
the obvious failure mode — this test makes any drift a red build, and doubles as
a check that the CHANGELOG has a matching top section.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SKILL_VERSION_RE = re.compile(r'^\s*SKILL_VERSION\s*=\s*["\']([\d.]+)["\']', re.MULTILINE)
_METADATA_VERSION_RE = re.compile(r'^\s*version:\s*([\d.]+)\s*$', re.MULTILINE)
_DUNDER_VERSION_RE = re.compile(r'^\s*__version__\s*=\s*["\']([\d.]+)["\']', re.MULTILINE)
# Regex rather than ``tomllib``: that module is stdlib only on Python 3.11+, and
# this repo's floor is 3.10 (the CI matrix runs 3.10). ``[build-system]`` carries
# no ``version`` key, so the first ``version = "…"`` in the file is the project's.
_PYPROJECT_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([\d.]+)["\']', re.MULTILINE)


def _pyproject_version(path: Path) -> tuple[str, str]:
    m = _PYPROJECT_VERSION_RE.search(path.read_text(encoding="utf-8"))
    assert m, f"{path.relative_to(REPO_ROOT)} has no project version"
    return str(path.relative_to(REPO_ROOT)), m.group(1)


def _dunder_version(path: Path) -> tuple[str, str]:
    m = _DUNDER_VERSION_RE.search(path.read_text(encoding="utf-8"))
    assert m, f"{path.relative_to(REPO_ROOT)} has no __version__"
    return str(path.relative_to(REPO_ROOT)), m.group(1)


def _collect() -> dict[str, str]:
    """Map every version source (relative path) to the version string it declares."""
    sources: dict[str, str] = {}

    for skill_md in sorted(REPO_ROOT.glob("sprezzature-*/SKILL.md")):
        m = _METADATA_VERSION_RE.search(skill_md.read_text(encoding="utf-8"))
        assert m, f"{skill_md.relative_to(REPO_ROOT)} has no metadata.version"
        sources[str(skill_md.relative_to(REPO_ROOT))] = m.group(1)

    # Repo-root ``scripts/`` too, not just the per-skill copies: its
    # _argparse.py is what ``cleanup_local_skills.py --version`` prints, and
    # it sat at 1.0.1 through a 1.1.0 bump because this glob did not reach it.
    for helper in sorted(REPO_ROOT.glob("sprezzature-*/scripts/_argparse.py")) + \
            sorted(REPO_ROOT.glob("sprezzature-*/scripts/_click.py")) + \
            sorted(REPO_ROOT.glob("scripts/_argparse.py")) + \
            sorted(REPO_ROOT.glob("scripts/_click.py")):
        m = _SKILL_VERSION_RE.search(helper.read_text(encoding="utf-8"))
        if m:  # not every helper defines it; check the ones that do
            sources[str(helper.relative_to(REPO_ROOT))] = m.group(1)

    for pyproject in (REPO_ROOT / "pyproject.toml",
                      REPO_ROOT / "sprezzature-cli" / "pyproject.toml"):
        rel, version = _pyproject_version(pyproject)
        sources[rel] = version

    # The installed packages' ``__version__`` — what ``sprezzature --version``
    # prints, and what ``sprezzature.__version__`` reports to anything that asks.
    for init_py in (REPO_ROOT / "sprezzature" / "__init__.py",
                    REPO_ROOT / "sprezzature-cli" / "src" / "sprezzature_cli" / "__init__.py"):
        rel, version = _dunder_version(init_py)
        sources[rel] = version

    return sources


def test_all_version_sources_agree() -> None:
    """Every SKILL.md, SKILL_VERSION literal, and pyproject version must match."""
    sources = _collect()
    distinct = set(sources.values())
    assert len(distinct) == 1, (
        "version drift across the repo — every source must declare the same version.\n"
        + "\n".join(f"  {v}  <- {p}" for p, v in sorted(sources.items()))
    )


def test_changelog_has_matching_top_section() -> None:
    """The CHANGELOG's most recent ``## [x.y.z]`` section must match the version."""
    (version,) = set(_collect().values())
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s*\[([\d.]+)\]", changelog, re.MULTILINE)
    assert m, "CHANGELOG.md has no '## [x.y.z]' release section"
    assert m.group(1) == version, (
        f"CHANGELOG top section is [{m.group(1)}] but the repo version is {version}. "
        "Add the release section before tagging."
    )
