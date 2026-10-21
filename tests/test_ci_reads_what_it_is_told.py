"""
A test dependency declared where CI never looks is not declared.

`starlette` 1.9.0 moved its TestClient onto `httpx2`, and nine repositories in
this suite use that client. The fix went into `requirements-dev.txt` — correct
for the four whose workflow ends in `-r requirements-dev.txt`, and inert for
the four that install `pip install -e ".[dev,...]"` and never read the file.
`speaker-helper` came back red on exactly the same error after being "fixed",
which is how the gap showed.

So: a `requirements-dev.txt` that no workflow reads is a file that looks like
a declaration and is not one. Either the workflow reads it, or it should not
be there to be believed.

Checked from this repository because it is the only place that can see all
nine siblings at once; each of them can only see itself. "At once" means on a
machine that has them checked out — the pre-push hook, and CI too since
``scripts/fetch_siblings.sh`` fetches all nine metadata-only. It used to clone
one (the figures generators, for the release test), so eight of these cases
skipped there and a skip reads like a pass.

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


def _bricks() -> list[Path]:
    """Sibling checkouts that ship a skill, beside this repository."""
    return sorted(
        p
        for p in SIBLINGS.glob("sprezzature-*")
        if (p / "pyproject.toml").is_file() and (REPO_ROOT / p.name).is_dir()
    )


def _checkouts() -> list[Path]:
    """Every ``sprezzature-*`` clone beside this repository.

    Deliberately looser than :func:`_bricks` — it asks only "is there a clone
    here" — so the two can be compared without either one knowing how many
    siblings this particular machine happens to have.
    """
    return sorted(p for p in SIBLINGS.glob("sprezzature-*") if (p / ".git").exists())


def _workflow_text(repo: Path) -> str:
    """Every workflow in one repository, concatenated."""
    return "\n".join(
        f.read_text(encoding="utf-8")
        for f in sorted((repo / ".github" / "workflows").glob("*.yml"))
    )


def test_no_sibling_clone_escapes_the_tests_below() -> None:
    """A glob that stopped matching would make the tests below vacuous.

    Not "are the nine siblings here": how many are checked out is a property
    of the machine, not of this suite, and asserting a count red-lit CI back
    when it cloned one sibling deliberately — while saying nothing about the
    glob. That is the question ``audit_surfaces.py --require-checkouts`` asks
    in the workflow, where the count *is* known because the fetch step sets
    it; it is not a question a test can ask of an arbitrary machine. What
    has to hold is that every clone that *is* beside this repository is one the
    tests below look at. Rename a brick folder on one side only, or move a
    ``pyproject.toml``, and :func:`_bricks` quietly shrinks: the parametrised
    cases below would then vanish rather than fail, and a test that disappeared
    reads exactly like a test that passed.
    """
    seen = {p.name for p in _bricks()}
    missed = [p.name for p in _checkouts() if p.name not in seen]
    assert not missed, (
        f"{missed} sit beside this repository and nothing below looks at them. "
        f"A brick is only seen here when it carries a pyproject.toml of its own "
        f"and this repository ships a skill folder of the same name."
    )


@pytest.mark.parametrize("repo", _bricks(), ids=lambda p: p.name)
def test_a_requirements_dev_file_is_one_ci_reads(repo: Path) -> None:
    """Otherwise a dependency added there is added nowhere."""
    requirements = repo / "requirements-dev.txt"
    if not requirements.is_file():
        pytest.skip(f"{repo.name} has no requirements-dev.txt")
    workflows = _workflow_text(repo)
    if not workflows:
        pytest.skip(f"{repo.name} has no workflows")
    assert "requirements-dev" in workflows, (
        f"{repo.name} ships a requirements-dev.txt that no workflow installs. "
        f"Anything added to it is invisible to CI — put test dependencies in "
        f'the `dev` extra instead, which `pip install -e ".[dev,...]"` reads.'
    )


@pytest.mark.parametrize("repo", _bricks(), ids=lambda p: p.name)
def test_the_test_client_has_its_backend_where_ci_looks(repo: Path) -> None:
    """`httpx2` is the concrete case, and the one that went wrong.

    Not a general "every import is declared" check — that is what a clean
    virtualenv is for. This is the narrow, verified fact: starlette's
    TestClient needs httpx2 from 1.9.0, and a repository whose tests use it
    must declare it somewhere the install actually reaches.
    """
    tests = repo / "tests"
    if not tests.is_dir():
        pytest.skip(f"{repo.name} has no tests/")
    uses = any(
        "TestClient" in f.read_text(encoding="utf-8", errors="replace")
        for f in tests.rglob("*.py")
    )
    if not uses:
        pytest.skip(f"{repo.name} does not use starlette's TestClient")

    workflows = _workflow_text(repo)
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    requirements = repo / "requirements-dev.txt"

    reachable = False
    if "requirements-dev" in workflows and requirements.is_file():
        reachable |= "httpx2" in requirements.read_text(encoding="utf-8")
    # `pip install -e ".[dev,...]"` — the extras named on the install line.
    for extras in re.findall(r'pip install -e "\.\[([^\]]+)\]"', workflows):
        for extra in (name.strip() for name in extras.split(",")):
            block = re.search(
                rf"^{re.escape(extra)} = \[(.*?)\]", pyproject, re.M | re.S
            )
            if block and "httpx2" in block.group(1):
                reachable = True

    assert reachable, (
        f"{repo.name} uses starlette's TestClient, which needs httpx2 from "
        f"starlette 1.9.0, and nothing its CI installs declares it. The suite "
        f"will go red the next time the runner resolves a current starlette."
    )
