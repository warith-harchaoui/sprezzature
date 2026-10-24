"""
The container surface names extras, modules and ports that exist.

``audit_surfaces.py`` decides a brick holds the Docker and Compose surfaces by
asking whether the files are there. That is the right question for a contract
table and the whole of what anything asked: nothing read what those files
*say*. Every other surface in this suite is held to the opposite standard —
a skill's "invoked as" sentence must name a console script the brick installs,
a TRIGGERS table must name a real MCP tool, the driver must route to commands
that exist — and the container surface was the one place a name could be
invented without anyone noticing until a `docker compose up` failed.

Four things are decidable from the two files and the brick's own metadata:

* every extra the ``pip install ".[…]"`` line names is an extra the package
  declares — a typo there builds an image that cannot run its own ``CMD``;
* the ASGI app the ``CMD`` serves is a module the package ships;
* ``EXPOSE``, the ``--port`` in the ``CMD`` and the port the compose file
  publishes are the same number;
* a command quoted in the compose file's own usage comments is a console
  script the package installs.

A build argument (``.[${EXTRAS}]``) is not a typo: it is the install made
parametric, and the value arrives at build time.

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
import yaml

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent

_COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml")
_EXTRAS_IN_INSTALL = re.compile(r'pip install[^\n]*?"\.\[([^\]]+)\]"')
_ASGI_APP = re.compile(r'"([\w.]+):app"')
_EXPOSE = re.compile(r"^EXPOSE\s+(\d+)", re.M)
_CMD_PORT = re.compile(r'--port[ ",]+(\d+)')
_SUITE_COMMAND = re.compile(r"\b(?:sprezzature|make)-[a-z0-9-]+\b")
#: ``.[${EXTRAS}]`` and friends: a build argument, not a name to check.
_BUILD_ARG = re.compile(r"^\$\{?\w+\}?$")


def _brick(name: str) -> Path | None:
    repo = REPO_ROOT.parent / name
    return repo if (repo / "pyproject.toml").is_file() else None


def _project(repo: Path) -> dict:
    return tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8")).get(
        "project", {}
    )


def _compose_path(repo: Path) -> Path | None:
    return next((repo / n for n in _COMPOSE_NAMES if (repo / n).is_file()), None)


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_dockerfile_installs_extras_that_exist(brick: str) -> None:
    """A typo in the extras list builds an image that cannot run its own CMD."""
    repo = _brick(brick)
    if repo is None or not (repo / "Dockerfile").is_file():
        pytest.skip(f"no Dockerfile for {brick}")
    declared = set(_project(repo).get("optional-dependencies", {}))
    body = (repo / "Dockerfile").read_text(encoding="utf-8")
    unknown = sorted(
        {
            extra
            for named in _EXTRAS_IN_INSTALL.findall(body)
            for extra in (part.strip() for part in named.split(","))
            if extra and not _BUILD_ARG.match(extra) and extra not in declared
        }
    )
    assert not unknown, (
        f"{brick}/Dockerfile installs .[{','.join(unknown)}], which "
        f"pyproject.toml does not declare. Known: {sorted(declared)}"
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_dockerfile_serves_a_module_the_package_ships(brick: str) -> None:
    """``CMD ["uvicorn", "pkg.api:app"]`` has to name a file that is there."""
    repo = _brick(brick)
    if repo is None or not (repo / "Dockerfile").is_file():
        pytest.skip(f"no Dockerfile for {brick}")
    body = (repo / "Dockerfile").read_text(encoding="utf-8")
    served = _ASGI_APP.findall(body)
    if not served:
        pytest.skip(f"{brick}'s image serves no ASGI app")
    missing = [
        module
        for module in served
        if not (repo / Path(module.replace(".", "/") + ".py")).is_file()
    ]
    assert not missing, (
        f"{brick}/Dockerfile serves {missing}, and no such module is in the "
        f"repository. The image builds and the container exits."
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_the_three_statements_of_the_port_agree(brick: str) -> None:
    """``EXPOSE``, the ``--port`` in the CMD, and the compose mapping."""
    repo = _brick(brick)
    compose = _compose_path(repo) if repo else None
    if repo is None or not (repo / "Dockerfile").is_file():
        pytest.skip(f"no Dockerfile for {brick}")
    body = (repo / "Dockerfile").read_text(encoding="utf-8")
    exposed = set(_EXPOSE.findall(body))
    if not exposed:
        pytest.skip(f"{brick}/Dockerfile exposes no port")
    served = set(_CMD_PORT.findall(body))
    assert not served or served == exposed, (
        f"{brick}: EXPOSE {sorted(exposed)} and the CMD serves on "
        f"{sorted(served)}. One of the two is what a reader will publish."
    )
    if compose is None:
        return
    document = yaml.safe_load(compose.read_text(encoding="utf-8")) or {}
    published = {
        str(mapping).split(":")[-1].strip('"')
        for service in (document.get("services") or {}).values()
        for mapping in (service.get("ports") or [])
    }
    assert not published or published & exposed, (
        f"{brick}: the image exposes {sorted(exposed)} and {compose.name} "
        f"maps to {sorted(published)}; nothing listens on the published port."
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_compose_file_quotes_commands_that_exist(brick: str) -> None:
    """The usage lines in the comments are the first thing anybody runs."""
    repo = _brick(brick)
    compose = _compose_path(repo) if repo else None
    if compose is None:
        pytest.skip(f"no compose file for {brick}")
    body = compose.read_text(encoding="utf-8")
    scripts = set(_project(repo).get("scripts", {}))  # type: ignore[arg-type]
    # The image tag (`sprezzature-colors:local`) and the brick's own name are
    # not command names; everything else in that shape is.
    invented = sorted(
        {
            name
            for name in _SUITE_COMMAND.findall(body)
            if name not in scripts
            and name != brick
            and f"{name}:" not in body
        }
    )
    assert not invented, (
        f"{brick}/{compose.name} quotes {invented} in its usage lines, and "
        f"`pip install` puts none of them on PATH."
    )


def test_this_run_saw_container_surfaces() -> None:
    """A file that skipped everything reads exactly like a file that passed."""
    with_images = [
        brick
        for brick in SHIPPED_SKILLS
        if (repo := _brick(brick)) is not None and (repo / "Dockerfile").is_file()
    ]
    assert with_images, (
        "no brick here ships a Dockerfile, so every case above skipped. Run "
        "scripts/fetch_siblings.sh, which is what CI does."
    )
