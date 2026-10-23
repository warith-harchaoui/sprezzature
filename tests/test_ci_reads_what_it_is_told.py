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
import yaml

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


#: Repositories whose workflows this file holds to the same two settings: the
#: nine bricks and the hub, which pays for the same runners.
def _every_repo() -> list[Path]:
    return [REPO_ROOT, *_bricks()]


def _workflows(repo: Path) -> list[Path]:
    folder = repo / ".github" / "workflows"
    return sorted(folder.glob("*.yml")) if folder.is_dir() else []


@pytest.mark.parametrize("repo", _every_repo(), ids=lambda p: p.name)
def test_every_job_has_a_ceiling(repo: Path) -> None:
    """A hung job stops at a wall instead of running until GitHub's six hours.

    Not a budget — the numbers are far above what any of these suites takes,
    and `sprezzature-maps` is deliberately slow for reasons measured and
    written down in its own workflow. It is the difference between a job that
    fails and a job that is still "in progress" tomorrow. None of the ten had
    one.
    """
    workflows = _workflows(repo)
    if not workflows:
        pytest.skip(f"{repo.name} has no workflows")
    uncapped: list[str] = []
    for workflow in workflows:
        doc = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        for name, job in (doc.get("jobs") or {}).items():
            if not isinstance(job, dict) or "timeout-minutes" not in job:
                uncapped.append(f"{workflow.name}:{name}")
    assert not uncapped, (
        f"{repo.name} has jobs with no timeout-minutes: {uncapped}. A job that "
        f"hangs there runs for six hours before GitHub stops it."
    )


@pytest.mark.parametrize("repo", _every_repo(), ids=lambda p: p.name)
def test_the_test_workflow_cancels_a_superseded_run(repo: Path) -> None:
    """Two pushes a minute apart do not run two full matrices to the end.

    Only the test workflow. A release or a publish workflow must never be
    cancelled halfway by the next push, which is why those are left alone and
    this check names `ci.yml` rather than looping over every file.
    """
    ci = repo / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        pytest.skip(f"{repo.name} has no ci.yml")
    doc = yaml.safe_load(ci.read_text(encoding="utf-8")) or {}
    group = (doc.get("concurrency") or {}).get("group")
    assert group, (
        f"{repo.name}/ci.yml declares no concurrency group, so a push that "
        f"follows another runs a second full matrix to the end for a commit "
        f"nobody will look at."
    )
    assert (doc.get("concurrency") or {}).get("cancel-in-progress") is True, (
        f"{repo.name}/ci.yml groups its runs and does not cancel them, which "
        f"queues the superseded run instead of stopping it."
    )


@pytest.mark.parametrize("repo", _bricks(), ids=lambda p: p.name)
def test_ci_installs_the_test_dependencies_somehow(repo: Path) -> None:
    """pytest reaches the runner by one of the two routes, and one is enough.

    Seven bricks ship a ``requirements-dev.txt`` and name it on the install
    line; ``sprezzature-publish`` and ``sprezzature-ui`` put the same packages
    in a ``dev`` extra and install ``.[dev,...]``. Both work. The test above
    asks only "is a shipped requirements-dev.txt one CI reads", so for those
    two it skipped — and a skip reads exactly like a pass, which is how a
    brick with *neither* route would look from here.

    So this asks the question that actually matters, of all nine: whatever a
    brick's CI installs, does pytest arrive? A workflow that runs the suite
    without installing it fails loudly on the runner, but only after the push,
    and only for whoever pushed.
    """
    workflows = _workflow_text(repo)
    if not workflows:
        pytest.skip(f"{repo.name} has no workflows")
    if "pytest" not in workflows:
        pytest.skip(f"{repo.name}'s workflows do not run pytest")

    requirements = repo / "requirements-dev.txt"
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")

    routes: list[str] = []
    if "requirements-dev" in workflows and requirements.is_file():
        if "pytest" in requirements.read_text(encoding="utf-8"):
            routes.append("requirements-dev.txt")
    for extras in re.findall(r'pip install -e "\.\[([^\]]+)\]"', workflows):
        for extra in (name.strip() for name in extras.split(",")):
            block = re.search(
                rf"^{re.escape(extra)} = \[(.*?)\]", pyproject, re.M | re.S
            )
            if block and "pytest" in block.group(1):
                routes.append(f"the `{extra}` extra")

    assert routes, (
        f"{repo.name}'s CI runs pytest and nothing it installs declares "
        f"pytest: no requirements-dev.txt on the install line, and no extra "
        f"named there that carries it. The suite would only say so on the "
        f"runner, after the push."
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
