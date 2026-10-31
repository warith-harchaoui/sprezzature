"""The shipped caption tracks are what the current cue rule produces.

The defect this guards, and why the auditor beside it is not enough.
--------------------------------------------------------------------
``tests/test_the_films_captions_pass_the_suites_own_auditor.py`` asks whether
the tracks can be *read*: 42 characters to a line, 17 a second, 7 seconds on
screen. It is the right question and it is not this one. A track can satisfy
every one of those limits and still not be what
``brag-output/make_captions.timed_cues`` emits today — a hand edit, a partial
re-emit, a rule that moved while the files did not. The auditor would pass it,
and the files would quietly stop being derived from anything.

That is the failure mode this repository keeps meeting. On the same day this
was written, ``web/img/figures/landscape-positioning.png`` turned out to be a
hand-made copy of a ``standpoint`` run from eleven weeks earlier that nothing
produced, and ``sprezzature-video`` was serving a 29-tool map from a commit
that had added the thirtieth. Both were readable. Both were wrong. The repair
in each case was the same: stop maintaining the copy and assert it is the
output, byte for byte.

So these files are tracked, and this says they are *taken* rather than kept.

Why the tracks are in the clone at all.
---------------------------------------
Until 2026-10-31 every file under ``web/video/`` was ignored, for the reason
the 258 MB of H.264 gives. The captions went with them, and the consequence was
that the auditor test could not run in CI: it failed on its own precondition,
an empty directory, so the one guard on a number the ``audio`` film puts on
screen never ran anywhere but a developer's laptop. 88 KB of text now ships.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAG = REPO_ROOT / "brag-output"
VIDEO = REPO_ROOT / "web" / "video"
REWRITER = BRAG / "rewrite_cues.py"

#: The films are eleven, in two languages. Stated so a renamed directory or a
#: half-finished copy cannot turn the parametrisation below into no tests at
#: all -- an empty loop passes, which is how the auditor beside this one spent
#: its whole life in CI.
EXPECTED_TRACKS = 22


def _tracks() -> list[Path]:
    return sorted(VIDEO.glob("*.vtt"))


@pytest.fixture(scope="module")
def rewriter() -> Any:
    """``brag-output/rewrite_cues.py``, loaded by path.

    ``brag-output`` is a directory of scripts rather than a package, and the
    module's own name carries a hyphenated sibling it imports, so it is loaded
    the way the other film tests load their subjects.
    """
    pytest.importorskip(
        "sprezzature_audio",
        reason="sprezzature-audio writes and reads the cues; without it there "
        "is no rule to compare against",
    )
    spec = importlib.util.spec_from_file_location("rewrite_cues", REWRITER)
    assert spec and spec.loader, f"cannot load {REWRITER}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["rewrite_cues"] = module
    spec.loader.exec_module(module)
    return module


def test_the_tracks_are_all_there() -> None:
    """A precondition that cannot quietly become false."""
    assert VIDEO.is_dir(), f"no caption directory at {VIDEO}"
    found = _tracks()
    assert len(found) >= EXPECTED_TRACKS, (
        f"expected at least {EXPECTED_TRACKS} caption tracks under "
        f"{VIDEO.relative_to(REPO_ROOT)}, found {len(found)}"
    )


def test_the_tracks_are_tracked_by_git() -> None:
    """And they are in the clone, which is the point of the 2026-10-31 change.

    Asserted on git's own index rather than on the ignore file: a later edit to
    ``.gitignore`` that re-excludes them would leave every other test in this
    file passing on a developer's machine and skipping in CI, which is exactly
    the state this change was made to end.
    """
    import subprocess

    listed = subprocess.run(
        ["git", "ls-files", "web/video"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    vtt = [name for name in listed if name.endswith(".vtt")]
    assert len(vtt) >= EXPECTED_TRACKS, (
        f"git tracks {len(vtt)} caption track(s) under web/video, expected at "
        f"least {EXPECTED_TRACKS}. A clone cannot audit captions it does not "
        f"have, and that is how this guard's neighbour came to never run in CI."
    )
    # The voice stamps are tracked too, and for the same reason: they are what
    # `test_no_film_is_voiced_by_a_retired_engine.py` reads, and that guard was
    # skipping on an empty directory until the tracks arrived.
    heavy = [
        name
        for name in listed
        if not name.endswith(".vtt") and not name.endswith(".voice.json")
    ]
    assert not heavy, (
        "web/video should carry the caption tracks and their voice stamps and "
        "nothing else; git also "
        f"tracks {', '.join(heavy[:5])}. The films and their posters are "
        "render output, 258 MB of it, and do not belong in a clone."
    )


def test_every_track_is_byte_for_byte_what_the_rule_emits(rewriter: Any) -> None:
    """Re-emitting a shipped track returns the shipped bytes.

    It holds the wrapping, the cue end times, the identifiers and the timestamp
    format at once, because all four come out of one function, and it needs no
    copy of any of their rules here -- a guard carrying its own copy of the
    thing it checks is the defect one layer up.

    What it does and does not catch, measured rather than assumed.
    -------------------------------------------------------------
    The rewriter's input is the track, so this asserts that the track is a
    **fixed point of the rule**, which is narrower than "derived from the
    script" and the difference is worth knowing:

    * **Caught**: the rule moved and the tracks were not re-emitted. Dropping
      ``READING_TARGET_CPS`` from 16 to 14 fails this test on every track, and
      fails nothing else in the suite -- the captions stay perfectly readable,
      so the auditor beside this one goes on passing. This is the drift the
      test exists for.
    * **Not caught**: a hand edit the rule overwrites. Moving one cue's end
      from ``06.500`` to ``06.499`` passes, because the rule recomputes that
      end from the reading speed and puts it back. The sabotage is repaired
      rather than reported, which is an acceptable outcome for a timing but
      not something to claim as detection.
    * **Caught elsewhere, on purpose**: an edit to a cue's *words*. The
      rewriter keeps the text it reads, so this test is blind to it, and
      ``test_no_film_is_voiced_by_a_stale_track.py`` is not -- it compares
      every cue against the narration script in ``make_captions.FILMS``.
      Verified by changing one word in ``ui.en``: that test fails, this one
      does not. Two guards, two questions, neither duplicating the other.
    """
    drifted: list[str] = []
    for track in _tracks():
        if track.read_text(encoding="utf-8") != rewriter.rewritten(track):
            drifted.append(track.name)
    assert not drifted, (
        f"{len(drifted)} caption track(s) are not what the current cue rule "
        f"emits: {', '.join(drifted)}.\n"
        f"Run `python3 brag-output/rewrite_cues.py` -- it re-emits the cues "
        f"from the track's own words and speech timings, and does not narrate "
        f"anything again."
    )


def test_re_emitting_twice_changes_nothing(rewriter: Any, tmp_path: Path) -> None:
    """The rule is idempotent, which is what makes the test above meaningful.

    Without idempotence a rule that wrapped an already-wrapped line, or
    extended an already-extended cue, would make the comparison above depend on
    how many times the rewriter had been run -- a guard that is a coin toss
    recorded in git.

    The second pass reads the **output** of the first, from a file of its own.
    Calling ``rewritten(track)`` twice on the shipped path would compare two
    reads of the same bytes and pass whatever the rule did, which is a test
    that tests nothing.
    """
    sample = _tracks()[:4]
    assert sample, "no tracks to re-emit"
    for track in sample:
        once = rewriter.rewritten(track)
        again = tmp_path / track.name
        again.write_text(once, encoding="utf-8")
        twice = rewriter.rewritten(again)
        assert twice == once, (
            f"{track.name}: re-emitting the rule's own output changes it, so "
            f"the shipped bytes depend on how often the rewriter was run"
        )
