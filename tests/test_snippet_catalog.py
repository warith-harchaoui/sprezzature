"""
Tests for the sprezzature-ui snippet catalog at
``sprezzature-ui/assets/snippets/``.

The catalog is the make-side counterpart to the sprezzature-ux-laws
``--fix`` mode: the auditor repairs what the agent emits; the
catalog gives the agent shapes worth emitting in the first place.
Both halves stay in sync only if the catalog itself keeps passing
the auditors.

The tests parametrise over every ``.html`` file in the catalog,
running each through:

* ``sprezzature-ux-laws/scripts/audit_laws_of_ux.py`` — must return zero
  findings.
* ``sprezzature-accessibility/scripts/lint_a11y.py`` — must return zero
  findings.

Plus a structural test: every snippet must be referenced from
``INDEX.md`` (and vice versa).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SNIPPETS_DIR: Path = REPO_ROOT / "sprezzature-ui" / "assets" / "snippets"
INDEX: Path = SNIPPETS_DIR / "INDEX.md"
AUDIT_LAWS: Path = (
    REPO_ROOT / "sprezzature-ux-laws" / "scripts" / "audit_laws_of_ux.py"
)
LINT_A11Y: Path = (
    REPO_ROOT / "sprezzature-accessibility" / "scripts" / "lint_a11y.py"
)


def _snippets() -> list[Path]:
    """Return every .html snippet in the catalog, deterministic order."""
    return sorted(SNIPPETS_DIR.glob("*.html"))


def test_snippets_dir_exists() -> None:
    """The catalog folder must exist; the rest of the suite depends on it."""
    assert SNIPPETS_DIR.is_dir()


def test_index_md_exists() -> None:
    """The catalog ships its own INDEX.md so consumers can browse it."""
    assert INDEX.is_file()


def test_catalog_is_non_empty() -> None:
    """At least one snippet must ship — the catalog is not aspirational."""
    assert _snippets(), (
        f"No .html snippets in {SNIPPETS_DIR} — the catalog is the "
        f"point of this folder."
    )


@pytest.mark.parametrize("snippet", _snippets(), ids=lambda p: p.name)
def test_snippet_passes_laws_of_ux_audit(snippet: Path) -> None:
    """Every snippet must produce zero Laws-of-UX findings."""
    proc = subprocess.run(
        [sys.executable, str(AUDIT_LAWS), str(snippet)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"{snippet.name} failed the Laws-of-UX audit:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )


@pytest.mark.parametrize("snippet", _snippets(), ids=lambda p: p.name)
def test_snippet_passes_accessibility_lint(snippet: Path) -> None:
    """Every snippet must produce zero accessibility findings."""
    proc = subprocess.run(
        [sys.executable, str(LINT_A11Y), str(snippet)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"{snippet.name} failed the accessibility lint:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )


@pytest.mark.parametrize("snippet", _snippets(), ids=lambda p: p.name)
def test_snippet_is_referenced_in_index(snippet: Path) -> None:
    """Every snippet on disk must appear in INDEX.md (and vice versa)."""
    body: str = INDEX.read_text(encoding="utf-8")
    assert snippet.name in body, (
        f"{snippet.name} ships in the catalog but is not referenced "
        f"in INDEX.md — add a row with its law and trigger phrases."
    )


def test_index_lists_no_orphan_filenames() -> None:
    """Conversely, INDEX.md must not name a snippet that does not exist."""
    body: str = INDEX.read_text(encoding="utf-8")
    on_disk: set[str] = {p.name for p in _snippets()}
    # Scan for any *bare-basename* token matching ``*.html`` between
    # backticks. We exclude path tokens (anything containing ``/``)
    # and template placeholders (anything containing ``<``) so the
    # "Adding a new snippet" stub instructions do not register as
    # orphans.
    import re
    referenced: set[str] = {
        m
        for m in re.findall(r"`([^`\s]+\.html)`", body)
        if "/" not in m and "<" not in m
    }
    orphans: set[str] = referenced - on_disk
    assert not orphans, (
        f"INDEX.md names snippet(s) absent from disk: {sorted(orphans)}"
    )


def test_each_snippet_has_a_header_comment() -> None:
    """
    Every snippet opens with an HTML comment explaining the law.

    The comment is how a future contributor (or the agent) decides
    whether the snippet is the right pick — without it, the catalog
    is a pile of HTML files with no context.
    """
    for snippet in _snippets():
        first_chars: str = snippet.read_text(encoding="utf-8")[:5].strip()
        assert first_chars.startswith("<!--"), (
            f"{snippet.name} does not open with an HTML comment "
            f"explaining the law it embodies."
        )
