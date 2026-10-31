"""
The films' captions are read by the auditor the suite sells.

The defect this is shaped after
--------------------------------
`sprezzature-audio` ships `sprezzature-audio-audit`, which measures a caption
track against the Netflix Timed Text Style Guide: 42 characters to a line, two
lines to a cue, 17 characters a second. The `audio` film puts **42** on screen
as a number the suite stands behind.

On 2026-10-29 every one of the twenty-two shipped tracks failed that auditor.
184 cues, 287 findings, 177 of them a line over budget, with individual lines
reaching 90 characters.

The cause was not a wrong limit, it was an unapplied one. `make_captions.py`
held `LINE_LIMIT = 58`, sourced to nothing, and the only function reading it
stopped being called on 2026-10-26 when the narration began writing its own
WebVTT. From that morning the cue text was the script line, as written, with
no wrapping anywhere on the path. Nothing failed, because nothing looked.

So this test is the thing that looks, and it deliberately does not re-implement
the rules: it calls `sprezzature_audio.audit_cues`, the same function the
command line calls. A guard that carries its own copy of a standard is a
second opinion that drifts from the first, which is the defect one layer up.

The two kinds of finding, and why both are kept
-----------------------------------------------
`line-too-wide` is a *wrapping* fault and is repaired mechanically, by putting
a newline where the player would otherwise guess.

`cue-too-fast` is a *script* fault and cannot be repaired by wrapping: a
sentence of 158 characters spoken in three seconds is unreadable at any
width. The repair is to write a shorter sentence, or to give it more room.
Both are failures here, because a caption nobody can read in time fails the
reader exactly as thoroughly as one that runs off the screen.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "web" / "video"


def _tracks() -> list[Path]:
    """Every caption track that ships with the site."""
    return sorted(VIDEO.glob("*.vtt"))


def test_there_are_tracks_to_audit() -> None:
    """A precondition that cannot quietly become false.

    Without this, a renamed directory turns the audit below into a loop over
    nothing, and an empty loop passes. The films are eleven in two languages.
    """
    assert VIDEO.is_dir(), f"no caption directory at {VIDEO}"
    assert len(_tracks()) >= 22, (
        f"expected at least 22 caption tracks, found {len(_tracks())}"
    )


def test_every_caption_track_is_readable() -> None:
    """Width, reading speed and cue length, measured by the suite's own tool."""
    audio = pytest.importorskip(
        "sprezzature_audio",
        reason="sprezzature-audio absent: the auditor is the thing under test",
    )

    failures: list[str] = []
    cues_seen = 0
    for track in _tracks():
        # `parse`, not `parse_caption_cues`: the two are different readers and
        # only one of them feeds the auditor. `parse_caption_cues` returns
        # dicts for the speaker-attribution path; `parse` returns the `Cue`
        # objects `audit_cues` reads, which is what the command line uses.
        cues = audio.parse(track.read_text(encoding="utf-8"))
        cues_seen += len(cues)
        for finding in audio.audit_cues(cues):
            failures.append(
                f"{track.name} cue {finding.cue} @ {finding.start:7.3f}s "
                f"{finding.rule}: {finding.message}"
            )

    assert cues_seen, "the tracks parsed to no cues at all"
    assert not failures, (
        f"{len(failures)} finding(s) across {len(_tracks())} caption track(s), "
        f"{cues_seen} cue(s). These are the films' own captions failing the "
        f"auditor this suite ships and quotes on screen. Re-narrate with "
        f"`python3 brag-output/narrate_films.py`; a `cue-too-fast` finding is "
        f"a sentence to shorten, not a wrap to fix.\n  "
        + "\n  ".join(failures[:40])
        + (f"\n  ... and {len(failures) - 40} more" if len(failures) > 40 else "")
    )
