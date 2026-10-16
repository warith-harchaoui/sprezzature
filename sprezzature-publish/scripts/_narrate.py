"""
_narrate
========

Shared helpers for the narration pipeline (``narrate_post.py`` + the
per-engine wrappers ``narrate_openvoice.py``, ``narrate_chatterbox.py``).

The pipeline returns **segments**, not flat strings: one entry per
heading / paragraph / list item / blockquote, each carrying the
narration hints derived from Markdown structure (and optionally
enriched by a local LLM via :func:`enrich_with_llm`). The wrappers
synthesise one segment at a time and concatenate the audio with the
requested pauses.

Three responsibilities, intentionally engine-agnostic:

1. **Markdown → segment list.** Structural cues are derived from the
   Markdown tree: heading level, list-item position, blockquote
   wrapping, emoji-driven admonitions, frontmatter ``narration.tone``
   baseline.
2. **Pronunciation overrides.** When ``pronunciation.yaml`` sits next
   to the source post (or in the project root), apply token
   substitution.
3. **Manifest + sha256 cache.** Record every narration into
   ``out/audio/manifest.json`` keyed on
   ``(source_sha256, engine, voice)`` so a re-run skips unchanged
   posts.

The engine wrappers import the heavy ML library at module-import time,
so they are invoked **as subprocesses** from ``narrate_post.py`` —
keeping ``_narrate`` pure-Python keeps every doctest and the
deterministic test suite fast and dependency-free.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypedDict


# ── Module-level configuration ──────────────────────────────────────────────

#: Pronunciation override filename. Searched next to the post first,
#: then walking up to the project root.
PRONUNCIATION_FILE: str = "pronunciation.yaml"

#: Baseline pause lengths, in milliseconds, derived from Markdown
#: structure. Heading H1 / H2 / H3+ get progressively shorter breathing
#: room; paragraphs get a comma-pause-style break; list items get just
#: enough silence to mark the enumeration.
PAUSE_HEADING_MS: dict[int, int] = {1: 1500, 2: 1000, 3: 700, 4: 500, 5: 500, 6: 500}
PAUSE_PARAGRAPH_MS: int = 800
PAUSE_LIST_ITEM_MS: int = 400
PAUSE_BLOCKQUOTE_MS: int = 700

#: Hard bounds the LLM-enriched values are clamped to. Defends against
#: hallucinated 10-second pauses that would wreck pacing.
#: Breath between two sentences of the same block. Shorter than the pause
#: between blocks, because a paragraph read with paragraph-length gaps inside
#: it sounds like a list of unrelated statements.
PAUSE_SENTENCE_MS: int = 250

PAUSE_MIN_MS: int = 0
PAUSE_MAX_MS: int = 3000
INTENSITY_MIN: float = 0.0
INTENSITY_MAX: float = 1.0

#: Emoji → emotion lookup. Covers the common semantic markers used in
#: modern Markdown (admonitions, callouts, "TIL"-style notes). Extend
#: per-project via ``pronunciation.yaml`` if needed.
EMOJI_EMOTION: dict[str, str] = {
    "⚠️": "cautious", "🚨": "cautious", "❗": "cautious", "🛑": "cautious",
    "💡": "calm", "📝": "calm", "📌": "calm", "ℹ️": "calm",
    "🎉": "cheerful", "✨": "cheerful", "🎊": "cheerful",
    "❤️": "warm", "💙": "warm", "🙏": "warm",
    "🔥": "enthusiastic", "🚀": "enthusiastic", "⚡": "enthusiastic",
    "😢": "sad", "😔": "sad", "💔": "sad",
    "🤔": "contemplative", "🧐": "contemplative",
}

#: Default emotion / pace when no signal carries information.
DEFAULT_EMOTION: str = "neutral"
DEFAULT_INTENSITY: float = 0.5
DEFAULT_PACE: str = "normal"


# ── Segment shape ──────────────────────────────────────────────────────────

class Segment(TypedDict):
    """
    One narration unit. Engine wrappers iterate over a list of these,
    synthesise audio for each ``text``, and concatenate with the
    requested pauses.
    """

    text: str
    kind: str            # "heading" | "paragraph" | "list_item" | "blockquote"
    heading_level: int   # 1-6 for "heading", 0 otherwise
    pause_before_ms: int
    pause_after_ms: int
    emotion: str
    intensity: float
    pace: str            # "slow" | "normal" | "fast"
    emphasis_word: str   # empty string when none


def make_segment(
    text: str,
    *,
    kind: str = "paragraph",
    heading_level: int = 0,
    pause_before_ms: int = 0,
    pause_after_ms: int = PAUSE_PARAGRAPH_MS,
    emotion: str = DEFAULT_EMOTION,
    intensity: float = DEFAULT_INTENSITY,
    pace: str = DEFAULT_PACE,
    emphasis_word: str = "",
) -> Segment:
    """
    Build a :class:`Segment` with sane defaults.

    Parameters are mostly self-documenting; defaults match the
    structural baselines used by :func:`extract_segments`.
    """
    return {
        "text": text,
        "kind": kind,
        "heading_level": heading_level,
        "pause_before_ms": pause_before_ms,
        "pause_after_ms": pause_after_ms,
        "emotion": emotion,
        "intensity": intensity,
        "pace": pace,
        "emphasis_word": emphasis_word,
    }


# ── Manifest entry (kept as a dataclass for readability) ───────────────────

@dataclass(frozen=True)
class NarrationManifestEntry:
    """
    One row in ``out/audio/manifest.json``. See module docstring for
    the cache invariant.
    """

    source: str
    audio: str
    engine: str
    voice: str
    source_sha256: str
    duration_seconds: float


# ── Markdown → segments ────────────────────────────────────────────────────

# Patterns kept module-level so the regex compiler caches them across
# repeated runs (a long blog post can have hundreds of segments).
#: A leading YAML frontmatter block. Public because the page route has to
#: drop exactly what the narration drops: anything else and the two stop
#: agreeing about where the document starts.
FRONTMATTER_RE: re.Pattern[str] = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.S)
_CODE_FENCE_RE: re.Pattern[str] = re.compile(r"^ {0,3}```.*?$.*?^ {0,3}```", re.M | re.S)

#: An HTML comment, including a multi-line one. The tag pattern cannot match
#: those -- it stops at the first ``>`` and never spans lines -- so a
#: commented-out note at the top of a file was read out in full, starting
#: with "less-than exclamation mark".
_HTML_COMMENT_RE: re.Pattern[str] = re.compile(r"<!--.*?-->", re.S)
#: A code span. The delimiter is a *run* of backticks closed by a run of the
#: same length, as Markdown defines it: ``dialog.showModal()`` is written
#: with two on each side so the single ones inside survive. Matching one
#: backtick at a time consumed the inner pair and left the outer two in the
#: prose, which a voice then read out as "backtick".
_INLINE_CODE_RE: re.Pattern[str] = re.compile(
    r"(?P<fence>`+)(?P<code>.+?)(?P=fence)(?!`)", re.S
)
_IMAGE_RE: re.Pattern[str] = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE: re.Pattern[str] = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HTML_TAG_RE: re.Pattern[str] = re.compile(r"<[^>]+>")

#: An ``<img>`` written as HTML rather than as ``![alt](src)``. Its alt text
#: is kept for the same reason the Markdown form's is: it is what a listener
#: gets instead of the picture. Unwrapped before tags are stripped, or the
#: tag pattern takes the description with the tag -- which is how a gallery
#: entry's logo was described on the page and silent in the audio.
_HTML_IMG_RE: re.Pattern[str] = re.compile(
    r'<img\b[^>]*?\balt\s*=\s*(?:"([^"]*)"|\'([^\']*)\')[^>]*>', re.I
)

#: A Markdown autolink -- ``<https://example.com>``, ``<mailto:a@b.c>`` or a
#: bare ``<a@b.c>``. Unwrapped before tags are stripped, because the tag
#: pattern would eat it whole and take the address with it: "open an issue at
#: ``<https://…/issues>``" came back as "open an issue at", which is a
#: sentence that has lost its point. The renderer shows the address, so the
#: narration says it -- and it shows an e-mail address *without* its
#: ``mailto:`` scheme, so the scheme is dropped here too rather than being
#: spelled out to a listener who is not going to type it.
_AUTOLINK_RE: re.Pattern[str] = re.compile(
    r"<(?:mailto:)?((?:https?://[^<>\s]+)|(?:[^<>\s@]+@[^<>\s@]+\.[^<>\s@]+))>"
)

#: Emphasis markers, in the order they have to be removed: the two-character
#: forms first, or the single-character rule would eat half of ``**bold**``.
#:
#: Each pattern requires a non-space just inside the markers, which is what
#: Markdown itself requires, and the single-character forms refuse a word
#: character on the outside -- that is what keeps ``snake_case`` whole and
#: stops ``3 * 4`` from being read as emphasis. Strikethrough is included
#: even though this project's renderer does not implement it (the tildes
#: reach the page as text): they are markup either way, and a voice saying
#: "tilde tilde" is not reading the sentence.
_EMPHASIS_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S),
    re.compile(r"(?<![\w_])__(?=\S)(.+?)(?<=\S)__(?![\w_])", re.S),
    re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.S),
    re.compile(r"(?<![\w*])\*(?=\S)([^*]+?)(?<=\S)\*(?![\w*])", re.S),
    re.compile(r"(?<![\w_])_(?=\S)([^_]+?)(?<=\S)_(?![\w_])", re.S),
)
_HEADING_RE: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_ITEM_RE: re.Pattern[str] = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")
_BLOCKQUOTE_RE: re.Pattern[str] = re.compile(r"^>\s?(.*)$")

#: A thematic break: three or more ``-``, ``*`` or ``_``, optionally spaced.
#: It separates sections visually and holds no words, so narrating it makes
#: the voice say "dash dash dash" where a reader sees a line.
_THEMATIC_BREAK_RE: re.Pattern[str] = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")

#: A table row: a line whose content is bounded by pipes. A table is skipped
#: for the reason code fences are -- it is sigil-heavy and rarely reads well
#: -- and skipping it is also what keeps a narrated page followable: the
#: renderer puts a table in ``<table>``, which the read-along does not treat
#: as narrated prose either, so both sides pass over the same thing.
_TABLE_ROW_RE: re.Pattern[str] = re.compile(r"^\s{0,3}\|.*\|\s*$")

#: The words wrapped around a quoted block so a listener hears where it
#: starts and ends. Named rather than inlined because the read-along has to
#: see through them to match a cue to the sentence on the page, and a string
#: spelled out in two modules is a string that drifts.
QUOTE_OPENING: str = "Quote:"
QUOTE_CLOSING: str = "End quote."

#: Inline marker the author can drop in to override the LLM/structure
#: hints for the segment that follows. ``[emotion: cheerful]`` until
#: ``[emotion: default]`` or the next section heading.
_EMOTION_MARKER_RE: re.Pattern[str] = re.compile(
    r"\[emotion:\s*([A-Za-z_]+)\s*\]",
)


def _strip_emphasis(text: str) -> str:
    """Remove emphasis markers, keeping the words they emphasise."""
    for pattern in _EMPHASIS_RES:
        text = pattern.sub(r"\1", text)
    return text


def _strip_inline(text: str) -> str:
    """Clean a chunk of Markdown text to bare narratable prose.

    Code spans are set aside before emphasis and HTML tags are removed, and
    put back afterwards. Both rules would otherwise damage them, and in both
    cases the renderer keeps what they hold -- so the damage would also be
    the one thing that makes the page and the narration disagree about the
    sentence:

    * ``a*b*c`` inside backticks is a pattern being read out, not an
      emphasis on ``b``;
    * ``<version>`` inside backticks is a placeholder a reader is meant to
      hear, not a tag. Stripping it loses the word outright, which is how
      "run ``release.sh <version>``" became "run release dot s h".

    Masking rather than splitting, because emphasis legitimately *spans* a
    code span -- ``**one model: `qwen3-vl:8b`**`` is one bold phrase -- and
    stripping each side of the span on its own leaves both halves of the
    ``**`` pair behind.
    """
    text = _IMAGE_RE.sub(r"\1", text)         # keep alt text only
    text = _LINK_RE.sub(r"\1", text)          # keep link text only
    text = _AUTOLINK_RE.sub(r"\1", text)      # keep the address
    text = _HTML_IMG_RE.sub(                  # keep an HTML image's alt text
        lambda m: m.group(1) if m.group(1) is not None else (m.group(2) or ""), text
    )
    held: list[str] = []

    def _hold(match: re.Match[str]) -> str:
        held.append(match.group("code"))
        # NUL cannot occur in Markdown prose, and it counts as neither a word
        # character nor whitespace, so it does not disturb the lookarounds
        # the emphasis patterns rely on.
        return f"\x00{len(held) - 1}\x00"

    text = _INLINE_CODE_RE.sub(_hold, text)   # drop backticks, keep content
    text = _HTML_TAG_RE.sub("", text)         # strip HTML tags
    text = _strip_emphasis(text)
    for index, content in enumerate(held):
        text = text.replace(f"\x00{index}\x00", content)
    # Collapse whitespace introduced by the above substitutions.
    return re.sub(r"\s+", " ", text).strip()


def _parse_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    """
    Split frontmatter from body. Returns ``({}, markdown)`` when no
    frontmatter or PyYAML missing.
    """
    m = FRONTMATTER_RE.match(markdown)
    if not m:
        return {}, markdown
    body: str = markdown[m.end():]
    try:
        import yaml
    except ImportError:
        return {}, body
    try:
        data: Any = yaml.safe_load(m.group("yaml"))
    except yaml.YAMLError:
        return {}, body
    return (data if isinstance(data, dict) else {}), body


def _emoji_emotion(text: str) -> str:
    """Return the first known emoji's emotion, or empty string."""
    for emoji, emotion in EMOJI_EMOTION.items():
        if emoji in text:
            return emotion
    return ""


def extract_segments(markdown: str) -> list[Segment]:
    """
    Parse a Markdown post into a list of narration segments.

    Each segment carries structural hints derived from the Markdown
    tree (heading level → pause length, list item → enumeration cue,
    blockquote → "Quote: ..." cue + lower expressiveness, leading
    emoji → emotion baseline) and the cleaned prose. Inline
    ``[emotion: X]`` markers override the structural emotion for
    subsequent segments until a closing ``[emotion: default]`` or a
    new section heading.

    Parameters
    ----------
    markdown : str
        Raw Markdown source. May start with a YAML frontmatter
        block — ``narration.tone`` is honoured as the baseline
        emotion. ``narration.pace`` is honoured as the baseline pace.

    Returns
    -------
    list of Segment
        Empty input yields an empty list.

    Examples
    --------
    >>> segs = extract_segments("# Hello\\n\\nA paragraph.\\n")
    >>> segs[0]["kind"], segs[0]["heading_level"], segs[0]["text"]
    ('heading', 1, 'Hello')
    >>> segs[1]["kind"], segs[1]["text"]
    ('paragraph', 'A paragraph.')
    """
    if not markdown.strip():
        return []
    frontmatter, body = _parse_frontmatter(markdown)
    tone_baseline: str = str(
        (frontmatter.get("narration") or {}).get("tone", DEFAULT_EMOTION)
        if isinstance(frontmatter.get("narration"), dict)
        else DEFAULT_EMOTION
    )
    pace_baseline: str = str(
        (frontmatter.get("narration") or {}).get("pace", DEFAULT_PACE)
        if isinstance(frontmatter.get("narration"), dict)
        else DEFAULT_PACE
    )
    # Drop code blocks entirely — sigil-heavy and rarely reads well.
    body = _CODE_FENCE_RE.sub("", body)
    # And comments, which are addressed to whoever opens the file, not to a
    # reader. Removed from the whole body rather than per block because a
    # comment may span several of them.
    body = _HTML_COMMENT_RE.sub("", body)

    segments: list[Segment] = []
    # The author marker stays in effect until reset or a new heading
    # appears. ``""`` means "follow the per-segment structural default".
    sticky_emotion: str = ""

    # Walk paragraphs separated by blank lines. Each "paragraph" may
    # actually be a heading, a list, a blockquote, or prose.
    for block in re.split(r"\n\s*\n", body):
        # Leading blank lines are dropped, not just trailing ones: a block
        # that begins with one has ``""`` as its first line, and every test
        # below reads that line. That is how a file whose frontmatter ended
        # just above kept the ``#`` of its own title and the ``>`` of its
        # first quotation -- both read out as prose.
        block = block.strip("\n").rstrip()
        if not block:
            continue

        # Check for an emotion marker inline. Capture the most recent
        # one in the block and strip it before narration.
        marker = _EMOTION_MARKER_RE.search(block)
        if marker:
            value: str = marker.group(1).lower()
            if value == "default":
                sticky_emotion = ""
            else:
                sticky_emotion = value
            block = _EMOTION_MARKER_RE.sub("", block).strip()
            if not block:
                # Marker-only block (sets the mode for what follows).
                continue

        lines: list[str] = block.splitlines()
        # Nothing to say about a horizontal rule, and a table read as a row
        # of pipes is noise. Both are skipped for the reason code fences are.
        if all(_THEMATIC_BREAK_RE.match(line) for line in lines):
            continue
        if sum(bool(_TABLE_ROW_RE.match(line)) for line in lines) >= 2:
            continue

        # Heading? Resets the sticky author emotion — a new section
        # starts clean unless re-declared inside it.
        first_line: str = lines[0]
        heading_match = _HEADING_RE.match(first_line)
        if heading_match:
            level: int = len(heading_match.group(1))
            heading_text: str = _strip_inline(heading_match.group(2))
            segments.append(make_segment(
                heading_text,
                kind="heading",
                heading_level=level,
                pause_before_ms=PAUSE_HEADING_MS.get(level, 500),
                pause_after_ms=PAUSE_HEADING_MS.get(level, 500),
                emotion=_emoji_emotion(heading_text) or tone_baseline,
                pace=pace_baseline,
            ))
            sticky_emotion = ""
            # If the block has more lines after the heading (rare but
            # possible), narrate the rest as a paragraph below.
            rest_lines: list[str] = block.splitlines()[1:]
            if rest_lines:
                rest_text: str = _strip_inline(" ".join(rest_lines))
                if rest_text:
                    segments.append(make_segment(
                        rest_text,
                        emotion=sticky_emotion or _emoji_emotion(rest_text)
                                or tone_baseline,
                        pace=pace_baseline,
                    ))
            continue

        # Blockquote? Wrap the inner text with "Quote: ... End quote."
        # and lower the intensity so it's audibly distinct.
        if all(_BLOCKQUOTE_RE.match(l) for l in block.splitlines()):
            inner: str = " ".join(
                _BLOCKQUOTE_RE.match(l).group(1)  # type: ignore[union-attr]
                for l in block.splitlines()
            )
            inner = _strip_inline(inner)
            quoted_text: str = f"{QUOTE_OPENING} {inner} {QUOTE_CLOSING}"
            segments.append(make_segment(
                quoted_text,
                kind="blockquote",
                pause_before_ms=PAUSE_BLOCKQUOTE_MS,
                pause_after_ms=PAUSE_BLOCKQUOTE_MS,
                emotion=sticky_emotion or _emoji_emotion(inner) or tone_baseline,
                intensity=max(INTENSITY_MIN, DEFAULT_INTENSITY - 0.15),
                pace=pace_baseline,
            ))
            continue

        # List? Each item is its own segment with a short pause.
        # Collected raw and cleaned once per item at the end: an emphasis
        # pair, a link or a code span may wrap across a continuation line,
        # and cleaning each line on its own leaves half of the construct
        # behind -- which is how "the **maximum local of the curve**" kept
        # its asterisks when the phrase happened to break over two lines.
        list_items: list[str] = []
        for line in block.splitlines():
            li = _LIST_ITEM_RE.match(line)
            if li:
                list_items.append(li.group(1))
            elif list_items:
                # Continuation line of the previous item.
                list_items[-1] += " " + line.strip()
        list_items = [_strip_inline(item) for item in list_items]
        # The block is a list when it *starts* as one. Comparing the item
        # count to the line count instead -- as this did -- switched the
        # continuation handling directly above off again: a continuation
        # line adds a line without adding an item, so any wrapped item sent
        # the whole block to the prose branch, markers and all, and
        # "1. Redistributions..." came back as a sentence reading "1.".
        if list_items and _LIST_ITEM_RE.match(lines[0]):
            for i, item_text in enumerate(list_items):
                segments.append(make_segment(
                    item_text,
                    kind="list_item",
                    pause_before_ms=0,
                    # Final item gets a paragraph-length pause; others
                    # get just enough silence to mark enumeration.
                    pause_after_ms=(
                        PAUSE_PARAGRAPH_MS if i == len(list_items) - 1
                        else PAUSE_LIST_ITEM_MS
                    ),
                    emotion=sticky_emotion or _emoji_emotion(item_text)
                            or tone_baseline,
                    pace=pace_baseline,
                ))
            continue

        # Default: a paragraph.
        prose: str = _strip_inline(" ".join(block.splitlines()))
        if prose:
            segments.append(make_segment(
                prose,
                kind="paragraph",
                pause_after_ms=PAUSE_PARAGRAPH_MS,
                emotion=sticky_emotion or _emoji_emotion(prose) or tone_baseline,
                pace=pace_baseline,
            ))
    return segments


def segments_to_text(segments: list[Segment]) -> str:
    """
    Flatten segments into a single narratable string, for engines
    that don't support per-segment metadata (or for hashing).

    The text-only flattening drops every pause / emotion / pace cue
    and joins with single spaces, so it stays stable across
    refactorings of the hint plumbing.
    """
    return " ".join(seg["text"] for seg in segments if seg["text"]).strip()


# ── Pronunciation overrides ────────────────────────────────────────────────

def load_pronunciation(post_path: Path) -> dict[str, str]:
    """
    Load ``pronunciation.yaml`` if present (per-post then project-root).

    Returns an empty mapping when no file exists or PyYAML is missing.
    Overrides are an opt-in feature, never a hard requirement.
    """
    candidates: list[Path] = [post_path.parent / PRONUNCIATION_FILE]
    cursor: Path = post_path.parent
    for _ in range(8):  # ceiling so we never walk the whole disk
        if (cursor / ".git").exists():
            candidates.append(cursor / PRONUNCIATION_FILE)
            break
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    for candidate in candidates:
        if candidate.is_file():
            try:
                import yaml
            except ImportError:
                return {}
            data: Any = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return {
                str(k): str(v) for k, v in data.items()
                if isinstance(k, (str, int, float))
                and isinstance(v, (str, int, float))
            }
    return {}


def apply_pronunciation(
    segments: list[Segment], overrides: dict[str, str],
) -> list[Segment]:
    """
    Apply token-substitution overrides to every segment's text.

    Substitution is whole-word and case-sensitive. Longer tokens win
    when they overlap (``"WCAG 2.2"`` beats ``"WCAG"``).
    """
    if not overrides:
        return segments
    tokens: list[str] = sorted(
        (t for t in overrides if t), key=len, reverse=True,
    )
    out: list[Segment] = []
    for seg in segments:
        new_text: str = seg["text"]
        for token in tokens:
            new_text = re.sub(
                rf"\b{re.escape(token)}\b",
                overrides[token],
                new_text,
            )
        out.append({**seg, "text": new_text})
    return out


# ── LLM enrichment (Ollama, optional) ──────────────────────────────────────

#: System prompt for the Ollama emotion classifier. Returns strict JSON
#: per segment; the orchestrator validates and clamps the result before
#: it reaches the engine. Loaded from prompts/narration_emotion.yaml, NOT
#: inlined — LLM prompts, like GUI strings, live in a YAML catalog per the
#: sprezzature-* i18n rule (see sprezzature-ui/scripts/audit_i18n.py, rule I18N002).
import sys as _sys  # noqa: E402

_sys.path.insert(0, str(Path(__file__).resolve().parent))
from _prompts import load_prompt as _load_prompt  # noqa: E402

LLM_SYSTEM_PROMPT: str = _load_prompt(
    "narration_emotion", prompts_dir=Path(__file__).resolve().parent / "prompts"
)["system"]


def _clamp(value: Any, lo: float, hi: float, fallback: float) -> float:
    """Force ``value`` into ``[lo, hi]``, falling back when not numeric."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, x))


def merge_llm_hint(seg: Segment, hint: dict[str, Any]) -> Segment:
    """
    Merge a single LLM response into one segment, clamping bad values.

    Structural baseline survives whenever the LLM omits a field or
    returns garbage — fail-soft is the default everywhere in the
    pipeline.

    Parameters
    ----------
    seg : Segment
        Segment with structural defaults already filled in.
    hint : dict
        Parsed JSON returned by Ollama. Any subset of segment keys.

    Returns
    -------
    Segment
        Merged segment ready for the engine wrapper.
    """
    out: Segment = dict(seg)  # type: ignore[assignment]
    if isinstance(hint.get("emotion"), str) and hint["emotion"].strip():
        out["emotion"] = hint["emotion"].strip().lower()
    out["intensity"] = _clamp(
        hint.get("intensity"), INTENSITY_MIN, INTENSITY_MAX, seg["intensity"],
    )
    if hint.get("pace") in {"slow", "normal", "fast"}:
        out["pace"] = hint["pace"]
    out["pause_before_ms"] = int(_clamp(
        hint.get("pause_before_ms"), PAUSE_MIN_MS, PAUSE_MAX_MS,
        seg["pause_before_ms"],
    ))
    out["pause_after_ms"] = int(_clamp(
        hint.get("pause_after_ms"), PAUSE_MIN_MS, PAUSE_MAX_MS,
        seg["pause_after_ms"],
    ))
    if isinstance(hint.get("emphasis_word"), str):
        out["emphasis_word"] = hint["emphasis_word"].strip()
    return out


# ── Manifest + sha256 cache ────────────────────────────────────────────────

def source_sha256(prose: str) -> str:
    """SHA-256 of the prose fed to the engine, UTF-8 encoded."""
    return hashlib.sha256(prose.encode("utf-8")).hexdigest()


def read_manifest(path: Path) -> dict[str, NarrationManifestEntry]:
    """Read ``manifest.json`` if present, returning a source-keyed mapping."""
    if not path.is_file():
        return {}
    try:
        rows: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(rows, list):
        return {}
    out: dict[str, NarrationManifestEntry] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            entry = NarrationManifestEntry(
                source=str(row["source"]),
                audio=str(row["audio"]),
                engine=str(row["engine"]),
                voice=str(row["voice"]),
                source_sha256=str(row["source_sha256"]),
                duration_seconds=float(row.get("duration_seconds", -1)),
            )
        except (KeyError, TypeError, ValueError):
            continue
        out[entry.source] = entry
    return out


def write_manifest(
    path: Path, entries: dict[str, NarrationManifestEntry],
) -> None:
    """Write the manifest to disk, sorted by source path for stable diffs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = [
        asdict(entries[source]) for source in sorted(entries)
    ]
    path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ── Timeline: where each segment actually landed in the audio ──────────────


@dataclass(frozen=True)
class Cue:
    """One narrated unit, with the slice of audio that speaks it.

    ``index`` is the position in the **original** segment list, not in the
    audio. The two differ: segments whose text is empty after cleaning are
    skipped rather than synthesised, so counting emitted pieces drifts from
    counting segments. Carrying the original index is what lets a page map a
    cue back to the block it came from.
    """

    index: int
    text: str
    start_seconds: float
    end_seconds: float


class Timeline:
    """Accumulates durations while an engine accumulates audio.

    Two problems, one object.

    The first is that ``pause_before_ms`` was computed by everything and
    applied by nothing. ``extract_segments`` sets it from the structural
    baselines, the Ollama pass is asked for it by name in
    ``prompts/narration_emotion.yaml`` and clamps the answer in
    :func:`merge_llm_hint` -- and then both engine wrappers appended silence
    for ``pause_after_ms`` only. The silence that sets a heading apart from
    what precedes it was computed, stored, and dropped. Both wrappers had
    their own copy of the same loop, which is how one omission became two.

    The second is that nothing recorded *where* each segment ended up, so a
    page could play the narration but not follow it. The offsets are exact
    and already known at concatenation time -- this just keeps them.

    Deliberately numpy-free: it counts samples and the caller holds the
    arrays, so ``_narrate`` stays importable with nothing but the standard
    library (see the module docstring).

    Examples
    --------
    >>> timeline = Timeline(1000)
    >>> timeline.silence(500)
    500
    >>> timeline.speech(2000, index=0, text="Hello.")
    >>> timeline.silence(250)
    250
    >>> [(c.start_seconds, c.end_seconds) for c in timeline.cues]
    [(0.5, 2.5)]
    >>> timeline.total_seconds
    2.75
    """

    def __init__(self, sample_rate_hz: int) -> None:
        self.sample_rate_hz = int(sample_rate_hz)
        self._samples = 0
        self._cues: list[Cue] = []

    def silence(self, milliseconds: float) -> int:
        """Advance the clock by `milliseconds`; return the sample count to append.

        Returning the count rather than an array is what keeps this module
        numpy-free. A caller that ignores the return value desynchronises the
        timeline from its own audio, which is why both engines append exactly
        what this hands back.
        """
        count = int(self.sample_rate_hz * max(0.0, float(milliseconds)) / 1000.0)
        self._samples += count
        return count

    def speech(self, sample_count: int, *, index: int, text: str) -> None:
        """Record that `sample_count` samples of audio speak `text`."""
        start = self._samples / float(self.sample_rate_hz)
        self._samples += int(sample_count)
        end = self._samples / float(self.sample_rate_hz)
        self._cues.append(Cue(index=index, text=text, start_seconds=start, end_seconds=end))

    @property
    def cues(self) -> list[Cue]:
        """Every recorded cue, in playback order."""
        return list(self._cues)

    @property
    def total_seconds(self) -> float:
        """Length of the audio described so far, silences included."""
        return self._samples / float(self.sample_rate_hz)


def format_timestamp(seconds: float) -> str:
    """``HH:MM:SS.mmm`` -- the only timestamp form WebVTT accepts.

    Milliseconds are truncated rather than rounded, so a cue never claims to
    start before the sample that actually starts it.
    """
    if seconds < 0:
        seconds = 0.0
    total_ms = int(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def cues_to_vtt(cues: list[Cue]) -> str:
    """Render cues as a WebVTT file.

    WebVTT rather than a bespoke JSON for one reason: a browser parses it
    natively through ``<track>``, firing ``cuechange`` without a line of
    parsing code, and the same file doubles as captions for the audio
    element. It is also the format ``sprezzature-audio`` already emits for
    video, so a site has one caption format rather than two.

    Each cue is given its segment index as a WebVTT *identifier* -- the line
    before the timings -- which is what lets a page highlight the right block
    without matching on text.
    """
    lines = ["WEBVTT", ""]
    for cue in cues:
        lines.append(str(cue.index))
        lines.append(
            f"{format_timestamp(cue.start_seconds)} --> {format_timestamp(cue.end_seconds)}"
        )
        # A blank line ends a cue, so a hard-wrapped payload would split it.
        lines.append(" ".join(cue.text.split()))
        lines.append("")
    return "\n".join(lines)


# ── Sentences ──────────────────────────────────────────────────────────────

#: Tokens that end in a full stop without ending a sentence. Splitting on
#: ``.`` alone turns "Dr. Rosling said so." into two sentences and the
#: highlight jumps mid-phrase, which is worse than not highlighting at all.
#:
#: Bilingual on purpose: this suite writes English and French side by side,
#: and the French list is not a translation of the English one -- ``M.`` is
#: an abbreviation in French and a sentence end in English ("...the M.").
#: Compared case-insensitively, matched on the token before the stop.
_ABBREVIATIONS: frozenset[str] = frozenset(
    {
        # English
        "mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc",
        "inc", "ltd", "co", "fig", "al", "e.g", "i.e", "cf", "no", "vol",
        "ph.d", "approx", "dept", "est", "min", "max",
        # French
        "m", "mme", "mlle", "mm", "dr", "pr", "st", "ste", "av", "bd",
        "env", "ex", "fig", "cf", "éd", "vol", "chap", "p", "pp", "art",
        "réf", "tél", "pers", "sg", "env",
    }
)

#: A sentence ends at one of these, possibly followed by a closing quote or
#: bracket, and then whitespace. The lookahead for an opening character is
#: what keeps "...end.  Next" together with its following capital rather
#: than splitting on every stop it finds inside a number or an ellipsis.
_SENTENCE_END = re.compile(
    r"""
    (?P<terminator>[.!?…]+)              # one or more terminators (… and ...)
    (?P<closers>
        (?:[ \u00a0\u202f]*["'”’»\)\]])*   # closing marks that belong to it
    )
    (?P<space>\s+)                       # the gap before whatever follows
    """,
    re.VERBOSE,
)

def _ends_an_abbreviation(text: str, stop: int) -> bool:
    """Is the full stop at `stop` part of a token that is not a sentence end?"""
    head = text[:stop]
    # No check for decimals here, deliberately. A real decimal separator has
    # a digit straight after it, and `_SENTENCE_END` requires whitespace, so
    # "3.14" can never reach this function. An earlier version guarded
    # against them anyway and paid for it: "Voir p. 12. Puis la suite." was
    # left as one sentence, because the stop after "12" looked decimal.
    # The token before the stop: letters, digits and interior dots, so
    # "e.g" and "Ph.D" are recognised whole rather than by their last letter.
    token = re.split(r"[\s(\[\"'“«]", head)[-1].lower().rstrip(".")
    if not token:
        return False
    if token in _ABBREVIATIONS:
        return True
    # A single letter followed by a stop is an initial -- "J. R. R. Tolkien",
    # "W. Harchaoui" -- and never the end of a sentence.
    return len(token) == 1 and token.isalpha()


def split_sentences(text: str) -> list[str]:
    """Split a block of prose into sentences, for narration and highlighting.

    Sentence granularity is the choice the read-along is built on: a
    paragraph is too coarse to follow with the eye on anything longer than
    three lines, and a word needs forced alignment against audio this
    pipeline generated itself -- a statistical guess at something already
    known exactly. A sentence is both precise enough to follow and exact by
    construction, because each one is synthesised on its own and its length
    is therefore measured rather than estimated.

    Deliberately a small rule set rather than a model: it has to give the
    same answer for the page and for the audio, run with no dependency, and
    be inspectable when it gets one wrong. It handles terminators with their
    trailing quotes, ellipses, decimals, initials, and the abbreviations in
    :data:`_ABBREVIATIONS` for English and French.

    Parameters
    ----------
    text : str
        One block's text, already cleaned of markup by
        :func:`extract_segments`.

    Returns
    -------
    list of str
        One entry per sentence, whitespace-collapsed, never empty strings.
        Text with no terminator at all comes back as a single sentence.

    Examples
    --------
    >>> split_sentences("One. Two! Three?")
    ['One.', 'Two!', 'Three?']
    >>> split_sentences("Dr. Rosling said so. Then he left.")
    ['Dr. Rosling said so.', 'Then he left.']
    >>> split_sentences("It cost 3.14 euros. Exactly.")
    ['It cost 3.14 euros.', 'Exactly.']
    >>> split_sentences("No terminator here")
    ['No terminator here']
    """
    collapsed = " ".join(text.split())
    if not collapsed:
        return []

    sentences: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(collapsed):
        stop = match.start("terminator")
        # Only a lone full stop can be an abbreviation; "!" and "?" and any
        # run of terminators always end the sentence.
        if match.group("terminator") == "." and _ends_an_abbreviation(collapsed, stop):
            continue
        end = match.end("closers")
        piece = collapsed[start:end].strip()
        if piece:
            sentences.append(piece)
        start = match.end("space")

    tail = collapsed[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def explode_to_sentences(segments: list[Segment]) -> list[Segment]:
    """One segment per sentence, so the audio can be followed sentence by sentence.

    The read-along highlight is only as precise as the unit that gets its own
    slice of audio. Synthesising a whole paragraph gives one timestamp for ten
    lines; synthesising each sentence gives one per sentence, measured rather
    than aligned, because each is generated on its own.

    The block's pauses are redistributed rather than repeated, which is the
    part that is easy to get wrong: a block's ``pause_before_ms`` belongs to
    its **first** sentence only and its ``pause_after_ms`` to its **last**,
    with :data:`PAUSE_SENTENCE_MS` between the rest. Copying the block's
    pauses onto every sentence would put a heading-sized silence inside a
    paragraph and make prose read like a list.

    Everything else -- emotion, intensity, pace, kind, heading level -- is
    inherited unchanged: those describe how the block sounds, and a sentence
    does not change its mind halfway through a paragraph.

    Parameters
    ----------
    segments : list of Segment
        Blocks from :func:`extract_segments`, optionally enriched.

    Returns
    -------
    list of Segment
        One per sentence, in reading order. A block whose text holds no
        sentence at all contributes nothing, so this can be shorter than its
        input -- and the page must be built from *this* list, not from the
        blocks, or the two stop agreeing about what cue 12 is.

    Examples
    --------
    >>> blocks = extract_segments("One. Two.\\n\\nThree.")
    >>> [s["text"] for s in explode_to_sentences(blocks)]
    ['One.', 'Two.', 'Three.']
    """
    out: list[Segment] = []
    for block in segments:
        sentences = split_sentences(block.get("text", ""))
        if not sentences:
            continue
        last = len(sentences) - 1
        for position, sentence in enumerate(sentences):
            piece: Segment = dict(block)  # type: ignore[assignment]
            piece["text"] = sentence
            piece["pause_before_ms"] = (
                int(block.get("pause_before_ms", 0)) if position == 0 else 0
            )
            piece["pause_after_ms"] = (
                int(block.get("pause_after_ms", 0))
                if position == last
                else PAUSE_SENTENCE_MS
            )
            out.append(piece)
    return out
