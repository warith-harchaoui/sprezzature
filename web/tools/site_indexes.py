#!/usr/bin/env python3
"""
site_indexes — regenerate sitemap.xml, llms.txt and llms-full.txt for web/.

sprezzature-publish/scripts/site_indexes.py is Markdown/SSG-oriented (its
page discovery walks ``public/``, ``dist/``, ``build/`` … but not ``fr/``,
and its full-text corpus is built from Markdown sources only). This site is
hand-authored static HTML with an ``fr/`` translation tree, so this script
scans it directly instead: every ``web/*.html`` (except ``head.html``, a
``<head>``-only include fragment, not a page) and every ``web/fr/*.html``.

robots.txt is not regenerated here — it is three static lines that never
change with the page set.

Usage
-----
    python tools/site_indexes.py

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
BASE_URL = "https://sprezzature.ai"

# Section, in llms.txt display order -> the EN filenames it groups.
_SECTIONS: list[tuple[str, list[str]]] = [
    ("Home", ["index.html"]),
    ("Skills", [
        "ui.html", "cli.html", "publish.html", "accessibility.html",
        "colors.html", "vision.html", "audio.html", "ux-laws.html", "figures.html",
    ]),
    ("Case studies", [
        "case-studies.html", "hans-rosling.html", "maps.html",
        "financial-markets.html", "financial-markets-adverse.html",
    ]),
    ("Reference", ["packages.html", "ralph-eyeball-loop.html"]),
]


def _discover() -> tuple[list[Path], list[Path]]:
    """Return ``(en_pages, fr_pages)``, each sorted, ``head.html`` excluded."""
    en = sorted(p for p in WEB.glob("*.html") if p.name != "head.html")
    fr = sorted((WEB / "fr").glob("*.html"))
    return en, fr


def _url_for(page: Path) -> str:
    """Absolute site URL for a page, collapsing ``index.html`` to ``/``."""
    rel = page.relative_to(WEB).as_posix()
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    return f"{BASE_URL}/{rel}"


def _git_lastmod(page: Path) -> str:
    """Last commit date (YYYY-MM-DD) touching `page`; today if untracked/unavailable."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(page)],
            cwd=WEB, capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    return date.today().isoformat()


_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_DESC_RE = re.compile(r'<meta\s+name="description"\s+content="([^"]*)"', re.S)


def _read_title(page: Path) -> str:
    m = _TITLE_RE.search(page.read_text(encoding="utf-8"))
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else page.stem


def _read_desc(page: Path) -> str:
    m = _DESC_RE.search(page.read_text(encoding="utf-8"))
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def render_sitemap(en: list[Path], fr: list[Path]) -> str:
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page in en + fr:
        lines.append(f"  <url><loc>{_url_for(page)}</loc><lastmod>{_git_lastmod(page)}</lastmod></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_llms_txt(en: list[Path]) -> str:
    by_name = {p.name: p for p in en}
    seen: set[str] = set()
    lines = [
        "# Sprezzature",
        "",
        "> Nine Claude / OpenCode skills for one frontend stack: UI, CLI-to-GUI, "
        "publishing, accessibility, colors, alt text, captions, Laws of UX, and "
        "data-science figures. Each skill both makes artifacts and audits them.",
        "",
    ]
    for heading, names in _SECTIONS:
        entries = [n for n in names if n in by_name]
        if not entries:
            continue
        lines.append(f"## {heading}")
        lines.append("")
        for name in entries:
            page = by_name[name]
            seen.add(name)
            lines.append(f"- [{_read_title(page)}]({_url_for(page)}): {_read_desc(page)}")
        lines.append("")
    # Anything not bucketed above still gets listed, so a new page is never silently dropped.
    leftovers = [p for p in en if p.name not in seen]
    if leftovers:
        lines.append("## Other")
        lines.append("")
        for page in leftovers:
            lines.append(f"- [{_read_title(page)}]({_url_for(page)}): {_read_desc(page)}")
        lines.append("")
    lines.append("## French (Français)")
    lines.append("")
    lines.append("Every page above has a French translation at the same path under `/fr/` "
                  "(e.g. `/fr/figures.html`), declared via `hreflang` on each page.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


_TAG_STRIP = re.compile(r"<(script|style|nav|header|footer)\b.*?</\1>", re.S | re.I)
_MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S | re.I)
_H_RE = re.compile(r"<h([1-3])\b[^>]*>(.*?)</h\1>", re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> str:
    """Strip an HTML page's `<main>` content down to readable plain text.

    Headings (`h1`-`h3`) are kept as Markdown-style `#`/`##`/`###` lines so an
    LLM ingesting the corpus still sees document structure; everything else is
    de-tagged and whitespace-collapsed. Not a general HTML-to-Markdown
    converter -- good enough for the hand-authored, mostly-prose+card markup
    this site uses.
    """
    html = _TAG_STRIP.sub("", html)
    m = _MAIN_RE.search(html)
    body = m.group(1) if m else html

    def _heading(m: re.Match) -> str:
        level = int(m.group(1))
        text = _TAG_RE.sub("", m.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        return f"\n{'#' * level} {text}\n"

    body = _H_RE.sub(_heading, body)
    body = re.sub(r"</(p|li|figcaption|section|div|tr)>", "\n", body, flags=re.I)
    body = _TAG_RE.sub(" ", body)
    import html as _htmlmod
    body = _htmlmod.unescape(body)
    body = _WS_RE.sub(" ", body)
    body = "\n".join(line.strip() for line in body.splitlines())
    body = _BLANK_RE.sub("\n\n", body)
    return body.strip()


def render_llms_full(en: list[Path], max_bytes: int = 200 * 1024) -> tuple[str, list[str]]:
    """Full-text corpus of the EN pages (canonical language; FR is a translation
    of the same content, so it is not duplicated here -- see llms.txt's French
    section for the `/fr/` link pattern instead). Returns ``(text, dropped)``.
    """
    parts = [
        "# Sprezzature — full-text corpus\n"
        "\n"
        "> Concatenated plain text of every English page, for single-request "
        "ingestion by an LLM/agent. French pages are translations of the same "
        "content (see llms.txt) and are not duplicated here.\n"
    ]
    dropped: list[str] = []
    budget = max_bytes if max_bytes else float("inf")
    used = sum(len(p.encode("utf-8")) for p in parts)
    for page in en:
        title = _read_title(page)
        url = _url_for(page)
        text = _html_to_text(page.read_text(encoding="utf-8"))
        block = f"\n---\n\n# {title}\n\nSource: {url}\n\n{text}\n"
        block_len = len(block.encode("utf-8"))
        if used + block_len > budget:
            dropped.append(page.name)
            continue
        parts.append(block)
        used += block_len
    return "".join(parts).strip() + "\n", dropped


def main() -> int:
    en, fr = _discover()
    (WEB / "sitemap.xml").write_text(render_sitemap(en, fr), encoding="utf-8")
    print(f"-> wrote sitemap.xml ({len(en) + len(fr)} URLs: {len(en)} en + {len(fr)} fr)")

    (WEB / "llms.txt").write_text(render_llms_txt(en), encoding="utf-8")
    print(f"-> wrote llms.txt ({len(en)} en pages indexed)")

    full_text, dropped = render_llms_full(en)
    (WEB / "llms-full.txt").write_text(full_text, encoding="utf-8")
    kb = len(full_text.encode("utf-8")) / 1024
    print(f"-> wrote llms-full.txt ({kb:.0f} KB)" + (f" -- dropped: {', '.join(dropped)}" if dropped else ""))

    humans = WEB / "humans.txt"
    if humans.is_file():
        text = humans.read_text(encoding="utf-8")
        today = date.today().isoformat()
        text = re.sub(r"Last update: \d{4}-\d{2}-\d{2}", f"Last update: {today}", text)
        humans.write_text(text, encoding="utf-8")
        print(f"-> touched humans.txt (Last update: {today})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
