"""
The shipped figures are audited by the auditor the suite ships for figures.

``sprezzature-figures`` carries ``scripts/audit_figure.py``: eight rules for
the data-viz mistakes that survive review — a perspective pie, a rainbow
palette, chart junk, corners rounder than the house cap, ticks left as raw
magnitudes or ISO dates. Nothing ran it over ``web/img/``, which is where this
repository publishes 182 figures, their French twins and their academic-theme
siblings. The one place the suite's own standard is on display was the one
place it was not applied.

Run by hand on 2026-10-23 it returned 25 warnings and no errors, and the
triage is worth keeping, because it went three ways:

* **The rule was wrong.** Fifteen ``radius-over-cap`` warnings were pills —
  a legend chip, a pill node, a tooltip bubble, each with ``rx`` at exactly
  half its height. A capsule is a shape somebody chose, not a corner that
  drifted past a cap. And ``iso-date-tick`` counted hover bubbles, turning an
  axis with ten dates into "56 tick labels".
* **The figures were wrong.** Eleven generators rounded their canvas to 18,
  20 or 22 pixels against a house cap of 16 — breaking, in the gallery, a rule
  this same repository publishes. The candlestick chart printed ``2026-03-02``
  on its axis, three times the width of ``Mar 2`` for the same information.
* **Neither.** What is left is below, and each entry says why.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

#: ``(rule, path fragment) -> why this one is not a defect``. Read, decided,
#: and written down; not a list of things nobody looked at.
ACCEPTED: dict[tuple[str, str], str] = {
    ("chartjunk", "img/maps/"): (
        "a situation plate shades its relief and haloes its labels with a "
        "blur: on a map that is cartography, and the rule is written for "
        "decoration on a chart"
    ),
    ("chartjunk", "situation_map.svg"): (
        "the same plate, shown in the figures gallery as an example of the "
        "map generators"
    ),
    ("unformatted-tick", "table.svg"): (
        "a table figure: the raw magnitudes in its cells are the content, not "
        "an axis a reader scans"
    ),
    ("unformatted-tick", "funnel-area.svg"): (
        "values printed inside each funnel segment, one per stage, read one "
        "at a time rather than compared down an axis"
    ),
}

#: Everything this repository publishes as a figure: the gallery, its French
#: twins, the academic-theme siblings, and the map plates.
SHIPPED: list[Path] = sorted(
    p
    for folder in ("img/figures", "img/figures/fr", "img/figures/academic", "img/maps")
    for p in (WEB / folder).glob("*.svg")
)


def _auditor():
    """The auditor, loaded from the figures checkout by file path.

    Not ``import sprezzature_figures``: a sibling fetched by
    ``scripts/fetch_siblings.sh`` is a checkout, and that package's name maps
    to a directory only once the distribution is installed. ``scripts/`` is
    one of the paths the fetch brings.
    """
    path = REPO_ROOT.parent / "sprezzature-figures" / "scripts" / "audit_figure.py"
    if not path.is_file():
        pytest.skip("no sprezzature-figures checkout; run scripts/fetch_siblings.sh")
    name = "_engine_audit_figure"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _accepted(rule: str, path: Path) -> str | None:
    rendered = path.as_posix()
    for (known_rule, fragment), why in ACCEPTED.items():
        if rule == known_rule and fragment in rendered:
            return why
    return None


@pytest.mark.parametrize("svg", SHIPPED, ids=lambda p: str(p.relative_to(WEB)))
def test_a_shipped_figure_passes_the_auditor(svg: Path) -> None:
    """No error, and no warning that has not been read and written down."""
    findings = _auditor().audit_one(svg)
    unexplained = [
        f"{f['rule']}: {f['message']}"
        for f in findings
        if _accepted(f["rule"], svg) is None
    ]
    assert not unexplained, (
        f"{svg.relative_to(WEB)}: {unexplained}. Fix the figure, or add the "
        f"pair to ACCEPTED with the reason — an entry nobody can explain is "
        f"the thing this file exists to prevent."
    )


def test_every_accepted_entry_still_matches_something() -> None:
    """An exemption that stopped applying is a sentence nobody can check.

    Left in place it reads as a decision that still holds, and the next
    reader has no way to tell it from one that does.
    """
    audit = _auditor()
    seen: set[tuple[str, str]] = set()
    for svg in SHIPPED:
        for finding in audit.audit_one(svg):
            for key in ACCEPTED:
                if finding["rule"] == key[0] and key[1] in svg.as_posix():
                    seen.add(key)
    stale = sorted(set(ACCEPTED) - seen)
    assert not stale, f"these exemptions no longer match any figure: {stale}"


def test_there_are_figures_to_audit() -> None:
    """A glob that stopped matching would make every case above vacuous."""
    assert len(SHIPPED) >= 300, f"only {len(SHIPPED)} SVG found under web/img"
