"""
Every brick ships the same set of documents, and names only things that exist.

Two defects, one file, because they were found together.

**The papers.** Seven of the nine bricks carry ``CODING.md``,
``CONTRIBUTING.md``, ``EXAMPLES.md`` and ``TRIGGERS.md`` at their root. Two
did not: ``sprezzature-publish`` and ``sprezzature-ui``, the two youngest,
went out without any of the four and nothing noticed for weeks. Nothing
*could* notice: each brick's own suite checks what that brick has, and a file
absent from a repository is absent from the list of files that repository
tests. The question "do the nine agree" can only be asked from here, which is
the one place that sees all nine.

**The names.** ``TRIGGERS.md`` is the file an agent reads to choose a tool, so
it is dense with command names and MCP tool names. Writing the two missing
ones produced five invented MCP tools in a single table, all plausible, none
real: ``meta_tags`` for a package whose tool is called nothing at all, a
``transcribe`` in a neighbour that has ``convert_captions``. A reader who
believes the table calls a tool that is not there. This is the suite's oldest
rule, that a name quoted to a reader must come from the thing it describes,
applied to the file where getting it wrong is most expensive.

Both halves skip, per brick, when that brick has no sibling checkout. The
companion test below refuses to let the whole file go quiet that way: a run
that saw nothing says so and fails, because a skip and a pass look alike in a
summary line.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

#: What a brick's root is expected to hold. The pairs are the EN/FR parity
#: the writing charter asks for; ``LICENSE`` is extensionless in every brick
#: and ``LICENSE.md`` only in this repository, which is why it is spelled
#: without one here.
CANONICAL_PAPERS: tuple[str, ...] = (
    "README.md",
    "LISEZMOI.md",
    "CHANGELOG.md",
    "CODING.md",
    "CONTRIBUTING.md",
    "EXAMPLES.md",
    "TRIGGERS.md",
    "LANDSCAPE.md",
    "PAYSAGE.md",
    "LICENSE",
)

#: A console script named inside backticks. Digits are in the class because
#: ``sprezzature-ui-i18n-audit`` has one, and the first version of this
#: pattern silently matched nothing in the brick it was written for.
_BACKTICKED_COMMAND = re.compile(r"`((?:sprezzature|make)-[a-z0-9-]+)`")

#: A row of a Markdown table whose header carries an ``MCP tool`` column.
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")

#: ``operation_id="lint_html"`` in a brick's FastAPI module. These become the
#: MCP tool names, which is why the names are read from there and not from a
#: list kept beside them.
_OPERATION_ID = re.compile(r'operation_id="([a-z_]+)"')

#: ``my-command = "pkg.module:main"`` under ``[project.scripts]``.
_CONSOLE_SCRIPT = re.compile(r"^([a-z][a-z0-9-]*)\s*=\s*\"", re.M)


def _checkout(brick: str) -> Path | None:
    """The sibling checkout for ``brick``, or ``None`` if this machine has none."""
    repo = REPO_ROOT.parent / brick
    return repo if repo.is_dir() else None


def _every_console_script() -> set[str]:
    """Every command name the suite installs, across every brick present.

    Across bricks on purpose. ``TRIGGERS.md`` routes *away* from its own
    package as often as towards it, and a table that sends a reader to
    ``sprezzature-audio-captions`` is naming a real command even though it
    belongs to a neighbour.
    """
    names: set[str] = set()
    for brick in SHIPPED_SKILLS:
        repo = _checkout(brick)
        if repo is None:
            continue
        pyproject = repo / "pyproject.toml"
        if not pyproject.is_file():
            continue
        body = pyproject.read_text(encoding="utf-8")
        start = body.find("[project.scripts]")
        if start == -1:
            continue
        end = body.find("\n[", start + 1)
        section = body[start : end if end != -1 else len(body)]
        names |= set(_CONSOLE_SCRIPT.findall(section))
    return names


def _every_mcp_tool() -> set[str]:
    """Every MCP tool name the suite exposes, across every brick present."""
    names: set[str] = set()
    for brick in SHIPPED_SKILLS:
        repo = _checkout(brick)
        if repo is None:
            continue
        for api in repo.glob("*/api.py"):
            names |= set(_OPERATION_ID.findall(api.read_text(encoding="utf-8")))
    return names


def _mcp_cells(triggers: str) -> list[str]:
    """Values in the ``MCP tool`` column of every table that has one.

    A cell is read only when the table above it declares the column, so a
    free-text mention of a tool elsewhere in the prose is left alone. The
    point is the table, which is what an agent scans.
    """
    cells: list[str] = []
    column: int | None = None
    for line in triggers.splitlines():
        row = _TABLE_ROW.match(line)
        if row is None:
            column = None
            continue
        parts = [p.strip() for p in row.group(1).split("|")]
        if any(p.lower() == "mcp tool" for p in parts):
            column = next(i for i, p in enumerate(parts) if p.lower() == "mcp tool")
            continue
        if column is None or column >= len(parts):
            continue
        if set(parts[column]) <= {"-", ":", " "}:  # the ``|---|---|`` rule
            continue
        cells.append(parts[column])
    return cells


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_brick_carries_the_canonical_papers(brick: str) -> None:
    """The nine agree on which documents a brick ships."""
    repo = _checkout(brick)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick}")
    absent = [name for name in CANONICAL_PAPERS if not (repo / name).is_file()]
    assert not absent, (
        f"{brick} is missing {absent}, which the other bricks carry. Either "
        f"write them or take the name out of CANONICAL_PAPERS and say why."
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_brick_routes_to_commands_that_exist(brick: str) -> None:
    """A command named in TRIGGERS.md is one `pip install` puts on PATH."""
    repo = _checkout(brick)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick}")
    triggers = repo / "TRIGGERS.md"
    if not triggers.is_file():
        pytest.skip(f"{brick} has no TRIGGERS.md; the test above is the one to read")
    installed = _every_console_script()
    named = set(_BACKTICKED_COMMAND.findall(triggers.read_text(encoding="utf-8")))
    # A brick name is not a command name, and both are spelled the same way.
    named -= set(SHIPPED_SKILLS)
    invented = sorted(named - installed)
    assert not invented, (
        f"{brick}/TRIGGERS.md tells an agent to call {invented}, and no brick "
        f"on this machine installs them"
    )


@pytest.mark.parametrize("brick", SHIPPED_SKILLS)
def test_a_brick_routes_to_mcp_tools_that_exist(brick: str) -> None:
    """An MCP tool named in a TRIGGERS.md table is a real ``operation_id``."""
    repo = _checkout(brick)
    if repo is None:
        pytest.skip(f"no sibling checkout for {brick}")
    triggers = repo / "TRIGGERS.md"
    if not triggers.is_file():
        pytest.skip(f"{brick} has no TRIGGERS.md; the test above is the one to read")
    exposed = _every_mcp_tool()
    invented: list[str] = []
    for cell in _mcp_cells(triggers.read_text(encoding="utf-8")):
        # The first backticked name is the tool. What follows it is a
        # qualifier: figures writes ``render_figure`` (`options`) to say
        # which argument carries the rest, and ``options`` is not a tool.
        #
        # A cell with no backticked name at all is prose saying there is no
        # tool, which is an answer and not a gap.
        names = re.findall(r"`([a-z_]+)`", cell)
        if names and names[0] not in exposed:
            invented.append(names[0])
    assert not invented, (
        f"{brick}/TRIGGERS.md offers {sorted(set(invented))} as MCP tools, and "
        f"no brick on this machine declares that operation_id"
    )


def test_ci_fetches_the_papers_this_file_asks_for() -> None:
    """The list above and the fetch script's path list are one question.

    ``scripts/fetch_siblings.sh`` brings a sibling in as a sparse checkout of
    named paths. None of the ten documents above were among them, so on a
    runner the checkout exists — no skip — and every one of those files is
    missing: nine failures, in the one place a developer does not look until
    the build is red.

    It never showed, because the commit that added the check has not been
    pushed. The two lists are kept together here rather than in a comment,
    which is what they were relying on.
    """
    fetch = REPO_ROOT / "scripts" / "fetch_siblings.sh"
    assert fetch.is_file(), fetch
    block = re.search(r"^PATHS=\((.*?)^\)", fetch.read_text(encoding="utf-8"), re.M | re.S)
    assert block, "fetch_siblings.sh no longer declares a PATHS array"
    fetched = set(re.findall(r"'/([^']+)'", block.group(1)))
    missing = [name for name in CANONICAL_PAPERS if name not in fetched]
    assert not missing, (
        f"the papers check asks for {missing} and fetch_siblings.sh does not "
        f"bring them, so this file is red on CI and green everywhere else. "
        f"Add the path there, or drop the name from CANONICAL_PAPERS."
    )


def test_this_run_saw_bricks_to_check() -> None:
    """A file that skipped everything reads exactly like a file that passed.

    Not a count of the nine: that would measure which checkouts this machine
    happens to hold rather than whether the guard works, and it would fail on
    a laptop holding one clone. It asks the smaller question the skips above
    cannot answer for themselves.
    """
    seen = [brick for brick in SHIPPED_SKILLS if _checkout(brick) is not None]
    assert seen, (
        "no sibling checkout at all, so every test in this file skipped. "
        "Run scripts/fetch_siblings.sh, which is what CI does."
    )
    assert _every_console_script(), "read no console scripts from any brick"
    assert _every_mcp_tool(), "read no MCP tool names from any brick"
