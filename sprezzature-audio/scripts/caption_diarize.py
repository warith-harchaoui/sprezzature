#!/usr/bin/env python3
"""
caption_diarize
===============

Merge Whisper caption segments with Sortformer speaker turns to emit a
**speaker-labelled** WebVTT / SRT / plain-text transcript.

Inputs
------

* ``captions.vtt`` (or ``.srt``) from :mod:`captions_from_whisper`.
* ``diarization.json`` (turn list) from :mod:`diarize_from_nemo`.
* Optional ``speakers.json`` (id → name) from :mod:`identify_from_titanet`.

Output
------

* WebVTT with ``<v Speaker Name>`` voice cues per line.
* SRT with ``Speaker Name: text`` prefixes.
* Plain text with paragraph breaks on speaker change or long pause.

Merge rule
----------

For each caption cue ``[c_start, c_end]``, pick the diarization turn
whose overlap with the cue is greatest. On ties, prefer the turn whose
center is closer to the cue center. Cues with zero overlap (the
diarizer missed a stretch) fall back to the previous speaker's label.

Usage
-----
::

    # Speaker-labelled VTT from a captions file + a diarization JSON
    python caption_diarize.py \\
        --captions interview.vtt \\
        --diarization interview.diarization.json \\
        --out interview.speakers.vtt

    # Named speakers via a mapping file
    python caption_diarize.py \\
        --captions podcast.srt \\
        --diarization podcast.diarization.json \\
        --speakers podcast.speakers.json \\
        --format srt \\
        --out podcast.speakers.srt

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path as _PathHelper
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402

import click


#: Format of the ``<v ...>`` cue in WebVTT. WebVTT parsers strip the
#: markup when the reader lacks the voice-cue extension, so the readable
#: fallback is ``Speaker Name text``.
VTT_VOICE_CUE: str = "<v {name}>{text}"

#: Prefix used in the SRT output (no voice-cue extension in SRT).
SRT_SPEAKER_PREFIX: str = "{name}: {text}"

#: Duration threshold (seconds) beyond which the plain-text output inserts
#: a blank line between cues even for the same speaker.
LONG_PAUSE_SECONDS: float = 1.5


# ── VTT / SRT parsers (stdlib only) ────────────────────────────────────────

_TIMESTAMP_VTT = re.compile(
    r"^(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[.,](?P<ms>\d{3})\s*-->\s*"
    r"(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2})[.,](?P<ms2>\d{3})"
)


def _parse_timestamp(h: str, m: str, s: str, ms: str) -> float:
    """Return seconds from an ``HH:MM:SS.mmm`` field group."""
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _format_timestamp(t: float, srt: bool = False) -> str:
    """Format seconds as ``HH:MM:SS.mmm`` (VTT) / ``HH:MM:SS,mmm`` (SRT)."""
    total_ms = max(0, int(round(t * 1000)))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    sep = "," if srt else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def parse_caption_cues(text: str) -> List[Dict[str, Any]]:
    """Parse a WebVTT or SRT document into a flat list of caption cues.

    Parameters
    ----------
    text : str
        Contents of a ``.vtt`` or ``.srt`` file.

    Returns
    -------
    list of dict
        ``[{"start": float, "end": float, "text": str}, ...]`` sorted
        by ``start``.
    """
    cues: List[Dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = _TIMESTAMP_VTT.match(line)
        if not m:
            i += 1
            continue
        start = _parse_timestamp(m.group("h"), m.group("m"), m.group("s"), m.group("ms"))
        end = _parse_timestamp(m.group("h2"), m.group("m2"), m.group("s2"), m.group("ms2"))
        j = i + 1
        body_lines: List[str] = []
        while j < len(lines) and lines[j].strip() != "":
            # Strip any pre-existing <v ...> voice cue so the merger doesn't
            # double-tag.
            raw = re.sub(r"^<v\s+[^>]+>", "", lines[j]).strip()
            body_lines.append(raw)
            j += 1
        cues.append({"start": start, "end": end, "text": " ".join(body_lines).strip()})
        i = j + 1
    cues.sort(key=lambda c: (c["start"], c["end"]))
    return cues


# ── Merger ─────────────────────────────────────────────────────────────────

def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Return the overlap length in seconds of ``[a0, a1]`` and ``[b0, b1]``."""
    return max(0.0, min(a1, b1) - max(a0, b0))


def attribute_speakers(
    cues: List[Dict[str, Any]],
    turns: List[Dict[str, Any]],
    speaker_names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Attach a speaker label to every caption cue.

    Parameters
    ----------
    cues : list of dict
        Caption cues from :func:`parse_caption_cues`.
    turns : list of dict
        Diarization turns from :mod:`diarize_from_nemo`.
    speaker_names : dict of str to str, optional
        Optional mapping from anonymous speaker id to display name
        (from :mod:`identify_from_titanet`).

    Returns
    -------
    list of dict
        Cues augmented with a ``speaker`` key.
    """
    names = speaker_names or {}
    last_spk: Optional[str] = None
    out: List[Dict[str, Any]] = []
    for cue in cues:
        best_overlap = 0.0
        best_center = float("inf")
        best_spk: Optional[str] = None
        c_center = 0.5 * (cue["start"] + cue["end"])
        for t in turns:
            ov = _overlap(cue["start"], cue["end"], float(t["start"]), float(t["end"]))
            if ov <= 0.0:
                continue
            t_center = 0.5 * (float(t["start"]) + float(t["end"]))
            center_gap = abs(c_center - t_center)
            if ov > best_overlap or (ov == best_overlap and center_gap < best_center):
                best_overlap = ov
                best_center = center_gap
                best_spk = str(t["speaker"])
        if best_spk is None:
            best_spk = last_spk if last_spk is not None else "0"
        last_spk = best_spk
        display = names.get(best_spk, f"Speaker {int(best_spk) + 1}" if best_spk.isdigit() else best_spk)
        out.append({**cue, "speaker_id": best_spk, "speaker": display})
    return out


# ── Renderers ──────────────────────────────────────────────────────────────

def render_vtt(cues: List[Dict[str, Any]]) -> str:
    """Render speaker-attributed cues as a WebVTT document."""
    lines: List[str] = ["WEBVTT", ""]
    for cue in cues:
        if not cue["text"]:
            continue
        lines.append(f"{_format_timestamp(cue['start'])} --> {_format_timestamp(cue['end'])}")
        lines.append(VTT_VOICE_CUE.format(name=cue["speaker"], text=cue["text"]))
        lines.append("")
    return "\n".join(lines)


def render_srt(cues: List[Dict[str, Any]]) -> str:
    """Render speaker-attributed cues as a SubRip (SRT) document."""
    lines: List[str] = []
    idx = 1
    for cue in cues:
        if not cue["text"]:
            continue
        lines.append(str(idx))
        lines.append(
            f"{_format_timestamp(cue['start'], srt=True)} --> {_format_timestamp(cue['end'], srt=True)}"
        )
        lines.append(SRT_SPEAKER_PREFIX.format(name=cue["speaker"], text=cue["text"]))
        lines.append("")
        idx += 1
    return "\n".join(lines)


def render_text(cues: List[Dict[str, Any]]) -> str:
    """Render speaker-attributed cues as plain text with paragraph breaks."""
    out: List[str] = []
    prev_spk: Optional[str] = None
    prev_end: Optional[float] = None
    current: List[str] = []
    for cue in cues:
        if not cue["text"]:
            continue
        new_speaker = cue["speaker"] != prev_spk
        long_pause = prev_end is not None and cue["start"] - prev_end > LONG_PAUSE_SECONDS
        if new_speaker or long_pause:
            if current:
                out.append(" ".join(current))
                out.append("")
            current = [f"{cue['speaker']}: {cue['text']}"] if new_speaker else [cue["text"]]
        else:
            current.append(cue["text"])
        prev_spk = cue["speaker"]
        prev_end = cue["end"]
    if current:
        out.append(" ".join(current))
    return "\n".join(out) + "\n"


# ── CLI ────────────────────────────────────────────────────────────────────

@sprezzature_command(
    "sprezzature-audio-caption-diarize",
    help=(
        "Merge Whisper caption segments with Sortformer speaker turns; "
        "emit a speaker-labelled WebVTT / SRT / plain-text transcript."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-audio-caption-diarize --captions t.vtt --diarization t.diarization.json --out t.speakers.vtt\n"
        "  sprezzature-audio-caption-diarize --captions t.srt --diarization t.diarization.json \\\n"
        "      --speakers t.speakers.json --format srt --out t.speakers.srt\n"
    ),
)
@click.option("--captions", "captions_path", type=click.Path(path_type=Path), required=True,
              help="Path to a .vtt or .srt file from captions_from_whisper.")
@click.option("--diarization", "diarization_path", type=click.Path(path_type=Path), required=True,
              help="Path to a .diarization.json from diarize_from_nemo.")
@click.option("--speakers", "speakers_path", type=click.Path(path_type=Path), default=None,
              help="Optional .speakers.json from identify_from_titanet.")
@click.option("--format", "fmt", type=click.Choice(["vtt", "srt", "text"]), default="vtt",
              show_default=True, help="Output format.")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Output path. Default: sibling '<captions-stem>.speakers.<ext>'.")
def _cli(
    captions_path: Path,
    diarization_path: Path,
    speakers_path: Optional[Path],
    fmt: str,
    out: Optional[Path],
) -> int:
    """Click command body; returns an int exit code."""
    if not captions_path.is_file():
        click.echo(f"No such file: {captions_path}", err=True)
        return 1
    if not diarization_path.is_file():
        click.echo(f"No such file: {diarization_path}", err=True)
        return 1

    cues = parse_caption_cues(captions_path.read_text(encoding="utf-8"))
    turns = json.loads(diarization_path.read_text(encoding="utf-8"))
    speaker_names: Dict[str, str] = {}
    if speakers_path is not None and speakers_path.is_file():
        speaker_names = json.loads(speakers_path.read_text(encoding="utf-8"))

    attributed = attribute_speakers(cues, turns, speaker_names=speaker_names)

    renderers = {"vtt": render_vtt, "srt": render_srt, "text": render_text}
    payload = renderers[fmt](attributed)

    ext = "txt" if fmt == "text" else fmt
    out_path = out or Path(str(captions_path.with_suffix("")) + f".speakers.{ext}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    click.echo(f"→ Wrote {out_path}")
    speakers = sorted({c["speaker"] for c in attributed})
    click.echo(f"→ {len(attributed)} cue(s), {len(speakers)} speaker(s): {', '.join(speakers)}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Writes ``<stem>.speakers.<ext>`` by default."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
