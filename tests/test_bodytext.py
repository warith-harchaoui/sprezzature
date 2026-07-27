"""
test_bodytext — the shared body-text extractor + language detection helper.

Covers ``_lang.extract_body_text`` (HTML / Markdown / plain), the
``detect_language`` convenience wrapper, and — crucially — a **sync guard** that
every skill's ``scripts/_lang.py`` copy is byte-identical, since the helper is
duplicated for self-containment and must not drift.

``_lang`` is importable directly (conftest puts each skill's ``scripts/`` on
``sys.path``).

Author
------
Project maintainers.
"""

from __future__ import annotations

from pathlib import Path

import _lang  # noqa: E402  (path set by conftest)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── extract_body_text ───────────────────────────────────────────────────────

def test_html_strips_tags_scripts_styles() -> None:
    html = (
        "<html><head><style>.x{color:red}</style></head><body>"
        "<h1>Hello</h1><p>brave <b>world</b></p>"
        "<script>var a = 1 < 2;</script></body></html>"
    )
    out = _lang.extract_body_text(html, "html")
    assert out == "Hello brave world"
    assert "color" not in out and "var a" not in out


def test_markdown_keeps_prose_drops_syntax() -> None:
    md = (
        "# Heading\n\n"
        "Some **bold** and _italic_ and `code` text with a "
        "[link label](https://example.com) and an ![alt](img.png).\n\n"
        "```python\nprint('ignored code')\n```\n"
        "- item one\n- item two\n"
    )
    out = _lang.extract_body_text(md, "markdown")
    assert "Heading" in out and "bold" in out and "link label" in out
    assert "item one" in out and "item two" in out
    # Syntax and fenced code content are gone.
    assert "**" not in out and "```" not in out and "ignored code" not in out
    assert "img.png" not in out and "https://example.com" not in out


def test_plain_is_passed_through_collapsed() -> None:
    assert _lang.extract_body_text("  hello   world \n\n again ", "text") == "hello world again"


def test_auto_sniff_html_vs_markdown_vs_text() -> None:
    assert _lang.extract_body_text("<html><body>Bonjour tout le monde</body></html>") == "Bonjour tout le monde"
    assert _lang.extract_body_text("# Title\n\nbody words here") == "Title body words here"
    assert _lang.extract_body_text("just some plain words") == "just some plain words"


def test_malformed_html_does_not_crash() -> None:
    # Unclosed tags / stray angle brackets must degrade, not raise.
    out = _lang.extract_body_text("<div><p>text without close <b>bold", "html")
    assert "text without close" in out and "bold" in out


# ── detect_language (extract + detect) ──────────────────────────────────────

def test_detect_language_from_html_content() -> None:
    fr = ("<html><body><p>Le rapide renard brun saute par-dessus le chien "
          "paresseux et continue sa route le long du fleuve.</p></body></html>")
    en = ("<html><body><p>The quick brown fox jumps over the lazy dog and "
          "keeps running along the river bank all day.</p></body></html>")
    assert _lang.detect_language(fr) == "fr"
    assert _lang.detect_language(en) == "en"


def test_detect_language_falls_back_when_no_signal() -> None:
    # Too little text to detect → the explicit fallback (no configured default).
    assert _lang.detect_language("<html><body></body></html>", fallback="xx") == "xx"


# ── sync guard: every _lang.py copy is byte-identical ───────────────────────

def test_lang_helper_copies_are_identical() -> None:
    """The shared helper is duplicated for self-containment; the copies must
    never drift. This test fails the moment one is edited without the others."""
    copies = sorted(REPO_ROOT.glob("front-*/scripts/_lang.py"))
    assert len(copies) >= 4, f"expected several _lang.py copies, found {len(copies)}"
    canonical = copies[0].read_text(encoding="utf-8")
    drifted = [str(p.relative_to(REPO_ROOT)) for p in copies[1:]
               if p.read_text(encoding="utf-8") != canonical]
    assert not drifted, (
        f"_lang.py copies drifted from {copies[0].relative_to(REPO_ROOT)}: {drifted}. "
        "Edit one, then propagate the exact bytes to all copies."
    )
