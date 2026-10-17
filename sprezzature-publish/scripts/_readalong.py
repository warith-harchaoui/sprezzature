"""
_readalong — wire a narrated page to its audio, sentence by sentence.

The audio and the page come from the same Markdown by two different routes:
``_narrate.extract_segments`` cleans the Markdown and hands sentences to a TTS
engine, while ``md_to_html`` renders the Markdown with the ``markdown``
library. Nothing makes those two agree about what sentence twelve is, and a
read-along that is wrong by one sentence is worse than none -- it tells a
reader with confidence to look at the wrong line.

So this module does not number sentences independently. It takes the cues the
narration actually produced, splits the rendered HTML with the *same*
splitter, and compares the two lists. They match, or it raises and names the
first divergence. There is no third outcome where it wraps something and
hopes.

Reading the page as a tree, not as a pattern
--------------------------------------------
The blocks are found by walking the HTML rather than matching it, because
three things a regex cannot see decide what a block's text is:

* A code fence inside a list item. The narration drops fenced code; a
  pattern matching ``<li>…</li>`` swallows the ``<pre>`` with it and reads
  out ``git clone … cd … python3 -m venv``.
* A nested list. ``<li>Parent<ul><li>Child</li></ul></li>`` is two narrated
  segments in the audio and one match to a pattern, which merges them.
* An image. ``![alt](src)`` is narrated -- the alt text is what a listener
  gets instead of the picture -- so the page has to count that text too,
  and the picture is what gets highlighted while it is read.

Cues with nothing of their own to highlight
-------------------------------------------
Not every cue has a sentence on the page. ``extract_segments`` wraps a
blockquote in :data:`_narrate.QUOTE_OPENING` and
:data:`_narrate.QUOTE_CLOSING` so a listener hears where the quotation
starts and stops, and "End quote." is a sentence the reader never sees.
Those cues are attached to the block they belong to instead of being matched
to text, and the player simply keeps the current highlight while they play.

What it emits
-------------
* ``<span class="ra-s" id="ra-12">`` around each sentence, which is what the
  highlight attaches to.
* A player: ``<audio controls>`` plus a ``<track kind="metadata">`` pointing
  at the narration's WebVTT, so the browser parses the cues and fires
  ``cuechange`` with no parsing code of ours.

Accessibility notes, since that is the point of the feature
-----------------------------------------------------------
Read-along audio is not for screen-reader users -- they already have speech,
and a second voice talking over theirs is an obstacle, not an aid. It serves
dyslexic readers, readers with low vision who use magnification, readers
tired or distracted, and people reading in a second language. That shapes
every decision below:

* The highlight is **visual only**. No ARIA live region, no ``aria-current``
  churn: announcing every sentence as it is spoken would make the page
  unusable for anyone who *is* on a screen reader, for the benefit of someone
  who is not.
* Auto-scroll becomes instant under ``prefers-reduced-motion`` rather than
  disappearing. Smooth scrolling is the vestibular trigger; a jump is not
  animation, and removing the scroll altogether would leave a reader hunting
  for the highlight they asked to follow.
* The highlight is a background tint **and** a left border, never colour
  alone -- WCAG 1.4.1.
* Every sentence is clickable to seek, and the player keeps native controls,
  so the feature is reachable by keyboard without a single custom key
  handler.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import html
import os
import re
import shutil
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

#: Block elements whose text is narrated. Code blocks are deliberately absent:
#: ``extract_segments`` strips them, so the narration has nothing to say about
#: them and wrapping them would push every later index out by one.
NARRATED_BLOCKS: frozenset[str] = frozenset(
    {"p", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
)

#: Subtrees whose text is not read. ``pre`` holds code and ``table`` is
#: skipped for the same reason; the rest is page furniture that exists on
#: every hand-written page and on no Markdown one -- a reader asking to hear
#: *this article* did not ask for the navigation, the cookie banner or the
#: contents of a ``<style>`` block.
SKIPPED_SUBTREES: frozenset[str] = frozenset(
    {
        "pre", "table",
        "script", "style", "template", "noscript", "svg", "head", "title",
        "nav", "footer", "aside", "form", "dialog", "select", "option",
    }
)

def _matches(selector: str, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
    """Whether an element matches a one-step selector.

    Three forms, which is all a scope needs: ``article`` (tag name),
    ``#main`` (id) and ``.post-body`` (one class). Deliberately not a CSS
    engine -- descendant combinators and attribute predicates would invite
    the caller to express something this walker cannot honour, and the
    failure would be a page narrated from the wrong element.
    """
    if selector.startswith("#"):
        return any(name == "id" and value == selector[1:] for name, value in attrs)
    if selector.startswith("."):
        return any(
            name == "class" and selector[1:] in (value or "").split()
            for name, value in attrs
        )
    return tag == selector.lower()


#: Attributes that take an element out of the reading. ``aria-hidden`` is the
#: one that matters: it already hides the element from assistive technology,
#: and narrating what a screen reader is told to ignore would have this
#: feature contradict the page it is trying to help.
def _is_hidden(attrs: list[tuple[str, str | None]]) -> bool:
    """Whether an element is hidden from readers, by markup rather than CSS."""
    for name, value in attrs:
        if name == "hidden":
            return True
        if name == "aria-hidden" and (value or "").strip().lower() == "true":
            return True
    return False

#: Class on every wrapped sentence. Short because it appears once per
#: sentence and a long name is measurable page weight on a long post.
SENTENCE_CLASS = "ra-s"

#: Audio types this player will declare, by file extension. Public so the
#: converter can look for exactly the recordings this player can serve. A ``<source>``
#: with the wrong ``type`` is a file the browser declines to load, and one
#: with no ``type`` costs a round trip to find out -- so an unknown extension
#: raises here rather than being guessed at.
AUDIO_TYPES: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
}

#: Elements with no closing tag. They are tracked separately because inline
#: depth is counted by pairs: a ``<br>`` that increments and never decrements
#: pushes every later piece of the block one level deeper, and the crossing
#: check below then refuses a sentence that was never crossing anything. A
#: hard line break inside a paragraph is ordinary prose, so this was not a
#: rare case.
VOID_ELEMENTS: frozenset[str] = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
     "meta", "param", "source", "track", "wbr"}
)

#: Strikethrough markers, which this project's renderer does not implement:
#: ``~~F5-TTS~~`` reaches the page as text. The narration drops them -- a
#: voice saying "tilde tilde" is not reading the sentence -- so the page side
#: has to agree they are markup and not words.
_TILDES = re.compile(r"~~")

_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class VttCue:
    """One cue read back from a narration WebVTT file."""

    index: int
    text: str
    start_seconds: float
    end_seconds: float


class ReadAlongMismatch(RuntimeError):
    """The page and the narration disagree about the sentences.

    Raised rather than worked around. The two lists come from the same
    Markdown, so a divergence means one of the two routes changed -- a new
    Markdown construct that ``extract_segments`` strips and the renderer
    keeps, or the reverse -- and the fix is to make them agree again, not to
    wrap whatever happens to line up.
    """


def _timestamp_seconds(stamp: str) -> float:
    """Parse ``HH:MM:SS.mmm`` or ``MM:SS.mmm`` into seconds."""
    parts = stamp.strip().split(":")
    if len(parts) == 2:
        parts = ["0", *parts]
    hours, minutes, rest = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def parse_vtt(text: str) -> list[VttCue]:
    """Read the cues a narration run wrote.

    Only what this project emits is supported -- an identifier line, a timing
    line, one line of payload. Styling blocks, regions and positioning are
    not parsed, because nothing here writes them and silently ignoring a
    construct is how a parser starts lying about its input.
    """
    if not text.lstrip().startswith("WEBVTT"):
        raise ReadAlongMismatch("not a WebVTT file: it does not start with WEBVTT")

    cues: list[VttCue] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks[1:]:  # blocks[0] is the WEBVTT header
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        identifier, timing, *payload = lines
        if "-->" not in timing:
            continue
        start, end = (part.strip() for part in timing.split("-->", 1))
        cues.append(
            VttCue(
                index=int(identifier.strip()),
                text=" ".join(" ".join(payload).split()),
                start_seconds=_timestamp_seconds(start),
                end_seconds=_timestamp_seconds(end.split()[0]),
            )
        )
    return cues


def _visible_text(fragment: str) -> str:
    """The words a reader sees, with markup and entities resolved.

    Comparison has to happen on this rather than on raw HTML: the narration
    never saw ``<em>`` and the page never saw the Markdown asterisks, so the
    two agree on words and on nothing else.
    """
    return " ".join(html.unescape(_TAG.sub("", fragment)).split())


# ── Reading the page as a tree ──────────────────────────────────


@dataclass
class _Piece:
    """One atom of a block's content: its markup, and the words it shows.

    Three kinds, distinguished by what may be done to them:

    * **text** -- may be cut, because a sentence can end in the middle of it;
    * **atomic** -- may not. An ``<img>`` is the case that matters: its alt
      text is narrated, possibly as several sentences, but a picture is one
      object and a span boundary inside it has nowhere to go;
    * **a nested block** -- a list inside a list item, say. Its words belong
      to *it*, so it shows none of its own here, and it is rendered by
      recursion once its own sentences are wrapped.
    """

    raw: str
    visible: str = ""
    atomic: bool = False
    child: "_Block | None" = None
    #: Inline nesting depth on each side of this piece. A span must open and
    #: close at the same depth: one that opens outside an ``<em>`` and closes
    #: inside it crosses the element, which is not valid HTML -- so it is
    #: detected, not emitted. Both sides are recorded because a span grows by
    #: swallowing the tags that close inside it, and only ``after`` says when
    #: it has swallowed enough.
    depth: int = 0
    after: int = 0


@dataclass
class _Block:
    """One narrated block of the page, with the markup that opened it."""

    tag: str
    open_raw: str = ""
    close_raw: str = ""
    pieces: list[_Piece] = field(default_factory=list)
    #: Inside a ``<blockquote>``. Carried because the narration says where a
    #: quotation starts and stops, and on a hand-written page the quoted text
    #: lives in a ``<p>`` *inside* the ``<blockquote>`` rather than in the
    #: element itself -- so the quotation is not visible from the block's own
    #: tag.
    in_quote: bool = False

    @property
    def visible(self) -> str:
        """The words this block shows itself, whitespace collapsed.

        A nested block's words are not among them: the narration gives a
        nested list item its own segment, so counting it twice -- once for
        the parent, once for itself -- would put every later cue out by one.
        """
        return " ".join("".join(piece.visible for piece in self.pieces).split())


class _PageWalker(HTMLParser):
    """Split rendered HTML into narrated blocks, keeping the markup.

    Rebuilds the document rather than indexing into it: every event is
    re-emitted verbatim, so the output differs from the input only by the
    spans that get inserted. ``convert_charrefs`` is off so that entities
    stay entities -- resolving them would quietly rewrite ``&amp;`` as ``&``
    in the page's own source.
    """

    def __init__(self, scope: str | None = None) -> None:
        super().__init__(convert_charrefs=False)
        #: Only blocks inside this element are narrated. ``None`` narrates the
        #: whole document, which is right for a page this project rendered and
        #: wrong for one it did not: a hand-written page carries a header, a
        #: nav and a footer that a reader asking for *this article* did not
        #: ask to hear.
        self._scope = scope
        self._scope_at: int | None = None
        #: The pieces holding the start tags of the scope element and of
        #: ``<body>``. Kept so a player can be placed at the top of the
        #: article it belongs to: the pieces are mutable, so the injection
        #: appends to one of them rather than hunting for a tag in the
        #: rebuilt string.
        self.scope_piece: _Piece | None = None
        self.body_piece: _Piece | None = None
        #: The document itself, as pieces. Nested content hangs off
        #: ``_Piece.child`` rather than being flattened, so reading order
        #: survives into the rebuild.
        self.out: list[_Piece] = []
        #: Every narrated block, in reading order -- which is the order the
        #: cues are in, and the only order the alignment may use.
        self.blocks: list[_Block] = []
        self._open: list[_Block] = []
        self._skip = 0
        self._depth = 0
        #: ``<blockquote>`` nesting, so a paragraph knows it is quoted.
        self._quoted = 0
        #: Depth of the hidden subtree we are inside, if any. Tracked by the
        #: whole element stack rather than a flag: ``aria-hidden`` on a
        #: wrapper hides everything under it, not just its own text.
        self._hidden_at: int | None = None
        self._stack = 0

    def _emit(self, piece: _Piece) -> None:
        (self._open[-1].pieces if self._open else self.out).append(piece)

    def _raw(self, raw: str, visible: str = "", *, atomic: bool = False,
             after: int | None = None) -> None:
        self._emit(_Piece(
            raw, visible, atomic=atomic,
            depth=self._depth,
            after=self._depth if after is None else after,
        ))

    # -- events ------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text() or f"<{tag}>"
        if tag not in VOID_ELEMENTS:
            self._stack += 1
            if self._hidden_at is None and _is_hidden(attrs):
                self._hidden_at = self._stack
        if tag == "blockquote":
            self._quoted += 1
        if (
            self._scope is not None
            and self._scope_at is None
            and tag not in VOID_ELEMENTS
            and _matches(self._scope, tag, attrs)
        ):
            self._scope_at = self._stack
            self._raw(raw, atomic=True)
            self.scope_piece = (self._open[-1].pieces if self._open else self.out)[-1]
            return
        if self._hidden_at is not None:
            self._raw(raw, atomic=True)
            return
        if tag in SKIPPED_SUBTREES:
            self._raw(raw, atomic=True)
            self._skip += 1
            return
        if self._skip:
            self._raw(raw, atomic=True)
            return
        if tag == "img":
            alt = next((value or "" for name, value in attrs if name == "alt"), "")
            self._raw(raw, html.unescape(alt), atomic=True)
            return
        if tag in NARRATED_BLOCKS:
            block = _Block(tag, open_raw=raw, in_quote=self._quoted > 0)
            self._emit(_Piece("", child=block, atomic=True, depth=self._depth))
            self._open.append(block)
            if self._scope is None or self._scope_at is not None:
                self.blocks.append(block)
            self._depth = 0
            return
        if tag in VOID_ELEMENTS:
            # A line break separates words. Without the space, "Line one.<br>
            # Line two." reads back as one run of characters and the
            # comparison fails on a page that is perfectly ordinary.
            self._raw(raw, " " if tag == "br" else "", atomic=True)
            return
        self._raw(raw, atomic=True, after=self._depth + 1)
        if tag == "body":
            self.body_piece = (self._open[-1].pieces if self._open else self.out)[-1]
        self._depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text() or f"<{tag}/>"
        if tag == "img" and not self._skip:
            alt = next((value or "" for name, value in attrs if name == "alt"), "")
            self._raw(raw, html.unescape(alt), atomic=True)
            return
        self._raw(raw, atomic=True)

    def handle_endtag(self, tag: str) -> None:
        raw = f"</{tag}>"
        if tag == "blockquote":
            self._quoted = max(0, self._quoted - 1)
        if tag not in VOID_ELEMENTS:
            leaving_hidden = self._hidden_at == self._stack
            if self._scope_at == self._stack:
                self._scope_at = None
            self._stack = max(0, self._stack - 1)
            if leaving_hidden:
                self._hidden_at = None
                self._raw(raw, atomic=True)
                return
        if self._hidden_at is not None:
            self._raw(raw, atomic=True)
            return
        if tag in SKIPPED_SUBTREES:
            self._skip = max(0, self._skip - 1)
            self._raw(raw, atomic=True)
            return
        if self._skip:
            self._raw(raw, atomic=True)
            return
        if tag in NARRATED_BLOCKS and self._open and self._open[-1].tag == tag:
            self._open.pop().close_raw = raw
            self._depth = 0
            return
        if tag in VOID_ELEMENTS:
            self._raw(raw, atomic=True)
            return
        self._raw(raw, atomic=True, after=max(0, self._depth - 1))
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip or self._hidden_at is not None:
            self._raw(data, atomic=True)
            return
        # Tildes are markup this renderer leaves behind; they are emitted as
        # they stand but must not count as words.
        self._raw(data, _TILDES.sub("", data))

    def handle_entityref(self, name: str) -> None:
        self._raw(f"&{name};", html.unescape(f"&{name};"), atomic=True)

    def handle_charref(self, name: str) -> None:
        self._raw(f"&#{name};", html.unescape(f"&#{name};"), atomic=True)

    def handle_comment(self, data: str) -> None:
        self._raw(f"<!--{data}-->", atomic=True)

    def handle_decl(self, decl: str) -> None:
        self._raw(f"<!{decl}>", atomic=True)

    def handle_pi(self, data: str) -> None:
        self._raw(f"<?{data}>", atomic=True)

    def unknown_decl(self, data: str) -> None:
        self._raw(f"<![{data}]>", atomic=True)


def _walk(body_html: str, scope: str | None = None) -> _PageWalker:
    """Parse a rendered page into blocks and pieces."""
    walker = _PageWalker(scope)
    walker.feed(body_html)
    walker.close()
    return walker


def page_blocks(body_html: str, *, scope: str | None = None) -> list[_Block]:
    """The narrated blocks of a rendered page that show words, in reading order."""
    return [block for block in _walk(body_html, scope).blocks if block.visible]


def page_sentences(body_html: str, *, split, scope: str | None = None) -> list[str]:
    """Every sentence the page shows, in reading order.

    Separate from :func:`wrap_sentences` so the agreement between a page and
    its narration can be checked -- in a test, or before a build commits to
    narrating a post -- without producing any markup.
    """
    return [
        sentence
        for block in page_blocks(body_html, scope=scope)
        for sentence in split(block.visible)
    ]


# ── Matching cues to sentences ─────────────────────────────────────────────


def _unframe(text: str, opening: str, closing: str) -> str | None:
    """A cue's text as the page shows it, or ``None`` if the page never shows it.

    The narration's quotation framing is the only thing standing between the
    two: ``Quote:`` is spoken before a quoted block and ``End quote.`` after
    it, and neither is on the page.
    """
    stripped = " ".join(text.split())
    if stripped == closing:
        return None
    if stripped.startswith(opening):
        return stripped[len(opening):].strip()
    return stripped


def align(blocks: list[_Block], cues: list[VttCue], *, split,
          opening: str, closing: str) -> list[list[list[VttCue]]]:
    """Match each block's sentences to the cues that speak them.

    Returns
    -------
    list of list of list of VttCue
        Per block, per sentence, the cues that speak it -- normally exactly
        one, and more when the narration added framing words of its own.

    Raises
    ------
    ReadAlongMismatch
        If the page's sentences are not the narration's sentences. The
        message names the first one that differs, because "they diverged
        somewhere" is not actionable.
    """
    assignments: list[list[list[VttCue]]] = []
    position = 0
    numbered = 0
    reading: list[VttCue] | None = None

    def _absorb_framing() -> None:
        """Hand a framing cue to whatever sentence is being read."""
        nonlocal position
        while position < len(cues) and _unframe(cues[position].text, opening, closing) is None:
            if reading is not None:
                reading.append(cues[position])
            position += 1

    for block in blocks:
        per_sentence: list[list[VttCue]] = []
        for sentence in split(block.visible):
            _absorb_framing()
            spoken = (
                _unframe(cues[position].text, opening, closing)
                if position < len(cues)
                else None
            )
            if spoken != sentence:
                heard = (
                    repr(cues[position].text) if position < len(cues)
                    else "(nothing left in the audio)"
                )
                raise ReadAlongMismatch(
                    f"the page and the narration disagree at sentence {numbered}: "
                    f"page says {sentence!r}, audio says {heard}. "
                    f"The narration has {len(cues)} cues."
                )
            reading = [cues[position]]
            per_sentence.append(reading)
            position += 1
            numbered += 1
        assignments.append(per_sentence)

    _absorb_framing()
    if position != len(cues):
        raise ReadAlongMismatch(
            f"the narration has {len(cues) - position} cue(s) the page shows no sentence "
            f"for, starting with {cues[position].text!r}. "
            f"The page has {numbered} sentences."
        )
    return assignments


# ── Wrapping ───────────────────────────────────────────────────────────────


def _render(pieces: list[_Piece], wrapped: dict[int, str]) -> str:
    """Serialise pieces, replacing each nested block with its wrapped form."""
    out: list[str] = []
    for piece in pieces:
        if piece.child is None:
            out.append(piece.raw)
            continue
        block = piece.child
        out.append(block.open_raw)
        out.append(wrapped.get(id(block), _render(block.pieces, wrapped)))
        out.append(block.close_raw)
    return "".join(out)


def _visible_count(text: str) -> int:
    """Characters a comparison can see: no whitespace, no leftover tildes."""
    return sum(1 for char in text if not char.isspace() and char != "~")


def _cut(piece: _Piece, needed: int) -> tuple[_Piece, _Piece | None, int]:
    """Cut a text piece after ``needed`` visible characters.

    Returns the part that closes the current sentence, the remainder (or
    ``None`` when the piece is used up), and how many visible characters were
    taken. Atomic pieces are never cut: they go whole or not at all.
    """
    counted = _visible_count(piece.visible)
    if piece.atomic or counted <= needed:
        return piece, None, counted

    taken = 0
    cut = len(piece.raw)
    for index, char in enumerate(piece.raw):
        if taken == needed:
            cut = index
            break
        if not char.isspace() and char != "~":
            taken += 1
    head, tail = piece.raw[:cut], piece.raw[cut:]
    return (
        _Piece(head, _TILDES.sub("", head), depth=piece.depth, after=piece.after),
        _Piece(tail, _TILDES.sub("", tail), depth=piece.depth, after=piece.after),
        taken,
    )


def _span_runs(taken: list[_Piece]) -> list[tuple[bool, list[_Piece]]] | None:
    """Split a sentence's pieces into the runs a span can legally wrap.

    Usually there is one run and it is the whole sentence, markup and all.
    The exception is a sentence that crosses a boundary between elements. A
    bibliography entry ends ``…</cite> <span class="note">Keeps a memory…``
    with no full stop in between, so what a reader hears as one sentence runs
    out of the citation and into the note; and ``A <em>sentence that. Ends</em>
    here.`` puts one ``<em>`` across two of them. No single element can hold
    either -- a span cannot close a tag it did not open -- so the sentence is
    wrapped in *several*, which carry the same cue and light up together.

    That is a capability, not a compromise: the spans still cover exactly the
    sentence's own words, which is the whole promise. What is refused is a
    split that would leave some of those words outside every span, because a
    highlight that quietly drops half a sentence is the wrongness this module
    exists to prevent.

    Returns
    -------
    list of (bool, list of _Piece), or None
        ``True`` for a run to wrap, ``False`` for pieces to emit untouched,
        in document order. ``None`` when no split covers every word.
    """
    base = taken[0].depth
    if (
        taken[-1].after == base
        and all(piece.depth >= base and piece.after >= base for piece in taken)
    ):
        # The ordinary case, and the one every Markdown page takes.
        return [(True, taken)]

    out: list[tuple[bool, list[_Piece]]] = []
    pending = list(taken)
    while pending:
        # A tag shows no words, so it cannot decide the depth a span lives
        # at: it is emitted exactly where the page already had it. Whitespace
        # between two elements is skipped for the same reason -- a span around
        # a space highlights nothing.
        if _visible_count(pending[0].visible) == 0:
            out.append((False, [pending.pop(0)]))
            continue
        current = pending[0].depth
        # The longest prefix that never leaves the element the run starts in,
        # trimmed back to where it closes everything it opened.
        end = 1
        while end < len(pending) and pending[end].depth >= current \
                and pending[end].after >= current:
            end += 1
        run = pending[:end]
        while run and run[-1].after != current:
            run.pop()
        if not run:
            out.append((False, [pending.pop(0)]))
            continue
        out.append((True, run))
        # Whatever was trimmed stays in `pending` and is reconsidered: it is
        # the start of the next run, not something to drop.
        del pending[:len(run)]

    spilled = any(
        not is_span and any(_visible_count(piece.visible) for piece in pieces)
        for is_span, pieces in out
    )
    return None if spilled or not any(is_span for is_span, _ in out) else out


def _wrap_block(block: _Block, per_sentence: list[list[VttCue]], wrapped: dict[int, str],
                *, split) -> str:
    """Wrap one block's sentences, keeping the inline markup it already has."""
    queue = list(block.pieces)
    out: list[str] = []

    for sentence, cues in zip(split(block.visible), per_sentence):
        needed = _visible_count(sentence)
        # A nested block before the sentence's first word stays outside the
        # span: one that opened on a nested list would highlight every item
        # of it for the sake of one. Inline markup is the opposite case --
        # ``<strong>`` opening the sentence belongs *inside*, or the span
        # would close the tag it never opened.
        while queue and queue[0].child is not None:
            out.append(_render([queue.pop(0)], wrapped))
        taken: list[_Piece] = []
        while needed > 0 and queue:
            head, tail, got = _cut(queue[0], needed)
            taken.append(head)
            if tail is None:
                queue.pop(0)
            else:
                queue[0] = tail
            needed -= got
        if not taken:
            continue
        # Swallow the tags that close what the sentence opened: a heading
        # that is entirely a link stops on the link text, one piece short of
        # its own ``</a>``. Kept only if it balances the run, because the next
        # tag along may be an *opening* one, which would leave the span worse
        # off than it started.
        opened_at = taken[0].depth
        if taken[-1].after != opened_at:
            held = len(taken)
            while taken[-1].after != opened_at and queue and queue[0].child is None \
                    and _visible_count(queue[0].visible) == 0:
                taken.append(queue.pop(0))
            if taken[-1].after != opened_at:
                queue[:0] = taken[held:]
                del taken[held:]
        runs = _span_runs(taken)
        if runs is None:
            raise ReadAlongMismatch(
                f"the sentence {sentence!r} opens and closes at different inline-markup "
                "depths, so a span around it would cross an element. Emphasis that "
                "straddles a sentence boundary cannot be highlighted sentence by "
                "sentence; rephrase the source, or narrow --scope to leave it out."
            )
        cue = cues[0]
        # ``data-ra-cue`` is written only when the sentence needed more than
        # one span, because it costs bytes on every sentence of every page and
        # earns them on very few. The id stays on the first run: it is where
        # the sentence starts, and what the player scrolls to.
        spans = sum(1 for is_span, _ in runs if is_span)
        marker = f' data-ra-cue="{cue.index}"' if spans > 1 else ""
        first = True
        for is_span, pieces in runs:
            if not is_span:
                out.append(_render(pieces, wrapped))
                continue
            identity = f' id="ra-{cue.index}"' if first else ""
            out.append(
                f'<span class="{SENTENCE_CLASS}"{identity}{marker} '
                f'data-start="{cue.start_seconds:.3f}">'
                + _render(pieces, wrapped)
                + "</span>"
            )
            first = False
    out.append(_render(queue, wrapped))
    return "".join(out)


def wrap_sentences(body_html: str, cues: list[VttCue], *, split,
                   opening: str, closing: str, scope: str | None = None) -> str:
    """Wrap each narrated sentence in a span the highlight can find.

    Parameters
    ----------
    body_html : str
        Rendered page body.
    cues : list of VttCue
        What the narration actually said, in order.
    split : callable
        ``_narrate.split_sentences``. Passed in rather than imported so this
        module stays testable on its own and so there is visibly *one*
        splitter rather than two that happen to agree today.
    opening, closing : str
        ``_narrate.QUOTE_OPENING`` and ``_narrate.QUOTE_CLOSING`` -- the words
        the narration says around a quotation and the page does not show.
        Passed in for the same reason as the splitter.

    Returns
    -------
    str
        The body with every narrated sentence wrapped.

    Raises
    ------
    ReadAlongMismatch
        If the page's sentences are not the narration's sentences.
    """
    walker = _walk(body_html, scope)
    blocks = [block for block in walker.blocks if block.visible]
    assignments = align(blocks, cues, split=split, opening=opening, closing=closing)

    # Innermost first, so a parent's render finds its children already
    # wrapped rather than re-wrapping them.
    wrapped: dict[int, str] = {}
    for block, per_sentence in reversed(list(zip(blocks, assignments))):
        wrapped[id(block)] = _wrap_block(block, per_sentence, wrapped, split=split)
    return _render(walker.out, wrapped)


_HEAD_CLOSE = re.compile(r"</head\s*>", re.I)


def inject_into_page(html: str, cues: list[VttCue], *, split, opening: str, closing: str,
                     scope: str | None = None, head: str = "", player: str = "") -> str:
    """Add a read-along to a page that already exists.

    The counterpart to building a page from Markdown: here the document is
    the input, and it comes back with its sentences wrapped, the stylesheet
    and module in its ``<head>``, and the player at the top of the article.
    Everything else is returned byte for byte -- the page is rebuilt from a
    parse of itself, so a hand-written document keeps its own markup,
    attribute order and entities.

    This is the case the feature is for. A page that was never Markdown is a
    page nobody can regenerate, which is exactly the page that most needs an
    accessibility pass it can receive without being rewritten.

    Parameters
    ----------
    html : str
        The whole document.
    cues : list of VttCue
        What the narration said, in order.
    split : callable
        ``_narrate.split_sentences``.
    opening, closing : str
        ``_narrate.QUOTE_OPENING`` / ``QUOTE_CLOSING``.
    scope : str, optional
        ``article``, ``#id`` or ``.class`` -- the element to read. Without
        it the whole document is read, header and footer included, which is
        rarely what a reader asked for.
    head : str
        Markup for the document head, usually the stylesheet and module
        links. Placed before ``</head>``, or at the very top when the input
        is a fragment with no head at all.
    player : str
        The player markup, placed immediately after the scope element's
        opening tag -- top of the article, which is this skill's placement
        rule -- or after ``<body>`` when there is no scope.

    Returns
    -------
    str
        The page, with the read-along in it.
    """
    walker = _walk(html, scope)
    blocks = [block for block in walker.blocks if block.visible]
    assignments = align(blocks, cues, split=split, opening=opening, closing=closing)

    wrapped: dict[int, str] = {}
    for block, per_sentence in reversed(list(zip(blocks, assignments))):
        wrapped[id(block)] = _wrap_block(block, per_sentence, wrapped, split=split)

    if player:
        anchor = walker.scope_piece or walker.body_piece
        if anchor is None:
            raise ReadAlongMismatch(
                "nowhere to put the player: the page has no <body> and no element "
                f"matching {scope!r}. Pass a scope that the page actually contains."
            )
        # Mutating the piece rather than the rebuilt string: the piece is the
        # one place that is certainly this element's start tag, where a
        # pattern over the output would have to guess among several.
        anchor.raw += "\n" + player
    out = _render(walker.out, wrapped)

    if head:
        if _HEAD_CLOSE.search(out):
            out = _HEAD_CLOSE.sub(lambda m: head + "\n" + m.group(0), out, count=1)
        else:
            out = head + "\n" + out
    return out


# ── Wiring a page to a narration run ───────────────────────────────────────

#: Wording for the player's label, which is the accessible name of the audio
#: element. No default: a language this project has not been taught is worth
#: seeing, not worth serving in English.
PLAYER_LABELS: dict[str, str] = {
    "en": "Listen to this page",
    "fr": "Écouter cette page",
}

#: Files that drive the highlight, copied next to the page. Linked rather
#: than inlined so a reader's browser caches them once for a whole site.
ASSET_FILES: tuple[str, ...] = ("readalong.css", "readalong.js")


def assets_dir() -> Path:
    """Where the stylesheet and module that drive the highlight live."""
    return Path(__file__).resolve().parent.parent / "assets" / "readalong"


def player_label(lang: str) -> str:
    """The player's accessible name in `lang`, or a refusal naming the gap."""
    label = PLAYER_LABELS.get(lang)
    if label is None:
        raise ReadAlongMismatch(
            f"no read-along player wording for language {lang!r}; add it to "
            "PLAYER_LABELS rather than labelling a French page in English"
        )
    return label


def narration_sources(narration_dir: Path, stem: str) -> tuple[Path, Path] | None:
    """The audio file and cue file for one page, if a narration ran.

    Returns ``None`` when there is nothing to attach, which is the ordinary
    case: most pages of a site are not narrated, and a missing recording is
    not an error.
    """
    cues = narration_dir / "narration.vtt"
    if not cues.is_file():
        return None
    audio = next(
        (
            candidate
            for suffix in AUDIO_TYPES
            for candidate in [narration_dir / f"{stem}{suffix}"]
            if candidate.is_file()
        ),
        None,
    )
    return None if audio is None else (audio, cues)


def copy_assets(out_dir: Path) -> None:
    """Put the stylesheet and module next to the page that links them."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        shutil.copyfile(assets_dir() / name, out_dir / name)


def head_markup() -> str:
    """The two links a read-along page needs in its document head."""
    return (
        '  <link rel="stylesheet" href="readalong.css">\n'
        '  <script type="module" src="readalong.js"></script>'
    )


def href_from(path: Path, page_dir: Path) -> str:
    """`path` as the page's own HTML would reference it.

    Relative, so the output can be moved or served from a sub-path without a
    single link being rewritten.
    """
    return os.path.relpath(path.resolve(), page_dir.resolve()).replace(os.sep, "/")


def page_words(body_html: str, *, scope: str | None = None) -> list[str]:
    """The words the page shows, for a reading-time estimate.

    Counted from the same blocks the narration was built from, so the two
    figures on the page describe the same text: anything skipped by one --
    code, tables -- is skipped by both.
    """
    return [
        word
        for block in page_blocks(body_html, scope=scope)
        for word in block.visible.split()
    ]


def spoken_seconds(vtt_text: str) -> float:
    """How long the narration runs, read off its last cue.

    Measured rather than estimated: the timeline counted samples as it laid
    the audio out, so the end of the final cue *is* the end of the recording.
    """
    cues = parse_vtt(vtt_text)
    return cues[-1].end_seconds if cues else 0.0


def player_html(*, audio_src: str, vtt_src: str, label: str, lang: str) -> str:
    """The audio player, with its cue track.

    ``kind="metadata"`` rather than ``"captions"``: these cues drive a
    highlight, they are not a caption overlay, and a browser showing them as
    subtitles over an audio element would be noise. The same file *is* served
    as captions elsewhere; what changes is the role it is given here.

    Raises
    ------
    ReadAlongMismatch
        If the audio file's extension is not one of :data:`AUDIO_TYPES`.
        Declaring the wrong type is a file the browser declines to play, and
        guessing is how that happens quietly.
    """
    suffix = Path(audio_src).suffix.lower()
    audio_type = AUDIO_TYPES.get(suffix)
    if audio_type is None:
        raise ReadAlongMismatch(
            f"no audio type known for {suffix or audio_src!r}; add it to AUDIO_TYPES "
            f"rather than letting the page declare the wrong one. "
            f"Known: {', '.join(sorted(AUDIO_TYPES))}."
        )
    return (
        '<div class="ra-player" data-readalong>\n'
        f"  <p id=\"ra-label\">{html.escape(label)}</p>\n"
        '  <audio controls preload="none" aria-labelledby="ra-label" '
        'data-ra-audio>\n'
        f'    <source src="{html.escape(audio_src)}" type="{audio_type}">\n'
        f'    <track kind="metadata" src="{html.escape(vtt_src)}" '
        f'srclang="{html.escape(lang)}" label="Sentences" default>\n'
        "  </audio>\n"
        "</div>"
    )


#: Silent reading speed for prose, in words per minute. 200 is the low end of
#: the usual 200-250 range for adult readers on screen, chosen because an
#: estimate that runs slightly long is a promise kept and one that runs short
#: is a reader who stopped trusting the number.
READING_WORDS_PER_MINUTE: int = 200

#: Wording, per language. Not a translation table with a default: a missing
#: language should be visible, not silently served English.
_READING_PHRASES: dict[str, dict[str, str]] = {
    "en": {
        "read": "{minutes} min read",
        "listen": "{minutes} min listen",
        "join": " · ",
    },
    "fr": {
        "read": "{minutes} min de lecture",
        "listen": "{minutes} min d’écoute",
        "join": " · ",
    },
}


def _minutes(seconds: float) -> int:
    """Whole minutes, never zero -- "0 min read" tells a reader nothing."""
    return max(1, round(seconds / 60.0))


def reading_meta_html(*, words: int, spoken_seconds: float, lang: str) -> str:
    """Reading time beside listening time.

    Two numbers of different kinds, which is the interesting part. The
    reading time is an *estimate* from a word count and an assumed speed. The
    listening time is **measured**: the narration's own length, down to the
    sample, because the timeline counted every sentence and every silence as
    it laid them out. They are shown together and they will not agree --
    speech is slower than reading -- and that is information rather than an
    error: a reader deciding between the two deserves both figures.

    Marked up with ``<time datetime="PT…M">`` so the duration is machine
    readable, and the whole line is given ``role="doc-tip"``-free plain text:
    it is not a control, not a landmark, and announcing it as either would
    add noise for the screen-reader user this feature is careful not to
    disturb.
    """
    phrases = _READING_PHRASES.get(lang)
    if phrases is None:
        raise ReadAlongMismatch(
            f"no reading-time wording for language {lang!r}; add it to "
            "_READING_PHRASES rather than falling back to English"
        )
    read_minutes = _minutes(words / float(READING_WORDS_PER_MINUTE) * 60.0)
    listen_minutes = _minutes(spoken_seconds)
    return (
        '<p class="ra-meta">'
        f'<time datetime="PT{read_minutes}M">'
        f"{html.escape(phrases['read'].format(minutes=read_minutes))}</time>"
        f"{html.escape(phrases['join'])}"
        f'<time datetime="PT{listen_minutes}M">'
        f"{html.escape(phrases['listen'].format(minutes=listen_minutes))}</time>"
        "</p>"
    )
