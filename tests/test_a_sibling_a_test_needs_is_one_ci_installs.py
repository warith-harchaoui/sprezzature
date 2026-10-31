"""
A test that skips for want of a sibling package names it as a dev dependency.

Two bricks reached across to a neighbour and skipped when it was absent:

* ``sprezzature-ui`` runs ``sprezzature-accessibility``'s linter over the
  markup it ships — it is the package whose job is to set the example, and an
  exemplar that fails the suite's own lint is worth nothing. Sixteen cases.
* ``sprezzature-publish`` checks that the engine command it builds names a
  module that really exists in ``sprezzature-audio``. One case, whose own
  docstring says it "passed on every developer's laptop and failed on the one
  environment that installs nothing extra".

Both skipped rather than failing, which is the same silence with a friendlier
face: on a runner the neighbour is never installed, so those seventeen checks
were dormant in the one place they were written for, and the summary line read
seventeen passes.

The rule, then: if a brick's tests can skip because a *sibling of this suite*
is missing, that sibling belongs in the brick's ``dev`` extra. Not in its
runtime dependencies — none of this is needed to use the package — and not
only on the workflow's install line, so that a contributor running
``pip install -e ".[dev]"`` gets the whole suite rather than a weaker one.

Read statically, from here, because the question spans two repositories and
neither can ask it alone.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 — tomllib landed in 3.11
    import tomli as tomllib

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent

#: A ``pytest.skip`` whose reason names a sibling **package**. The name must
#: not be followed by ``/``: ``sprezzature-accessibility/scripts/install.py``
#: inside a skip message is a path in a hint, not a thing pip installs.
#:
#: The first version was ``[^)]*?`` under ``re.S``, which let the match run
#: across statements and found a sibling named in an unrelated skip four lines
#: below — it reported ``sprezzature-publish`` as reaching for the a11y linter
#: on the strength of an "install Ollama like this" hint. A guard whose first
#: run produces a false positive is a guard nobody will trust the second time.
_SKIP_REASON = re.compile(
    r"""pytest\.skip\(\s*f?["'][^"'\n]*?(sprezzature-[a-z-]+)(?!/)"""
)

#: Not the opt-in eval lane. Those tests skip on a *daemon* being unreachable,
#: not on a package being absent, and no install here would wake them.
_OPT_IN_LANES: tuple[str, ...] = ("eval",)


def _checkout(brick: str) -> Path | None:
    repo = REPO_ROOT.parent / brick
    return repo if (repo / "pyproject.toml").is_file() else None


def _dev_dependencies(repo: Path) -> set[str]:
    """Every sibling named anywhere in the brick's optional dependencies.

    Any extra counts, not only ``dev``: a brick that pulls a sibling through
    ``[all]`` or a named feature extra has the same effect, as long as its own
    workflow installs that extra. Which extras the workflow installs is
    ``test_ci_installs_the_test_dependencies_somehow``'s question.
    """
    table = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    extras = table.get("project", {}).get("optional-dependencies", {})
    named: set[str] = set()
    for requirements in extras.values():
        for requirement in requirements:
            found = re.match(r"(sprezzature-[a-z-]+)", str(requirement))
            if found:
                named.add(found.group(1))
    return named


def _siblings_skipped_over(repo: Path) -> set[str]:
    """Siblings this brick's tests name in a skip reason."""
    tests = repo / "tests"
    if not tests.is_dir():
        return set()
    wanted: set[str] = set()
    own = repo.name
    for module in tests.rglob("*.py"):
        if any(part in _OPT_IN_LANES for part in module.relative_to(tests).parts):
            continue
        body = module.read_text(encoding="utf-8", errors="replace")
        for name in _SKIP_REASON.findall(body):
            if name != own and name in SHIPPED_SKILLS:
                wanted.add(name)
    return wanted


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_sibling_a_test_skips_over_is_a_declared_extra(brick: str) -> None:
    """Nothing a brick's suite reaches for is absent from its own extras."""
    repo = _checkout(brick)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick}")
    wanted = _siblings_skipped_over(repo)
    if not wanted:
        pytest.skip(f"{brick}'s tests skip over no sibling")
    undeclared = sorted(wanted - _dev_dependencies(repo))
    assert not undeclared, (
        f"{brick} has tests that skip when {undeclared} is missing, and names "
        f"it in no extra of its own. On a runner it is never installed, so "
        f"those cases are dormant in the one place they were written for — "
        f"and a skip reads exactly like a pass."
    )


def test_this_run_found_a_brick_that_reaches_across() -> None:
    """A regex that stopped matching would make every case above skip.

    Two bricks reach across today. If that drops to zero, either the pattern
    broke or the suite stopped checking across packages — and the second
    would be worth knowing too.
    """
    here = [b for b in SHIPPED_SKILLS if _checkout(b) is not None]
    if not here:
        pytest.skip("no sibling checkout; CI runs scripts/fetch_siblings.sh first")
    reaching = {
        brick: sorted(_siblings_skipped_over(_checkout(brick)))  # type: ignore[arg-type]
        for brick in here
    }
    assert any(reaching.values()), (
        f"no brick's tests name a sibling in a skip reason: {reaching}. Either "
        f"_SKIP_REASON stopped matching or the cross-package checks are gone."
    )


# --------------------------------------------------------------------------
# The same rule, turned on the repository that wrote it
# --------------------------------------------------------------------------
#
# Everything above reads the *bricks'* suites. The hub's own tests were never
# asked the question, and on 2026-10-31 three of them were answering it badly:
# the caption auditor and the two guards beside it reach `sprezzature_audio`
# through `pytest.importorskip`, nothing installed it on a runner, and all
# three skipped there. The caption work of that day had just put 22 tracks and
# their voice stamps into the clone so that the audit *could* run in CI — and
# it still would not have.
#
# Two reasons this was invisible to the cases above. `_SKIP_REASON` matches
# `pytest.skip(...)`, not `pytest.importorskip(...)`; and it matches a
# distribution name with hyphens, where an import is spelled with underscores.
#
# The distinction the rule turns on is worth keeping straight, because the
# broadened pattern first made it look as though five siblings were missing.
# A test that skips on a sibling **checkout** — a file read by path, with the
# skip reason naming `sprezzature-figures/scripts/...` — is served by
# `scripts/fetch_siblings.sh` and needs no install. Only a skip on an
# **importable package** needs pip. Measured: of the five, three were checkout
# skips and were already fine in CI.

#: A sibling the hub imports through ``pytest.importorskip``, spelled as a
#: module. Converted to its distribution name by the test.
_IMPORT_OR_SKIP = re.compile(
    r"""pytest\.importorskip\(\s*["'](sprezzature_[a-z_]+)["']"""
)

#: Siblings whose install this repository declines, with the measurement that
#: decided it and the guard that sleeps as a result.
#:
#: An exemption, not a silence: every entry names a cost and a consequence, and
#: the test below fails if an entry stops being needed, so the list can only
#: shrink by being correct. `sprezzature-audio` is deliberately absent from it —
#: four packages and 13 MB in a clean venv, against three guards.
_NOT_INSTALLED_ON_PURPOSE = {
    "sprezzature-video": (
        "21 packages and 161 MB in a clean venv, on three matrix jobs per "
        "push, to wake one guard: "
        "tests/test_every_film_pitches_in_the_voice_too.py"
    ),
}


def _hub_imports_or_skips() -> set[str]:
    """Siblings the hub's own tests reach through ``pytest.importorskip``."""
    wanted: set[str] = set()
    for module in (REPO_ROOT / "tests").rglob("*.py"):
        body = module.read_text(encoding="utf-8", errors="replace")
        for name in _IMPORT_OR_SKIP.findall(body):
            distribution = name.replace("_", "-")
            if distribution in SHIPPED_SKILLS:
                wanted.add(distribution)
    return wanted


def _ci_installs() -> set[str]:
    """Siblings a runner ends up with, read from what the workflow installs.

    ``requirements-dev.txt`` is the whole runtime install for this repository
    — the workflow's own comment says so — plus ``./sprezzature-cli`` for the
    driver. Read from the file rather than from the environment: the question
    is what a runner gets, and this machine has every brick installed as an
    editable, which is exactly why the gap was invisible here.
    """
    text = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    installed = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        found = re.match(r"(sprezzature-[a-z-]+)", line)
        if found:
            installed.add(found.group(1))
    return installed | {"sprezzature-cli"}


def test_a_sibling_the_hubs_own_tests_import_is_one_its_ci_installs() -> None:
    """Nothing the hub's suite imports is absent from what a runner installs.

    Except by name, in :data:`_NOT_INSTALLED_ON_PURPOSE`, with its price.
    """
    wanted = _hub_imports_or_skips()
    assert wanted, (
        "no hub test reaches a sibling through pytest.importorskip, which "
        "either means the pattern stopped matching or the cross-package "
        "guards left — and the second would be worth knowing too"
    )
    dormant = sorted(wanted - _ci_installs() - set(_NOT_INSTALLED_ON_PURPOSE))
    assert not dormant, (
        f"the hub's tests import {dormant} through pytest.importorskip and no "
        f"runner installs it, so those cases are dormant in the one place they "
        f"were written for. Add it to requirements-dev.txt, or name it in "
        f"_NOT_INSTALLED_ON_PURPOSE with what it costs and what sleeps."
    )


def test_no_exemption_outlives_the_reason_for_it() -> None:
    """An entry in the deferral list is still a sibling some test reaches for.

    Without this the list is write-only. A guard that stops importing a brick
    would leave its name here for ever, and the next reader would take the
    exemption for a standing decision instead of a stale one.
    """
    wanted = _hub_imports_or_skips()
    installed = _ci_installs()
    stale = sorted(name for name in _NOT_INSTALLED_ON_PURPOSE if name not in wanted)
    assert not stale, (
        f"_NOT_INSTALLED_ON_PURPOSE names {stale}, which no hub test imports "
        f"any more. Remove the entry rather than leaving a deferral nobody is "
        f"deferring."
    )
    both = sorted(set(_NOT_INSTALLED_ON_PURPOSE) & installed)
    assert not both, (
        f"{both} is both declined in _NOT_INSTALLED_ON_PURPOSE and installed "
        f"by requirements-dev.txt. One of the two is out of date."
    )
