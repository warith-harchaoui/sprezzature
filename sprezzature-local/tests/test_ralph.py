"""
test_ralph — unit tests for the Ralph loop and its prose specialisation.

All LLM calls are mocked; no live server is required.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

from unittest.mock import patch

from sprezzature_local.ralph import prose_loop, ralph_loop


# ---------------------------------------------------------------------------
# ralph_loop — generic driver
# ---------------------------------------------------------------------------

def test_ralph_loop_ships_on_first_verdict() -> None:
    """ralph_loop returns immediately when the first verdict says ship."""
    source, history = ralph_loop(
        "initial",
        render=lambda s: s.encode(),
        inspect=lambda _a: "looks good",
        apply_fix=lambda s, _c: s + "-fixed",
        verdict=lambda _c: {"ship": True, "score": 1.0, "blocking": []},
        max_iters=6,
    )
    assert source == "initial"
    assert len(history) == 1
    assert history[0][2]["ship"] is True


def test_ralph_loop_stops_on_noop_fix() -> None:
    """ralph_loop stops early when apply_fix returns the same source unchanged."""
    calls: list[int] = []

    def _apply(s: str, _c: str) -> str:
        calls.append(1)
        return s  # no change → loop should stop

    source, history = ralph_loop(
        "v0",
        render=lambda s: s.encode(),
        inspect=lambda _a: "needs work",
        apply_fix=_apply,
        verdict=lambda _c: {"ship": False, "score": 0.3, "blocking": ["something"]},
        max_iters=6,
    )
    # apply_fix called once; loop detected no-op and stopped
    assert len(calls) == 1
    assert source == "v0"


def test_ralph_loop_exhausts_budget() -> None:
    """ralph_loop iterates up to max_iters when the verdict never says ship."""
    counter = {"n": 0}

    def _apply(s: str, _c: str) -> str:
        counter["n"] += 1
        return s + f"-{counter['n']}"

    source, history = ralph_loop(
        "v0",
        render=lambda s: s.encode(),
        inspect=lambda _a: "still bad",
        apply_fix=_apply,
        verdict=lambda _c: {"ship": False, "score": 0.2, "blocking": ["x"]},
        max_iters=3,
    )
    assert len(history) == 3


def test_prose_loop_no_changes_needed() -> None:
    """prose_loop returns the original text when every seam is already clean."""
    clean_verdict = {"needs_fix": False, "reasons": []}

    with patch("sprezzature_local.ralph.llm.chat", return_value=clean_verdict):
        result = prose_loop(
            "Para one.\n\nPara two.\n\nPara three.",
            charter="Be concise.",
            max_passes=2,
        )

    # No edits made — output should rejoin the three paragraphs.
    assert "Para one." in result
    assert "Para two." in result
    assert "Para three." in result


def test_prose_loop_fixes_seam() -> None:
    """prose_loop applies the model fix when needs_fix is True for a seam."""
    call_count: list[int] = []

    def _fake_chat(prompt: str, *, system: str | None = None, **kwargs):
        call_count.append(1)
        # First call: seam inspection says fix needed
        if system and "charter" in system:
            return {"needs_fix": True, "reasons": ["bolted-on transition"]}
        # Second call (fix pass): return two patched paragraphs
        return "Para A revised|||Para B revised"

    with patch("sprezzature_local.ralph.llm.chat", side_effect=_fake_chat):
        result = prose_loop("Para A.\n\nPara B.", charter="Be crisp.", max_passes=1)

    assert "Para A revised" in result
    assert "Para B revised" in result
