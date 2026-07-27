"""
_lang
=====

Shared, stdlib-first helper for **content-based language handling**: extract the
visible body text from HTML / Markdown / plain content, then detect its language
with `langdetect`_. One canonical implementation, duplicated (intentionally)
across every front-* skill so each stays self-contained — **keep every copy
byte-identical** (a test, ``tests/test_bodytext.py``, enforces it).

There is **no configured default language** anywhere in the suite: callers pass
the content they actually process (surrounding text, page HTML, the input to
rewrite, a transcript, chart labels) and the language is detected from it.

``langdetect`` is opt-in — it lives under each Ollama tool's own
``requirements-*.txt``. When it is absent, detection degrades to the caller's
explicit fallback; ``extract_body_text`` itself is pure stdlib.

Determinism note: ``langdetect`` seeds its RNG from the input by default; we pin
``DetectorFactory.seed`` once at import so the same text always maps to the same
tag.

.. _langdetect: https://github.com/Mimino666/langdetect

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import re
from html.parser import HTMLParser


# ── Body-text extraction (stdlib only) ──────────────────────────────────────

class _VisibleTextParser(HTMLParser):
    """Collect an HTML document's visible text, skipping ``<script>``,
    ``<style>``, ``<svg>`` and ``<noscript>`` (code / graphics / boilerplate,
    not prose)."""

    def __init__(self) -> None:
        """Initialise the parser with an empty skip-depth counter and chunk buffer."""
        super().__init__(convert_charrefs=True)
        self._skip_depth: int = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        """Enter a skip region for code/graphics/boilerplate tags."""
        # ``attrs`` is part of the HTMLParser override contract (unused here).
        if tag in ("script", "style", "svg", "noscript"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        """Leave a skip region when its closing tag is reached."""
        if tag in ("script", "style", "svg", "noscript") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        """Collect non-empty visible text outside any skip region."""
        if not self._skip_depth and data.strip():
            self.chunks.append(data.strip())


def _strip_html(content: str) -> str:
    """Return the visible text of an HTML fragment/document."""
    parser = _VisibleTextParser()
    try:
        parser.feed(content)
    except Exception:  # noqa: BLE001 — malformed HTML must never crash a caller
        # Fall back to a crude tag strip so we still return *some* text.
        return re.sub(r"<[^>]+>", " ", content)
    return " ".join(parser.chunks)


#: Ordered Markdown cleanups: each (pattern, replacement) drops syntax while
#: keeping the human-readable text (link/image *labels*, list *items*, …).
_MD_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"```.*?```", re.S), " "),        # fenced code blocks
    (re.compile(r"~~~.*?~~~", re.S), " "),         # fenced code blocks (~)
    (re.compile(r"`[^`]*`"), " "),                  # inline code
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), " "),     # images (drop alt + url)
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),  # links -> label text
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.M), ""),   # ATX heading markers
    (re.compile(r"^\s{0,3}>\s?", re.M), ""),         # blockquote markers
    (re.compile(r"^\s{0,3}([*+-]|\d+\.)\s+", re.M), ""),  # list markers
    (re.compile(r"^\s*([-*_]\s*){3,}$", re.M), " "),  # horizontal rules
    (re.compile(r"[*_~]{1,3}"), ""),                 # emphasis / strikethrough
    (re.compile(r"<[^>]+>"), " "),                    # inline HTML tags
)


def _strip_markdown(content: str) -> str:
    """Return the prose text of a Markdown document (syntax removed)."""
    text: str = content
    for pattern, repl in _MD_SUBS:
        text = pattern.sub(repl, text)
    return text


def _sniff_format(content: str) -> str:
    """Guess the content format: ``"html"``, ``"markdown"``, or ``"text"``."""
    head: str = content.lstrip()[:2000].lower()
    if "<html" in head or "<body" in head or re.search(r"</[a-z][a-z0-9]*>", head):
        return "html"
    # Markdown signals: fenced code, ATX heading, or a link/image.
    if re.search(r"(^|\n)\s{0,3}#{1,6}\s", content) or "```" in content \
            or re.search(r"!\?\[[^\]]*\]\([^)]*\)", content) \
            or re.search(r"\[[^\]]+\]\([^)]+\)", content):
        return "markdown"
    return "text"


def extract_body_text(content: str, fmt: str = "auto") -> str:
    """Extract the visible **body text** from HTML / Markdown / plain content.

    A single, shared extraction step so every skill detects language (and
    reasons over content) from the *same* cleanly-extracted text rather than
    each caller assembling its own detection input. Stdlib-only.

    Parameters
    ----------
    content : str
        Raw source — an HTML document/fragment, a Markdown document, or plain
        text.
    fmt : str, optional
        ``"html"`` / ``"htm"``, ``"markdown"`` / ``"md"``, ``"text"`` /
        ``"plain"``, or ``"auto"`` (sniff from the content). Default ``"auto"``.

    Returns
    -------
    str
        Whitespace-collapsed visible text (single-spaced, trimmed).

    Examples
    --------
    >>> extract_body_text("<html><body><p>Hello <b>world</b></p>"
    ...                    "<script>var x=1</script></body></html>", "html")
    'Hello world'
    >>> extract_body_text("# Title\\n\\nSome **bold** [text](http://x).", "markdown")
    'Title Some bold text.'
    """
    resolved: str = _sniff_format(content) if fmt == "auto" else fmt.strip().lower()
    if resolved in ("html", "htm"):
        text = _strip_html(content)
    elif resolved in ("markdown", "md"):
        text = _strip_markdown(content)
    else:
        text = content
    return " ".join(text.split())


# ── Language detection ──────────────────────────────────────────────────────

def _have_langdetect() -> bool:
    """Return ``True`` when ``langdetect`` is importable."""
    return importlib.util.find_spec("langdetect") is not None


# Pin the seed once so output is reproducible. Guarded so this module stays
# importable on lightweight (stdlib-only) installs.
if _have_langdetect():
    from langdetect import DetectorFactory  # type: ignore[import-not-found]
    DetectorFactory.seed = 0


def detect_text_language(text: str, fallback: str = "en") -> str:
    """
    Detect the language of ``text`` as a two-letter BCP-47 base tag.

    Strategy:

    1. If ``langdetect`` is installed and the text has enough signal
       (≥ 20 non-whitespace characters), use it.
    2. Otherwise, return ``fallback``.

    Parameters
    ----------
    text : str
        Source text. Empty / whitespace-only input falls back immediately.
    fallback : str, optional
        Two-letter code returned when detection is not possible. Default
        ``"en"``.

    Returns
    -------
    str
        Lower-case two-letter language code.
    """
    if not _have_langdetect():
        return fallback
    stripped: str = "".join(text.split())
    if len(stripped) < 20:
        # Below the threshold langdetect's output is essentially random;
        # the fallback is more reliable.
        return fallback
    try:
        # ``langdetect.detect`` returns BCP-47 tags like "en", "fr",
        # "zh-cn"; we keep only the base subtag.
        from langdetect import detect  # type: ignore[import-not-found]
        from langdetect.lang_detect_exception import LangDetectException  # type: ignore[import-not-found]
        return detect(text).split("-")[0].lower()[:2]
    except LangDetectException:
        return fallback


def detect_language(content: str, fmt: str = "auto", fallback: str = "en") -> str:
    """Extract the body text of ``content`` and detect its language.

    Convenience wrapper: ``detect_text_language(extract_body_text(content,
    fmt), fallback)``. This is the one call every skill should use when it has
    raw HTML / Markdown / text and wants the language — no configured default,
    always detected from the content.

    Parameters
    ----------
    content : str
        Raw HTML / Markdown / plain content.
    fmt : str, optional
        Format hint for :func:`extract_body_text` (default ``"auto"``).
    fallback : str, optional
        Returned only when the language cannot be detected (default ``"en"``).

    Returns
    -------
    str
        Two-letter language code.
    """
    return detect_text_language(extract_body_text(content, fmt), fallback=fallback)


#: English names for the languages we can name to an LLM in a prompt. Lets ANY
#: detected language be requested by name ("Write ... in Korean.") instead of
#: silently collapsing to a hardcoded set — a language whose two-letter code is
#: here gets output in that language even when a skill has no curated,
#: written-in-the-target-language instruction for it.
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "fr": "French", "es": "Spanish", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "sv": "Swedish",
    "no": "Norwegian", "da": "Danish", "fi": "Finnish", "cs": "Czech",
    "el": "Greek", "he": "Hebrew", "id": "Indonesian", "uk": "Ukrainian",
    "ro": "Romanian", "hu": "Hungarian", "vi": "Vietnamese", "th": "Thai",
}


def language_name(code: str, default: str = "English") -> str:
    """Return the English name of a language code (``"fr"`` → ``"French"``).

    Used to name a target language to an LLM in a prompt so ANY detected
    language can be requested by name instead of collapsing to one hardcoded
    default. Accepts region-tagged codes (``"pt-BR"``) and is case-insensitive.

    Parameters
    ----------
    code : str
        Two-letter (or region-tagged, e.g. ``"pt-BR"``) language code.
    default : str, optional
        Returned when ``code`` is not in :data:`LANGUAGE_NAMES`. Defaults to
        ``"English"`` (a safe prompt fallback); pass the code itself when the
        caller would rather keep an unnamed code than substitute English.

    Returns
    -------
    str
        The language's English name, or ``default``.
    """
    return LANGUAGE_NAMES.get(code.split("-")[0].lower()[:2], default)
