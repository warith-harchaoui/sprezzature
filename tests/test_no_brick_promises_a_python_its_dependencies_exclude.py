"""
No brick promises a Python its own dependencies exclude.

The defect
----------
``requires-python`` is a promise printed on the tin: PyPI shows it, and pip
refuses the install on an interpreter outside it. A dependency carries the same
promise, and the narrower of the two is the one that decides. So a brick saying
``>=3.10`` while depending on a package saying ``>=3.10,<3.14`` advertises an
interpreter on which ``pip install <brick>`` cannot resolve at all — and says
so nowhere a reader of either manifest can see it.

That is not hypothetical here. The suite's own helper family —
``os-helper``, ``audio-helper``, ``video-helper``, ``speaker-helper``,
``sftp-helper`` — is pinned ``>=3.10,<3.14`` across the board, and bricks reach
for it: ``sprezzature-video`` names ``os-helper`` and ``audio-helper`` among its
base dependencies. It declares ``>=3.10,<3.14`` for exactly this reason, and it
is the only brick that got there on purpose. The ceiling travels with the
dependency; this is the check that makes it travel.

What is asserted, and what is not
---------------------------------
**Base dependencies only.** A ceiling in a base dependency breaks
``pip install <brick>``, which is the sentence the brick's own metadata makes.
A ceiling reached through an *extra* leaves the base install resolvable — only
``pip install "<brick>[feature]"`` narrows — so that is a documentation
question, not a broken promise, and asserting it from here would make this
guard fail on a manifest whose plain install is correct.

Both ends are checked. A floor is the same fault mirrored: an extra pulling a
package that wants ``>=3.11`` into a brick promising ``>=3.10`` is a resolution
failure on the floor of the matrix, which is where nobody looks.

Why regex and not ``tomllib``
-----------------------------
The floor is 3.10 and ``tomllib`` arrived in 3.11. A bare import here fails
*collection* on the oldest job of the matrix, which is the one place this is
written for — the defect ``test_nothing_imports_a_module_the_floor_lacks``
exists to catch. ``tomli`` is declared in ``requirements-dev.txt``, so the
fallback would work; a ten-line reader that needs neither is cheaper than
depending on that being installed.

Where the other side of the comparison comes from
-------------------------------------------------
Two sources, and **not** the installed distribution:

1. **A sibling's own manifest.** Every brick-to-brick edge is answered from
   the file itself, which ``scripts/fetch_siblings.sh`` fetches on the runner.
   No install needed, and it is the half that cannot go stale.
2. **The table below**, for the helper family. Those packages are not installed
   in the hub's CI job — the hub depends on none of them at runtime — so
   without a declared answer this guard would quietly compare nothing where it
   matters most.

The third source, ``importlib.metadata`` on whatever happens to be installed,
was tried first and is deliberately gone. It measures the machine, not the
manifest. ``sprezzature-figures`` asks for ``scipy>=1.11`` and
``sprezzature-maps`` for ``pyproj>=3.6``; the copies installed here are scipy
1.17.1 and pyproj 3.7.2, both of which declare ``>=3.11``, while the versions
those floors actually name declare ``>=3.9``. Reading the installed metadata
therefore reported two bricks as advertising a Python they exclude, on a floor
pip resolves around by picking an older release. A lower bound is not a pin,
and the window of one resolved version is not the window of a requirement.

The table is kept honest by ``test_the_declared_windows_agree_with_what_is_installed``:
where the package *is* installed, the two must say the same thing. A table that
can drift without a complaint is worse than no table.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.metadata as metadata
import re
from pathlib import Path

from skills_manifest import SHIPPED_SKILLS

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The Python window of packages this suite depends on and CI does not install.
#: Short on purpose: a long list of packages no brick names would make this
#: guard look thorough while answering nothing. ``None`` for an end means "no
#: bound declared".
DECLARED_WINDOWS: dict[str, tuple[tuple[int, int] | None, tuple[int, int] | None]] = {
    "os-helper": ((3, 10), (3, 14)),
    "audio-helper": ((3, 10), (3, 14)),
    "video-helper": ((3, 10), (3, 14)),
    "speaker-helper": ((3, 10), (3, 14)),
    "sftp-helper": ((3, 10), (3, 14)),
    "vocal-helper": ((3, 10), (3, 14)),
}

_REQUIRES_PYTHON = re.compile(r'^\s*requires-python\s*=\s*"([^"]+)"', re.M)
_FLOOR = re.compile(r">=\s*(\d+)\.(\d+)")
_CEILING = re.compile(r"<\s*(\d+)\.(\d+)")
_SECTION = re.compile(r"^\[([^\]]+)\]\s*$", re.M)
_DIST_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
_ARRAY_KEY = re.compile(r'^[ \t]*(?:"([^"]+)"|([A-Za-z0-9_-]+))[ \t]*=[ \t]*\[', re.M)


def _strip_comments(text: str) -> str:
    """Drop ``#`` comments, leaving quoted ``#`` alone.

    A comment inside a dependency array is prose, and prose contains quoted
    words. Reading the array without this step reported ``invoked``,
    ``passed`` and ``3.11`` as packages the suite depends on — three
    dependencies that do not exist, in a guard whose whole job is to be
    believed about dependencies.
    """
    out: list[str] = []
    for line in text.splitlines():
        quoted = False
        cut = len(line)
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


def _sections(body: str) -> dict[str, str]:
    """``{table name: its text}`` for the top-level tables of a manifest."""
    found: dict[str, str] = {}
    name: str | None = None
    start = 0
    for match in _SECTION.finditer(body):
        if name is not None:
            found[name] = body[start : match.start()]
        name, start = match.group(1), match.end()
    if name is not None:
        found[name] = body[start:]
    return found


def _arrays(block: str) -> dict[str, list[str]]:
    """``{key: [strings]}`` for every ``key = [ … ]`` in *block*.

    Brace-matched rather than line-matched: every dependency array in this
    suite spans many lines, and several hold a nested extra reference.
    """
    found: dict[str, list[str]] = {}
    for match in _ARRAY_KEY.finditer(block):
        key = match.group(1) or match.group(2)
        index, depth = match.end() - 1, 0
        while index < len(block):
            if block[index] == "[":
                depth += 1
            elif block[index] == "]":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        found[key] = re.findall(r'"([^"]+)"', block[match.end() : index])
    return found


def _window(spec: str) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """``(floor, ceiling)`` of a ``requires-python`` specifier."""
    floor = _FLOOR.search(spec)
    ceiling = _CEILING.search(spec)
    return (
        (int(floor.group(1)), int(floor.group(2))) if floor else None,
        (int(ceiling.group(1)), int(ceiling.group(2))) if ceiling else None,
    )


def _dist(requirement: str) -> str:
    """The normalised distribution name a requirement string names."""
    match = _DIST_NAME.match(requirement.strip())
    return match.group(0).lower().replace("_", "-") if match else ""


class Manifest:
    """One ``pyproject.toml``, read far enough to answer this guard."""

    def __init__(self, label: str, path: Path) -> None:
        body = _strip_comments(path.read_text(encoding="utf-8"))
        tables = _sections(body)
        project = tables.get("project", "")
        spec = _REQUIRES_PYTHON.search(project)
        self.label = label
        self.path = path
        self.spec = spec.group(1) if spec else ""
        self.floor, self.ceiling = _window(self.spec)
        self.base = [
            _dist(r) for r in _arrays(project).get("dependencies", []) if _dist(r)
        ]
        self.extras = {
            name: [_dist(r) for r in reqs if _dist(r)]
            for name, reqs in _arrays(
                tables.get("project.optional-dependencies", "")
            ).items()
        }


def _manifests() -> list[Manifest]:
    """The hub and every brick beside it that has a manifest to read."""
    found = [Manifest("sprezzature", REPO_ROOT / "pyproject.toml")]
    for brick in SHIPPED_SKILLS:
        path = REPO_ROOT.parent / brick / "pyproject.toml"
        if path.is_file():
            found.append(Manifest(brick, path))
    return found


def _dependency_window(
    name: str, siblings: dict[str, Manifest]
) -> tuple[tuple[int, int] | None, tuple[int, int] | None] | None:
    """The Python window a dependency declares, or ``None`` if unknowable here.

    Never ``importlib.metadata``: see the module docstring. A requirement is a
    lower bound over many releases, and the one release this machine resolved
    is not allowed to speak for the rest.
    """
    if name in siblings:
        sibling = siblings[name]
        return sibling.floor, sibling.ceiling
    return DECLARED_WINDOWS.get(name)


def test_no_brick_promises_a_python_its_base_dependencies_exclude() -> None:
    """Every manifest's own window fits inside the window its base deps allow."""
    manifests = _manifests()
    siblings = {m.label: m for m in manifests}
    broken: list[str] = []

    for brick in manifests:
        for name in brick.base:
            window = _dependency_window(name, siblings)
            if window is None:
                continue
            floor, ceiling = window
            if ceiling is not None and (
                brick.ceiling is None or brick.ceiling > ceiling
            ):
                broken.append(
                    f"{brick.label}: requires-python {brick.spec!r} promises Python "
                    f"{ceiling[0]}.{ceiling[1]} and later, which its base dependency "
                    f"{name!r} (<{ceiling[0]}.{ceiling[1]}) excludes. "
                    f"Add ,<{ceiling[0]}.{ceiling[1]} to requires-python."
                )
            if floor is not None and (brick.floor is None or brick.floor < floor):
                broken.append(
                    f"{brick.label}: requires-python {brick.spec!r} promises Python "
                    f"below {floor[0]}.{floor[1]}, which its base dependency "
                    f"{name!r} (>={floor[0]}.{floor[1]}) excludes. "
                    f"Raise the floor to >={floor[0]}.{floor[1]}."
                )

    assert not broken, (
        f"{len(broken)} brick(s) advertise a Python their own base dependencies "
        f"cannot be installed on:\n  " + "\n  ".join(broken)
    )


def test_the_guard_compared_something() -> None:
    """A precondition that cannot be met is a pass that means nothing.

    The check above iterates and asserts ``not broken``, which is exactly as
    true over an empty list as over a clean suite. Three structural facts are
    asserted instead of a count, because a count moves with every manifest
    edit and a threshold nobody maintains is the next silent pass:

    * the siblings are beside the hub at all — without them there is one
      manifest, the hub's, and it declares no base dependencies whatever;
    * every brick-to-brick base edge resolved from a manifest;
    * at least one base dependency was answered by ``DECLARED_WINDOWS``. That
      is the helper family, the only ceiling in the suite, and the half that
      would go quiet if the table were emptied or the names drifted.
    """
    manifests = _manifests()
    siblings = {m.label: m for m in manifests}
    base_pairs = [(brick, name) for brick in manifests for name in brick.base]

    assert len(manifests) >= 2, (
        "only the hub's own manifest was readable, and it declares no base "
        "dependencies — so the comparison above ran over nothing. Run "
        "scripts/fetch_siblings.sh."
    )

    unresolved = sorted(
        {
            name
            for _brick, name in base_pairs
            if name.startswith("sprezzature-") and name not in siblings
        }
    )
    assert not unresolved, (
        "brick-to-brick edges must always be answerable from the manifests, "
        f"and these were not: {unresolved}"
    )

    from_table = sorted(
        {name for _brick, name in base_pairs if name in DECLARED_WINDOWS}
    )
    assert from_table, (
        "no base dependency in the suite was answered by DECLARED_WINDOWS, so "
        "the only Python ceiling the suite carries went unexamined. Either the "
        "table no longer names what the bricks depend on, or the bricks no "
        "longer depend on the helper family — and the second needs saying."
    )


def test_the_declared_windows_agree_with_what_is_installed() -> None:
    """Where a table entry's package is installed, the two must say the same.

    The table exists because the hub's CI installs none of the helper family.
    It is also the half that can rot: a helper that lifts its ceiling to 3.14
    would leave this guard faulting bricks that are now correct. So every
    entry is cross-read against real metadata wherever real metadata exists,
    which is a developer's machine and every brick's own job.
    """
    disagree: list[str] = []
    checked = 0
    for name, declared in DECLARED_WINDOWS.items():
        try:
            spec = metadata.metadata(name).get("Requires-Python")
        except metadata.PackageNotFoundError:
            continue
        if not spec:
            continue
        checked += 1
        installed = _window(spec)
        if installed != declared:
            disagree.append(
                f"{name}: DECLARED_WINDOWS says {declared}, the installed "
                f"{metadata.version(name)} says {spec!r} -> {installed}"
            )
    assert not disagree, (
        "DECLARED_WINDOWS has drifted from the packages it describes:\n  "
        + "\n  ".join(disagree)
    )
    if checked == 0:
        return  # a bare runner installs none of them; nothing to cross-read
    assert checked >= 1
