"""
Every tool the `sprezzature` driver routes to has to be installable.

The driver is a published package whose whole job is to shell out somewhere
else. So each sub-command names a target, and every target is a promise about
a repository other than this one:

* ``console_script=`` — a command the brick registers in ``[project.scripts]``;
* ``module=`` — a module ``python -m`` can run from the installed brick;
* the script file name — the pre-split in-repo layout, a fallback only.

Nine sub-commands named none of the first two and shelled straight to
``<skill>/scripts/<file>.py``, from when the bricks still carried their scripts
here. They had all left. `sprezzature publish icons`, `… meta`, `… indexes`,
`… plain`, `… lint-md`, `… md-to-html`, `sprezzature vision alt`,
`… install` and `sprezzature ui validate` therefore exited 2 — "skill not
found" — on every clean checkout and every install, which is to say for every
user. On a developer's machine they resolved a folder, because the
``__pycache__`` nobody commits was enough to answer ``is_dir()``.

What this asks, from the one place that can see the bricks at once: a name the
driver routes to is a name the brick declares. Each case skips when its sibling
is not checked out, which the pre-push hook and CI both avoid: the workflow runs
``scripts/fetch_siblings.sh`` first. A skip here means a machine with fewer
clones, not a gap nobody checks.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent
DRIVER = REPO_ROOT / "sprezzature-cli" / "src" / "sprezzature_cli" / "cli.py"


def _routes() -> list[tuple[str, str | None, str | None]]:
    """Every ``_run_tool`` call in the driver, as (skill, console_script, module).

    Read from the syntax tree rather than by import: the keywords are literals
    at every call site, and parsing keeps this test free of Click and of the
    driver's own dependencies.
    """
    tree = ast.parse(DRIVER.read_text(encoding="utf-8"))
    out: list[tuple[str, str | None, str | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "_run_tool"):
            continue
        skill = node.args[0].value if isinstance(node.args[0], ast.Constant) else None
        if not isinstance(skill, str):  # not a literal: nothing to check
            continue
        kwargs = {
            k.arg: k.value.value
            for k in node.keywords
            if isinstance(k.value, ast.Constant) and isinstance(k.arg, str)
        }
        out.append((skill, kwargs.get("console_script"), kwargs.get("module")))
    return sorted(set(out), key=lambda r: tuple(x or "" for x in r))


def _declared_commands(repo: Path) -> set[str] | None:
    """A brick's ``[project.scripts]`` keys, or None when it is not checked out."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        return None
    block = re.search(
        r"^\[project\.scripts\]\n(.*?)(?=^\[|\Z)",
        pyproject.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    if block is None:
        return set()
    return set(re.findall(r"^([\w.-]+)\s*=", block.group(1), re.M))


def _entry_point_modules(repo: Path) -> set[str]:
    """The module half of every ``[project.scripts]`` value in a brick."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        return set()
    return set(
        re.findall(r'=\s*"([\w.]+):\w+"', pyproject.read_text(encoding="utf-8"))
    )


def _command_for_module(repo: Path, module: str) -> str | None:
    """The command a brick registers for `module`, if it registers one."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.is_file():
        return None
    block = re.search(
        r"^\[project\.scripts\]\n(.*?)(?=^\[|\Z)",
        pyproject.read_text(encoding="utf-8"),
        re.M | re.S,
    )
    if block is None:
        return None
    for name, named_module in re.findall(
        r'^([\w.-]+)\s*=\s*"([\w.]+):\w+"', block.group(1), re.M
    ):
        if named_module == module:
            return name
    return None


def test_the_driver_still_routes_somewhere() -> None:
    """A parse that stopped finding calls would make the cases below vacuous."""
    found = _routes()
    assert len(found) >= 10, found


@pytest.mark.parametrize(
    "route", _routes(), ids=lambda r: f"{r[0]}:{r[1] or r[2] or '?'}"
)
def test_a_routed_console_script_is_one_the_brick_declares(
    route: tuple[str, str | None, str | None],
) -> None:
    """``shutil.which`` on a name no brick registers can only ever miss."""
    skill, console_script, _ = route
    if console_script is None:
        pytest.skip(f"{skill} route declares no console script")
    declared = _declared_commands(SIBLINGS / skill)
    if declared is None:
        pytest.skip(f"{skill} is not checked out beside this repository")
    assert console_script in declared, (
        f"the driver runs {console_script!r} for {skill}, which "
        f"{skill}/pyproject.toml does not install. Declared: {sorted(declared)}"
    )


@pytest.mark.parametrize(
    "route", _routes(), ids=lambda r: f"{r[0]}:{r[2] or '-'}"
)
def test_a_routed_module_is_one_the_brick_ships(
    route: tuple[str, str | None, str | None],
) -> None:
    """The ``python -m`` fallback is the last one; a wrong name ends the chain.

    Checked against the brick's own entry points rather than its file tree:
    ``[project.scripts]`` is where the importable name is decided, and for
    these packages it differs from the folder on disk — ``scripts/`` is mapped
    to ``sprezzature_<brick>_scripts`` at build time, so looking for a
    directory of that name would find nothing.
    """
    skill, _, module = route
    if module is None:
        pytest.skip(f"{skill} route declares no module")
    repo = SIBLINGS / skill
    if not (repo / "pyproject.toml").is_file():
        pytest.skip(f"{skill} is not checked out beside this repository")
    known = _entry_point_modules(repo)
    assert module in known, (
        f"the driver falls back to `python -m {module}` for {skill}, a module "
        f"no entry point in {skill}/pyproject.toml names. Known: {sorted(known)}"
    )


@pytest.mark.parametrize(
    "route", _routes(), ids=lambda r: f"{r[0]}:{r[2] or '-'}"
)
def test_a_route_names_the_command_its_brick_registers(
    route: tuple[str, str | None, str | None],
) -> None:
    """Falling through to ``python -m`` is right only while there is no command.

    Three routes carried no ``console_script`` — the two colour tools and the
    caption installer — because when they were written their bricks registered
    none. They do now, and nothing said so: the module fallback still works, so
    the omission costs correctness nothing and is invisible from here. What it
    does cost is the one step that works for a user who installed the brick and
    never put this driver's Python on their path.
    """
    skill, console_script, module = route
    if module is None:
        pytest.skip(f"{skill} route declares no module")
    repo = SIBLINGS / skill
    if not (repo / "pyproject.toml").is_file():
        pytest.skip(f"{skill} is not checked out beside this repository")
    registered = _command_for_module(repo, module)
    if registered is None:
        assert console_script is None or console_script in (
            _declared_commands(repo) or set()
        ), (
            f"{skill} registers no command for {module}, and the driver names "
            f"{console_script!r}, which it does not install either."
        )
        return
    assert console_script == registered, (
        f"{skill} registers {registered!r} for {module}; the driver routes "
        f"through {console_script!r}."
    )
