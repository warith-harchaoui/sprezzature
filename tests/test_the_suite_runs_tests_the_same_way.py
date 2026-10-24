"""
The ten repositories run their tests the same way, and say what they ran.

Three properties of ``[tool.pytest.ini_options]``, asked from the one place
that sees every brick. Each brick's own suite can only check the brick it
lives in, and "do the nine agree" is not a question a single clone can ask.

**``--strict-markers``.** pytest warns about an unknown mark and then runs the
test anyway, so a typo in ``@pytest.mark.slow`` produces something that reads
as a marked test and behaves as an unmarked one. It cost
``sprezzature-accessibility`` seven LLM-quality tests running in every default
run for weeks -- tests that need Ollama, in a lane whose own comment said they
were excluded -- and that repository was the only one of the nine carrying the
flag. ``sprezzature-figures`` is where it matters most: four markers deselect
418 of its 1714 tests, so a misspelled marker name moves a test between lanes
in silence.

**No ``-q`` in ``addopts``.** ``-q`` there plus the ``-q`` a human types, or
the one a pre-push hook passes, is ``-qq``, and at that verbosity pytest drops
its final line: the run ends on the progress bar with no ``N passed`` at all.
Four of the ten were in that state. Failures still printed, so nothing was
ever wrong -- but a check that will not say what it did is the wrong default
for a suite whose argument is that a check must speak.

**``testpaths``.** Without it a bare ``pytest`` collects from the repository
root, which sweeps up whatever a build left behind. ``sprezzature-colors`` had
no pytest section at all.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 — tomllib landed in 3.11
    import tomli as tomllib

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def _checkout(brick: str) -> Path | None:
    """The sibling checkout for ``brick``, or ``None`` if this machine has none."""
    repo = REPO_ROOT.parent / brick
    return repo if repo.is_dir() else None


def _ini_options(repo: Path) -> dict[str, str] | None:
    """A repository's pytest settings, from wherever it keeps them.

    ``pytest.ini`` wins over ``pyproject.toml``, which is pytest's own order.
    Returns ``None`` when a repository declares pytest settings nowhere --
    itself a finding, and the reason this is not an exception.
    """
    ini = repo / "pytest.ini"
    if ini.is_file():
        parser = configparser.ConfigParser()
        parser.read_string(ini.read_text(encoding="utf-8"))
        if parser.has_section("pytest"):
            return dict(parser["pytest"])
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        table = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        options = table.get("tool", {}).get("pytest", {}).get("ini_options")
        if options is not None:
            return {k: str(v) for k, v in options.items()}
    return None


def _settings(brick_or_root: str) -> dict[str, str]:
    """Pytest settings for a brick name, or for this repository."""
    repo = REPO_ROOT if brick_or_root == "sprezzature" else _checkout(brick_or_root)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick_or_root}")
    options = _ini_options(repo)
    if options is None:
        pytest.fail(
            f"{brick_or_root} declares no pytest settings at all: no [pytest] "
            f"section in pytest.ini, no [tool.pytest.ini_options] in "
            f"pyproject.toml. A bare `pytest` there collects from the "
            f"repository root."
        )
    return options


#: Every repository whose test configuration this file checks: the nine bricks
#: and the hub, which has a suite of its own and the same obligations.
EVERY_REPO: tuple[str, ...] = ("sprezzature", *SHIPPED_SKILLS)


@pytest.mark.parametrize("repo", EVERY_REPO)
def test_a_repo_runs_with_strict_markers(repo: str) -> None:
    """``--strict-markers`` is on, so a misspelled marker fails collection."""
    addopts = _settings(repo).get("addopts", "")
    assert "--strict-markers" in addopts, (
        f"{repo} runs pytest without --strict-markers (addopts={addopts!r}). "
        f"A typo in a @pytest.mark name there is a warning and a test that "
        f"runs in the wrong lane."
    )


@pytest.mark.parametrize("repo", EVERY_REPO)
def test_a_repo_still_says_how_many_tests_ran(repo: str) -> None:
    """No ``-q`` in ``addopts``: ``pytest -q`` must still print its last line."""
    addopts = _settings(repo).get("addopts", "")
    quiet = [word for word in addopts.split() if word in ("-q", "--quiet")]
    assert not quiet, (
        f"{repo} has {quiet[0]} in addopts, so the `pytest -q` its hooks and "
        f"its contributors run is -qq and prints no `N passed` line at all. "
        f"Pass -q at the call site, not from the config."
    )


@pytest.mark.parametrize("repo", EVERY_REPO)
def test_a_repo_says_where_its_tests_live(repo: str) -> None:
    """``testpaths`` is declared, so collection does not start at the root."""
    settings = _settings(repo)
    assert settings.get("testpaths"), (
        f"{repo} declares no testpaths, so a bare `pytest` collects from the "
        f"repository root and sweeps up whatever a build left behind."
    )


def test_this_run_saw_bricks_to_check() -> None:
    """A file that skipped everything reads exactly like a file that passed."""
    seen = [brick for brick in SHIPPED_SKILLS if _checkout(brick) is not None]
    assert seen, (
        "no sibling checkout at all, so every brick above skipped. Run "
        "scripts/fetch_siblings.sh, which is what CI does."
    )
    assert _ini_options(REPO_ROOT), "read no pytest settings from this repository"
