#!/usr/bin/env python3
"""
audit_surfaces — does every brick offer the five surfaces?

A brick of this suite is an *engine*, and an engine nobody can reach is a
private script. The house rule, written down in ``SURFACES.md``, is that one
engine is published through five surfaces, so that the same code answers to a
human at a terminal, to another program, to a service, to an agent, and to
Claude:

1. **library** — ``import sprezzature_<brick>`` works, and the package's
   ``__init__`` exports the engine rather than hiding it behind a script.
2. **command line** — an argparse command *and* its click twin, both on PATH
   via ``[project.scripts]``. Not one or the other: a CLI installed by
   ``pip install`` is the surface most people actually touch first, and the
   two parsers suit different callers.
3. **HTTP API** — ``api.py`` holding a FastAPI app, declared behind an ``api``
   extra, with a ``Dockerfile`` so it runs without a Python install at all —
   and a ``docker-compose.yml`` beside it, always, so the port, the volume,
   the environment and the command are declared rather than reconstructed.
4. **MCP** — ``mcp.py`` republishing those same routes as agent tools through
   ``fastapi-mcp``, behind an ``mcp`` extra, with its own console script.
5. **skill** — ``SKILL.md`` in this monorepo, so Claude can reach the engine
   with the vocabulary of the problem rather than the vocabulary of the CLI.

Why a script and not only a test: seven of the ten bricks live in **sibling
repositories** next to this one, and a checkout of this repo alone cannot see
them. A test that depended on them would be red on any machine that cloned one
repository, and red in CI, which has none of them. So the offline half is
``tests/test_surfaces_contract.py`` (the contract is complete and every
exemption is justified), and this is the half that looks at what is actually
on disk.

Usage
-----
::

    python scripts/audit_surfaces.py              # table for every brick
    python scripts/audit_surfaces.py --brick maps # one brick
    python scripts/audit_surfaces.py --json       # machine-readable

Exits 0 when every brick present on disk holds every surface it owes, 1
otherwise, naming what is missing. Bricks with no sibling checkout are
reported and do not fail the run: absence of a clone is not absence of a
surface, and the script refuses to confuse the two.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _argparse import make_parser  # noqa: E402
from skills_manifest import SHIPPED_SKILLS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The five surfaces, in the order ``SURFACES.md`` presents them. The tuple is
#: the contract: a sixth entry here is a change of doctrine, not a detail, and
#: ``tests/test_surfaces_contract.py`` holds both ends to it.
SURFACES: tuple[str, ...] = ("library", "cli", "api", "mcp", "skill")

#: The container surfaces. Kept apart from the five because they are *how* the
#: API ships, not a sixth way in: a Dockerfile is owed by every brick that has
#: an API, and a compose file by every brick that has a Dockerfile.
CONTAINERS: tuple[str, ...] = ("docker", "compose")

#: How a brick becomes installable by someone who is not us. Every brick owes
#: both halves: its own name on PyPI, and a line in this repo's ``all`` extra
#: so ``pip install sprezzature[all]`` pulls the suite. The second half is
#: decidable from a checkout; the first needs the network, so it is opt-in
#: behind ``--pypi`` and never runs in CI.
PUBLICATION: tuple[str, ...] = ("all-extra", "pypi")

#: PyPI's simple index, not ``/pypi/<name>/json``. The two endpoints are cached
#: independently and the legacy JSON one lags by minutes after an upload, which
#: would make this audit report NOT PUBLISHED for something pip already
#: resolves. ``scripts/check_all_extra_resolves.py`` learned that the hard way.
SIMPLE_INDEX = "https://pypi.org/simple/{name}/"
TIMEOUT = 15


#: Surfaces a brick does not owe, each with the reason it does not owe it.
#:
#: This table exists so that "we did not do it" and "it would be wrong to do
#: it" stop looking alike in the output. An exemption without a reason is
#: refused by the test suite — the point is to force the thought, not to
#: provide an escape hatch.
EXEMPTIONS: dict[tuple[str, str], str] = {}

#: Nothing is exempt today, and that is worth a note rather than an empty
#: dict with no explanation.
#:
#: ``sprezzature-ui`` was the one entry here: its API was declared exempt
#: because writing a component is the model's work and no route can carry it.
#: The brick now ships a narrow API anyway — one route over the i18n audit,
#: which *is* engine-able — so the exemption became a lie in the useful
#: direction and was removed. The narrowness is still the point, and it is
#: stated in that package's own module docstring where a reader meets it.
#:
#: The table stays because the next brick may genuinely owe nothing on some
#: surface, and saying so out loud is better than a silent gap.

#: Why compose is owed by *every* brick that ships a Dockerfile, with no
#: exceptions and no "only when there is a second container":
#:
#: a Dockerfile alone is a recipe, not a way in. It leaves the next person to
#: reconstruct the port mapping, the volume, the environment and the command
#: from reading it — and to get one of them wrong in silence. The compose file
#: is where those four live as *declared facts*, so that ``docker compose up``
#: is the whole onboarding. One container is reason enough; a second only makes
#: it worse. None of the seven published bricks carries one today.
COMPOSE_IS_OWED_WITH_DOCKER = True


def _all_extra() -> set[str]:
    """Package names floored in this repo's ``all`` extra."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"^all = \[(.*?)^\]", text, re.M | re.S)
    if not match:
        return set()
    return set(re.findall(r'"([A-Za-z0-9_.\-]+)\s*>=', match.group(1)))


def _on_pypi(name: str) -> bool | None:
    """Does PyPI hold this project? ``None`` when the network did not answer."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(
            SIMPLE_INDEX.format(name=name), timeout=TIMEOUT
        ) as response:
            return response.status == 200
    except urllib.error.HTTPError as error:
        return False if error.code == 404 else None
    except OSError:
        return None


def _package_dir(repo: Path, brick: str) -> Path:
    """The import package inside a brick's repository.

    ``sprezzature-ux-laws`` ships ``sprezzature_ux_laws``: the folder name with
    hyphens turned into underscores, which is also what ``pip install`` puts on
    ``sys.path``.
    """
    return repo / brick.replace("-", "_")


def _read(path: Path) -> str:
    """File contents, or the empty string when the file is not there."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _console_scripts(pyproject: str) -> dict[str, str]:
    """The ``[project.scripts]`` table, as ``{command: target}``.

    Parsed with a regex rather than ``tomllib`` on purpose: this script runs
    against sibling checkouts whose ``pyproject.toml`` may be mid-edit, and a
    table that is readable but not yet valid TOML should still be reported
    rather than crash the audit.
    """
    match = re.search(r"\[project\.scripts\](.*?)(?=\n\[|\Z)", pyproject, re.S)
    if not match:
        return {}
    pairs = re.findall(r'^\s*([\w.\-]+)\s*=\s*"([^"]+)"', match.group(1), re.M)
    return dict(pairs)


def _extras(pyproject: str) -> set[str]:
    """Names declared under ``[project.optional-dependencies]``."""
    match = re.search(
        r"\[project\.optional-dependencies\](.*?)(?=\n\[(?!tool)|\Z)",
        pyproject,
        re.S,
    )
    if not match:
        return set()
    return set(re.findall(r"^\s*([\w.\-]+)\s*=\s*\[", match.group(1), re.M))


def _uses(module: str, needles: tuple[str, ...]) -> bool:
    """Does this module's source mention any of these names?"""
    return any(needle in module for needle in needles)


def _package_dirs(pyproject: str) -> dict[str, str]:
    """The ``[tool.setuptools.package-dir]`` mapping, as ``{package: folder}``.

    Every brick ships a second, generated package: ``scripts/`` becomes
    ``sprezzature_<brick>_scripts`` so the skill's tools survive a ``pip
    install``, where a path like ``scripts/lint_a11y.py`` does not. Resolving a
    console script's target back to a file means honouring that mapping.
    """
    match = re.search(
        r"\[tool\.setuptools\.package-dir\](.*?)(?=\n\[|\Z)", pyproject, re.S
    )
    if not match:
        return {}
    pairs = re.findall(r'^\s*"?([\w.\-]+)"?\s*=\s*"([^"]*)"', match.group(1), re.M)
    return dict(pairs)


def _target_source(repo: Path, pyproject: str, target: str) -> str:
    """Source of the module a ``[project.scripts]`` target names.

    ``"sprezzature_maps.cli:main"`` resolves to ``sprezzature_maps/cli.py``;
    ``"sprezzature_accessibility_scripts.lint_a11y:main"`` resolves through the
    package-dir mapping to ``scripts/lint_a11y.py``. Returns the empty string
    when the target points at something not on disk — a dangling console
    script, which the audit then reports as a missing command line rather than
    crashing on.
    """
    module = target.split(":")[0]
    head, _, tail = module.partition(".")
    mapping = _package_dirs(pyproject)
    folder = mapping.get(head, head)
    relative = Path(folder, *tail.split(".")).with_suffix(".py")
    for base in (repo, repo / "src"):
        candidate = base / relative
        if candidate.is_file():
            return _read(candidate)
    return ""


def audit(brick: str, check_pypi: bool = False) -> dict[str, Any]:
    """Look at one brick on disk and report which surfaces it holds.

    Parameters
    ----------
    brick : str
        Folder name as it appears in ``SKILLS.txt``, e.g. ``sprezzature-maps``.
    check_pypi : bool, optional
        Ask PyPI whether the brick is published. Off by default: it is the one
        question here that needs the network, and an audit that fails on a
        train is worse than an audit that says "not asked".

    Returns
    -------
    dict
        ``{"brick", "repo", "surfaces", "containers", "publication",
        "missing", "notes"}``. ``repo`` is ``None`` when no sibling checkout
        exists, in which case every surface but ``skill`` is reported as
        unknown rather than absent — absence of a clone is not absence of a
        surface.
    """
    repo = REPO_ROOT.parent / brick
    skill = (REPO_ROOT / brick / "SKILL.md").is_file()
    # A folder with the right files in it is not yet a brick. Seven of these
    # are git repositories with a GitHub remote; the eighth looked complete
    # from a file listing and had no `.git` at all -- a draft extraction, not
    # something anyone else could clone. The audit should not let those two
    # states look alike.
    standalone = (repo / ".git").exists()
    in_all = brick in _all_extra()
    published = _on_pypi(brick) if check_pypi else None
    publication = {"all-extra": in_all, "pypi": published}
    publication_gaps = ["all-extra"] if not in_all else []
    if published is False:
        publication_gaps.append("pypi")

    if not repo.is_dir():
        return {
            "brick": brick,
            "repo": None,
            "surfaces": {s: None for s in SURFACES} | {"skill": skill},
            "containers": {c: None for c in CONTAINERS},
            "publication": publication,
            "standalone": False,
            "missing": (["skill"] if not skill else [])
            + ["repo"]
            + publication_gaps,
            "notes": ["no sibling checkout — surfaces undecidable here"],
        }

    package = _package_dir(repo, brick)
    pyproject = _read(repo / "pyproject.toml")
    scripts = _console_scripts(pyproject)
    extras = _extras(pyproject)
    notes: list[str] = []

    # 1. library — the package imports, and __init__ exports something.
    init = _read(package / "__init__.py")
    library = bool(init.strip()) and "__all__" in init

    # 2. command line — argparse *and* click, both reachable after pip install.
    #
    # Measured on the installed commands, not on the source tree: a parser
    # sitting in a module that no console script names is reachable from a
    # clone and from nowhere else, which is the failure `sprezzature-ux-laws`
    # shipped with — its --help advertised a command nothing installed.
    on_path = {
        command: target
        for command, target in scripts.items()
        if not command.endswith("-mcp")
    }
    sources = {
        command: _target_source(repo, pyproject, target)
        for command, target in on_path.items()
    }
    # Matched on imports, never on the bare word. `_uses(src, ("argparse",))`
    # was the first version and it was wrong in the way that matters: a module
    # whose docstring said "behaviour is identical to the prior argparse-driven
    # main" counted as having an argparse command line. sprezzature-accessibility read
    # as holding both parsers while shipping only click.
    argparse_cli = any(
        _uses(src, ("import argparse", "from _argparse import", "make_parser("))
        for src in sources.values()
    )
    click_cli = any(
        _uses(src, ("import click", "from click", "sprezzature_command("))
        for src in sources.values()
    )
    cli = bool(on_path) and argparse_cli and click_cli
    if argparse_cli and not click_cli:
        notes.append("argparse command on PATH, click twin missing")

    # "Both parsers exist somewhere in the repo" is a weaker claim than the
    # contract makes, and sprezzature-accessibility is how that showed: its click
    # command is the drafter and its argparse command is the *installer* --
    # two different tools, so the engine itself had one parser, not two. The
    # reference layout puts both over the same engine, in cli.py and
    # cli_click.py, which is also the only version of this that a script can
    # check without guessing which command is the important one.
    if cli and not (
        _uses(_read(package / "cli.py"), ("argparse",))
        and _uses(
            _read(package / "cli_click.py"), ("import click", "from click")
        )
    ):
        notes.append(
            "both parsers reach PATH, but not as cli.py + cli_click.py over "
            "the same engine -- check they are not two different tools"
        )
    for command, source in sources.items():
        if not source:
            notes.append(f"console script `{command}` points at no file on disk")

    # 3. HTTP API — a FastAPI app, declared behind its own extra.
    api_src = _read(package / "api.py")
    api = "FastAPI(" in api_src and "api" in extras
    if "FastAPI(" in api_src and "api" not in extras:
        notes.append("api.py exists but no `api` extra declares its deps")

    # 4. MCP — fastapi-mcp over those same routes, with its own command.
    mcp_src = _read(package / "mcp.py")
    mcp = (
        _uses(mcp_src, ("FastApiMCP", "fastapi_mcp"))
        and "mcp" in extras
        and any(cmd.endswith("-mcp") for cmd in scripts)
    )

    # Containers: how the API ships.
    docker = (repo / "Dockerfile").is_file()
    compose = any(
        (repo / name).is_file()
        for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml")
    )

    if not standalone:
        notes.append(
            "no .git here: the files are in place but nobody can clone them"
        )

    held = {
        "library": library,
        "cli": cli,
        "api": api,
        "mcp": mcp,
        "skill": skill,
    }
    missing = [
        name
        for name, ok in held.items()
        if not ok and (brick, name) not in EXEMPTIONS
    ]
    if api and not docker:
        missing.append("docker")
    if docker and not compose:
        missing.append("compose")
        notes.append(
            "Dockerfile with no compose file: the port, the volume, the "
            "environment and the command are left for the reader to "
            "reconstruct, and to get wrong in silence"
        )

    return {
        "brick": brick,
        "repo": str(repo),
        "surfaces": held,
        "containers": {"docker": docker, "compose": compose},
        "publication": publication,
        "standalone": standalone,
        "missing": missing + ([] if standalone else ["repo"]) + publication_gaps,
        "notes": notes,
    }


def _cell(value: bool | None, exempt: bool) -> str:
    """One table cell: held, missing, exempt, or undecidable."""
    if exempt:
        mark = "~"
    elif value is None:
        mark = "?"
    else:
        mark = "ok" if value else "--"
    return f"{mark:^6}"


#: Column headings, short enough to stay in a four-character cell.
_COLUMNS: tuple[tuple[str, str], ...] = (
    ("repo", "repo"),
    ("library", "lib"),
    ("cli", "cli"),
    ("api", "api"),
    ("mcp", "mcp"),
    ("skill", "skil"),
    ("docker", "dock"),
    ("compose", "comp"),
    ("all-extra", "all"),
    ("pypi", "pypi"),
)


def _table(reports: list[dict[str, Any]]) -> str:
    """The whole audit as a fixed-width table."""
    width = max(len(r["brick"]) for r in reports)
    head = f"{'brick':<{width}}  " + "".join(
        f"{short:^6}" for _, short in _COLUMNS
    )
    lines = [head, "-" * len(head)]
    for report in reports:
        cells = ""
        for name, _ in _COLUMNS:
            if name == "repo":
                value, exempt = report["standalone"], False
            elif name in SURFACES:
                value = report["surfaces"][name]
                exempt = (report["brick"], name) in EXEMPTIONS
            elif name in CONTAINERS:
                value, exempt = report["containers"][name], False
            else:
                value, exempt = report["publication"][name], False
            cells += _cell(value, exempt)
        lines.append(f"{report['brick']:<{width}}  {cells}")
    lines.append("")
    lines.append(
        "ok = held   -- = missing   ~ = exempt (see EXEMPTIONS)   "
        "? = not decidable here"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the audit and report. Returns the process exit code."""
    parser = make_parser(
        prog="audit-surfaces",
        description=(
            "Check every sprezzature brick against the five-surface contract "
            "written down in SURFACES.md: library, command line (argparse and "
            "click), HTTP API, MCP, skill -- plus the Dockerfile and compose "
            "file the API ships in, and publication to PyPI."
        ),
        epilog=(
            "Examples:\n"
            "  python scripts/audit_surfaces.py\n"
            "  python scripts/audit_surfaces.py --brick sprezzature-maps\n"
            "  python scripts/audit_surfaces.py --pypi\n"
            "  python scripts/audit_surfaces.py --json\n"
        ),
    )
    parser.add_argument(
        "--brick",
        metavar="NAME",
        help="audit one brick only (folder name, e.g. sprezzature-maps)",
    )
    parser.add_argument(
        "--pypi",
        action="store_true",
        help="also ask PyPI whether each brick is published (needs the network)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the full report as JSON instead of a table",
    )
    args = parser.parse_args(argv)

    bricks = list(SHIPPED_SKILLS)
    if args.brick:
        if args.brick not in bricks:
            print(f"error: {args.brick} is not in SKILLS.txt", file=sys.stderr)
            return 2
        bricks = [args.brick]

    reports = [audit(brick, check_pypi=args.pypi) for brick in bricks]

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        print(_table(reports))
        for report in reports:
            for note in report["notes"]:
                print(f"  note  {report['brick']}: {note}")
        gaps = [r for r in reports if r["missing"]]
        if gaps:
            print()
            for report in gaps:
                print(f"  gap   {report['brick']}: missing {', '.join(report['missing'])}")

    return 1 if any(r["missing"] for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
