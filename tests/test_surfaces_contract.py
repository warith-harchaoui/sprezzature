"""
Tests for the five-surface contract — the offline half.

``scripts/audit_surfaces.py`` answers "which brick holds which surface right
now", and it has to look at the **sibling repositories** next to this one to do
it. CI has none of them, and neither does anyone who cloned a single repo. So
the live audit stays a script, and what is tested here is the half that travels
with the checkout: that the contract is complete, that every exemption carries
its reason, and that the auditor's own detectors can tell a brick that holds a
surface from one that does not.

That last part matters more than it looks. An auditor that answers "ok" to
everything passes every test that only checks it runs. The detectors are
therefore exercised against a brick built in a temporary directory — once
whole, once with one surface removed — so a detector that stopped detecting
fails here rather than being discovered the day someone trusts a green table.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _auditor():
    """Load ``scripts/audit_surfaces.py`` as a module."""
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "_audit_surfaces", ROOT / "scripts" / "audit_surfaces.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = _auditor()
SURFACES_MD = (ROOT / "SURFACES.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# The contract is complete and says the same thing in both places
# --------------------------------------------------------------------------


def test_the_five_surfaces_are_the_five_surfaces() -> None:
    """
    The tuple in the auditor is the contract.

    Pinned by name: adding a sixth is a change of doctrine and should cost a
    deliberate edit here, not slip in as a detail.
    """
    assert AUDIT.SURFACES == ("library", "cli", "api", "mcp", "skill")


def test_surfaces_md_describes_all_five_and_points_at_the_state() -> None:
    """
    The doctrine covers each surface, and sends the reader to the live state.

    Deliberately *not* "names every brick": the contract is per-surface, and a
    file listing ten folder names would go stale the day an eleventh arrives.
    What must not go stale is that each of the five is explained, and that the
    reader is told where to find which brick holds what today — otherwise
    SURFACES.md becomes a frozen table claiming things that stopped being
    true.
    """
    for surface in ("Library", "Command line", "HTTP API", "MCP", "Skill"):
        assert f"**{surface}**" in SURFACES_MD, f"{surface} is not described"
    assert "scripts/audit_surfaces.py" in SURFACES_MD
    assert "SKILLS.txt" in SURFACES_MD


def test_every_exemption_names_a_real_brick_and_a_real_surface() -> None:
    """An exemption for a brick or surface that does not exist is a typo."""
    for brick, surface in AUDIT.EXEMPTIONS:
        assert brick in AUDIT.SHIPPED_SKILLS, f"{brick} is not in SKILLS.txt"
        assert surface in AUDIT.SURFACES, f"{surface} is not one of the five"


def test_every_exemption_carries_a_reason() -> None:
    """
    The reason is the whole point of the table.

    Without it the output cannot distinguish "it would be wrong to build this"
    from "nobody got to it yet", which is exactly the confusion the contract
    exists to remove. A one-word reason is not a reason.
    """
    for (brick, surface), reason in AUDIT.EXEMPTIONS.items():
        assert len(reason.split()) >= 10, (
            f"the exemption for {brick}/{surface} needs a reason that explains "
            f"itself, got {reason!r}"
        )


def test_compose_is_owed_wherever_docker_is() -> None:
    """
    No brick may ship a Dockerfile without a compose file beside it.

    Written as a constant so the rule is greppable, and asserted here so it
    cannot be quietly relaxed back into "only when there is a second
    container" — which is how a Dockerfile's port, volume, environment and
    command end up being reconstructed by the next reader, and got wrong.
    """
    assert AUDIT.COMPOSE_IS_OWED_WITH_DOCKER is True
    assert "docker-compose.yml" in SURFACES_MD


# --------------------------------------------------------------------------
# The detectors can actually tell the two cases apart
# --------------------------------------------------------------------------


PYPROJECT = """\
[project]
name = "sprezzature-demo"
version = "0.1.0"

[project.optional-dependencies]
cli = ["click>=8.1"]
api = ["fastapi>=0.115"]
mcp = ["fastapi-mcp>=0.3"]

[project.scripts]
make-demo = "sprezzature_demo.cli:main"
sprezzature-demo = "sprezzature_demo.cli_click:main"
sprezzature-demo-mcp = "sprezzature_demo.mcp:main"

[tool.setuptools.package-dir]
"sprezzature_demo_scripts" = "scripts"
"""


def _build_brick(root: Path) -> Path:
    """Write a brick that holds every surface, and return its repo path."""
    repo = root / "sprezzature-demo"
    package = repo / "sprezzature_demo"
    package.mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / ".git").mkdir()
    (repo / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (package / "__init__.py").write_text(
        '"""demo."""\n\nfrom .engine import run\n\n__all__ = ["run"]\n',
        encoding="utf-8",
    )
    (package / "cli.py").write_text("import argparse\n", encoding="utf-8")
    (package / "cli_click.py").write_text("import click\n", encoding="utf-8")
    (package / "api.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI(title='demo')\n",
        encoding="utf-8",
    )
    (package / "mcp.py").write_text(
        "from fastapi_mcp import FastApiMCP\n", encoding="utf-8"
    )
    (repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (repo / "docker-compose.yml").write_text("services:\n  api:\n", encoding="utf-8")
    return repo


@pytest.fixture
def brick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A whole brick on disk, with the auditor pointed at it."""
    repo = _build_brick(tmp_path)
    monkeypatch.setattr(AUDIT, "REPO_ROOT", tmp_path / "monorepo")
    (tmp_path / "monorepo" / "sprezzature-demo").mkdir(parents=True)
    (tmp_path / "monorepo" / "sprezzature-demo" / "SKILL.md").write_text(
        "# demo\n", encoding="utf-8"
    )
    monkeypatch.setattr(AUDIT, "_all_extra", lambda: {"sprezzature-demo"})
    return repo


def test_a_whole_brick_reports_no_gap(brick: Path) -> None:
    """The happy path, so the failing cases below mean something."""
    report = AUDIT.audit("sprezzature-demo")
    assert report["missing"] == [], report
    assert all(report["surfaces"].values())
    assert report["standalone"] is True


@pytest.mark.parametrize(
    ("removed", "surface"),
    [
        ("sprezzature_demo/cli_click.py", "cli"),
        ("sprezzature_demo/api.py", "api"),
        ("sprezzature_demo/mcp.py", "mcp"),
        ("docker-compose.yml", "compose"),
        (".git", "repo"),
    ],
)
def test_removing_one_surface_is_noticed(
    brick: Path, removed: str, surface: str
) -> None:
    """
    Take one thing away; the audit must name exactly that thing.

    The click twin is in the list on purpose: it is the surface most likely to
    be treated as optional, and an auditor that shrugged at its absence would
    report every brick of this suite as holding a command line when four of
    them ship argparse alone.
    """
    target = brick / removed
    if target.is_dir():
        target.rmdir()
    else:
        target.unlink()

    report = AUDIT.audit("sprezzature-demo")
    assert surface in report["missing"], (
        f"removing {removed} should have been reported as a missing "
        f"{surface}, got {report['missing']}"
    )


def test_a_metadata_only_init_is_not_a_library(brick: Path) -> None:
    """
    The failure four bricks of this suite actually shipped.

    An ``__init__.py`` carrying ``__version__`` and a docstring imports fine
    and exports nothing callable. The audit must call that a missing library
    surface, not a present one.
    """
    (brick / "sprezzature_demo" / "__init__.py").write_text(
        '"""demo."""\n\n__version__ = "0.1.0"\n__author__ = "Someone"\n',
        encoding="utf-8",
    )
    report = AUDIT.audit("sprezzature-demo")
    assert "library" in report["missing"]


def test_a_console_script_pointing_nowhere_is_reported(brick: Path) -> None:
    """
    A ``[project.scripts]`` entry naming a module that is not there.

    It installs without complaint and fails on first run, which is the worst
    moment to find out. The audit says so while the repo is still on a laptop.
    """
    (brick / "sprezzature_demo" / "cli.py").unlink()
    report = AUDIT.audit("sprezzature-demo")
    assert any("points at no file" in note for note in report["notes"]), report
