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
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
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
_FRONTMATTER_RE: re.Pattern[str] = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.S)
_CODE_FENCE_RE: re.Pattern[str] = re.compile(r"^```.*?$.*?^```", re.M | re.S)
_INLINE_CODE_RE: re.Pattern[str] = re.compile(r"`([^`]+)`")
_IMAGE_RE: re.Pattern[str] = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE: re.Pattern[str] = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HTML_TAG_RE: re.Pattern[str] = re.compile(r"<[^>]+>")
_HEADING_RE: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_ITEM_RE: re.Pattern[str] = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")
_BLOCKQUOTE_RE: re.Pattern[str] = re.compile(r"^>\s?(.*)$")

#: Inline marker the author can drop in to override the LLM/structure
#: hints for the segment that follows. ``[emotion: cheerful]`` until
#: ``[emotion: default]`` or the next section heading.
_EMOTION_MARKER_RE: re.Pattern[str] = re.compile(
    r"\[emotion:\s*([A-Za-z_]+)\s*\]",
)


def _strip_inline(text: str) -> str:
    """Clean a chunk of Markdown text to bare narratable prose."""
    text = _IMAGE_RE.sub(r"\1", text)         # keep alt text only
    text = _LINK_RE.sub(r"\1", text)          # keep link text only
    text = _INLINE_CODE_RE.sub(r"\1", text)   # drop backticks
    text = _HTML_TAG_RE.sub("", text)         # strip HTML tags
    # Collapse whitespace introduced by the above substitutions.
    return re.sub(r"\s+", " ", text).strip()


def _parse_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    """
    Split frontmatter from body. Returns ``({}, markdown)`` when no
    frontmatter or PyYAML missing.
    """
    m = _FRONTMATTER_RE.match(markdown)
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

    segments: list[Segment] = []
    # The author marker stays in effect until reset or a new heading
    # appears. ``""`` means "follow the per-segment structural default".
    sticky_emotion: str = ""

    # Walk paragraphs separated by blank lines. Each "paragraph" may
    # actually be a heading, a list, a blockquote, or prose.
    for block in re.split(r"\n\s*\n", body):
        block = block.rstrip()
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

        # Heading? Resets the sticky author emotion — a new section
        # starts clean unless re-declared inside it.
        first_line: str = block.splitlines()[0]
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
            quoted_text: str = f"Quote: {inner} End quote."
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
        list_items: list[str] = []
        for line in block.splitlines():
            li = _LIST_ITEM_RE.match(line)
            if li:
                list_items.append(_strip_inline(li.group(1)))
            elif list_items:
                # Continuation line of the previous item.
                list_items[-1] += " " + _strip_inline(line)
        if list_items and len(list_items) == len(block.splitlines()):
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
#: front-* i18n rule (see sprezzature-ui/scripts/audit_i18n.py, rule I18N002).
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
