"""
``brag-output/figure_cli.py`` is a reconstruction, and reconstructions rot.

The ``interface`` film's middle scene shows a real form, produced by
sprezzature-cli-gui from a real ``argparse``. That parser was written for the
shoot and thrown away, so for a year the two captures in ``_assets/shots/``
were its only record: unregenerable, and one disk failure from gone. It has
been rebuilt by reading the captures, and ``restore_assets.py`` now renders and
captures the form again on demand.

What that buys is only as good as the parser staying faithful. The failure mode
is quiet — a flag renamed, a default changed, a help line reworded — and it
would surface as a film whose form no longer matches the one shipped, which no
test would otherwise notice.

So this pins every string the capture shows. Not the pixels: those belong to
the tool's stylesheet, which has already moved (the rebuilt page is 1054px tall
where the original was 1040), and a byte compare would break on the next CSS
tweak while telling us nothing about the parser. The words on screen are the
contract.

The two choice lists are checked differently, because a closed ``<select>``
shows only its selection — their contents were never visible in the capture and
come from the repos instead. What is checked there is the claim the form makes
out loud: "127 chart kinds".
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

figure_cli = pytest.importorskip("figure_cli")


# Read off _assets/shots/cli-gui-full.png, top to bottom, exactly as rendered.
ON_SCREEN = (
    "make-figure",
    "Turn a CSV into a hand-authored SVG figure. 127 chart kinds.",
    "--kind", "Which of the 127 chart kinds to draw",
    "--input", "Input CSV file",
    "--output", "Where to write the SVG",
    "--accessibility", "Accessibility level of the palette",
    "--title", "Figure title",
    "--audit", "Run the data-viz auditor after drawing",
)

# Defaults the capture shows as pre-filled field values.
DEFAULTS = {"kind": "bar", "output": "figure.svg", "accessibility": "universal"}


def test_every_string_the_capture_shows_is_still_produced():
    """The help text is the form's text: cli-gui renders one from the other."""
    text = figure_cli.parser().format_help()
    missing = [s for s in ON_SCREEN if s not in text]
    assert not missing, f"no longer on screen: {missing}"


def test_defaults_match_the_prefilled_fields():
    parsed = figure_cli.parser().parse_args([])
    for flag, want in DEFAULTS.items():
        assert getattr(parsed, flag) == want, f"--{flag} drifted from the capture"


def test_the_two_free_text_fields_are_empty_in_the_capture():
    """``--input`` and ``--title`` render blank, so they must have no default."""
    parsed = figure_cli.parser().parse_args([])
    assert parsed.input is None
    assert parsed.title is None


def test_audit_is_the_only_checkbox():
    """A checkbox means a flag that takes no value; the others are inputs."""
    parsed = figure_cli.parser().parse_args([])
    assert parsed.audit is False
    assert figure_cli.parser().parse_args(["--audit"]).audit is True


def test_the_palette_levels_are_the_suite_s_own():
    """Six levels, spelled as every figure generator in the suite spells them.

    Hard-coded in figure_cli so a bare clone can still render the form; compared
    here against sprezzature-colors when that checkout is present, which is what
    stops the copy from drifting silently.
    """
    assert figure_cli.LEVELS[0] == "universal", "the capture shows 'universal' selected"

    src = pathlib.Path.home() / "sprezzature-colors/scripts/accessibility_levels.py"
    if not src.exists():
        pytest.skip("sprezzature-colors checkout absent")
    ns: dict = {}
    body = src.read_text()
    start = body.index("LEVELS")
    exec(compile(body[start:body.index(")", start) + 1], "<levels>", "exec"), ns)  # noqa: S102
    assert tuple(ns["LEVELS"]) == figure_cli.LEVELS


def test_the_form_can_claim_127_kinds():
    """The description says "127 chart kinds" out loud; the select must back it.

    Skipped rather than failed without the catalog: figure_cli deliberately
    falls back to a one-entry list so the form still renders from a bare clone,
    and only the selected option is ever visible anyway.
    """
    if figure_cli.catalog() is None:
        pytest.skip("sprezzature-figures catalog not reachable")
    kinds = figure_cli.kinds()
    assert len(kinds) == 127, f"description says 127, catalog has {len(kinds)}"
    assert "bar" in kinds, "the capture shows 'bar' selected"
