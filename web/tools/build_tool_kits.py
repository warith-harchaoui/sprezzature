"""
build_tool_kits — a runnable zip behind every tool, not just every figure.

Why this exists
---------------
``build_figure_kits.py`` gives each chart in the gallery a folder you can
email: the generator, the engine, the data, a page that opens the result.
The other toolboxes deserve the same treatment and never had it. A reader
who wants to know whether their palette is accessible should not have to
clone a repository, create a virtualenv, and read a README to find out —
they should be able to unzip a folder, run one command, and look at the
answer.

What a kit is
-------------
A directory that runs on a machine with **nothing installed**: standard
library only, no network, no clone, no account. Every tool bundled here is
already pure stdlib, which is what makes this possible at all — the check
is enforced, not assumed (see :func:`verify_stdlib_only`).

Each kit carries:

``run.py``
    The one command. Reads the sample input, writes the report.
``lib/``
    The vendored tool, unmodified, so the kit and the repository cannot
    disagree about what the tool does.
``index.html``
    Opens the report. Double-clicking a bare SVG loses the context;
    ``<object>`` keeps the hover chrome and the linked webfont that an
    ``<img>`` would sandbox away.
``README.md`` / ``LISEZMOI.md``
    What it is, how to run it, what to change.

Usage
-----
::

    python3 build_tool_kits.py                 # every kit
    python3 build_tool_kits.py --only colors   # just one
    python3 build_tool_kits.py --out-dir /tmp/kits

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List

#: Where the standalone repositories live, relative to the monorepo root.
HOME = Path.home()

#: Modules the standard library provides. Anything imported by a vendored
#: file that is not here, and not vendored beside it, breaks the promise
#: that a kit runs on a bare machine.
_STDLIB = set(sys.stdlib_module_names) | {"__future__"}


def verify_stdlib_only(paths: List[Path], vendored: set[str]) -> List[str]:
    """
    Report any third-party import in the files a kit is about to ship.

    The whole claim of a kit is "this runs with nothing installed". That
    claim is cheap to make and easy to break — one convenience import added
    upstream months from now, and the zip still builds, still looks right,
    and fails on the recipient's machine with a traceback they cannot fix.
    So it is checked at build time rather than trusted.

    Parameters
    ----------
    paths : list of pathlib.Path
        Python files to inspect.
    vendored : set of str
        Module names shipped inside the kit, which are therefore fine.

    Returns
    -------
    list of str
        One line per offending import, empty when the kit is clean.
    """
    problems: List[str] = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # a file that will not parse cannot ship
            problems.append(f"{path.name}: does not parse ({exc})")
            continue
        # An import inside `try:` or `if:` is optional by construction —
        # _lang.py guards `from langdetect import ...` behind a find_spec
        # check precisely so the module stays importable without it. Only
        # unconditional imports can break a bare machine.
        guarded: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Try, ast.If)):
                for inner in ast.walk(node):
                    if isinstance(inner, (ast.Import, ast.ImportFrom)):
                        guarded.add(id(inner))

        for node in ast.walk(tree):
            if id(node) in guarded:
                continue
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                # A relative import stays inside the kit by construction.
                if node.level or node.module is None:
                    continue
                names = [node.module.split(".")[0]]
            else:
                continue
            for name in names:
                if name not in _STDLIB and name not in vendored:
                    problems.append(f"{path.name}:{node.lineno} imports {name!r}")
    return problems


def write_zip(kit: Path, destination: Path) -> int:
    """
    Zip `kit` into `destination`, deterministically.

    Fixed timestamps mean an unchanged kit produces byte-identical output,
    so republishing does not churn. ``ZIP_DEFLATED`` because the payload is
    text and compresses well.

    Parameters
    ----------
    kit : pathlib.Path
        Directory to archive. Its own name becomes the top-level folder.
    destination : pathlib.Path
        ``.zip`` path to write.

    Returns
    -------
    int
        Size of the archive in bytes.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(kit.rglob("*")):
            if path.is_dir() or path.name.startswith("."):
                continue
            # Running the kit at build time leaves __pycache__ behind. A
            # .pyc compiled for the builder's interpreter is worse than
            # useless on the recipient's — stale bytes for a version they
            # may not have — and it is a third of the archive.
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            info = zipfile.ZipInfo(
                str(Path(kit.name) / path.relative_to(kit)),
                date_time=(2026, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return destination.stat().st_size


# ──────────────────────────────────────────────────────────────────────────
# colors
# ──────────────────────────────────────────────────────────────────────────

_COLORS_RUN = '''"""
run — audit the palette in palette.csv, and draw the answer.

Two questions, both with defensible answers rather than opinions:

**Can text be read on it?**
    Every pair in the palette is scored with the WCAG contrast formula and
    checked against the 4.5:1 threshold for normal text. The matrix below
    marks each pair pass or fail.

**Does it survive colour blindness?**
    Each colour is put through the Machado matrices for the three common
    deficiencies. Two swatches that stay distinct are a safe pair; two that
    converge never were, however different they look to you.

Run it::

    python3 run.py            # writes contrast.svg and cvd.svg
    open index.html           # or double-click it

Then edit ``palette.csv`` — your own brand colours, one per row — and run it
again. Nothing here needs installing: the standard library is enough.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from _colors import (  # noqa: E402
    CVD_MATRICES,
    contrast_ratio_hex,
    load_palette,
    parse_hex,
    rgb_to_hex,
    simulate_pixel,
)

#: WCAG 2.x threshold for normal-size body text.
AA_NORMAL: float = 4.5

CELL: int = 46
PAD: int = 176
INK: str = "#1d1d1f"
SUBTLE: str = "#6e6e73"


def escape(text: str) -> str:
    """Minimal XML escaping for text that goes into an SVG."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def contrast_matrix(rows: list[dict[str, str]]) -> str:
    """
    Draw every pair's contrast ratio as a matrix.

    A matrix rather than a list because the question is never "is this one
    colour fine" but "which combinations may I use", and that is a shape
    with two axes. The diagonal is left blank: a colour on itself has a
    ratio of 1 and is never a choice anybody is weighing.

    Parameters
    ----------
    rows : list of dict
        Palette rows, each with ``name`` and ``hex``.

    Returns
    -------
    str
        A complete SVG document.
    """
    n = len(rows)
    width = PAD + n * CELL + 30
    height = PAD + n * CELL + 92
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Contrast ratio for every pair in the palette">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="24" y="38" font-family="system-ui, sans-serif" font-size="21" '
        f'font-weight="700" fill="{INK}">Which pairs can carry text</text>',
        f'<text x="24" y="62" font-family="system-ui, sans-serif" font-size="13" '
        f'fill="{SUBTLE}">WCAG contrast ratio · a filled cell clears 4.5:1 for normal text</text>',
    ]

    for i, row in enumerate(rows):      # column headers, rotated
        x = PAD + i * CELL + CELL / 2
        # rotate(+60) with text-anchor="end", not rotate(-60): SVG's y axis
        # points down, so a negative angle sends the label down-left, under
        # the grid cells, which then paint over it. Only the last letter or
        # two stayed visible. Positive lifts it clear, and anchoring at the
        # end sends it over the wide left margin rather than off the tight
        # right edge.
        out.append(
            f'<text x="{x:.1f}" y="{PAD - 10}" font-family="system-ui, sans-serif" '
            f'font-size="11" fill="{SUBTLE}" text-anchor="end" '
            f'transform="rotate(60 {x:.1f} {PAD - 10})">{escape(row["name"])}</text>'
        )

    for r, back in enumerate(rows):
        y = PAD + r * CELL
        out.append(
            f'<text x="{PAD - 10}" y="{y + CELL / 2 + 4:.1f}" '
            f'font-family="system-ui, sans-serif" font-size="11" fill="{SUBTLE}" '
            f'text-anchor="end">{escape(back["name"])}</text>'
        )
        for c, front in enumerate(rows):
            x = PAD + c * CELL
            if r == c:
                out.append(
                    f'<rect x="{x}" y="{y}" width="{CELL - 2}" height="{CELL - 2}" '
                    f'fill="#f5f5f7"/>'
                )
                continue
            ratio = contrast_ratio_hex(front["hex"], back["hex"])
            passes = ratio >= AA_NORMAL
            out.append(
                f'<rect x="{x}" y="{y}" width="{CELL - 2}" height="{CELL - 2}" '
                f'fill="{back["hex"]}" stroke="#e5e5ea"/>'
                f'<title>{escape(front["name"])} on {escape(back["name"])}: '
                f'{ratio:.2f}:1 — {"passes" if passes else "fails"} AA</title>'
            )
            # The number is set in the foreground colour it describes, which
            # makes the cell its own demonstration: an unreadable number is
            # exactly the failure the number is reporting.
            out.append(
                f'<text x="{x + (CELL - 2) / 2:.1f}" y="{y + CELL / 2 + 4:.1f}" '
                f'font-family="system-ui, sans-serif" font-size="11" '
                f'font-weight="{700 if passes else 400}" fill="{front["hex"]}" '
                f'text-anchor="middle">{ratio:.1f}</text>'
            )
            if not passes:
                # Never colour alone: a diagonal slash marks a failing pair
                # so the matrix survives greyscale and colour blindness.
                out.append(
                    f'<line x1="{x + 4}" y1="{y + CELL - 6}" x2="{x + CELL - 8}" '
                    f'y2="{y + 4}" stroke="#c7c7cc" stroke-width="1"/>'
                )

    legend_y = PAD + n * CELL + 28
    for offset, line in enumerate((
        "Row = background, column = text.",
        "A slash marks a pair below 4.5:1 — by shape, not colour alone,",
        "so the chart survives greyscale and colour blindness.",
    )):
        out.append(
            f'<text x="24" y="{legend_y + offset * 17}" '
            f'font-family="system-ui, sans-serif" font-size="12" fill="{SUBTLE}">{line}</text>'
        )
    out.append("</svg>")
    return "\\n".join(out)


def cvd_strip(rows: list[dict[str, str]]) -> str:
    """
    Draw the palette as seen with normal vision and with each deficiency.

    Four rows, same order, so a pair that merges lower down is obvious by
    comparison rather than by reading hex codes.

    Parameters
    ----------
    rows : list of dict
        Palette rows, each with ``name`` and ``hex``.

    Returns
    -------
    str
        A complete SVG document.
    """
    kinds = ["normal vision"] + list(CVD_MATRICES)
    n = len(rows)
    swatch, left, top = 56, 150, 96
    width = left + n * swatch + 24
    height = top + len(kinds) * (swatch + 14) + 40
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="The palette as seen with each colour-vision deficiency">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="24" y="38" font-family="system-ui, sans-serif" font-size="21" '
        f'font-weight="700" fill="{INK}">The same palette, four ways of seeing</text>',
        f'<text x="24" y="62" font-family="system-ui, sans-serif" font-size="13" '
        f'fill="{SUBTLE}">Machado matrices · two swatches that merge below were never '
        f'a safe pair</text>',
    ]
    for r, kind in enumerate(kinds):
        y = top + r * (swatch + 14)
        out.append(
            f'<text x="{left - 12}" y="{y + swatch / 2 + 4:.1f}" '
            f'font-family="system-ui, sans-serif" font-size="12" fill="{SUBTLE}" '
            f'text-anchor="end">{escape(kind)}</text>'
        )
        for c, row in enumerate(rows):
            shown = (
                row["hex"] if kind == "normal vision"
                else rgb_to_hex(simulate_pixel(parse_hex(row["hex"]), CVD_MATRICES[kind]))
            )
            out.append(
                f'<rect x="{left + c * swatch}" y="{y}" width="{swatch - 4}" '
                f'height="{swatch}" fill="{shown}" stroke="#e5e5ea"/>'
                f'<title>{escape(row["name"])} — {kind}: {shown}</title>'
            )
    out.append("</svg>")
    return "\\n".join(out)


def swatches() -> list[dict[str, str]]:
    """
    The palette as ``{name, hex}`` rows.

    ``load_palette`` hands back the CSV's own column names — ``Hexcode``,
    ``Base`` and eight more this kit has no use for. Normalising here keeps
    the two drawing functions from each knowing the file format.

    Returns
    -------
    list of dict
        One entry per colour, in file order.
    """
    return [{"name": r["Base"], "hex": r["Hexcode"]} for r in load_palette()]


def main() -> int:
    """Write both SVGs beside this script."""
    here = Path(__file__).resolve().parent
    rows = swatches()
    if not rows:
        print("palette.csv has no rows", file=sys.stderr)
        return 1

    for name, svg in (("contrast.svg", contrast_matrix(rows)), ("cvd.svg", cvd_strip(rows))):
        (here / name).write_text(svg, encoding="utf-8")
        print(f"wrote {name}  ({len(svg) // 1024} KB)")

    failures = [
        (a["name"], b["name"], contrast_ratio_hex(a["hex"], b["hex"]))
        for b in rows for a in rows
        if a is not b and contrast_ratio_hex(a["hex"], b["hex"]) < AA_NORMAL
    ]
    total = len(rows) * (len(rows) - 1)
    print(f"\\n{len(failures)} of {total} pairs fall below {AA_NORMAL}:1 for normal text.")
    print("Open index.html to see which.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


_LINT_RUN = """
\"\"\"
run @@DASH@@ check the sample page, and draw what it found.

The checker is the one from @@REPO@@, copied here unmodified. It reads
``sample.html`` and writes ``report.svg``: one row per group, so the shape
of the problem is visible before any single line is.

Run it::

    python3 run.py            # writes report.svg
    open index.html

Then replace ``sample.html`` with a page of your own and run it again.
Nothing here needs installing: the standard library is enough.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
\"\"\"

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

@@IMPORT@@

INK = "#1d1d1f"
SUBTLE = "#6e6e73"
ERROR = "#d1372e"
WARN = "#b8860b"
ROW = 26
WIDTH = 860


def escape(text):
    \"\"\"Minimal XML escaping for text that goes into an SVG.\"\"\"
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def report(findings):
    \"\"\"
    Draw the findings as a grouped list.

    Grouped rather than listed line by line, because the useful question is
    "what is wrong with this page" and not "what is wrong with line 42":
    one rule broken nineteen times is one decision to make, not nineteen.
    \"\"\"
    counts = Counter(@@KEY@@ for f in findings)
    order = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    height = 150 + max(1, len(order)) * ROW + 40
    out = []
    out.append(
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(WIDTH)
        + '" height="' + str(height) + '" viewBox="0 0 ' + str(WIDTH) + ' '
        + str(height) + '" role="img" aria-label="@@ARIA@@">'
    )
    out.append('<rect width="' + str(WIDTH) + '" height="' + str(height) + '" fill="#ffffff"/>')
    out.append(
        '<text x="24" y="40" font-family="system-ui, sans-serif" font-size="21" '
        'font-weight="700" fill="' + INK + '">@@HEADLINE@@</text>'
    )
    total = len(findings)
    plural = "" if total == 1 else "s"
    out.append(
        '<text x="24" y="64" font-family="system-ui, sans-serif" font-size="13" fill="'
        + SUBTLE + '">' + str(total) + " finding" + plural
        + ' in sample.html, grouped by @@GROUP@@</text>'
    )
    if not order:
        out.append(
            '<text x="24" y="120" font-family="system-ui, sans-serif" font-size="15" fill="'
            + INK + '">Nothing to report ' + chr(8212) + ' the page passes every check.</text>'
        )
        out.append("</svg>")
        return chr(10).join(out)

    biggest = max(counts.values())
    for i, item in enumerate(order):
        name, n = item
        y = 110 + i * ROW
        colour = @@SEVERITY@@
        bar = 380.0 * n / biggest
        out.append(
            '<rect x="330" y="' + str(y - 12) + '" width="' + format(bar, ".1f")
            + '" height="16" fill="' + colour + '" fill-opacity="0.85">'
            + "<title>" + escape(name) + ": " + str(n) + "</title></rect>"
        )
        out.append(
            '<text x="24" y="' + str(y) + '" font-family="ui-monospace, monospace" '
            'font-size="12" fill="' + INK + '">' + escape(name) + "</text>"
        )
        out.append(
            '<text x="' + format(336 + bar, ".1f") + '" y="' + str(y)
            + '" font-family="system-ui, sans-serif" font-size="12" fill="'
            + SUBTLE + '">' + str(n) + "</text>"
        )
    out.append("</svg>")
    return chr(10).join(out)


def main():
    \"\"\"Check the sample and write the report.\"\"\"
    here = Path(__file__).resolve().parent
    findings = @@CALL@@
    svg = report(findings)
    (here / "report.svg").write_text(svg, encoding="utf-8")
    print("wrote report.svg  (" + str(len(svg) // 1024) + " KB)")
    print("")
    print(str(len(findings)) + " finding(s) in sample.html.")
    print("Open index.html to see them, or edit sample.html and run again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def lint_run(repo, import_line, key, severity, call, aria, headline, group):
    """
    Fill the shared checker-kit template.

    Token substitution rather than ``str.format``: the template is Python
    source full of braces, and doubling every one of them to survive
    ``format`` is how the previous version acquired three separate quoting
    bugs in a row.
    """
    text = _LINT_RUN
    for token, value in (
        ("@@DASH@@", chr(8212)),
        ("@@REPO@@", repo),
        ("@@IMPORT@@", import_line),
        ("@@KEY@@", key),
        ("@@SEVERITY@@", severity),
        ("@@CALL@@", call),
        ("@@ARIA@@", aria),
        ("@@HEADLINE@@", headline),
        ("@@GROUP@@", group),
    ):
        text = text.replace(token, value)
    return text



#: A page with one clear instance of several faults. Deliberately small:
#: a kit whose sample throws two hundred findings teaches nothing, and a
#: kit whose sample is clean cannot demonstrate that the tool works.
_SAMPLE_HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Sample page</title></head>
<body>
  <h1>Quarterly review</h1>
  <h3>Revenue</h3>

  <img src="chart.png">
  <img src="spacer.gif" alt="" role="presentation">

  <a>Read more</a>
  <button></button>
  <div onclick="open()">Open the panel</div>

  <input type="email" placeholder="Your email">

  <video src="briefing.mp4"></video>
  <audio src="summary.mp3" autoplay></audio>

  <nav>
    <a href="/a">One</a><a href="/b">Two</a><a href="/c">Three</a>
    <a href="/d">Four</a><a href="/e">Five</a><a href="/f">Six</a>
    <a href="/g">Seven</a><a href="/h">Eight</a><a href="/i">Nine</a>
    <a href="/j">Ten</a><a href="/k">Eleven</a><a href="/l">Twelve</a>
  </nav>

  <p class="text-red-500">Failed</p>
  <p>Reference 4815162342 was filed at 14:32.</p>
  <button class="p-1">Go</button>
</body>
</html>
"""


_PAGE = '''<!doctype html>
<html lang="{lang}">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; --ink:#1d1d1f; --sub:#6e6e73; --bg:#fbfbfd; --card:#fff; --line:#e5e5ea; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --ink:#f5f5f7; --sub:#a1a1a6; --bg:#161617; --card:#1d1d1f; --line:#3a3a3c; }}
  }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }}
  main {{ max-width:1040px; margin:0 auto; padding:48px 20px 80px; }}
  h1 {{ font-size:30px; letter-spacing:-.4px; margin:0 0 8px; }}
  p.lede {{ color:var(--sub); margin:0 0 32px; }}
  .frame {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
            padding:16px; margin:0 0 28px; overflow-x:auto; }}
  .frame:fullscreen {{ overflow:auto; }}
  object {{ display:block; width:100%; max-width:100%; }}
  code {{ background:var(--card); border:1px solid var(--line); border-radius:5px; padding:1px 5px; }}
  button {{ font:inherit; padding:7px 14px; border-radius:9px; border:1px solid var(--line);
            background:var(--card); color:var(--ink); cursor:pointer; min-height:44px; }}
  button:focus-visible {{ outline:2px solid #0071e3; outline-offset:2px; }}
  footer {{ color:var(--sub); font-size:14px; border-top:1px solid var(--line); padding-top:20px; }}
</style>
<main>
  <h1>{title}</h1>
  <p class="lede">{lede}</p>
{figures}
  <p><button id="fs" type="button">{fs_label}</button></p>
  <footer>{repro_note}<br><code>{repro}</code></footer>
</main>
<script>
  // Fullscreen is a labelled button rather than a click handler on the
  // figure: a click belongs to whatever mark is under it.
  document.getElementById('fs').addEventListener('click', function () {{
    var frame = document.querySelector('.frame');
    if (document.fullscreenElement) {{ document.exitFullscreen(); }}
    else if (frame.requestFullscreen) {{ frame.requestFullscreen(); }}
  }});
</script>
</html>
'''


def kit_page(
    title: str,
    lede: str,
    figures: List[tuple[str, str]],
    repro: str,
    repro_note: str,
    french: bool,
) -> str:
    """
    The kit's ``index.html``.

    Uses ``<object>`` rather than ``<img>``: an ``<img>`` sandboxes the SVG,
    which kills the native ``<title>`` tooltips these figures carry and
    blocks any linked webfont. And ``:fullscreen`` sets ``overflow:auto``,
    because a promoted element loses the page's scrolling and a tall figure
    would have its lower half simply unreachable.

    Parameters
    ----------
    title, lede : str
        Page heading and standfirst.
    figures : list of (str, str)
        ``(svg filename, caption)`` pairs, in display order.
    repro, repro_note : str
        The command that rebuilds the output, and a sentence about it.
    french : bool
        Write the chrome in French.

    Returns
    -------
    str
        A complete, self-contained HTML page.
    """
    blocks = "\n".join(
        f'  <div class="frame">\n'
        f'    <object data="{name}" type="image/svg+xml" aria-label="{caption}"></object>\n'
        f"  </div>"
        for name, caption in figures
    )
    return _PAGE.format(
        lang="fr" if french else "en",
        title=title,
        lede=lede,
        figures=blocks,
        fs_label="⤢ Plein écran" if french else "⤢ Fullscreen",
        repro=repro,
        repro_note=repro_note,
    )


# ──────────────────────────────────────────────────────────────────────────
# Kit definitions
# ──────────────────────────────────────────────────────────────────────────

#: One entry per kit. ``sources`` are copied into ``lib/``; ``data`` is
#: copied to the kit root (where the vendored modules expect to find it).
KITS: Dict[str, Dict[str, Any]] = {
    "accessibility": {
        "repo": "sprezzature-accessibility",
        "sources": ["scripts/lint_a11y.py", "scripts/_argparse.py", "scripts/_lang.py"],
        "data": [],
        "sample": _SAMPLE_HTML,
        "run": lint_run(
            repo="sprezzature-accessibility",
            import_line="from lint_a11y import lint_html",
            key="f.rule",
            severity='WARN if name in _SOFT else ERROR',
            call='lint_html((here / "sample.html").read_text(encoding="utf-8"))',
            aria="Accessibility findings by rule",
            headline="What this page gets wrong",
            group="rule",
        ).replace(
            "ROW = 26",
            'ROW = 26\n\n#: Rules that make a page harder to use rather than impossible.\n'
            '_SOFT = ("img-redundant-aria", "color-only-state", "motion-no-reduce-guard",\n'
            '         "track-missing-srclang", "body-text-tracking-tight")',
        ),
        "outputs": [("report.svg", "Accessibility findings, grouped by rule")],
        "title": {
            "en": "What this page gets wrong",
            "fr": "Ce que cette page rate",
        },
        "lede": {
            "en": "Twenty WCAG-oriented checks over a sample page — images, controls, "
                  "headings, motion and captions. Replace sample.html with a page of "
                  "your own and run it again.",
            "fr": "Vingt contrôles inspirés du WCAG sur une page d'exemple — images, "
                  "commandes, titres, animation et sous-titres. Remplacez sample.html "
                  "par une page à vous et relancez.",
        },
    },
    "ux-laws": {
        "repo": "sprezzature-ux-laws",
        "sources": ["scripts/audit_laws_of_ux.py", "scripts/_argparse.py"],
        "data": [],
        "sample": _SAMPLE_HTML,
        "run": lint_run(
            repo="sprezzature-ux-laws",
            import_line="from audit_laws_of_ux import audit_html",
            key="f.law",
            severity='ERROR if any(g.severity == "error" for g in findings if g.law == name) else WARN',
            call='audit_html((here / "sample.html").read_text(encoding="utf-8"))',
            aria="Laws-of-UX findings by law",
            headline="Where this interface fights its reader",
            group="law",
        ),
        "outputs": [("report.svg", "Laws-of-UX findings, grouped by law")],
        "title": {
            "en": "Where this interface fights its reader",
            "fr": "Où cette interface contrarie son lecteur",
        },
        "lede": {
            "en": "Eight laws of UX — Hick, Miller, Fitts, Jakob, Tesler and friends — "
                  "read off the structure of a sample page. These are prompts for a "
                  "designer, not verdicts: no linter knows your audience.",
            "fr": "Huit lois de l'UX — Hick, Miller, Fitts, Jakob, Tesler et les autres — "
                  "lues dans la structure d'une page d'exemple. Ce sont des questions "
                  "pour un concepteur, pas des verdicts : aucun outil ne connaît votre public.",
        },
    },
    "colors": {
        "repo": "sprezzature-colors",
        "sources": ["scripts/_colors.py"],
        "data": [("references/palette.csv", "references/palette.csv")],
        "run": _COLORS_RUN,
        "outputs": [
            ("contrast.svg", "Contrast ratio for every pair in the palette"),
            ("cvd.svg", "The palette as seen with each colour-vision deficiency"),
        ],
        "title": {
            "en": "Is this palette readable?",
            "fr": "Cette palette est-elle lisible ?",
        },
        "lede": {
            "en": "Every pair scored against the WCAG threshold, and the whole palette "
                  "put through the three common colour-vision deficiencies. Edit "
                  "palette.csv with your own brand colours and run it again.",
            "fr": "Chaque paire notée face au seuil WCAG, et toute la palette passée "
                  "par les trois déficiences visuelles courantes. Remplacez "
                  "palette.csv par vos couleurs de marque et relancez.",
        },
    },
}


def build_kit(name: str, spec: Dict[str, Any], out_dir: Path, language: str) -> tuple[bool, str]:
    """
    Assemble one kit and zip it.

    Parameters
    ----------
    name : str
        Kit slug, e.g. ``"colors"``.
    spec : dict
        Its entry from :data:`KITS`.
    out_dir : pathlib.Path
        Where the ``.zip`` goes.
    language : str
        ``"en"`` or ``"fr"``.

    Returns
    -------
    tuple of (bool, str)
        Success flag and a one-line report.
    """
    french = language == "fr"
    repo = HOME / spec["repo"]
    if not repo.is_dir():
        return False, f"{name}: {repo} not found"

    staging = out_dir / f".build-{name}-{language}"
    if staging.exists():
        shutil.rmtree(staging)
    kit = staging / name
    (kit / "lib").mkdir(parents=True)

    vendored: set[str] = set()
    for relative in spec["sources"]:
        source = repo / relative
        if not source.is_file():
            return False, f"{name}: missing source {relative}"
        shutil.copy2(source, kit / "lib" / source.name)
        vendored.add(source.stem)

    for relative, target in spec["data"]:
        source = repo / relative
        if not source.is_file():
            return False, f"{name}: missing data {relative}"
        destination = kit / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    (kit / "run.py").write_text(spec["run"], encoding="utf-8")
    if spec.get("sample"):
        (kit / "sample.html").write_text(spec["sample"], encoding="utf-8")

    # macOS writes AppleDouble sidecars ("._run.py") on non-HFS volumes, and
    # they match *.py while being binary. Skip anything dot-prefixed.
    python_files = [f for f in sorted(kit.rglob("*.py")) if not f.name.startswith(".")]
    problems = verify_stdlib_only(python_files, vendored)
    if problems:
        return False, f"{name}: not standalone — {problems[0]}"

    # Run it now: a kit that ships without ever having been executed is a
    # promise, not a deliverable. This also produces the SVGs the page loads.
    result = subprocess.run(
        [sys.executable, "run.py"], cwd=kit, capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0:
        return False, f"{name}: run.py failed — {result.stderr.strip().splitlines()[-1:]}"

    page_name = "index.html"
    (kit / page_name).write_text(
        kit_page(
            title=spec["title"][language],
            lede=spec["lede"][language],
            figures=spec["outputs"],
            repro="python3 run.py",
            repro_note=(
                "Modifiez les données, relancez, les figures changent."
                if french
                else "Edit the data, run it again, the figures change."
            ),
            french=french,
        ),
        encoding="utf-8",
    )

    readme = "LISEZMOI.md" if french else "README.md"
    (kit / readme).write_text(kit_readme(name, spec, french), encoding="utf-8")

    target_dir = out_dir / "fr" if french else out_dir
    size = write_zip(kit, target_dir / f"{name}.zip")
    shutil.rmtree(staging)
    return True, f"{name}: {size // 1024} KB zip (stdlib only)"


def kit_readme(name: str, spec: Dict[str, Any], french: bool) -> str:
    """The kit's README, in English or French."""
    outputs = "\n".join(f"| `{f}` | {c} |" for f, c in spec["outputs"])
    if french:
        return f"""# {spec['title']['fr']}

{spec['lede']['fr']}

## Lancer

```bash
python3 run.py
```

Puis ouvrez `index.html` dans un navigateur.

**Aucune installation.** Ce kit n'utilise que la bibliothèque standard de
Python : pas de `pip install`, pas de réseau, pas de compte. Python 3.10 ou
plus récent suffit.

## Contenu

| Fichier | Rôle |
|---|---|
| `run.py` | Le script. C'est le fichier intéressant : il lit les données et écrit les figures. |
| `lib/` | L'outil, copié tel quel depuis `{spec['repo']}`. |
| `references/palette.csv` | Les données. Modifiez-les, relancez, tout change. |
{outputs}
| `index.html` | La page qui ouvre les figures : plein écran, survol. |

## Modifier

Remplacez les lignes de `references/palette.csv` par vos propres couleurs et
relancez. Le SVG est écrit directement, balise par balise — aucune
bibliothèque graphique n'intervient, ce qui est précisément pourquoi rien
n'est à installer.

## Licence

BSD-3-Clause · <https://github.com/warith-harchaoui/{spec['repo']}>
"""
    return f"""# {spec['title']['en']}

{spec['lede']['en']}

## Run it

```bash
python3 run.py
```

Then open `index.html` in a browser.

**Nothing to install.** This kit uses the Python standard library only: no
`pip install`, no network, no account. Python 3.10 or newer is enough.

## What is in here

| File | Role |
|---|---|
| `run.py` | The script. This is the interesting one: it reads the data and writes the figures. |
| `lib/` | The tool, copied verbatim from `{spec['repo']}`. |
| `references/palette.csv` | The data. Edit it, re-run, everything changes. |
{outputs}
| `index.html` | The page that opens the figures: fullscreen, hover. |

## Change it

Replace the rows in `references/palette.csv` with your own colours and run it
again. The SVG is written directly, tag by tag — no charting library is
involved, which is exactly why there is nothing to install.

## Licence

BSD-3-Clause · <https://github.com/warith-harchaoui/{spec['repo']}>
"""


def main(argv: "list[str] | None" = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="build_tool_kits.py",
        description="Build a runnable, standard-library-only zip for each toolbox.",
    )
    parser.add_argument("--only", action="append", help="Build just this kit. Repeatable.")
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path(__file__).resolve().parent.parent / "kits",
        help="Where the zips go. Defaults to web/kits/.",
    )
    args = parser.parse_args(argv)

    wanted = list(args.only) if args.only else sorted(KITS)
    unknown = [n for n in wanted if n not in KITS]
    if unknown:
        parser.error(f"unknown kit(s): {unknown}. Known: {sorted(KITS)}")

    built = failed = 0
    for language in ("en", "fr"):
        print(f"\n── {language} ──")
        for name in wanted:
            ok, message = build_kit(name, KITS[name], args.out_dir, language)
            print(("  " if ok else "  ✗ ") + message)
            built += ok
            failed += not ok
    print(f"\n{built} kit(s) built, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
