#!/usr/bin/env python3
"""The `make-figure` parser the `interface` film puts on screen.

The film's middle scene shows a real form, produced by sprezzature-cli-gui from
a real argparse. That argparse was written for the shoot and then thrown away,
so the two captures in _assets/shots/ were the only trace of it and could not be
regenerated. This file is that parser, rebuilt from the captures.

Nothing here is invented. The prog name, the description, every flag, every
default and every help string are read off shots/cli-gui-full.png. The two
choice lists are not visible there — a closed `<select>` shows only its
selection — so they come from the repos instead:

* ``--kind`` offers the 127 entries of ``sprezzature_figures/catalog/figures.json``,
  which is also where the description's "127 chart kinds" comes from.
* ``--accessibility`` offers ``LEVELS`` from
  ``sprezzature-colors/scripts/accessibility_levels.py``, the same six values
  every figure generator in the suite accepts.

Used by restore_assets.py; see there for the capture step.
"""

from __future__ import annotations

import argparse
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent

# The six palette levels, spelled as sprezzature-figures' generators spell them.
# Hard-coded rather than imported: this file has to work from a clone with no
# sibling checkout, and a drift here shows up as a wrong word on screen, which
# the eyeball loop catches.
LEVELS = ("universal", "high-contrast", "monochrome",
          "deuteranopia", "protanopia", "tritanopia")

def catalog() -> pathlib.Path | None:
    """figures.json, wherever this machine keeps it.

    The monorepo vendors only the skill text of sprezzature-figures, not its
    package, so the catalog lives in the installed distribution or in a sibling
    checkout. Both are tried before giving up.
    """
    try:
        import sprezzature_figures

        p = pathlib.Path(sprezzature_figures.__file__).parent / "catalog/figures.json"
        if p.exists():
            return p
    except ImportError:
        pass
    for p in (pathlib.Path.home() / "sprezzature-figures/sprezzature_figures/catalog/figures.json",
              REPO / "sprezzature-figures/catalog/figures.json"):
        if p.exists():
            return p
    return None


def kinds() -> tuple[str, ...]:
    """The figure kinds, from the catalog when it is reachable, else the default.

    Falling back to one entry keeps the form renderable from a bare clone. The
    `<select>` then shows the same thing it shows in the film, since only the
    selected option is ever visible.
    """
    path = catalog()
    if path is None:
        return ("bar",)
    data = json.loads(path.read_text())
    entries = data if isinstance(data, list) else list(data.get("figures", data.values()))
    found = tuple(e.get("id") or e.get("name") or e.get("kind") for e in entries)
    return tuple(k for k in found if k) or ("bar",)


def parser() -> argparse.ArgumentParser:
    """Zero-argument factory, the shape `cli_to_gui.py <path>:<factory>` wants."""
    p = argparse.ArgumentParser(
        prog="make-figure",
        description="Turn a CSV into a hand-authored SVG figure. 127 chart kinds.",
    )
    p.add_argument("--kind", choices=kinds(), default="bar",
                   help="Which of the 127 chart kinds to draw")
    p.add_argument("--input", help="Input CSV file")
    p.add_argument("--output", default="figure.svg", help="Where to write the SVG")
    p.add_argument("--accessibility", choices=LEVELS, default="universal",
                   help="Accessibility level of the palette")
    p.add_argument("--title", help="Figure title")
    p.add_argument("--audit", action="store_true",
                   help="Run the data-viz auditor after drawing")
    return p


if __name__ == "__main__":
    parser().print_help()
