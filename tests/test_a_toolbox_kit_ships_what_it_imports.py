"""
A toolbox kit ships every local helper the tool it vendors imports.

``build_tool_kits.py`` lists, per kit, the files to copy into ``lib/``. The
list is written by hand, and the tools it copies keep growing helpers. Both
things are fine until nothing runs the builder, which is where this was:

* the **maps** kit named six of ``make_choropleth``'s local imports and the
  generator had reached twelve. Classification arrived in September, and place
  labels, provenance, simplification and the text box with it; the kit went on
  being built from the old six, so it failed outright, in both languages, and
  ``packages.html`` kept linking the zip from 12 September. The data followed
  the same drift: the choropleth now shades real terrain and places labels, so
  it wanted an elevation tier and a cities file the kit did not carry.
* the **accessibility** kit tripped its own standalone check on ``fill_alt``,
  the ``--fix-alt`` branch, imported inside the ``if`` that serves it. That
  one is right to be absent — drafting alt text needs a local vision model a
  kit promising "runs with nothing installed" cannot carry — so it is declared
  optional rather than vendored.

Four of ten kits did not build. What this asks is the question that catches
the first kind cheaply and from here: is the ``sources`` list the transitive
closure of the tool's own local imports? The second kind is what the
builder's ``optional`` list is for, and an entry there has to say why.

The full build is the honest check and it costs a minute; this one costs
nothing and fails on the same drift a day earlier.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER = REPO_ROOT / "web" / "tools" / "build_tool_kits.py"

#: ``from _helper import …`` / ``import _helper`` at the start of a line: a
#: sibling module in the same ``scripts/`` directory, which a kit must carry.
_LOCAL_IMPORT = re.compile(r"^(?:from|import)\s+(_\w+)", re.M)


def _builder():
    name = "_tool_kit_builder"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BUILDER)
    assert spec is not None and spec.loader is not None, BUILDER
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _closure(repo: Path, entry: Path) -> set[str]:
    """Every local helper reachable from ``entry``, transitively."""
    scripts = entry.parent
    seen: set[str] = set()
    queue = [entry]
    while queue:
        current = queue.pop()
        if not current.is_file():
            continue
        for helper in _LOCAL_IMPORT.findall(
            current.read_text(encoding="utf-8", errors="replace")
        ):
            if helper in seen:
                continue
            candidate = scripts / f"{helper}.py"
            if candidate.is_file():
                seen.add(helper)
                queue.append(candidate)
    return seen


KITS = sorted(_builder().KITS) if BUILDER.is_file() else []


@pytest.mark.parametrize("name", KITS)
def test_a_kit_vendors_every_helper_its_tool_imports(name: str) -> None:
    """The sources list is the closure, not a list somebody remembers."""
    builder = _builder()
    spec = builder.KITS[name]
    repo = REPO_ROOT.parent / spec["repo"]
    if not repo.is_dir():
        pytest.skip(f"no checkout for {spec['repo']}")

    sources = [Path(s) for s in spec["sources"]]
    shipped = {source.stem for source in sources}
    optional = set(spec.get("optional", []))

    needed: set[str] = set()
    for source in sources:
        needed |= _closure(repo, repo / source)

    missing = sorted(needed - shipped - optional)
    assert not missing, (
        f"the {name} kit vendors {sorted(shipped)} and its tools import "
        f"{missing}, which it does not carry. Either add the file to "
        f"`sources`, or — if the import sits inside a branch the kit does not "
        f"take — add the name to `optional` with the reason."
    )


def test_every_optional_entry_is_a_name_something_imports() -> None:
    """An `optional` entry nobody imports is a sentence nobody can check.

    The list is the kit's record of what it deliberately does without. A name
    that has stopped appearing anywhere reads as a decision that still holds,
    and the next reader cannot tell it from one that does not.
    """
    builder = _builder()
    stale: dict[str, list[str]] = {}
    for name, spec in builder.KITS.items():
        repo = REPO_ROOT.parent / spec["repo"]
        if not repo.is_dir():
            continue
        body = "\n".join(
            (repo / source).read_text(encoding="utf-8", errors="replace")
            for source in spec["sources"]
            if (repo / source).is_file()
        )
        unused = [
            entry
            for entry in spec.get("optional", [])
            if not re.search(rf"\b{re.escape(entry)}\b", body)
        ]
        if unused:
            stale[name] = unused
    assert not stale, f"optional entries nothing imports any more: {stale}"


def test_there_are_kits_to_check() -> None:
    """An empty registry would make every case above collect nothing."""
    assert len(KITS) >= 4, f"the builder declares {len(KITS)} kits"
