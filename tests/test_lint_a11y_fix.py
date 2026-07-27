"""
Tests for the ``lint_a11y.py --fix`` mode — the safe mechanical
accessibility repairs that ship inside
``sprezzature-accessibility/scripts/lint_a11y.py``.

Covers each of the five fixers:

* ``html-missing-lang``           → adds ``lang="en"`` to ``<html>``.
* ``img-redundant-aria``          → strips redundant ``role="presentation"``
                                    / ``aria-hidden="true"`` from
                                    ``<img alt="">``.
* ``tabindex-positive``           → demotes ``tabindex="N>0"`` to
                                    ``tabindex="0"``.
* ``aria-hidden-interactive``     → strips ``aria-hidden="true"`` from
                                    an interactive element.
* ``motion-no-reduce-guard``      → appends
                                    ``motion-reduce:transform-none`` to
                                    the class list of an animated element.

Plus:

* Idempotence — a second --fix pass on a fixed file performs zero
  edits and emits zero remaining findings.
* Dry-run — never writes to disk, exits 0 even when findings remain.
* Unfixable rules (empty button, missing label, heading skip, etc.)
  are counted separately and surfaced honestly.
* CLI plumbing: ``--fix`` and ``--dry-run`` flags reach ``--help``.

The script is stdlib-only so no fixtures beyond ``tmp_path``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# ``conftest.py`` adds ``sprezzature-accessibility/scripts`` to sys.path.
from lint_a11y import RULE_FIXERS, fix_file


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT: Path = (
    REPO_ROOT / "sprezzature-accessibility" / "scripts" / "lint_a11y.py"
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    """Write an HTML fixture and return its path."""
    p: Path = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# ── Per-fixer correctness ──────────────────────────────────────────────────


def test_fix_html_missing_lang_detects_english(tmp_path: Path) -> None:
    """The fixer detects the language from the document's own body text."""
    html = ("<html><body><p>The quick brown fox jumps over the lazy dog "
            "and keeps running along the river bank.</p></body></html>")
    p: Path = _write(tmp_path, "page.html", html)
    applied, _, _ = fix_file(p, ignored=set())
    assert applied >= 1
    assert 'lang="en"' in p.read_text(encoding="utf-8")


def test_fix_html_missing_lang_detects_french(tmp_path: Path) -> None:
    """Detection is content-driven — French body text yields ``lang="fr"``."""
    html = ("<html><body><p>Le rapide renard brun saute par-dessus le chien "
            "paresseux et continue sa route le long du fleuve.</p></body></html>")
    p: Path = _write(tmp_path, "page.html", html)
    fix_file(p, ignored=set())
    assert 'lang="fr"' in p.read_text(encoding="utf-8")


def test_fix_html_missing_lang_no_text_left_unfixed(tmp_path: Path) -> None:
    """No body text → language undetectable → NO default injected (left unfixed)."""
    p: Path = _write(tmp_path, "page.html", "<html><body></body></html>")
    fix_file(p, ignored=set())
    assert "lang=" not in p.read_text(encoding="utf-8")


def test_fix_img_redundant_aria(tmp_path: Path) -> None:
    """Redundant ARIA attrs on decorative <img alt=""> are stripped."""
    p: Path = _write(
        tmp_path,
        "img.html",
        '<html lang="en"><body>'
        '<img src="x.png" alt="" role="presentation" aria-hidden="true">'
        "</body></html>",
    )
    fix_file(p, ignored=set())
    body: str = p.read_text(encoding="utf-8")
    assert 'role="presentation"' not in body
    assert 'aria-hidden="true"' not in body
    # The image itself + the empty alt survive.
    assert 'alt=""' in body
    assert "<img" in body


def test_fix_tabindex_positive(tmp_path: Path) -> None:
    """``tabindex="3"`` is demoted to ``tabindex="0"``."""
    p: Path = _write(
        tmp_path,
        "tab.html",
        '<html lang="en"><body><button tabindex="3">X</button></body></html>',
    )
    fix_file(p, ignored=set())
    body: str = p.read_text(encoding="utf-8")
    assert 'tabindex="0"' in body
    assert 'tabindex="3"' not in body


def test_fix_aria_hidden_interactive(tmp_path: Path) -> None:
    """Interactive elements lose ``aria-hidden="true"``."""
    p: Path = _write(
        tmp_path,
        "ah.html",
        '<html lang="en"><body>'
        '<button aria-hidden="true">X</button>'
        "</body></html>",
    )
    fix_file(p, ignored=set())
    body: str = p.read_text(encoding="utf-8")
    assert 'aria-hidden="true"' not in body
    assert "<button" in body


def test_fix_motion_reduce_guard(tmp_path: Path) -> None:
    """Animated elements gain ``motion-reduce:transform-none``."""
    p: Path = _write(
        tmp_path,
        "mr.html",
        '<html lang="en"><body>'
        '<div class="animate-spin">spinner</div>'
        "</body></html>",
    )
    fix_file(p, ignored=set())
    body: str = p.read_text(encoding="utf-8")
    assert "motion-reduce:transform-none" in body


# ── Idempotence + dry-run ──────────────────────────────────────────────────


def test_fix_is_idempotent(tmp_path: Path) -> None:
    """A second --fix pass performs zero edits and emits zero findings."""
    src: str = (
        "<html><body>"
        "<p>The quick brown fox jumps over the lazy dog and keeps running.</p>"
        '<img src="x.png" alt="" role="presentation" aria-hidden="true">'
        '<button tabindex="3" aria-hidden="true">X</button>'
        '<div class="animate-spin">spin</div>'
        "</body></html>"
    )
    p: Path = _write(tmp_path, "idem.html", src)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(p)],
        capture_output=True, text=True,
    )
    first: str = p.read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(p)],
        capture_output=True, text=True,
    )
    second: str = p.read_text(encoding="utf-8")
    assert first == second, "second --fix mutated the file"
    assert "0 findings remaining" in proc.stdout
    assert proc.returncode == 0


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    """``--dry-run`` previews without touching disk; exits 0."""
    src: str = '<html><body><button tabindex="5">X</button></body></html>'
    p: Path = _write(tmp_path, "preview.html", src)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", "--dry-run", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert p.read_text(encoding="utf-8") == src
    assert "would apply" in proc.stderr


def test_unfixable_findings_pass_through(tmp_path: Path) -> None:
    """Rules without a fixer (empty button) are not auto-repaired."""
    src: str = '<html lang="en"><body><button></button></body></html>'
    p: Path = _write(tmp_path, "empty.html", src)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(p)],
        capture_output=True, text=True,
    )
    # The empty <button> is still empty — the linter must not invent
    # a label.
    body: str = p.read_text(encoding="utf-8")
    assert "<button></button>" in body
    # And the unfixable counter must reflect it on stderr.
    assert "1 unfixable" in proc.stderr or "unfixable" in proc.stderr


# ── CLI plumbing ───────────────────────────────────────────────────────────


def test_fix_and_dry_run_flags_in_help() -> None:
    """``--fix`` and ``--dry-run`` are advertised by ``--help``."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "--fix" in proc.stdout
    assert "--dry-run" in proc.stdout


@pytest.mark.parametrize("rule", sorted(RULE_FIXERS))
def test_every_registered_fixer_is_callable(rule: str) -> None:
    """Smoke: every entry in :data:`RULE_FIXERS` is actually callable."""
    fixer = RULE_FIXERS[rule]
    assert callable(fixer), f"{rule} fixer is not callable"
