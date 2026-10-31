#!/usr/bin/env python3
"""
landscape_to_csv — turn a LANDSCAPE star table into a standpoint input.

Why this is a converter and not a judgement
-------------------------------------------
Every ``LANDSCAPE.md`` in this suite already carries a star table: criteria
down the side, tools across the top, ⭐ to ⭐⭐⭐⭐⭐ in the cells. Those numbers
were argued over when they were written and they are already published. A
positioning map built from *new* ratings would be a second opinion competing
with the first, and the two would drift; built from these, it is the same
claim drawn differently.

So this script invents nothing. It reads the table that is there, transposes
it — ``standpoint`` wants options in rows and criteria in columns, the
LANDSCAPE tables are the other way round — and writes the CSV.

Two decisions worth stating
---------------------------
**``N/A`` becomes a 1**, and the first version of this script left it blank.
``standpoint`` fills a blank with that column's *minimum*, documented as "a
missing rating never flatters an option" — and on these tables that promise
does not hold, because the columns are sparse. In ``sprezzature-colors``'s
comparison only two of four tools rate "Token export" at all, so the minimum
of that column is a 3, and `axe-core` — marked ``N/A``, meaning it does not
export tokens — came out of the map claiming 3 out of 5 for doing so. The
blank flattered it.

In these tables ``N/A`` means *this tool does not do this*, which on a 1–5
capability scale is a 1. That is the faithful encoding, and it is only
distinguishable from "unknown" because these documents use ``N/A`` for the
former and simply rate everything they know.

**A table too small to project is refused, not drawn.** A positioning map is
worth looking at when the two axes *discard* something — that is what makes it
a summary rather than a redrawing. A table of ``n`` options and ``p`` criteria
holds at most ``min(n - 1, p)`` independent directions, so two axes throw away
``min(n - 1, p) - 2`` of them. This script requires that to be at least three.

The threshold is not cosmetic, and the two documents that used to be named
here as the examples are the proof of what it was really measuring. On
2026-10-29 ``sprezzature-accessibility`` compared four tools across five
criteria: two axes carried 99.4 % of that table, a number that reads as a
strong result and is really just "we kept two of three". ``sprezzature-ux-laws``
compared three, leaving two, and ``standpoint`` refused it outright, because
with ``N/A`` read as a floor two of its columns had become the same column.

Both now project, and nothing in this script changed. They compare 23 and 25
tools, and the threshold was never telling them their tables were badly built:
it was telling them the tables were too *small*, which is a fact about how
much of the field had been looked at. A refusal to draw was the right answer
to that, and the right repair was to go and read the field.

A LANDSCAPE that still trips this check keeps its table and gets no map, which
remains the correct outcome rather than a gap.

**The reference row is this suite's own brick.** ``standpoint`` puts the first
row top-right and orients everything else around it. That is a statement about
the drawing, not about quality — and it is the honest one to make in a file
that belongs to that brick.

Usage
-----
::

    python scripts/landscape_to_csv.py ../sprezzature-colors/LANDSCAPE.md
    python scripts/landscape_to_csv.py --all          # every sibling checkout

Writes ``<repo>/assets/landscape.csv`` and prints what it found. Exits
non-zero when a file has no star table — which is a fact about that
LANDSCAPE, not an error to paper over.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _blocks(markdown: str) -> list[list[list[str]]]:
    """Every pipe table in the document, as a list of row-lists.

    Blocks, not rows, and that distinction is the whole correctness of this
    script. A first version collected star rows and the last header-looking
    row it had seen, which in a document with several tables married the
    header of one to the body of another — figures came out as "22 tools × 37
    criteria" for a table that is neither, which is nonsense arriving quietly.
    """
    blocks: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            current.append([cell.strip() for cell in stripped.strip("|").split("|")])
            continue
        if current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _is_separator(cells: list[str]) -> bool:
    """Whether this row is a Markdown table's ``|---|---|`` rule."""
    return bool(cells) and all(set(cell) <= set("-: ") and cell for cell in cells)


def _stars(cell: str) -> str:
    """A star cell as a number, or ``"1"`` when the tool does not do this.

    Only the stars are counted — a cell like ``⭐⭐⭐ (with a caveat)`` is a 3,
    because the caveat belongs in the prose and not in the arithmetic.
    """
    count = cell.count("⭐")
    if count:
        return str(count)
    # Unrated means "does not do this" in these tables — see the module
    # docstring on why this is a 1 and not a blank.
    return "1"


def star_table(markdown: str) -> tuple[list[str], list[tuple[str, list[str]]]] | None:
    """The largest star table in the document, transposed.

    Returns ``(criteria, [(tool, values), ...])`` — tools as rows, which is
    the shape ``standpoint`` reads.

    The *largest* rather than the first: several of these documents open with
    a small orientation table and put the rated comparison further down, and
    picking by position would make the output depend on where somebody chose
    to introduce the subject.
    """
    best: tuple[list[str], list[tuple[str, list[str]]]] | None = None
    best_size = 0

    for block in _blocks(markdown):
        rows = [row for row in block if not _is_separator(row)]
        if len(rows) < 2:
            continue
        header, body = rows[0], rows[1:]
        # Only rows that are both starred *and* the header's width belong to
        # this table. A width mismatch means the row came from somewhere else.
        starred = [
            row for row in body if "⭐" in "".join(row) and len(row) == len(header)
        ]
        if not starred:
            continue
        size = len(starred) * (len(header) - 1)
        if size <= best_size:
            continue

        labels = [_clean(row[0]) for row in starred]
        values = [[_stars(cell) for cell in row[1:]] for row in starred]
        columns = [_clean(cell) for cell in header[1:]]

        # Both orientations exist in this suite and neither is wrong.
        # `sprezzature-colors` puts criteria down the side and tools across the
        # top; `sprezzature-figures` does the opposite. Transposing blindly
        # produced a file whose rows were "Free or open source" and whose
        # columns were tool names — arithmetic over nonsense, and it ran
        # without complaint.
        #
        # The discriminator is where the brick's own name sits, which is a
        # thing every one of these documents contains exactly once in its
        # comparison: in the header means criteria-down, in the first column
        # means tools-down.
        brick_in_header = any(label.startswith("sprezzature") for label in columns)
        if brick_in_header:
            best = (
                labels,
                [
                    (tool, [row[index] for row in values])
                    for index, tool in enumerate(columns)
                ],
            )
        else:
            best = (columns, list(zip(labels, values, strict=True)))
        best_size = size

    return best


#: Two axes must discard at least this many independent directions for the
#: projection to be a summary rather than a redrawing of the table.
MIN_DISCARDED = 3


def projectable(n_options: int, n_criteria: int) -> int:
    """How many directions two axes would throw away.

    A table holds at most ``min(n - 1, p)`` independent directions — one is
    lost to centring — so this is that, minus the two the map keeps. Negative
    or small means the map would show the table back rather than summarise it.
    """
    return min(n_options - 1, n_criteria) - 2


def convert(landscape: Path, *, out: Path | None = None) -> Path | None:
    """Write the CSV beside the LANDSCAPE, under ``assets/``."""
    table = star_table(landscape.read_text(encoding="utf-8"))
    if table is None:
        print(f"!!  {landscape}: no star table found", file=sys.stderr)
        return None
    criteria, tools = table

    discarded = projectable(len(tools), len(criteria))
    if discarded < MIN_DISCARDED:
        print(
            f"--  {landscape}: {len(tools)} options × {len(criteria)} criteria "
            f"leaves {discarded + 2} directions; two axes would discard "
            f"{max(discarded, 0)}. Too small to summarise — see the module "
            f"docstring. No map.",
            file=sys.stderr,
        )
        return None

    destination = out or (landscape.parent / "assets" / "landscape.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Tool", *(_clean(c) for c in criteria)])
        for tool, row in tools:
            writer.writerow([_clean(tool), *row])

    print(f"ok  {destination}: {len(tools)} tools × {len(criteria)} criteria")
    return destination


def _clean(label: str) -> str:
    """A table label without its Markdown emphasis or links."""
    import re

    label = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", label)
    return label.replace("**", "").replace("`", "").strip()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="landscape_to_csv",
        description=(
            "Turn a LANDSCAPE.md star table into a standpoint CSV. Invents no "
            "ratings: it reads the ones already published there."
        ),
    )
    parser.add_argument("landscape", nargs="*", type=Path, help="LANDSCAPE.md files.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Write here instead of <repo>/assets/landscape.csv. One file "
            "only — the French twins need it, since PAYSAGE.md's table has "
            "French labels and belongs beside paysage.svg, not landscape.csv."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Every sibling checkout beside this repository, plus this one.",
    )
    args = parser.parse_args(argv)

    targets: list[Path] = list(args.landscape)
    if args.all:
        targets = sorted(
            path
            for path in [REPO_ROOT / "LANDSCAPE.md"]
            + list(REPO_ROOT.parent.glob("sprezzature-*/LANDSCAPE.md"))
            if path.is_file()
        )
    if not targets:
        parser.error("name a LANDSCAPE.md, or pass --all")
    if args.out is not None and len(targets) != 1:
        parser.error("--out takes exactly one LANDSCAPE")

    skipped = [path for path in targets if convert(path, out=args.out) is None]
    if skipped:
        print(
            f"\n{len(skipped)} of {len(targets)} got no map: either the "
            f"LANDSCAPE is qualitative and has no star table, or its table is "
            f"too small for two axes to summarise. Both are facts about those "
            f"files, not something to work around here.",
            file=sys.stderr,
        )
    return 1 if len(skipped) == len(targets) else 0


if __name__ == "__main__":
    raise SystemExit(main())
