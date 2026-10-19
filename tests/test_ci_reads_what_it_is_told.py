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
nine siblings at once; each of them can only see itself.

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


def _workflow_text(repo: Path) -> str:
    """Every workflow in one repository, concatenated."""
    return "\n".join(
        f.read_text(encoding="utf-8")
        for f in sorted((repo / ".github" / "workflows").glob("*.yml"))
    )


def test_there_are_bricks_to_check() -> None:
    """A glob that stops matching would make the tests below vacuous."""
    found = _bricks()
    assert len(found) >= 8, [p.name for p in found]


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
