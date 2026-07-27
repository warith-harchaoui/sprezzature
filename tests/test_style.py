"""
test_style — the sprezzature-figures shared style helpers (`_style.py`).

`_style.py` is pure: palette lookups, the Vega/matplotlib config blocks, and the
polarity inference. It reads `sprezzature-colors/references/palette.csv` when
co-installed (it is, in-repo) and falls back to a small built-in set otherwise.
Either way the public helpers have deterministic, assertable contracts.

Author
------
Project maintainers.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "sprezzature-figures" / "scripts"))

import _style  # noqa: E402

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_qualitative_sequence_returns_n_distinct_hexes() -> None:
    """A qualitative sequence of n returns n distinct #rrggbb colours."""
    seq = _style.qualitative_sequence(8)
    assert len(seq) == 8
    assert all(_HEX.match(c) for c in seq), seq
    assert len(set(seq)) == 8, f"colours not distinct: {seq}"


def test_vega_config_dark_differs_from_light() -> None:
    """Dark and light Vega configs are not the same object/content."""
    assert _style.vega_config(dark=True) != _style.vega_config(dark=False)


def test_emotion_to_hex_known_and_unknown() -> None:
    """A resolvable emotion yields a hex; a nonsense one yields None."""
    unknown = _style.emotion_to_hex("definitely-not-an-emotion-xyz")
    assert unknown is None
    # At least one palette Emotion label should resolve to a valid hex.
    resolved = [_style.emotion_to_hex(e) for e in ("Joy", "Anger", "Fear", "Sadness", "Peace")]
    hits = [c for c in resolved if c is not None]
    assert hits, "no palette emotion resolved to a colour"
    assert all(_HEX.match(c) for c in hits), hits


def test_infer_polarity_contract() -> None:
    """infer_polarity returns higher-better / lower-better / None only."""
    for name in ("latency", "error rate", "revenue", "conversion", "throughput", "xyzzy"):
        p = _style.infer_polarity(name)
        assert p in ("higher-better", "lower-better", None), (name, p)


def test_polarity_tag_reflects_direction() -> None:
    """The English polarity tag names the direction when one is given."""
    assert "higher" in _style.polarity_tag("higher-better", "en").lower()
    assert "lower" in _style.polarity_tag("lower-better", "en").lower()
    assert _style.polarity_tag(None, "en") == ""
