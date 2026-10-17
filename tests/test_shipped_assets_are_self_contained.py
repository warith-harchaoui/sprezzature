"""
No shipped file may depend on a path that exists on one machine.

The defect this guards against is the quiet kind. Two Mermaid-generated SVGs
in ``sprezzature-figures/assets/`` loaded their typeface from

    file:///Users/warithharchaoui/front/web/fonts/roboto/Roboto-Variable.woff2

an absolute path into ``front``, the repository this one was renamed from.
It had been wrong since the rename and nobody saw it, for the worst possible
reason: **the old folder is still on the author's laptop**, so the font
resolved locally and the figure looked right to the only person likely to
open it. Everywhere else — a clone, a CI runner, a reader's browser, the
published site — the ``@font-face`` silently failed and the diagram fell back
to a system face. A broken link announces itself; this does not.

The rule is therefore about *portability*, not about one URL: a file this
repository ships has to carry what it needs, or reference it relatively.
Absolute local paths and ``file://`` URLs are neither.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: Extensions whose contents are shipped and read by something other than a
#: developer: assets served to a browser, bundled into a wheel, or embedded
#: in a page. Source code is excluded on purpose — a path in a test fixture
#: or a developer script is a different conversation.
SHIPPED_SUFFIXES = {".svg", ".html", ".css", ".js", ".json", ".xml", ".vtt"}

#: Directories that never ship.
SKIP_PARTS = {
    ".git", "node_modules", "__pycache__", ".venv", "dist", "build",
    ".private", ".pytest_cache", ".ruff_cache", ".mypy_cache", "brag-output",
    "g",
}

#: What a path that only exists on one machine looks like.
#:
#: Matched on a *baked-in* path, never on the scheme alone. The first version
#: of this pattern flagged ``const url = 'file://' + path.resolve(src)`` --
#: a renderer building a URL correctly at run time -- and a comment in
#: gapminder-player.js reading "and from file://". Both are fine; a guard
#: that cries at them is a guard someone switches off. So ``file://`` must be
#: followed by a rooted path with at least one directory in it, which is the
#: shape a dead absolute reference actually has.
LOCAL_PATH = re.compile(
    r"""file:///[A-Za-z0-9_.~%-]+/[^\s"')>]*"""      # file:///Users/…/x.woff2
    r"""|["'(]\s*/(?:Users|home)/[^\s"')>]+"""        # the same without a scheme
    r"""|[A-Za-z]:\\\\[^\s"')>]+"""                  # C:\Users\…
)


def _shipped_files() -> list[Path]:
    found: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SHIPPED_SUFFIXES:
            continue
        if SKIP_PARTS & set(path.relative_to(ROOT).parts):
            continue
        found.append(path)
    return sorted(found)


SHIPPED = _shipped_files()


def test_there_are_shipped_files_to_check() -> None:
    """A guard over an empty list is a guard over nothing."""
    assert len(SHIPPED) > 100, (
        f"only {len(SHIPPED)} shipped files found; the walk has probably "
        f"stopped matching"
    )


def test_no_shipped_file_points_at_a_path_on_one_machine() -> None:
    """
    The whole rule, in one pass.

    Reported together rather than one test per file: these arrive in families
    — a generator that emits an absolute path emits it into every figure it
    draws — and a list of all of them is more useful than the first one
    alphabetically.
    """
    offenders: list[str] = []
    for path in SHIPPED:
        text = path.read_text(encoding="utf-8", errors="replace")
        # Font and image payloads are embedded as data: URIs and can be
        # megabytes of base64; nothing in them is a path.
        text = re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,…", text)
        for hit in LOCAL_PATH.findall(text):
            offenders.append(f"{path.relative_to(ROOT)}: {hit.strip()[:90]}")

    assert not offenders, (
        "shipped files reference paths that exist on one machine; they "
        "resolve for whoever wrote them and for nobody else:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "name", ["ralph-eyeball-loop.svg", "ralph-eyeball-loop-fr.svg"]
)
def test_the_mermaid_diagrams_carry_their_typeface(name: str) -> None:
    """
    The regression, named.

    These two are the files that had the dead path, and they are generated
    output — so the next regeneration can reintroduce it. The check is not
    "no absolute path" (the test above owns that) but the positive form: the
    face they declare must travel with them.
    """
    path = ROOT / "sprezzature-figures" / "assets" / name
    text = path.read_text(encoding="utf-8")
    faces = re.findall(r"@font-face\{[^}]*\}", text)
    assert faces, f"{name} declares no @font-face at all"
    for face in faces:
        assert "data:font/" in face, (
            f"{name} declares a typeface it does not carry: "
            f"{re.sub(r'base64,[A-Za-z0-9+/=]+', 'base64,…', face)[:160]}"
        )
