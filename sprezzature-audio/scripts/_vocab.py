"""
_vocab
======

Shared vocabulary-extraction helpers for the local AI helpers.

Both :mod:`captions_from_whisper` (whisper.cpp / pywhispercpp) and
:mod:`alt_from_ollama` (Qwen3-VL vision via Ollama) accept an optional
vocabulary biasing input. The user supplies it in one of four shapes:

1. ``--prompt "<text>"``           — verbatim prompt text.
2. ``--vocab path/to/glossary.txt`` — one term per line.
3. ``--vocab-from path``            — single file *or* directory.
4. ``--auto-project``               — walk upward from the source file
                                      to find a project root, then collect
                                      vocabulary from the whole tree.

This module owns the input-shape resolution and the term-extraction logic;
prompt-template composition is left to the consuming script because the
right wording differs (whisper's ``initial_prompt`` vs Qwen3-VL's instruction).

The extractor recognizes three pattern classes likely to carry meaningful
names: backtick code spans, CamelCase / snake_case identifiers, and
capitalized multi-word phrases.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


# ── Configuration constants ────────────────────────────────────────────────

#: Filenames probed first when auto-detecting a vocab source next to the
#: media file. The first sibling found wins.
AUTO_VOCAB_SOURCES: tuple[str, ...] = (
    "README.md", "index.html", "transcript.md", "PRODUCT.md", "ABOUT.md",
)

#: Marker files that indicate the root of a project tree, in priority order.
#: Used by :func:`find_project_root`.
PROJECT_ROOT_MARKERS: tuple[str, ...] = (
    ".git",
    "SKILL.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "README.md",
)

#: Top-level filenames scanned when collecting project vocabulary.
PROJECT_VOCAB_NAMES: frozenset[str] = frozenset({
    "README.md", "SKILL.md", "LISEZMOI.md", "MANIFEST.md",
    "manifest.json", "package.json", "pyproject.toml",
})

#: Folders walked recursively for ``.md`` files inside a project.
PROJECT_VOCAB_DIRS: frozenset[str] = frozenset({
    "docs", "doc", "site", "content", "src", "references",
})

#: Hard cap on total source bytes read from a project tree.
PROJECT_READ_BUDGET: int = 512 * 1024

#: How many characters on each side of an image reference are kept by
#: :func:`surrounding_text`. ~800 chars total per match is comfortably more
#: context than the alt-text generator can use and stays well under any
#: model's prompt budget.
SURROUNDING_WINDOW: int = 400


# ── Term extraction ─────────────────────────────────────────────────────────

def extract_vocabulary(text: str) -> list[str]:
    """
    Extract a list of likely proper-noun and technical terms from prose.

    The extraction is intentionally cheap — no NLP, just three pattern
    classes that catch the bulk of high-value names:

    1. Backtick-delimited identifiers (Markdown code spans).
    2. CamelCase and snake_case words (likely API names).
    3. Capitalized multi-word phrases that aren't sentence starters.

    Parameters
    ----------
    text : str
        Raw text, Markdown, or HTML to extract from.

    Returns
    -------
    list of str
        Unique terms in source order. Empty list when no terms match.
    """
    # Strip script / style blocks then drop the rest of the HTML tags so
    # raw HTML files extract cleanly without a parser.
    cleaned = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)

    seen: set[str] = set()
    terms: list[str] = []

    def keep(term: str) -> None:
        # Strip surrounding punctuation and accept terms ≥ 2 chars only.
        """Add a cleaned term to the ordered set, skipping dupes and 1-char noise."""
        term = term.strip(" .,;:!?'\"()[]{}")
        if len(term) < 2 or term.lower() in seen:
            return
        seen.add(term.lower())
        terms.append(term)

    # 1. Backtick code spans.
    for m in re.finditer(r"`([^`\n]+)`", cleaned):
        keep(m.group(1))

    # 2. CamelCase / snake_case identifiers (≥ 2 chars; ensure the token
    # carries an upper-case letter so plain lowercase words don't qualify).
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)\b", cleaned):
        keep(m.group(1))
    for m in re.finditer(r"\b([a-z]+_[a-z][a-z0-9_]*)\b", cleaned):
        keep(m.group(1))

    # 3. Capitalized multi-word proper nouns, ignoring sentence starters.
    # The "not at start of sentence" filter is approximated by requiring the
    # phrase to be preceded by a non-sentence-ending character.
    for m in re.finditer(
        r"(?<=[^\.\?\!\n]\s)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})",
        cleaned,
    ):
        keep(m.group(1))

    return terms


def surrounding_text(doc: Path, image: Path, window: int = SURROUNDING_WINDOW) -> str:
    """
    Extract the text around every reference to ``image`` inside ``doc``.

    Both Markdown image references (``![alt](path)``) and HTML
    ``<img src="path">`` syntaxes are recognized by basename match — the
    caller's ``image`` argument can be a full path or just the filename
    as it appears in ``doc``.

    For each match, ``window`` characters on each side are kept, and the
    nearest preceding Markdown heading (``# ...`` / ``## ...`` …) is
    prepended so the model knows the section title. Multiple matches are
    joined with a blank line.

    Parameters
    ----------
    doc : Path
        Document the image lives in (Markdown, HTML, plain text).
    image : Path
        Image path (or filename) that appears in ``doc``.
    window : int, optional
        Characters of context on each side of the reference. Default
        :data:`SURROUNDING_WINDOW`.

    Returns
    -------
    str
        Concatenated context windows, or ``""`` when no reference is found.
    """
    text: str = doc.read_text(encoding="utf-8", errors="ignore")
    basename: str = image.name

    matches: list[tuple[int, int]] = []
    for m in re.finditer(re.escape(basename), text):
        matches.append(m.span())
    if not matches:
        return ""

    # Pre-index Markdown heading positions so we can prepend the nearest
    # one before each window without re-scanning the whole document.
    heading_offsets: list[tuple[int, str]] = []
    for m in re.finditer(r"^(#{1,6}\s+.+)$", text, re.M):
        heading_offsets.append((m.start(), m.group(1).strip()))

    parts: list[str] = []
    for start, end in matches:
        # Closest preceding heading, if any.
        heading: str = ""
        for offset, text_of in reversed(heading_offsets):
            if offset < start:
                heading = text_of
                break

        # Context window, clamped to document bounds.
        ctx_start: int = max(0, start - window)
        ctx_end: int = min(len(text), end + window)
        chunk: str = text[ctx_start:ctx_end].strip()

        if heading:
            parts.append(f"{heading}\n{chunk}")
        else:
            parts.append(chunk)

    return "\n\n".join(parts)


def read_vocab_file(path: Path) -> list[str]:
    """
    Read a glossary file with one term per line.

    Lines starting with ``#`` are treated as comments. Empty lines are
    skipped. Terms are returned in source order, deduplicated case-insensitively.

    Parameters
    ----------
    path : Path
        File to read.

    Returns
    -------
    list of str
        Unique terms.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower() in seen:
            continue
        seen.add(line.lower())
        out.append(line)
    return out


# ── Project walking ────────────────────────────────────────────────────────

def find_project_root(start: Path) -> Optional[Path]:
    """
    Walk upward from ``start`` looking for the nearest project root.

    A directory qualifies when it contains any file or folder listed in
    :data:`PROJECT_ROOT_MARKERS`. The search stops at the filesystem root.

    Parameters
    ----------
    start : Path
        Starting directory (typically the source file's parent).

    Returns
    -------
    Path or None
        The project root, or ``None`` when no marker is found between
        ``start`` and the filesystem root.
    """
    current: Path = start.resolve()
    while True:
        for marker in PROJECT_ROOT_MARKERS:
            if (current / marker).exists():
                return current
        if current.parent == current:
            return None
        current = current.parent


def collect_project_text(root: Path, budget: int = PROJECT_READ_BUDGET) -> str:
    """
    Concatenate vocabulary-relevant text from a project tree.

    Reads, in priority order:

    1. The top-level marker files (``README``, ``SKILL.md``, manifests).
    2. ``.md`` files under the known doc folders (:data:`PROJECT_VOCAB_DIRS`),
       walked recursively.

    Reading stops as soon as ``budget`` bytes have been accumulated.

    Parameters
    ----------
    root : Path
        Project root.
    budget : int, optional
        Maximum bytes to read. Default :data:`PROJECT_READ_BUDGET`.

    Returns
    -------
    str
        Concatenated text content.
    """
    parts: list[str] = []
    used: int = 0

    def append(text: str) -> None:
        """Append text up to the remaining character budget, then stop."""
        nonlocal used
        if used >= budget:
            return
        remaining: int = budget - used
        chunk: str = text[:remaining]
        parts.append(chunk)
        used += len(chunk)

    # Top-level marker files.
    for name in PROJECT_VOCAB_NAMES:
        path = root / name
        if path.is_file():
            append(path.read_text(encoding="utf-8", errors="ignore"))
            if used >= budget:
                return "\n".join(parts)

    # .md files inside known doc folders.
    for folder in PROJECT_VOCAB_DIRS:
        sub = root / folder
        if not sub.is_dir():
            continue
        for md in sub.rglob("*.md"):
            append(md.read_text(encoding="utf-8", errors="ignore"))
            if used >= budget:
                return "\n".join(parts)

    return "\n".join(parts)


# ── Source-shape resolution ────────────────────────────────────────────────

def resolve_vocab_terms(
    source: Path,
    *,
    in_doc: Optional[Path] = None,
    vocab_file: Optional[Path] = None,
    vocab_from: Optional[Path] = None,
    auto_project: bool = False,
) -> list[str]:
    """
    Resolve a list of vocabulary terms from the available inputs.

    Resolution order (first non-empty result wins):

    1. ``in_doc`` — extract surrounding text from the document the source
       lives in. Highest signal for image alt text (page-level context).
    2. ``vocab_file`` — explicit glossary file.
    3. ``vocab_from`` — single file *or* directory (walked as a project).
    4. ``auto_project`` — walk upward from ``source`` to find a project
       root, then collect text from the whole tree.
    5. Auto-detect a sibling source matching :data:`AUTO_VOCAB_SOURCES`.
    6. Empty list — no vocabulary available.

    Parameters
    ----------
    source : Path
        The media file (audio / video / image) whose context is being built.
    in_doc : Path or None, optional
        Document the source is embedded in. When supplied, the text around
        every reference to ``source.name`` is extracted and mined for terms.
    vocab_file : Path or None, optional
        Glossary path supplied by ``--vocab``.
    vocab_from : Path or None, optional
        File or directory supplied by ``--vocab-from``.
    auto_project : bool, optional
        When ``True``, walk upward from ``source`` to discover a project root.

    Returns
    -------
    list of str
        Extracted terms, in source order, deduped case-insensitively.
    """
    if in_doc is not None:
        ctx: str = surrounding_text(in_doc, source)
        if ctx:
            return extract_vocabulary(ctx)

    if vocab_file is not None:
        return read_vocab_file(vocab_file)

    if vocab_from is not None:
        if vocab_from.is_dir():
            text = collect_project_text(vocab_from)
        else:
            text = vocab_from.read_text(encoding="utf-8")
        return extract_vocabulary(text)

    # Subtitle siblings — for audio / video sources, a prior transcript or
    # caption file (``.vtt`` / ``.srt`` / ``.txt``) sharing the source's
    # stem is the highest-signal vocabulary available.
    for ext in (".vtt", ".srt", ".txt"):
        sibling = source.with_suffix(ext)
        if sibling.is_file() and sibling != source:
            return extract_vocabulary(sibling.read_text(encoding="utf-8"))

    if auto_project:
        root: Optional[Path] = find_project_root(source.parent)
        if root is not None:
            return extract_vocabulary(collect_project_text(root))

    for name in AUTO_VOCAB_SOURCES:
        sibling = source.parent / name
        if sibling.is_file():
            return extract_vocabulary(sibling.read_text(encoding="utf-8"))

    return []
