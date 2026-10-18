"""
_vtt: one WebVTT, read and written in one place.

This suite had four WebVTT writers and two readers. Three writers lived in
this package — ``captions_from_whisper``, ``caption_diarize`` and
``translate_captions`` — and a fourth in ``sprezzature-publish``'s narration
engine, which emits the same format for the opposite reason: captions make
sound readable, narration makes text audible, and both land as a timed text
track beside an audio file.

Four implementations of one format is four places for a timestamp to be
rounded differently, and the differences were not cosmetic. They are kept
here rather than flattened, because each one exists for a reason:

* **Voice tags.** ``caption_diarize`` emits ``<v Name>`` once speakers are
  attributed. ``translate_captions`` deliberately does not: W3C reserves
  voice tags for the same-language ``captions`` track, and a translated
  subtitle track is dialogue. Hence ``voices=False`` rather than a guess
  from whether a speaker happens to be set.
* **Identifiers.** The narration path writes each cue's segment index as the
  WebVTT identifier — the line before the timings — which is what lets a page
  highlight the right block without matching on text. Nothing else needs
  them, so an unset ``identifier`` emits nothing.
* **Line structure.** The older reader joined a cue's lines with a space.
  That is right for a merger and wrong for an auditor: ``audit_captions``
  checks line count and line width, and cannot do either on a cue whose
  lines have been glued together. So :func:`parse` keeps the newlines and
  the caller joins if it wants to.

Stdlib only, as every helper in this package is.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

#: ``HH:MM:SS.mmm --> HH:MM:SS.mmm``, with the hour optional and either
#: decimal separator, so one expression reads WebVTT and SubRip alike.
_TIME = r"(?:(?P<{p}h>\d+):)?(?P<{p}m>\d{{2}}):(?P<{p}s>\d{{2}})[.,](?P<{p}ms>\d{{3}})"
TIMESTAMP_RE = re.compile(
    _TIME.format(p="") + r"\s*-->\s*" + _TIME.format(p="e"),
)

#: A voice tag introducing a speaker: ``<v Ada Lovelace>Hello``.
VOICE_RE = re.compile(r"^<v\s+([^>]+)>\s*")

#: How a voice tag is written back out.
VOICE_CUE = "<v {name}>{text}"


@dataclass(frozen=True)
class Cue:
    """One timed piece of text.

    Attributes
    ----------
    start, end : float
        Seconds from the beginning of the media.
    text : str
        The caption. Newlines are significant: a renderer breaks lines where
        they are, and the audit rules count them.
    speaker : str or None
        Who is speaking, when that has been worked out. Written as a
        ``<v Name>`` tag only when the caller asks for voices.
    identifier : str or None
        The optional WebVTT cue identifier, written on the line before the
        timings. The narration path uses it to carry a segment index, so a
        page can follow along without matching on text.
    """

    start: float
    end: float
    text: str
    speaker: str | None = None
    identifier: str | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def lines(self) -> list[str]:
        """The cue's lines, as a renderer will break them."""
        return [line for line in self.text.splitlines() if line.strip()]

    def collapsed(self) -> Cue:
        """The same cue with its text on one line.

        A blank line ends a cue, so a hard-wrapped payload would split one
        cue into two. Callers that assemble text from a document rather than
        from a transcript want this before writing.
        """
        return replace(self, text=" ".join(self.text.split()))


def format_timestamp(seconds: float, *, srt: bool = False) -> str:
    """
    Format seconds as ``HH:MM:SS.mmm`` (WebVTT) or ``HH:MM:SS,mmm`` (SubRip).

    Negative input clamps to zero: a negative timestamp is never meaningful
    and a renderer's behaviour on one is undefined rather than obvious.
    """
    # Truncated, not rounded. Rounding up lets a cue claim to start before
    # the sample that actually starts it — half a millisecond early is still
    # early, and for narration the highlight then lands on a word the voice
    # has not reached. The narration path had worked this out and the caption
    # path had not; consolidating the two meant picking the one with a
    # reason, not the one that was written first.
    total_ms = max(0, int(seconds * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    separator = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def from_centiseconds(value: int) -> float:
    """Convert a pywhispercpp timestamp (10-ms units) to seconds."""
    return value / 100.0


def _seconds(hours: str | None, minutes: str, secs: str, millis: str) -> float:
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(secs) + int(millis) / 1000


def parse(text: str) -> list[Cue]:
    """
    Read a WebVTT or SubRip document into cues.

    Both formats are accepted because this package writes both, and a reader
    holding one has no reason to convert it before doing anything with it.

    A ``<v Name>`` tag is lifted into :attr:`Cue.speaker` rather than left in
    the text, so a caller that re-writes the cue does not double-tag it — and
    one that does not want voices simply never asks for them.

    Newlines inside a cue are preserved. Callers that want a single line call
    :meth:`Cue.collapsed`.
    """
    cues: list[Cue] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = TIMESTAMP_RE.match(lines[index].strip())
        if not match:
            index += 1
            continue
        groups = match.groupdict()
        start = _seconds(groups["h"], groups["m"], groups["s"], groups["ms"])
        end = _seconds(groups["eh"], groups["em"], groups["es"], groups["ems"])

        # A WebVTT identifier sits on the line before the timings; so does a
        # SubRip sequence number. Both are the cue's name, and neither is its
        # text.
        identifier: str | None = None
        if index > 0:
            previous = lines[index - 1].strip()
            if previous and not TIMESTAMP_RE.match(previous):
                identifier = previous

        cursor = index + 1
        body: list[str] = []
        speaker: str | None = None
        while cursor < len(lines) and lines[cursor].strip() != "":
            line = lines[cursor]
            voice = VOICE_RE.match(line.strip())
            if voice is not None:
                speaker = voice.group(1).strip()
                line = VOICE_RE.sub("", line.strip())
            body.append(line.rstrip())
            cursor += 1

        cues.append(Cue(
            start=start,
            end=end,
            text="\n".join(body).strip(),
            speaker=speaker,
            identifier=identifier,
        ))
        index = cursor + 1

    cues.sort(key=lambda cue: (cue.start, cue.end))
    return cues


def write_vtt(cues: list[Cue], *, voices: bool = True) -> str:
    """
    Render cues as a WebVTT document.

    Parameters
    ----------
    cues : list of Cue
        Timed text. Cues with no text are dropped: a timed blank box is on
        screen for its full duration and says nothing.
    voices : bool, optional
        Write ``<v Name>`` tags for cues that carry a speaker. Default
        ``True``. Pass ``False`` for a translated subtitle track: W3C
        reserves voice tags for the same-language ``captions`` track.

    Returns
    -------
    str
        A WebVTT document, ready to write to a ``.vtt`` file.
    """
    out: list[str] = ["WEBVTT", ""]
    for cue in cues:
        text = cue.text.strip()
        if not text:
            continue
        if cue.identifier:
            out.append(str(cue.identifier))
        out.append(
            f"{format_timestamp(cue.start)} --> {format_timestamp(cue.end)}"
        )
        out.append(
            VOICE_CUE.format(name=cue.speaker, text=text)
            if voices and cue.speaker else text
        )
        out.append("")
    return "\n".join(out)


def write_srt(cues: list[Cue]) -> str:
    """
    Render cues as a SubRip document.

    SubRip has no voice tags, so a speaker is written as a plain prefix —
    the convention every player renders and no player hides.
    """
    out: list[str] = []
    number = 1
    for cue in cues:
        text = cue.text.strip()
        if not text:
            continue
        out.append(str(number))
        out.append(
            f"{format_timestamp(cue.start, srt=True)} --> "
            f"{format_timestamp(cue.end, srt=True)}"
        )
        out.append(f"{cue.speaker}: {text}" if cue.speaker else text)
        out.append("")
        number += 1
    return "\n".join(out)
