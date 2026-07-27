"""
Tests for the ``lint_markdown --fix`` mode — specifically the new
MD009 trailing-whitespace stripper.

The existing ``--fix`` flag in ``lint_markdown.py`` was scoped to
Mermaid PNG insertions on ``--render-mermaid``. v0.12.0 extends it
to also fix MD009 (trailing whitespace) so the markdown lint gains
parity with the other auditors' ``--fix`` modes.

Covers:

* The pure function :func:`fix_trailing_whitespace` against every
  shape the spec cares about (clean lines, tab-trailing lines, the
  intentional two-space line-break, blank-line-of-whitespace).
* Idempotence — a second pass through the fixer produces an
  identical string.
* Trailing-newline preservation — the file's final EOL is kept.
* CLI integration — ``--fix`` rewrites a real file in place, and
  the residual MD009 finding count drops to zero on a re-lint.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# ``conftest.py`` adds ``sprezzature-publish/scripts`` to sys.path.
from lint_markdown import fix_trailing_whitespace


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT: Path = (
    REPO_ROOT / "sprezzature-publish" / "scripts" / "lint_markdown.py"
)


# ── Pure-function tests ────────────────────────────────────────────────────


def test_strips_single_trailing_space() -> None:
    """One trailing space is stripped (it is neither the line-break nor blank)."""
    assert fix_trailing_whitespace("hello \n") == "hello\n"


def test_strips_tabs_at_end_of_line() -> None:
    """Trailing tabs are stripped regardless of count."""
    assert fix_trailing_whitespace("hello\t\t\n") == "hello\n"
    assert fix_trailing_whitespace("hello \t\n") == "hello\n"


def test_preserves_intentional_two_space_line_break() -> None:
    """Exactly two trailing spaces is the canonical Markdown ``<br>`` — keep it."""
    src: str = "first line  \nsecond\n"
    assert fix_trailing_whitespace(src) == src


def test_strips_three_or_more_trailing_spaces() -> None:
    """Three or more spaces are not the line break — strip them."""
    assert fix_trailing_whitespace("hello   \n") == "hello\n"
    assert fix_trailing_whitespace("hello     \n") == "hello\n"


def test_collapses_blank_line_of_spaces() -> None:
    """A line consisting solely of whitespace becomes empty (line count kept)."""
    src: str = "para\n   \nnext\n"
    assert fix_trailing_whitespace(src) == "para\n\nnext\n"


def test_preserves_clean_lines() -> None:
    """Lines without trailing whitespace pass through unchanged."""
    src: str = "# Heading\n\nClean body line.\n\n- bullet\n"
    assert fix_trailing_whitespace(src) == src


def test_preserves_trailing_newline_presence() -> None:
    """Final-EOL absence / presence survives the round-trip."""
    with_eol: str = "hello \n"
    no_eol: str = "hello "
    assert fix_trailing_whitespace(with_eol).endswith("\n")
    assert not fix_trailing_whitespace(no_eol).endswith("\n")


def test_idempotent() -> None:
    """A second pass produces an identical string."""
    src: str = "a   \nb  \nc\t\n   \n"
    once: str = fix_trailing_whitespace(src)
    twice: str = fix_trailing_whitespace(once)
    assert once == twice


# ── CLI integration ───────────────────────────────────────────────────────


def test_cli_fix_strips_trailing_whitespace(tmp_path: Path) -> None:
    """``--fix`` rewrites a real file in place and clears MD009."""
    src: Path = tmp_path / "doc.md"
    src.write_text(
        "# Title   \n\nBody line.\n   trailing tabs\t\n",
        encoding="utf-8",
    )
    # Apply the fix.
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(src)],
        capture_output=True, text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr  # exit 1 if other rules fire
    body: str = src.read_text(encoding="utf-8")
    # No line ends in three-or-more spaces; the cleaned ``# Title`` is
    # no longer flagged by MD009.
    assert "# Title\n" in body
    assert "   trailing tabs\n" in body  # leading spaces preserved
    # Re-lint — MD009 should not appear in the output.
    proc2 = subprocess.run(
        [sys.executable, str(SCRIPT), str(src)],
        capture_output=True, text=True,
    )
    assert "MD009" not in proc2.stdout


def test_cli_fix_is_idempotent(tmp_path: Path) -> None:
    """A second ``--fix`` pass leaves the file untouched."""
    src: Path = tmp_path / "doc.md"
    src.write_text("hello   \nworld\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(src)],
        capture_output=True, text=True,
    )
    first: str = src.read_text(encoding="utf-8")
    subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(src)],
        capture_output=True, text=True,
    )
    second: str = src.read_text(encoding="utf-8")
    assert first == second


def test_help_advertises_md009_in_fix(tmp_path: Path) -> None:
    """``--help`` mentions MD009 / trailing whitespace under ``--fix``."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    collapsed: str = " ".join(proc.stdout.split())
    assert "MD009" in collapsed
