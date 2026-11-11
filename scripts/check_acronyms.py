#!/usr/bin/env python3
"""
check_acronyms — every acronym on the site and in the docs is defined where it first appears.

Warith's rule (2026-11-11): "never use any acronym without clearly defining
it in context before". A reader of sprezzature.ai is not necessarily in the
trade; "SVG", "OKLCH" or "ACLED" on first sight is a word they cannot read.

An acronym counts as defined at its first occurrence on a page when, within
the same sentence-ish window, it sits next to a parenthesis that spells it
out -- "SVG (Scalable Vector Graphics, ...)" or "Scalable Vector Graphics
(SVG)" -- or when its letters are the initials of the words just before it.
Code is not prose: anything in ``<code>``, ``<pre>``, backticks, a URL, a
file name or an HTML attribute is skipped, so ``--classes`` and
``make-figure`` are never asked to explain themselves.

    python scripts/check_acronyms.py                 # report every page
    python scripts/check_acronyms.py web/maps.html   # one page
    python scripts/check_acronyms.py --summary       # counts per file

Exits 1 when anything is undefined.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = REPO_ROOT.parent

#: Upper-case runs that are not acronyms a reader has to decode: Roman
#: numerals, units written in capitals, and words the house style sets in
#: capitals for emphasis or as names.
NOT_ACRONYMS = frozenset({
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
    "KB", "MB", "GB", "TB", "KM", "MI", "PM", "AM", "OK",
    "README", "LISEZMOI", "CHANGELOG", "LICENSE", "TODO", "FAQ",
    "NOT", "ONE", "NVIDIA",
    # Names, not abbreviations: surnames cited without a first name, a
    # graph language, a dataset.
    "MACHADO", "OLIVEIRA", "FERNANDES", "OKABE", "ITO", "BECKER", "DOT",
    "ADMIN", "EXPRESS",
})

#: Acronyms a general reader knows without being in the trade. Warith's call
#: (2026-11-11), delegated: "are old, very well-known acronyms to be
#: defined? your call". Spelling these out reads as condescending and adds
#: nothing; the test for a member is whether a cultivated reader outside
#: computing reads it without effort. Everything of the trade -- SVG, JSON,
#: CSV, YAML, API, HTTP, CSS, CLI, MCP, CI, WCAG -- is still defined.
COMMON = frozenset({
    "PDF", "PNG", "JPEG", "JPG", "GIF", "MP3", "MP4", "HTML", "URL", "AI",
    "IA", "UN", "ONU", "US", "USA", "UK", "EU", "UE", "GPS", "USB", "PC",
    "TV", "ID", "PHD", "CEO", "NGO", "ONG", "NASA", "NATO", "OTAN", "DNA",
    "ADN", "WIFI", "FAQ", "OK",
})

ACRONYM = re.compile(r"(?<![\w./@#-])([A-Z][A-Z0-9]*[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)?)(?![\w/-]*\.\w)(?![a-z])")


def prose(text: str, suffix: str) -> str:
    """The reader-facing text of a page or a document, code removed."""
    if suffix in (".html", ".htm"):
        text = re.sub(r"<(script|style|pre|code)\b.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        # alt and aria-label text is read aloud; keep it, drop other attributes
        kept = " ".join(re.findall(r'\b(?:alt|aria-label|content|title)="([^"]*)"', text))
        text = re.sub(r"<[^>]+>", " ", text) + " " + kept
        text = html.unescape(text)
    else:
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"^ {4,}.*$", " ", text, flags=re.M)
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    # Emphasis is not a word boundary a reader sees: "**ASR** (automatic
    # speech recognition)" is defined, and "CTAs" is the plural of CTA.
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\b([A-Z][A-Z0-9]+)s\b", r"\1", text)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\S+\.(?:py|md|html|json|yaml|yml|toml|svg|png|txt|sh|csv|tex)\b", " ", text)
    return text


def defined_here(acr: str, text: str, at: int) -> bool:
    """Whether the acronym at ``at`` is spelt out beside it."""
    after = text[at + len(acr): at + len(acr) + 160]
    before = text[max(0, at - 200): at]
    # "SVG (Scalable Vector Graphics ...)" -- a parenthesis right after,
    # holding at least two words.
    m = re.match(r"\s*\(([^)]{6,})\)", after)
    if m and len(m.group(1).split()) >= 2:
        return True
    # "Scalable Vector Graphics (SVG)" -- the acronym inside parentheses,
    # after its expansion.
    if before.rstrip().endswith("(") and re.match(r"[^)]*\)", after):
        return True
    # "... the Armed Conflict Location & Event Data project (ACLED ..."
    # or initials of the words just before.
    words = re.findall(r"[A-Za-zÀ-ÿ][\w'-]*", before)[-len(acr) - 4:]
    initials = "".join(w[0].upper() for w in words)
    letters = re.sub(r"[^A-Z]", "", acr)
    return len(letters) >= 2 and letters in initials


def check(path: Path) -> list[tuple[str, str]]:
    text = prose(path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower())
    seen: set[str] = set()
    missing: list[tuple[str, str]] = []
    for m in ACRONYM.finditer(text):
        acr = m.group(1)
        if acr in NOT_ACRONYMS or acr.upper() in COMMON or acr in seen or len(re.sub(r"[^A-Z]", "", acr)) < 2:
            continue
        # A surname in capitals after a first name -- the house style for
        # people, "Warith HARCHAOUI", "Hans ROSLING" -- is a name, not an
        # acronym; so is a run of capital words, a place set in capitals on
        # a plate ("BLACK SEA", "HELD BY THE RSF" keeps RSF, which is short).
        before = text[max(0, m.start() - 40): m.start()]
        if acr.isalpha() and len(acr) >= 4 and re.search(r"[A-ZÀ-Ý][a-zà-ÿ'-]+\s+$", before):
            continue
        if acr.isalpha() and len(acr) >= 5 and re.search(r"\b[A-Z]{3,}\s+$", before):
            continue
        seen.add(acr)
        if not defined_here(acr, text, m.start()):
            context = " ".join(text[max(0, m.start() - 50): m.start() + 60].split())
            missing.append((acr, context))
    return missing


def targets() -> list[Path]:
    web = REPO_ROOT / "web"
    pages = sorted(p for p in web.glob("*.html")) + sorted(p for p in (web / "fr").glob("*.html"))
    docs: list[Path] = []
    for repo in [REPO_ROOT, *sorted(SIBLINGS.glob("sprezzature-*"))]:
        if not (repo / ".git").exists() and repo != REPO_ROOT:
            continue
        for name in ("README.md", "LISEZMOI.md", "PHILOSOPHY.md", "PHILOSOPHIE.md"):
            if (repo / name).is_file():
                docs.append(repo / name)
    docs += sorted(REPO_ROOT.glob("sprezzature-*/SKILL.md"))
    return pages + docs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    files = args.paths or targets()
    total = 0
    for path in files:
        missing = check(path)
        total += len(missing)
        if not missing:
            continue
        rel = path.resolve()
        rel = rel.relative_to(SIBLINGS) if SIBLINGS in rel.parents else rel
        if args.summary:
            print(f"{len(missing):4d}  {rel}")
            continue
        print(f"\n{rel}")
        for acr, context in missing:
            print(f"  {acr:10s} …{context}…")
    print(f"\n{total} undefined acronym(s) across {len(files)} file(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
