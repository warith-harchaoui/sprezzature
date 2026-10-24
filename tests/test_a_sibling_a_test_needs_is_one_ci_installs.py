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
