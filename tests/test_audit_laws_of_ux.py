"""
Tests for ``audit_laws_of_ux`` — the static Laws-of-UX auditor that ships
inside ``sprezzature-ux-laws/scripts/audit_laws_of_ux.py``.

Covers the eight implemented checks:

* Hick's Law — `<nav>` with > 7 top-level *logical* choices (after
  collapsing radiogroups / tablists / details / dialog / menu).
* Choice Overload — pricing-grid heuristic.
* Miller's Law — long alphanumeric run that contains at least one digit.
* Jakob's Law — clickable ``<div>`` / ``<span>``.
* Fitts's Law — interactive element without an explicit ``min-h-`` /
  ``h-`` / ``size-`` ≥ 11 token.
* Aesthetic-Usability — interactive element missing
  ``focus-visible:ring-*``.
* Selective Attention — status colour without a second channel.
* Tesler's Law — bare ``HH:MM`` time with no nearby timezone token.

Also smoke-tests:

* CLI ``--version`` and ``--help`` (already covered by
  ``test_cli_help.py`` for the whole repo but kept here as a friendly
  self-contained run target).
* ``--only`` / ``--ignore`` filter semantics.
* ``--json`` output shape.
* Non-strict exit code policy (errors fail the run; warnings do not
  unless ``--strict`` is set).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# ``conftest.py`` injects ``sprezzature-ux-laws/scripts`` onto sys.path so the
# module imports cleanly without packaging gymnastics.
from audit_laws_of_ux import (
    LAW_REGISTRY,
    audit_file,
)


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT: Path = REPO_ROOT / "sprezzature-ux-laws" / "scripts" / "audit_laws_of_ux.py"


# ── Helpers ────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, name: str, body: str) -> Path:
    """Write an HTML fixture and return its path."""
    p: Path = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def _laws(findings) -> list[str]:
    """Extract law slugs in deterministic order."""
    return sorted(f.law for f in findings)


# ── Per-check correctness ──────────────────────────────────────────────────


def test_hick_fires_on_eight_link_nav(tmp_path: Path) -> None:
    """A nav with eight peers exceeds Hick's seven-item ceiling."""
    p: Path = _write(
        tmp_path,
        "nav.html",
        "<nav>"
        + "".join(f'<a href="/{i}">{i}</a>' for i in range(8))
        + "</nav>",
    )
    findings = audit_file(p, {"hick"})
    assert len(findings) == 1
    assert findings[0].severity == "error"


def test_hick_collapses_radiogroup_to_single_choice(tmp_path: Path) -> None:
    """Three radio buttons inside a radiogroup count as one logical choice."""
    p: Path = _write(
        tmp_path,
        "nav.html",
        '<nav>'
        + '<a href="/a">A</a><a href="/b">B</a><a href="/c">C</a>'
        + '<div role="radiogroup">'
        + '  <button type="button" role="radio">Light</button>'
        + '  <button type="button" role="radio">Dark</button>'
        + '  <button type="button" role="radio">Auto</button>'
        + "</div>"
        + '<a href="/d">D</a><a href="/e">E</a><a href="/f">F</a>'
        + "</nav>",
    )
    # 6 anchors + 1 radiogroup = 7 logical choices; should NOT fire.
    assert audit_file(p, {"hick"}) == []


def test_hick_treats_two_navs_independently(tmp_path: Path) -> None:
    """A sibling nav must not inflate another sibling nav's choice count."""
    p: Path = _write(
        tmp_path,
        "two-navs.html",
        '<nav>'
        + "".join(f'<a href="/h{i}">{i}</a>' for i in range(4))
        + "</nav>"
        + '<nav>'
        + "".join(f'<a href="/t{i}">{i}</a>' for i in range(4))
        + "</nav>",
    )
    assert audit_file(p, {"hick"}) == []


def test_miller_fires_on_long_digit_run(tmp_path: Path) -> None:
    """A 27-char IBAN-like run triggers Miller chunking advice."""
    p: Path = _write(
        tmp_path, "iban.html", "<p>IBAN: FR7630006000011234567890189</p>"
    )
    findings = audit_file(p, {"miller"})
    assert len(findings) == 1
    assert "FR7630006000011234567890189" in findings[0].message


def test_miller_skips_pure_alphabetic_words(tmp_path: Path) -> None:
    """Ordinary English (``collaborators``, ``implementation``) must not fire."""
    p: Path = _write(
        tmp_path,
        "prose.html",
        "<p>This is the implementation; 4 collaborators are working on it.</p>",
    )
    assert audit_file(p, {"miller"}) == []


def test_jakob_fires_on_clickable_div(tmp_path: Path) -> None:
    """A clickable ``<div>`` without a real interactive child is a Jakob error."""
    p: Path = _write(
        tmp_path,
        "fake-button.html",
        '<div role="button" class="cursor-pointer" onclick="go()">Save</div>',
    )
    findings = audit_file(p, {"jakob"})
    assert len(findings) == 1
    assert findings[0].severity == "error"


def test_jakob_exempts_wrapper_around_real_button(tmp_path: Path) -> None:
    """A clickable wrapper around a real ``<button>`` should not fire."""
    p: Path = _write(
        tmp_path,
        "wrapper.html",
        '<div class="cursor-pointer"><button>Save</button></div>',
    )
    assert audit_file(p, {"jakob"}) == []


def test_tesler_accepts_timezone_token(tmp_path: Path) -> None:
    """``14:30 UTC`` is fine; bare ``14:30`` warns."""
    bad: Path = _write(tmp_path, "no-tz.html", "<p>Meeting at 14:30 tomorrow.</p>")
    good: Path = _write(
        tmp_path, "with-tz.html", "<p>Meeting at 14:30 UTC tomorrow.</p>"
    )
    assert len(audit_file(bad, {"tesler"})) == 1
    assert audit_file(good, {"tesler"}) == []


def test_selective_attention_accepts_status_word(tmp_path: Path) -> None:
    """``<span class="text-red-700">Failed</span>`` is fine; bare red span warns."""
    bad: Path = _write(tmp_path, "red.html", '<span class="text-red-500">Hi</span>')
    good: Path = _write(
        tmp_path, "labelled.html", '<span class="text-red-700">Failed</span>'
    )
    assert len(audit_file(bad, {"selective-attention"})) == 1
    assert audit_file(good, {"selective-attention"}) == []


def test_aesthetic_usability_fires_without_focus_ring(tmp_path: Path) -> None:
    """Interactive elements without ``focus-visible:ring-*`` must warn."""
    p: Path = _write(
        tmp_path,
        "btn.html",
        '<button class="bg-brand-blue px-4 py-2">Save</button>',
    )
    assert len(audit_file(p, {"aesthetic-usability"})) == 1


def test_fitts_fires_without_min_h(tmp_path: Path) -> None:
    """A standalone ``<button>`` with no ``min-h-`` warns under Fitts."""
    p: Path = _write(tmp_path, "btn.html", '<button class="px-4 py-2">Go</button>')
    assert len(audit_file(p, {"fitts"})) == 1


# ── CLI surface ────────────────────────────────────────────────────────────


def test_version_flag() -> None:
    """``--version`` exits 0 and uses the shared SKILL_VERSION token."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--version"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "sprezzature-ux-laws-audit" in proc.stdout


def test_help_flag() -> None:
    """``--help`` exits 0 and advertises every law in ``--only``."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    # argparse may wrap long lines mid-token; collapse whitespace and
    # rejoin hyphen-broken tokens (``choice-\n   overload`` becomes
    # ``choice- overload`` after whitespace collapse, which we re-glue
    # back into ``choice-overload``) before checking.
    collapsed: str = " ".join(proc.stdout.split()).replace("- ", "-")
    for law in LAW_REGISTRY:
        assert law in collapsed, f"--help missed law '{law}'"


def test_json_output_is_well_formed(tmp_path: Path) -> None:
    """``--json`` emits a JSON array with one object per finding."""
    p: Path = _write(
        tmp_path,
        "bad.html",
        '<div role="button" class="cursor-pointer">x</div>',
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "--only", "jakob", str(p)],
        capture_output=True, text=True,
    )
    payload = json.loads(proc.stdout)
    assert isinstance(payload, list)
    assert payload and payload[0]["law"] == "jakob"
    assert payload[0]["severity"] == "error"


def test_strict_promotes_warnings(tmp_path: Path) -> None:
    """Warnings exit 0 by default but exit 1 under ``--strict``."""
    p: Path = _write(
        tmp_path,
        "warn.html",
        '<button class="bg-brand-blue px-4 py-2">Save</button>',
    )
    relaxed = subprocess.run(
        [sys.executable, str(SCRIPT), "--only", "aesthetic-usability", str(p)],
        capture_output=True, text=True,
    )
    strict = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict", "--only",
         "aesthetic-usability", str(p)],
        capture_output=True, text=True,
    )
    assert relaxed.returncode == 0
    assert strict.returncode == 1


def test_unknown_law_in_only_returns_two() -> None:
    """``--only nonsense`` must exit 2 (CLI argument error)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--only", "nonsense", "/dev/null"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2


@pytest.mark.parametrize("law", sorted(LAW_REGISTRY))
def test_registry_check_returns_iterable(tmp_path: Path, law: str) -> None:
    """Every registered check returns an iterable when run on an empty doc."""
    p: Path = _write(tmp_path, "empty.html", "<html><body></body></html>")
    out = audit_file(p, {law})
    assert isinstance(out, list)


# ── --fix mode ─────────────────────────────────────────────────────────────


def test_fix_fitts_inserts_min_h_11(tmp_path: Path) -> None:
    """The Fitts fixer adds ``min-h-11`` to the offending element's class list."""
    p: Path = _write(
        tmp_path,
        "btn.html",
        '<button class="bg-brand-blue px-4 py-2 focus-visible:ring-2">Save</button>',
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", "--only", "fitts", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    body: str = p.read_text(encoding="utf-8")
    assert "min-h-11" in body


def test_fix_aesthetic_usability_inserts_focus_ring(tmp_path: Path) -> None:
    """The Aesthetic-Usability fixer adds the house focus-visible tokens."""
    p: Path = _write(
        tmp_path,
        "btn.html",
        '<button class="min-h-11 bg-brand-blue px-4 py-2">Save</button>',
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix",
         "--only", "aesthetic-usability", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    body: str = p.read_text(encoding="utf-8")
    assert "focus-visible:ring-2" in body
    assert "focus-visible:ring-brand-blue" in body


def test_fix_miller_chunks_long_digit_run(tmp_path: Path) -> None:
    """The Miller fixer splits a long alphanumeric run with non-breaking spaces."""
    p: Path = _write(
        tmp_path, "iban.html", "<p>IBAN: FR7630006000011234567890189</p>"
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", "--only", "miller", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    body: str = p.read_text(encoding="utf-8")
    # The raw run must not survive, but each 4-char piece should.
    assert "FR7630006000011234567890189" not in body
    assert "FR7" in body and "6300" in body and "0189" in body
    # The chunk separator is U+00A0 (NBSP) so layout does not break.
    assert " " in body


def test_fix_jakob_rewrites_div_to_button(tmp_path: Path) -> None:
    """The Jakob fixer renames a clickable ``<div>`` to a real ``<button>``."""
    p: Path = _write(
        tmp_path,
        "fake.html",
        '<div role="button" class="cursor-pointer">Save</div>',
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", "--only", "jakob", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    body: str = p.read_text(encoding="utf-8")
    assert "<button" in body
    assert "</button>" in body
    assert "<div" not in body
    assert "</div>" not in body
    # Redundant role attribute must be stripped.
    assert 'role="button"' not in body


def test_fix_jakob_rewrites_span_with_onclick(tmp_path: Path) -> None:
    """``<span onclick=…>`` is also rewritten to ``<button>``."""
    p: Path = _write(
        tmp_path,
        "span.html",
        '<span onclick="go()" class="cursor-pointer">Save</span>',
    )
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", "--only", "jakob", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    body: str = p.read_text(encoding="utf-8")
    assert "<button" in body
    assert "</button>" in body
    assert "<span" not in body


def test_fix_is_idempotent(tmp_path: Path) -> None:
    """A second --fix pass on a fixed file performs zero edits."""
    p: Path = _write(
        tmp_path,
        "all.html",
        "<button class='bg-brand-blue px-2'>X</button>\n"
        '<div role="button" class="cursor-pointer">Y</div>\n'
        "<p>FR7630006000011234567890189</p>\n",
    )
    # First pass — applies edits.
    subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(p)],
        capture_output=True, text=True,
    )
    first: str = p.read_text(encoding="utf-8")
    # Second pass — must be a no-op on the body and emit zero
    # remaining findings.
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", str(p)],
        capture_output=True, text=True,
    )
    second: str = p.read_text(encoding="utf-8")
    assert first == second, "second --fix pass mutated the file"
    assert "0 findings" in proc.stdout or "0 finding(s)" in proc.stdout


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    """``--dry-run`` reports what would change without touching disk."""
    src: str = (
        '<div role="button" class="cursor-pointer">Save</div>'
    )
    p: Path = _write(tmp_path, "preview.html", src)
    proc = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--fix", "--dry-run", "--only", "jakob", str(p),
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert p.read_text(encoding="utf-8") == src
    # stderr carries the "would apply N fix(es)" line.
    assert "would apply" in proc.stderr


def test_fix_reports_unfixable_laws_separately(tmp_path: Path) -> None:
    """Findings without a fixer increment the 'unfixable' counter."""
    # Tesler has no fixer (it needs a design decision, not text).
    p: Path = _write(tmp_path, "tz.html", "<p>Meeting at 14:30 tomorrow.</p>")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fix", "--only", "tesler", str(p)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "1 unfixable finding" in proc.stderr
