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
2. **command line** — a click command on PATH via ``[project.scripts]``. A
   CLI installed by ``pip install`` is the surface most people actually touch
   first. Until 2026-10-25 the contract asked for an argparse command *and* a
   click twin; the pair cost every sub-command twice, forced a conditional
   ``main`` whose two definitions had to agree by hand, and let a command go
   missing from one door (``make-map density``) with nothing to notice.
3. **HTTP API** — ``api.py`` holding a FastAPI app, declared behind an ``api``
   extra, with a ``Dockerfile`` so it runs without a Python install at all —
   and a ``docker-compose.yml`` beside it, always, so the port, the volume,
   the environment and the command are declared rather than reconstructed.
4. **MCP** — ``mcp.py`` republishing those same routes as agent tools through
   ``fastapi-mcp``, behind an ``mcp`` extra, with its own console script.
5. **skill** — ``SKILL.md`` in this monorepo, so Claude can reach the engine
   with the vocabulary of the problem rather than the vocabulary of the CLI.

Why a script and not only a test: every brick lives in a **sibling
repository** next to this one, and a checkout of this repo alone cannot see
them. A test that depended on them would be red on any machine that cloned one
repository. So the offline half is ``tests/test_surfaces_contract.py`` (the
contract is complete and every exemption is justified), and this is the half
that looks at what is actually on disk.

CI used to have none of the siblings, which is why this stayed off the
workflow. It has all nine now — ``scripts/fetch_siblings.sh`` fetches them
metadata-only, including the package directory this audit reads — so the
workflow runs it with ``--require-checkouts``.

Usage
-----
::

    python scripts/audit_surfaces.py              # table for every brick
    python scripts/audit_surfaces.py --brick maps # one brick
    python scripts/audit_surfaces.py --json       # machine-readable
    python scripts/audit_surfaces.py --require-checkouts   # what CI runs

Exits 0 when every brick present on disk holds every surface it owes, 1
otherwise, naming what is missing. A brick with no sibling checkout is
reported and does not fail the run: absence of a clone is not absence of a
surface, and the script refuses to confuse the two. ``--require-checkouts``
is the other half of that refusal — where every sibling is *supposed* to be
present, as in CI, a fetch that quietly brought back eight of nine must be a
failure and not nine columns of ``?``.

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


def _share_an_engine(sources: dict[str, str]) -> bool:
    """Whether the click front door is built on the argparse one.

    The contract is "two parsers, one engine". The mechanical trace of that is
    an import: the click module names something the argparse module defines.
    A click command that imports nothing from its argparse twin is a second
    implementation, and the two are free to drift — which is the whole failure
    the twin was introduced to prevent.

    Both sides are identified by what they import rather than by filename,
    because this suite spells the pair three different ways:
    ``cli.py``/``cli_click.py``, ``make_figure.py``/``cli.py``, and an auditor
    in ``scripts/`` beside ``cli_click.py``. Demanding the filenames turned
    this into a note telling a human to go and look, every run, forever.
    """
    defined: set[str] = set()
    click_sources: list[str] = []
    for src in sources.values():
        if _uses(src, ("import argparse", "from _argparse import", "make_parser(")):
            defined |= _module_names_in(src)
        if _uses(src, ("import click", "from click", "sprezzature_command(")):
            click_sources.append(src)
    if not click_sources or not defined:
        return False
    return any(_imported_names(src) & defined for src in click_sources)


def _module_names_in(src: str) -> set[str]:
    """Top-level names a module defines.

    Parsed rather than grepped: a name mentioned in a docstring is not a name
    the module exports, and the first version of the surrounding check was
    wrong in exactly that way about ``argparse``.

    ``AnnAssign`` is handled as well as ``Assign``, which the first version
    was not — and that is the whole catalogue in this suite, since every
    front-door table is written ``TOOLS: dict[str, ...] = {...}``. The check
    reported five repositories as having two unrelated tools because of it.
    """
    import ast

    try:
        tree = ast.parse(src)
    except SyntaxError:  # pragma: no cover - unparseable source
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _imported_names(src: str) -> set[str]:
    """Every name a module imports, however deep the import sits.

    Not top-level only: a guarded front door puts its real imports inside the
    ``else`` branch of a ``try: import click``, so a top-level walk sees
    nothing and the check would call a correct module a second tool.

    Both the original name and the local alias are kept. ``from ...auditor
    import main as _audit`` binds ``_audit`` locally, but the name that says
    *which function was reached* is ``main`` — and matching on the alias alone
    reported sprezzature-ux-laws, sprezzature-cli-gui and sprezzature-maps as
    two unrelated tools when each is one engine behind two parsers.
    """
    import ast

    try:
        tree = ast.parse(src)
    except SyntaxError:  # pragma: no cover - unparseable source
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
                if alias.asname:
                    names.add(alias.asname)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
                if alias.asname:
                    names.add(alias.asname)
    return names


def _base_distributions(pyproject: str) -> set[str]:
    """Distribution names a plain ``pip install`` brings in.

    The declared ones only, never their transitive closure: a check that
    accepted whatever a dependency happened to pull today would pass until
    that dependency dropped something.
    """
    block = re.search(r"^dependencies\s*=\s*\[(.*?)^\]", pyproject, re.M | re.S)
    if not block:
        return set()
    return {
        name.lower().replace("-", "_")
        for name in re.findall(
            r'^\s*"([A-Za-z0-9][A-Za-z0-9._-]*)', block.group(1), re.M
        )
    }


def _unguarded_third_party(module_path: Path, base: set[str]) -> list[str]:
    """Module-level imports a bare install would not satisfy.

    Three things are *not* reported, each for its own reason:

    - imports inside a ``try``/``except ImportError``, which is the documented
      way to need something optional;
    - imports nested in a function, which happen when the function is called —
      after the command has started and printed its help;
    - a bare name matching a ``.py`` file beside this one, which is a sibling
      module. These scripts put their own directory on ``sys.path`` so each
      can also run on its own out of a downloaded zip, and the first version
      of this check read every one of them as a missing dependency — forty
      false reports across nine repositories.
    """
    import ast
    import sys

    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):  # pragma: no cover - unreadable source
        return []

    imported: set[str] = set()
    for node in tree.body:  # top level only: a `try` body is not tree.body
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])

    siblings = {f.stem for f in module_path.parent.glob("*.py")}
    return sorted(
        name
        for name in imported
        if name not in sys.stdlib_module_names
        and name.lower().replace("-", "_") not in base
        and name not in siblings
    )


def _target_source(repo: Path, pyproject: str, target: str) -> str:
    """Source of the module a ``[project.scripts]`` target names.

    ``"sprezzature_maps.cli:main"`` resolves to ``sprezzature_maps/cli.py``;
    ``"sprezzature_accessibility_scripts.lint_a11y:main"`` resolves through the
    package-dir mapping to ``scripts/lint_a11y.py``. Returns the empty string
    when the target points at something not on disk — a dangling console
    script, which the audit then reports as a missing command line rather than
    crashing on.
    """
    path = _target_path(repo, pyproject, target)
    return _read(path) if path else ""


def _target_path(repo: Path, pyproject: str, target: str) -> Path | None:
    """Where a ``[project.scripts]`` target's module sits, or ``None``.

    The path and not just the text, because deciding whether a bare-name
    import is a sibling module or a third-party package means looking at what
    is in the same folder.
    """
    module = target.split(":")[0]
    head, _, tail = module.partition(".")
    mapping = _package_dirs(pyproject)
    folder = mapping.get(head, head)
    relative = Path(folder, *tail.split(".")).with_suffix(".py")
    for base in (repo, repo / "src"):
        candidate = base / relative
        if candidate.is_file():
            return candidate
    return None


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
        # Undecidable, not missing. ``missing`` used to carry ``"repo"`` here,
        # which made the script exit 1 on any machine holding a single clone --
        # the very situation the paragraph at the top of this file says it
        # refuses to confuse with a missing surface. The two meanings are kept
        # apart now: ``undecidable`` for "no clone to look at", ``missing``
        # for what this machine can see and found wanting. ``--require-checkouts``
        # is how a caller that expects all nine turns the first into the second.
        #
        # ``standalone`` is ``None`` and not ``False`` for the same reason: in
        # the branch below it answers "has a .git, so somebody else could clone
        # it", and there is nothing here to answer that about.
        return {
            "brick": brick,
            "repo": None,
            "surfaces": {s: None for s in SURFACES} | {"skill": skill},
            "containers": {c: None for c in CONTAINERS},
            "publication": publication,
            "standalone": None,
            "undecidable": True,
            "missing": (["skill"] if not skill else []) + publication_gaps,
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
    click_cli = any(
        _uses(src, ("import click", "from click", "sprezzature_command("))
        for src in sources.values()
    )
    cli = bool(on_path) and click_cli

    # The old contract wanted both parsers and an import edge between them, so
    # that two front doors could not drift into two tools. One front door
    # cannot drift from itself, so that whole check is gone -- but the failure
    # it guarded against is worth naming in its replacement: a brick that still
    # ships an argparse umbrella has a second door nobody is maintaining.
    # Only the umbrella counts. The per-tool console scripts
    # (`sprezzature-colors-contrast` and friends) are the tools themselves and
    # keep their own parsers on purpose; the surface this audits is the one
    # front door, and that is the module a bare `sprezzature-<brick>` reaches.
    umbrella = {
        command: src
        for command, src in sources.items()
        if "_scripts." not in (on_path.get(command) or "")
    }
    argparse_cli = any(
        _uses(src, ("import argparse", "from _argparse import", "make_parser("))
        for src in umbrella.values()
    )
    if argparse_cli:
        notes.append(
            "a console script still reaches an argparse parser; click is the "
            "suite's only command line since 2026-10-25"
        )
    if on_path and not click_cli:
        notes.append("command on PATH, but no click parser behind it")
    for command, source in sources.items():
        if not source:
            notes.append(f"console script `{command}` points at no file on disk")

    # A command that cannot start is not a command line.
    #
    # `discussion-helper` shipped this: its headline console script imported
    # click at module level, and click was declared nowhere — not a
    # dependency, not an extra. `pip install` put a name on the PATH that
    # answered a traceback about a package the reader had never heard of.
    # A checkout cannot see it, because click is always already there.
    #
    # The rule: a module a console script names may import, at module level,
    # only the standard library, this package's declared base dependencies,
    # and its own siblings. Anything heavier belongs behind an extra *and*
    # behind a `try: ... except ImportError:` that names the extra.
    base_dists = _base_distributions(pyproject) | {
        repo.name.replace("-", "_"),
        repo.name.replace("-", "_") + "_scripts",
    }
    for command, target in on_path.items():
        module_path = _target_path(repo, pyproject, target)
        if module_path is None:
            continue
        stranded = _unguarded_third_party(module_path, base_dists)
        if stranded:
            notes.append(
                f"`{command}` imports {stranded} at module level and "
                f"pyproject declares none of them as a base dependency -- "
                f"a bare `pip install` puts it on PATH and it answers a "
                f"traceback"
            )

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

    # The MCP server takes its host and port from the environment, and those
    # two names have to say *this* brick. `mcp.py` is the file most often
    # started as a copy of a sibling's, and the prefix is the one line a copy
    # is never caught on: the server still starts, still binds 127.0.0.1:8000,
    # the tests still pass. What breaks is silent in both directions --
    # SPREZZATURE_<BRICK>_PORT does nothing here, and one setting meant for the
    # brick this file was copied from moves this server too. sprezzature-ui and
    # sprezzature-publish both shipped accessibility's two names, so a single
    # SPREZZATURE_ACCESSIBILITY_PORT moved three servers at once.
    own = "SPREZZATURE_" + brick.removeprefix("sprezzature-").upper().replace("-", "_")
    foreign = sorted(
        {
            name
            for name in re.findall(r"SPREZZATURE_[A-Z_]+_(?:HOST|PORT)", mcp_src)
            if not name.startswith(own + "_")
        }
    )
    if foreign:
        notes.append(
            "mcp.py reads " + ", ".join(foreign) + " -- another brick's "
            f"environment, so {own}_HOST and {own}_PORT do nothing here"
        )

    # Every command a bare `pip install` puts on PATH must be able to say
    # something useful when it cannot start.
    #
    # Click is an extra in most of these bricks — the argparse twin needs
    # nothing, which is the whole reason both ship — so the Click commands
    # install and then fail. Unguarded, what they print is
    # `ModuleNotFoundError: No module named 'click'`: a traceback about a
    # third-party package the reader never asked for, for a command their own
    # install had just created. figures and maps had guarded theirs from the
    # start; accessibility had not, and it took a bare-venv install to see it,
    # because a developer machine always has click.
    # Skipped entirely where click is a *base* dependency: there, a bare
    # install has it and the command cannot fail. Guarding it would be
    # defending against something that does not happen, which is its own kind
    # of noise.
    # Comment lines are stripped before looking: splitting the dependency
    # block on commas and testing each piece broke the moment a manifest put a
    # `# why` line inside the list, which every brick now does -- the piece
    # then starts with `#` and the requirement right under it is never seen.
    _deps_block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", pyproject, re.M | re.S)
    base_requires_click = bool(
        _deps_block
        and re.search(
            r'["\']click\b',
            re.sub(r"#[^\n]*", "", _deps_block.group(1)),
        )
    )

    if not base_requires_click:
        for command in on_path:
            source = sources.get(command, "")
            if not _uses(source, ("import click", "from click")):
                continue
            # The guard has to be around the import, not merely present in the
            # file: a `try:` three hundred lines below protects nothing.
            before = source.split("import click")[0][-300:]
            if "try:" not in before:
                notes.append(
                    f"`{command}` imports click unguarded, and click is an "
                    f"extra here: on a bare install it answers a "
                    f"ModuleNotFoundError about a package the reader never "
                    f"asked for"
                )

    # Containers: how the API ships.
    docker = (repo / "Dockerfile").is_file()
    compose = any(
        (repo / name).is_file()
        for name in (
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yaml",
            "compose.yml",
        )
    )

    if not standalone:
        notes.append("no .git here: the files are in place but nobody can clone them")

    held = {
        "library": library,
        "cli": cli,
        "api": api,
        "mcp": mcp,
        "skill": skill,
    }
    missing = [
        name for name, ok in held.items() if not ok and (brick, name) not in EXEMPTIONS
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
        "undecidable": False,
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
    head = f"{'brick':<{width}}  " + "".join(f"{short:^6}" for _, short in _COLUMNS)
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
            "  python scripts/audit_surfaces.py --require-checkouts\n"
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
    parser.add_argument(
        "--require-checkouts",
        action="store_true",
        help=(
            "fail when a brick has no sibling checkout, instead of reporting "
            "it as undecidable (what CI runs, after fetch_siblings.sh)"
        ),
    )
    args = parser.parse_args(argv)

    bricks = list(SHIPPED_SKILLS)
    if args.brick:
        if args.brick not in bricks:
            print(f"error: {args.brick} is not in SKILLS.txt", file=sys.stderr)
            return 2
        bricks = [args.brick]

    reports = [audit(brick, check_pypi=args.pypi) for brick in bricks]

    absent = [r for r in reports if r["undecidable"]]

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
                print(
                    f"  gap   {report['brick']}: missing {', '.join(report['missing'])}"
                )
        if absent and args.require_checkouts:
            print()
            print(
                f"  error no sibling checkout for "
                f"{', '.join(r['brick'] for r in absent)} -- "
                f"--require-checkouts says every brick in SKILLS.txt must be "
                f"here, so this is a fetch that came back short, not a "
                f"machine with one clone"
            )

    if any(r["missing"] for r in reports):
        return 1
    # A run that decided nothing is not a run that found nothing. Without this,
    # a fetch step that failed for one brick leaves a column of `?` and an exit
    # code of 0 -- a green CI job asserting the surfaces of a repository it
    # never read.
    return 1 if absent and args.require_checkouts else 0


if __name__ == "__main__":
    raise SystemExit(main())
