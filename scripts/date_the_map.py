#!/usr/bin/env python3
"""
date_the_map — stamp a standpoint figure with the date its ratings were made.

Why a positioning map needs a date
----------------------------------
``standpoint`` draws the geometry of a comparison table and nothing else: no
caption, no vintage. For a map of software that is a real omission, and
``sprezzature-maps`` is the repository that says so out loud — its own
``no-provenance`` rule exists because *"a map with neither is read as current,
forever, including years after it stopped being so"*. A quadrant of mapping
tools is read the same way. The judgements behind it were made on a particular
day, against the versions that existed on that day, and the figure should say
which day rather than leave the reader to assume today.

That rule first fired on these figures as a test failure, which is the useful
way for it to arrive: the honest fix was to date the figure, not to exempt the
file from the check.

What it does
------------
Appends one ``<text>`` element, bottom-left, reading ``Ratings as of <month>
<year> — <source>``. Idempotent: a figure that already carries the stamp is
left alone, so re-running after a redraw is safe and running twice is a no-op.

Usage
-----
::

    python scripts/date_the_map.py assets/*.svg --asof "October 2026" \\
        --source LANDSCAPE.md

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

#: The marker that makes a second run a no-op.
STAMP_CLASS = "provenance-stamp"

_VIEWBOX_RE = re.compile(r'viewBox="([-\d.]+)\s+([-\d.]+)\s+([\d.]+)\s+([\d.]+)"')


#: Default prefix. French figures pass ``--prefix "Notes à jour en"``; the
#: auditor's date pattern recognises "as of" and "à jour" alike, so a stamp
#: does not have to be in English to count — and a French plate captioned in
#: English is a defect of its own.
PREFIX = "Ratings as of"


def stamp_text(asof: str, source: str, prefix: str = PREFIX) -> str:
    """The caption, in the wording the auditor recognises as a date."""
    return f"{prefix} {asof} — {source}"


def stamp(svg: str, *, asof: str, source: str, prefix: str = PREFIX) -> str | None:
    """Return the stamped SVG, or ``None`` when it already carries one."""
    if STAMP_CLASS in svg:
        return None
    box = _VIEWBOX_RE.search(svg)
    if not box:
        raise ValueError("no viewBox — cannot place the caption")
    min_x, min_y, width, height = (float(g) for g in box.groups())

    # Bottom-left, inside the box by the same margin on both sides, so the
    # caption sits with the figure rather than against its edge.
    margin = min(width, height) * 0.02
    x = min_x + margin
    y = min_y + height - margin

    caption = (
        f'<text class="{STAMP_CLASS}" x="{x:.1f}" y="{y:.1f}" '
        f'font-size="{max(10.0, height * 0.018):.1f}" fill="#6b7280" '
        f'font-family="Roboto, system-ui, sans-serif">'
        f"{stamp_text(asof, source, prefix)}</text>"
    )
    close = svg.rindex("</svg>")
    return svg[:close] + caption + svg[close:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="date_the_map",
        description=(
            "Stamp a standpoint figure with the date its ratings were made. "
            "Idempotent; safe to re-run after a redraw."
        ),
    )
    parser.add_argument("svg", nargs="+", type=Path)
    parser.add_argument(
        "--asof",
        required=True,
        help='When the judgements were made, e.g. "October 2026".',
    )
    parser.add_argument(
        "--prefix",
        default=PREFIX,
        help=f'Caption prefix (default: "{PREFIX}"); use "Notes à jour en" in French.',
    )
    parser.add_argument(
        "--source",
        default="LANDSCAPE.md",
        help="Where the table lives (default: LANDSCAPE.md).",
    )
    args = parser.parse_args(argv)

    for path in args.svg:
        text = path.read_text(encoding="utf-8")
        stamped = stamp(text, asof=args.asof, source=args.source, prefix=args.prefix)
        if stamped is None:
            print(f"--  {path}: already stamped")
            continue
        path.write_text(stamped, encoding="utf-8")
        print(f"ok  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
