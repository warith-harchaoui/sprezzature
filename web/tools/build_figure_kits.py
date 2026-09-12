#!/usr/bin/env python3
"""
build_figure_kits
=================

One downloadable, runnable kit per card in the figure gallery.

A reader who likes a chart on ``figures.html`` currently gets a picture. The
kit gives them the thing that made it: the data as a CSV they can swap, the
generator that reads it, and the interactive SVG it produces, in a zip that
runs on a bare Python with nothing but the standard library (a few charts add
``numpy``). No account, no build step, no framework.

Each kit is deliberately **two Python files**, so the interesting one is
obvious at a glance:

``make_<slug>.py``
    The real generator from ``sprezzature-figures``, near-verbatim: same
    layout maths, same house style, same tooltip wiring. Only its import
    block is rewritten (the repo splits helpers across ``_style.py`` /
    ``_svg.py`` / … , the kit bundles them) and a ``data.csv`` loader is
    spliced into its ``__main__``. This is the file worth reading.

``sprezzature_svg.py``
    The drawing engine those imports resolve to: scales, SVG path builders,
    the palette, the label placer, the hover/fullscreen chrome, and the
    write-and-report tail. Concatenated from the repo's helper modules, which
    share no top-level names, so the merge is a plain join rather than a
    rewrite.

Fonts
-----

A figure in the repo embeds its typefaces as base64 WOFF2, which is right for
an artifact that must render identically forever, offline, in any rasteriser —
and costs about 430 KB per SVG. A kit is opened in a browser, so it links the
same faces from Google Fonts instead and the SVG lands around 20 KB. The
tradeoff is real and belongs in the README: an ``@import`` only fetches when
the SVG is the document (opened directly, or embedded via ``<object>`` /
``<iframe>``). Inside an ``<img>`` tag the browser blocks external requests and
the figure falls back to the next family in the stack.

No PNG ships in the kit. Rasterising needs a renderer well outside the
numpy/scipy/pandas budget, and a browser's "Save as image" covers the case.

Usage
-----
::

    python web/tools/build_figure_kits.py                    # every gallery card
    python web/tools/build_figure_kits.py --only bar,voronoi # a couple, while iterating
    python web/tools/build_figure_kits.py --check            # verify, write nothing

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import ast
import csv
import html
import io
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree
from typing import Dict, Iterable, Sequence

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent

#: Where the standalone generators live. The monorepo keeps the prose; the
#: code was split out (see SPLIT.md), so the kits are built against a
#: checkout sitting beside this one.
DEFAULT_FIGURES_REPO: Path = REPO_ROOT.parent / "sprezzature-figures"

#: Gallery pages whose cards get a kit link. Both must stay in step: the
#: French page mirrors the English one card for card.
GALLERY_PAGES: tuple[str, ...] = ("web/figures.html", "web/fr/figures.html")

#: Where the built zips land, relative to the repo root. Served as
#: ``https://sprezzature.ai/kits/<slug>.zip``.
KITS_DIR: str = "web/kits"

#: Helper modules concatenated into ``sprezzature_svg.py``, in dependency
#: order. Verified collision-free: no two of them define the same top-level
#: name, so the join needs no renaming.
BUNDLED_HELPERS: tuple[str, ...] = (
    "_scale",
    "_textfit",
    "_style",
    "_svg",
    "_labels",
    "_interactive",
)

#: Names from ``_render.py`` the kit replaces rather than vendors: they write
#: into the repo's ``assets/`` tree, or rasterise through a dependency a kit
#: is not allowed to have. Everything else in that module (the CLI flag table,
#: ``render_cli`` itself) is vendored verbatim so a kit's ``--help`` matches
#: the repo's.
RENDER_OVERRIDES: frozenset[str] = frozenset(
    {
        "_render_scale",
        "_svg_to_png_bytes",
        "_svg_to_html",
        "_write_in_format",
        "svg_example_path",
        "write_svg",
        "write_raster_companions",
    }
)

#: Top-level import lines dropped when a helper body is inlined: the bundle
#: is one module, so its parts no longer import each other, and the
#: consolidated header below carries the standard-library ones. Anchored at
#: column zero on purpose — an indented ``sys.path.insert`` is runtime logic
#: inside a function, and deleting it leaves an ``if`` with no body.
_DROP_IMPORT = re.compile(
    r"^(from\s+(__future__|_[a-z]+|sprezzature_figures)\b|import\s+resvg_py\b|sys\.path\.insert\()"
)

#: The same imports written *inside* a function (the repo defers a few to keep
#: module import cheap). Those cannot simply vanish without breaking the block,
#: so they become a ``pass``: in the bundle the names they wanted are already
#: at module level.
_DEFERRED_IMPORT = re.compile(
    r"^(\s+)(from\s+(_[a-z]+|sprezzature_figures)[\w.]*\s+import\b|import\s+resvg_py\b)"
)

#: Standard-library imports the merged bundle needs, once, at the top.
_BUNDLE_IMPORTS: str = """from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import textwrap
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from typing import List as _List
"""


def _strip_module_docstring(source: str) -> str:
    """
    Drop a module's own docstring, keeping every other docstring.

    The helper modules open with several hundred words explaining their place
    in the repo's layout — orientation that is wrong once the module is one
    section of a single bundled file. Function and class docstrings stay:
    they document behaviour, which is exactly what a kit reader wants.

    Parameters
    ----------
    source : str
        Full module source.

    Returns
    -------
    str
        The source with a leading string expression removed, if present.
    """
    tree = ast.parse(source)
    if not (tree.body and isinstance(tree.body[0], ast.Expr)):
        return source
    first = tree.body[0].value
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return source
    lines = source.splitlines(keepends=True)
    return "".join(lines[tree.body[0].end_lineno :])


def _inline(source: str) -> str:
    """Strip a helper body down to what the bundle can concatenate."""
    kept: list[str] = []
    for line in _strip_module_docstring(source).splitlines(keepends=True):
        if _DROP_IMPORT.match(line):
            continue
        deferred = _DEFERRED_IMPORT.match(line)
        if deferred:
            kept.append(f"{deferred.group(1)}pass  # bundled: already defined at module level\n")
            continue
        kept.append(line)
    return "".join(kept).strip("\n")


def _drop_top_level(source: str, names: Iterable[str]) -> str:
    """
    Remove named top-level definitions from a module body.

    Used on ``_render.py``: the kit keeps its CLI wiring verbatim and supplies
    its own path/write/raster functions, so the vendored copy has to lose the
    originals before the replacements are appended.

    Parameters
    ----------
    source : str
        Module source.
    names : iterable of str
        Top-level function, class or assignment names to drop.

    Returns
    -------
    str
        The source without those definitions.
    """
    wanted = set(names)
    tree = ast.parse(source)
    cuts: list[tuple[int, int]] = []
    for node in tree.body:
        label: str | None = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            label = node.name
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            label = node.targets[0].id
        if label in wanted:
            cuts.append((node.lineno - 1, node.end_lineno))
    lines = source.splitlines(keepends=True)
    for start, end in reversed(cuts):
        # Walk back over the decorator-free comment block that introduces the
        # definition, so a dropped function does not leave its comment behind.
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        del lines[start:end]
    return "".join(lines)


def _kit_runtime() -> str:
    """
    The kit-specific tail of ``sprezzature_svg.py``.

    Three jobs the repo's own helpers do differently: link the typefaces
    instead of embedding them, write the SVG next to the script instead of
    into the repo's asset tree, and refuse to rasterise instead of reaching
    for a renderer the kit does not ship.
    """
    return '''

# ──────────────────────────────────────────────────────────────────────────
# Typography
# ──────────────────────────────────────────────────────────────────────────

#: The house stacks. The bundled repo embeds these faces as base64 WOFF2;
#: a kit links them (see GOOGLE_FONTS_IMPORT) and keeps the SVG small.
_THEME_STACKS: Dict[str, Dict[str, str]] = {
    "corporate": {
        "chrome": "Roboto, system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif",
        "mono": "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
    },
    "academic": {
        "chrome": "'LM Roman', 'Latin Modern Roman', Georgia, 'Times New Roman', serif",
        "mono": "'LM Mono', 'Latin Modern Mono', ui-monospace, Menlo, monospace",
    },
}

#: Pulled from Google Fonts rather than embedded. This only fetches when the
#: SVG *is* the document — opened directly, or embedded via <object> /
#: <iframe>. Inside an <img> tag the browser blocks external requests and the
#: next family in the stack renders instead, which is why every stack above
#: ends in a system face rather than a bare generic.
#:
#: The ampersands are written ``&amp;``, and that is not optional: an SVG is
#: XML, so a bare ``&`` is an unterminated entity reference and the whole
#: document fails to parse. A browser shows "EntityRef: expecting ';'" and
#: renders nothing at all — not a missing font, a blank figure.
GOOGLE_FONTS_IMPORT: str = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Roboto:ital,wght@0,100..900;1,100..900&amp;"
    "family=Roboto+Mono:ital,wght@0,100..700;1,100..700&amp;display=swap');"
)

#: Kept for call-signature parity with the repo's font module.
DEFAULT_SVG_FACES: Tuple[str, ...] = ("sans", "mono")


def chrome_stack_for_theme(theme: str = "corporate") -> str:
    """CSS font stack for titles, labels and axis text."""
    return _THEME_STACKS.get(theme, _THEME_STACKS["corporate"])["chrome"]


def mono_stack_for_theme(theme: str = "corporate") -> str:
    """CSS font stack for tick values and numeric labels."""
    return _THEME_STACKS.get(theme, _THEME_STACKS["corporate"])["mono"]


def svg_font_defs(keys: Sequence[str] = DEFAULT_SVG_FACES) -> str:
    """A ``<defs>`` block linking the house faces, ready to splice into an SVG."""
    del keys
    return f"<defs><style>{GOOGLE_FONTS_IMPORT}</style></defs>"


def svg_faces_for_theme(theme: str = "corporate") -> Tuple[str, ...]:
    """Face keys to declare for `theme`. One link covers both stacks here."""
    del theme
    return DEFAULT_SVG_FACES


# ──────────────────────────────────────────────────────────────────────────
# Reading the data
# ──────────────────────────────────────────────────────────────────────────


def load_rows(
    path: "str | Path | None" = None,
    *,
    text_columns: Sequence[str] = (),
) -> List[Dict[str, Any]]:
    """
    Read the kit's data file back into the row dicts the generator expects.

    Two formats, chosen by what the chart actually holds. A chart whose rows
    are flat — one number per column — ships ``data.csv``, because the point
    of CSV is that it opens in a spreadsheet. A chart whose rows carry a list
    (a bullet chart's qualitative bands, a horizon chart's series, a
    set-membership list) ships ``data.json`` instead: forcing those into a
    cell gives you ``"[""Email"", ""SMS""]"``, which round-trips fine and is
    unreadable, losing the one advantage CSV had.

    From CSV, values are coerced back: numbers to ``int`` or ``float``,
    ``true`` / ``false`` to booleans, an empty cell to ``None``. JSON needs
    none of that — it kept the types.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        Data file to read. ``None`` (the default) looks beside the generator
        for ``data.json`` first, then ``data.csv``.
    text_columns : sequence of str, optional
        Columns to leave as text even when they look numeric. A year used as
        a category label ("2023") is the usual case: CSV cannot distinguish
        it from the number 2023, and the chart wants the label. Ignored for
        JSON, which never lost the distinction.

    Returns
    -------
    list of dict
        One dict per data row.

    Raises
    ------
    FileNotFoundError
        If `path` is given and missing, or if neither default file is there.
    """
    here = Path(__file__).resolve().parent
    if path is None:
        for candidate in ("data.json", "data.csv"):
            if (here / candidate).exists():
                source = here / candidate
                break
        else:
            raise FileNotFoundError("no data.json or data.csv beside this script")
    else:
        source = Path(path)
        if not source.is_absolute():
            source = here / source

    if source.suffix == ".json":
        return json.loads(source.read_text(encoding="utf-8"))

    keep = set(text_columns)
    with source.open(newline="", encoding="utf-8") as handle:
        return [
            {key: (value if key in keep else _coerce(value)) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _coerce(raw: "str | None") -> Any:
    """Turn one CSV cell back into the Python value it was written from."""
    if raw is None or raw == "":
        return None
    if raw[0] in "[{":
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    lowered = raw.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


# ──────────────────────────────────────────────────────────────────────────
# Writing the figure
# ──────────────────────────────────────────────────────────────────────────


def svg_example_path(script_file: str, figure_id: str) -> Path:
    """The default output path: ``<figure_id>.svg`` beside the generator."""
    return Path(script_file).resolve().parent / f"{figure_id}.svg"


def write_svg(out: Path, svg: str, *, embed_fonts: bool = True, theme: str = "corporate") -> Path:
    """
    Write `svg` to `out`, splicing in the font link, and report where it went.

    Parameters
    ----------
    out : pathlib.Path
        Destination ``.svg`` path.
    svg : str
        The complete SVG document.
    embed_fonts : bool, optional
        Add the ``@font-face`` link block when the document has none.
    theme : str, optional
        Accepted for parity with the generators; both themes link the same
        stylesheet here.

    Returns
    -------
    pathlib.Path
        `out` unchanged.
    """
    del theme
    if embed_fonts and "@import" not in svg and svg.lstrip().startswith("<svg"):
        insert_at = svg.index(">") + 1
        svg = svg[:insert_at] + svg_font_defs() + svg[insert_at:]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out}")
    return out


def write_raster_companions(svg: str, script_file: str, figure_id: str, *, zoom: float = 2.0) -> None:
    """
    No-op: a kit ships vector only.

    The repo writes a PNG beside the SVG for places that cannot take vector
    art. Rasterising needs a renderer far outside this kit's dependency
    budget, so the kit stops at the SVG — open it in a browser and use "Save
    as image" if a raster is what you need.
    """
    del svg, script_file, figure_id, zoom
'''


def bundle_source(figures_repo: Path) -> str:
    """
    Assemble ``sprezzature_svg.py``.

    Parameters
    ----------
    figures_repo : Path
        Root of the standalone ``sprezzature-figures`` checkout.

    Returns
    -------
    str
        The complete bundled module.
    """
    scripts = figures_repo / "scripts"
    parts: list[str] = [
        '"""',
        "sprezzature_svg — the drawing engine behind this figure, in one file.",
        "",
        "Scales and tick placement, SVG path builders, the house palette, the",
        "label placer, the hover and fullscreen chrome, and the write-and-report",
        "tail. Merged from the helper modules of sprezzature-figures so the kit",
        "stays at two Python files; the sections below are in dependency order",
        "and keep their original docstrings.",
        "",
        "The one deliberate difference from the repo: typefaces are linked from",
        "Google Fonts instead of embedded as base64, which takes a figure from",
        "roughly 430 KB to roughly 20 KB. See GOOGLE_FONTS_IMPORT for what that",
        "costs you.",
        "",
        "Author",
        "------",
        "`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_",
        '"""',
        "",
        _BUNDLE_IMPORTS,
    ]

    for helper in BUNDLED_HELPERS:
        body = _inline((scripts / f"{helper}.py").read_text(encoding="utf-8"))
        parts.append(
            f"\n# {'─' * 74}\n"
            f"# from {helper}.py\n"
            f"# {'─' * 74}\n\n{body}\n"
        )

    parts.append(_kit_runtime())

    render = _drop_top_level((scripts / "_render.py").read_text(encoding="utf-8"), RENDER_OVERRIDES)
    parts.append(
        f"\n# {'─' * 74}\n"
        f"# the command line, from _render.py\n"
        f"# {'─' * 74}\n\n{_inline(render)}\n"
    )
    return "\n".join(parts)


def generator_source(path: Path, rows: Sequence[dict]) -> str:
    """
    Rewrite one ``make_<slug>.py`` so it runs inside a kit.

    Four mechanical changes, and nothing else: helper imports point at the
    bundle, the repo's artifact path becomes "beside this script", any
    ``assets/`` read is re-rooted into the kit, and a ``data.csv`` loader is
    spliced above ``__main__`` so editing the CSV changes the figure. The
    layout maths, the house style and the tooltip wiring are untouched — the
    point of the kit is that this really is the generator.

    Parameters
    ----------
    path : Path
        The generator in the standalone repo.
    rows : sequence of dict
        Its ``DEMO_DATA``, used to work out which columns must survive the
        CSV round-trip as text.

    Returns
    -------
    str
        The kit's copy of the generator.
    """
    source = path.read_text(encoding="utf-8")
    source = re.sub(
        r"^from (?:_[a-z]+|sprezzature_figures\.fonts) import ",
        "from sprezzature_svg import ",
        source,
        flags=re.MULTILINE,
    )
    # A couple of generators reach for a whole helper module rather than
    # naming what they want (``import _style`` … ``_style.CORNERS``).
    source = re.sub(
        r"^import (_[a-z]+)$",
        r"import sprezzature_svg as \1",
        source,
        flags=re.MULTILINE,
    )
    # The repo's generators put their own folder on sys.path to find the
    # helper modules; in a kit the bundle is a sibling, already importable.
    source = re.sub(r"^sys\.path\.insert\(.*\n", "", source, flags=re.MULTILINE)
    # A dozen generators hard-code the repo's artifact path instead of asking
    # svg_example_path for it. In a kit the figure belongs beside its source.
    source = _SVG_EXAMPLES_PATH.sub("Path(__file__).resolve().parent", source)
    # Whatever else a generator reads out of ``assets/`` (a map's country
    # outlines) ships inside the kit, one level closer than in the repo.
    source = _ASSETS_PATH.sub('Path(__file__).resolve().parent\n    / "assets"', source)
    source = source.replace(
        'if __name__ == "__main__":',
        _main_preamble(rows) + 'if __name__ == "__main__":',
        1,
    )
    return source


#: ``Path(__file__).resolve().parent.parent / "assets" / "svg-examples"`` —
#: the repo's artifact folder, written inline (and across several lines) by
#: the generators that predate ``svg_example_path``.
_SVG_EXAMPLES_PATH = re.compile(
    r'Path\(__file__\)\.resolve\(\)\.parent\.parent\s*/\s*"assets"\s*/\s*"svg-examples"'
)

#: Any other ``assets/`` read, kept but re-rooted inside the kit.
_ASSETS_PATH = re.compile(r'Path\(__file__\)\.resolve\(\)\.parent\.parent\s*/\s*"assets"')

#: Asset files a generator reads, as the path segments after ``"assets"``.
#: Matched on the rewritten source so the kit copies exactly what will be
#: looked up at run time.
_ASSET_READ = re.compile(r'/\s*"assets"\s*((?:/\s*"[\w./-]+"\s*)+)')


def kit_assets(source: str) -> list[str]:
    """
    Relative paths under ``assets/`` that a generator reads at run time.

    Three map generators need a country or département outline; everything
    else computes its geometry from the CSV alone.

    Parameters
    ----------
    source : str
        A rewritten generator source.

    Returns
    -------
    list of str
        Paths like ``geo/countries-110m.json``, relative to ``assets/``.
    """
    found: list[str] = []
    for match in _ASSET_READ.finditer(source):
        parts = re.findall(r'"([\w./-]+)"', match.group(1))
        if parts and "." in parts[-1]:
            relative = "/".join(parts)
            if relative not in found:
                found.append(relative)
    return found


def text_columns(rows: Sequence[dict]) -> tuple[str, ...]:
    """
    Columns that must come back from the CSV as text, not as numbers.

    A slope chart's ``period`` column holds ``"2023"``: a string in the data,
    and a string the generator calls ``.replace()`` on. CSV cannot tell that
    from the number 2023, so the type is recorded at build time and passed
    back in explicitly.

    Parameters
    ----------
    rows : sequence of dict
        The generator's demo rows.

    Returns
    -------
    tuple of str
        Column names to keep as strings, in column order.
    """
    numeric = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
    out: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key in out or not isinstance(value, str):
                continue
            if any(isinstance(r.get(key), str) and numeric.match(r[key]) for r in rows):
                out.append(key)
    return tuple(out)


def _main_preamble(rows: Sequence[dict]) -> str:
    """The data loader spliced above a generator's ``__main__``."""
    name = data_filename(rows)
    # JSON kept the types, so the text-column rescue is a CSV problem only.
    keep = text_columns(rows) if name.endswith(".csv") else ()
    argument = f", text_columns={keep!r}" if keep else ""
    note = (
        f"\n# {', '.join(keep)} stays text: the values look numeric but the\n"
        "# generator treats them as labels.\n"
        if keep
        else ""
    )
    return _MAIN_PREAMBLE.format(argument=argument, note=note, name=name)


#: Spliced in just above the generator's ``__main__``. The repo's generators
#: read a module-level ``DEMO_DATA``; a kit reads the CSV beside them, so the
#: reader's first experiment is "edit the numbers and run it again".
_MAIN_PREAMBLE: str = '''
# ── kit: the data comes from {name} ──────────────────────────────────────
# The generator keeps its own DEMO_DATA above as a fallback and as a record
# of the expected column names. When {name} is present (it ships with this
# kit), it wins: edit the data, re-run this file, and the figure changes.{note}
from sprezzature_svg import load_rows  # noqa: E402

try:
    DEMO_DATA = load_rows("{name}"{argument}) or DEMO_DATA
except FileNotFoundError:
    pass


'''


def is_tabular(rows: Sequence[dict]) -> bool:
    """
    True when every value is a scalar, so the rows fit a real table.

    The kits ship CSV because CSV opens in a spreadsheet. That advantage
    disappears the moment a row carries a list: the cell becomes
    ``"[""Email"", ""SMS""]"``, which round-trips correctly and cannot be
    read or edited by the spreadsheet the format was chosen for. Four charts
    in the catalogue are in that case — a bullet chart's qualitative bands, a
    horizon chart's series, and the two set-membership charts — and they ship
    JSON instead.

    Parameters
    ----------
    rows : sequence of dict
        The generator's ``DEMO_DATA``.

    Returns
    -------
    bool
        ``True`` for CSV, ``False`` for JSON.
    """
    return all(
        not isinstance(value, (list, dict, tuple))
        for row in rows
        for value in row.values()
    )


def data_filename(rows: Sequence[dict]) -> str:
    """``"data.csv"`` or ``"data.json"``, whichever `rows` deserve."""
    return "data.csv" if is_tabular(rows) else "data.json"


def rows_to_json(rows: Sequence[dict]) -> str:
    """Serialise the demo rows as indented JSON, trailing newline included."""
    return json.dumps(list(rows), ensure_ascii=False, indent=2) + "\n"


def rows_to_csv(rows: Sequence[dict]) -> str:
    """
    Serialise the generator's demo rows as CSV.

    A value that is itself a list or dict (a bullet chart's qualitative
    bands, a horizon chart's series, a set-membership list) is written as
    JSON inside its cell, so the file stays one readable table and
    :func:`load_rows` can put it back exactly.

    Parameters
    ----------
    rows : sequence of dict
        Row dicts, as the generator's ``DEMO_DATA``.

    Returns
    -------
    str
        CSV text, header first.
    """
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
        )
    return buffer.getvalue()


def discover_cards(page: Path) -> list[str]:
    """
    Gallery slugs, in page order, from a figures page's zoom targets.

    Works on either language page: the French one prefixes its paths with
    ``../`` and serves localised figures out of ``img/figures/fr/``.
    """
    seen: list[str] = []
    for match in _CARD_SLUG.finditer(page.read_text(encoding="utf-8")):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen



def card_titles(page: Path) -> Dict[str, str]:
    """
    Map gallery slug to the human name its card shows.

    Read from the page rather than derived from the slug: "prcurve" is
    "Precision-recall curve" and "sfdp-largegraph" is "Large graph", and no
    amount of de-hyphenating gets there.

    Parameters
    ----------
    page : Path
        A figures gallery page.

    Returns
    -------
    dict of str to str
        Slug to display name; slugs whose card has no bold name are absent.
    """
    html = page.read_text(encoding="utf-8")
    titles: Dict[str, str] = {}
    for block in _FIGURE_BLOCK.finditer(html):
        slug_match = _CARD_SLUG.search(block.group(0))
        name_match = re.search(r'<span class="font-medium">([^<]+)</span>', block.group(0))
        if slug_match and name_match:
            titles[slug_match.group(1)] = name_match.group(1).strip()
    return titles


def resolve_generator(slug: str, scripts: Path) -> Path:
    """
    Find the generator behind a gallery slug.

    The gallery and the repo disagree on separators for a handful of figures
    (``embedding_projector`` on disk, ``embedding-projector`` in the page), so
    both spellings are tried.

    Raises
    ------
    FileNotFoundError
        When no generator matches, which means the gallery advertises a
        figure the code cannot draw.
    """
    for candidate in (slug, slug.replace("-", "_"), slug.replace("_", "-")):
        path = scripts / f"make_{candidate}.py"
        if path.is_file():
            return path
    raise FileNotFoundError(f"no generator for gallery card '{slug}'")


#: Third-party packages a kit may pin, mapped to the version this build was
#: verified against. Deliberately short: the generators compute their own
#: geometry, so the only real dependency anywhere in the catalogue is numpy,
#: and most kits need nothing at all.
PINS: dict[str, str] = {
    "numpy": "2.3.5",
    "scipy": "1.17.1",
    "pandas": "2.3.3",
}


def detect_requirements(sources: Iterable[str]) -> list[str]:
    """
    Which pinned packages this kit's Python files actually import.

    Parameters
    ----------
    sources : iterable of str
        The kit's Python source texts.

    Returns
    -------
    list of str
        ``package==version`` lines, alphabetical. Empty when the kit runs on
        the standard library alone.
    """
    found: set[str] = set()
    for source in sources:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                found |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".")[0])
    return [f"{name}=={PINS[name]}" for name in sorted(found & PINS.keys())]


def requirements_text(pins: Sequence[str]) -> str:
    """
    The kit's ``requirements.txt``, pinned exactly.

    Only called when there is something to pin. A file whose entire content
    says "you need nothing" is worse than no file: it is one more thing to
    open, and it invites a ``pip install -r`` that does nothing. Most kits in
    the catalogue are standard-library-only and simply do not ship one — see
    :func:`build_kit`.
    """
    return (
        "# Pinned to the versions this kit was built and verified against.\n"
        "# The generator computes its own geometry and writes its own SVG, so\n"
        "# there is no plotting library here and nothing to install beyond this.\n"
        "\n" + "\n".join(pins) + "\n"
    )



def data_script(slug: str, module: str, rows: Sequence[dict], french: bool) -> str:
    """
    The kit's ``make_data.py``: the rows as Python, written out as data.

    Splits the kit the way the figure repository is split — one file computes,
    the other draws. Here the "computation" is only a literal, but keeping it
    a separate step is what makes the data file a real seam rather than a
    dump: edit the Python for structure, edit the data for numbers, and the
    figure redraws from whichever you touched.

    The format follows the rows. Flat rows become ``data.csv``, which opens
    in a spreadsheet; rows carrying a list become ``data.json``, because a
    list crammed into a CSV cell is exactly what a spreadsheet cannot show.

    Parameters
    ----------
    slug : str
        Gallery slug, for the docstring.
    module : str
        The drawing script's file name, quoted in the usage note.
    rows : sequence of dict
        The generator's ``DEMO_DATA``.
    french : bool
        Write the prose in French.

    Returns
    -------
    str
        A standalone script, standard library only.
    """
    name = data_filename(rows)
    tabular = name.endswith(".csv")
    if french:
        why = (
            "CSV, qui est la forme éditable — un tableur, un export, un vrai flux."
            if tabular
            else "JSON, parce que les lignes portent des listes : les écraser dans\n"
            "une cellule de tableur donne du texte illisible."
        )
        head = (
            f"make_data — écrit les données de la figure « {slug} » dans {name}.\n\n"
            "Les lignes sont ci-dessous, en Python : c'est la forme lisible, celle\n"
            f"où l'on voit les colonnes et leur type. Lancer ce script les écrit en\n"
            f"{why}\n\n"
            f"    python3 make_data.py     # écrit {name}\n"
            f"    python3 {module}   # lit {name} et dessine\n\n"
            f"Modifier l'un ou l'autre marche : la figure lit toujours {name}."
        )
    else:
        why = (
            "CSV, which is the editable form — a spreadsheet, an export, a real feed."
            if tabular
            else "JSON, because the rows carry lists: flattening those into a\n"
            "spreadsheet cell produces text nobody can read."
        )
        head = (
            f"make_data — write the data behind the \"{slug}\" figure to {name}.\n\n"
            "The rows are below, as Python: the readable form, where the columns\n"
            f"and their types are visible. Running this writes them as\n"
            f"{why}\n\n"
            f"    python3 make_data.py     # writes {name}\n"
            f"    python3 {module}   # reads {name} and draws\n\n"
            f"Editing either works: the figure always reads {name}."
        )

    literal = json.dumps(list(rows), ensure_ascii=False, indent=4)
    # JSON is valid Python for these values except for the three singletons.
    for a, b in ((": true", ": True"), (": false", ": False"), (": null", ": None")):
        literal = literal.replace(a, b)

    if tabular:
        rows_note = (
            "#: The figure's rows, one flat record each — which is why this kit\n"
            "#: ships CSV: the file opens in a spreadsheet and edits like one."
        )
        writer = '''def write_data(path: "str | Path" = "data.csv") -> Path:
    """Write :data:`ROWS` to `path` as CSV and report where it went."""
    out = Path(path)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent / out

    columns: List[str] = []
    for row in ROWS:
        for key in row:
            if key not in columns:
                columns.append(key)

    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\\n")
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"wrote {out}  ({len(ROWS)} rows)")
    return out'''
        imports = "import csv\nfrom pathlib import Path"
    else:
        rows_note = (
            "#: The figure's rows. Each one carries a list, so this kit ships\n"
            "#: JSON: a list squeezed into a CSV cell round-trips but stops\n"
            "#: being readable, which was the only reason to prefer CSV."
        )
        writer = '''def write_data(path: "str | Path" = "data.json") -> Path:
    """Write :data:`ROWS` to `path` as JSON and report where it went."""
    out = Path(path)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent / out
    out.write_text(json.dumps(ROWS, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(f"wrote {out}  ({len(ROWS)} rows)")
    return out'''
        imports = "import json\nfrom pathlib import Path"

    return f'''"""
{head}

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

{imports}
from typing import Any, Dict, List

{rows_note}
ROWS: List[Dict[str, Any]] = {literal}


{writer}


if __name__ == "__main__":
    write_data()
'''


def kit_page(
    slug: str,
    title: str,
    module: str,
    pins: Sequence[str],
    french: bool,
    rows: Sequence[dict] = (),
) -> str:
    """
    The kit's ``index.html``: a page that opens the figure properly.

    Exists because the two obvious ways to look at the SVG both lose
    something. Double-clicking the file works but gives no context; putting it
    in an ``<img>`` tag sandboxes it, which kills the CSS ``:hover`` the
    tooltips are built on *and* blocks the linked webfont. ``<object>`` keeps
    both, so that is what this page uses.

    Fullscreen is a labelled button rather than a click handler on the figure:
    a click belongs to the mark under it. And ``:fullscreen`` sets
    ``overflow:auto``, because a promoted element loses the page's scrolling
    and a tall figure would have its lower half simply unreachable.

    Parameters
    ----------
    slug : str
        Gallery slug; names the SVG the page loads.
    title : str
        Human-readable figure name for the heading.
    module : str
        The drawing script, quoted in the reproduce note.
    pins : sequence of str
        Pinned requirements, or empty for a standard-library-only kit.
    french : bool
        Write the prose in French.
    rows : sequence of dict, optional
        The figure's rows, consulted only to name the data file the
        reproduce note points at — CSV for flat rows, JSON otherwise.

    Returns
    -------
    str
        A complete, self-contained HTML page.
    """
    install = "python3 -m pip install -r requirements.txt && " if pins else ""
    data_name = data_filename(rows) if rows else "data.csv"
    data_word = ("le CSV" if data_name.endswith(".csv") else "le JSON") if french \
        else ("CSV" if data_name.endswith(".csv") else "JSON")
    if french:
        lang, heading = "fr", title
        lede = ("La figure telle qu'elle est produite par le script du kit. "
                "Survolez une marque pour son relevé exact.")
        hint_b, hint = "Survolez ou cliquez", (
            "— le détail apparaît au pointeur. Un clic l'épingle, ce qui est le "
            "seul moyen de lire une valeur sur écran tactile ; <kbd>Tab</kbd> "
            "parcourt les marques au clavier. Tout est en CSS : la figure ne "
            "contient pas une ligne de JavaScript.")
        fs_on, fs_off = "⤡ Quitter le plein écran", "⤢ Plein écran"
        repro_h = "Refaire la figure"
        repro = (f"{install}python3 make_data.py && python3 {module}")
        repro_note = (f"<code>make_data.py</code> écrit <code>{data_name}</code>, "
                      f"<code>{module}</code> le lit et dessine. Modifiez "
                      f"{data_word}, relancez : la figure change.")
        foot = "Extrait de la galerie"
    else:
        lang, heading = "en", title
        lede = ("The figure exactly as the kit's script produces it. "
                "Hover a mark for its precise reading.")
        hint_b, hint = "Hover or click", (
            "— the detail follows the pointer. A click pins it, which is the "
            "only way to read a value on a touch screen; <kbd>Tab</kbd> walks "
            "the marks from the keyboard. It is all CSS: the figure contains "
            "no JavaScript at all.")
        fs_on, fs_off = "⤡ Leave fullscreen", "⤢ Fullscreen"
        repro_h = "Rebuild it"
        repro = (f"{install}python3 make_data.py && python3 {module}")
        repro_note = (f"<code>make_data.py</code> writes <code>{data_name}</code>, "
                      f"<code>{module}</code> reads it and draws. Edit the "
                      f"{data_word}, run again, the figure changes.")
        foot = "From the gallery at"

    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(heading)}</title>
<style>
  :root {{
    --ink:#1D1D1F; --secondary:#6E6E73; --line:#E5E5EA; --paper:#FFFFFF; --accent:#007AFF;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --ink:#F2F2F7; --secondary:#9A9AA0; --line:#2C2C2E; --paper:#0B0B0C; --accent:#0A84FF; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin:0; padding:40px 24px 64px; background:var(--paper); color:var(--ink);
    font:15px/1.55 Roboto, system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  }}
  main {{ max-width:1180px; margin:0 auto; }}
  h1 {{ font-size:25px; line-height:1.2; margin:0 0 6px; letter-spacing:-0.2px; }}
  h2 {{ font-size:16px; margin:32px 0 8px; }}
  .lede {{ color:var(--secondary); margin:0 0 22px; max-width:62ch; }}
  .hint {{
    display:flex; gap:10px; align-items:baseline;
    border-left:3px solid var(--accent); padding:10px 14px; margin:0 0 20px;
    background:color-mix(in srgb, var(--accent) 7%, transparent);
    border-radius:0 8px 8px 0; font-size:14px; max-width:78ch;
  }}
  .hint b {{ font-weight:600; }}
  kbd {{
    font-family:"Roboto Mono", ui-monospace, monospace; font-size:12px;
    border:1px solid var(--line); border-bottom-width:2px; border-radius:5px;
    padding:0 5px; background:color-mix(in srgb, var(--secondary) 8%, transparent);
  }}
  .toolbar {{ display:flex; margin:0 0 14px; }}
  .toolbar button {{
    font:inherit; font-size:14px; padding:7px 15px; min-height:40px;
    border:1px solid var(--line); border-radius:9px;
    background:transparent; color:var(--secondary); cursor:pointer;
  }}
  .toolbar button:hover {{ border-color:var(--accent); color:var(--accent); }}
  .toolbar button:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  .frame {{
    border:1px solid var(--line); border-radius:14px; overflow:hidden; background:#FFFFFF;
  }}
  /* Fullscreen promotes the element out of the page, so it loses the page's
     own scrolling: without this a tall figure has its lower half unreachable.
     `auto` overrides the `hidden` above, which only clips the rounded corners. */
  .frame:fullscreen {{
    overflow:auto; border:0; border-radius:0; padding:16px;
    -webkit-overflow-scrolling:touch;
  }}
  /* <object>, not <img>: an image element sandboxes the SVG, killing both the
     CSS :hover the tooltips rely on and the linked webfont. */
  .frame object {{ display:block; width:100%; height:auto; border:0; }}
  pre {{
    background:color-mix(in srgb, var(--secondary) 10%, transparent);
    padding:12px 14px; border-radius:9px; overflow-x:auto; font-size:13px;
  }}
  code {{ font-family:"Roboto Mono", ui-monospace, SFMono-Regular, Menlo, monospace; font-size:13px; }}
  p {{ max-width:74ch; }}
  footer {{
    margin-top:40px; padding-top:16px; border-top:1px solid var(--line);
    color:var(--secondary); font-size:13px;
  }}
  a {{ color:var(--accent); }}
</style>
</head>
<body>
<main>
  <h1>{html.escape(heading)}</h1>
  <p class="lede">{lede}</p>

  <p class="hint"><b>{hint_b}</b> <span>{hint}</span></p>

  <div class="toolbar">
    <button id="fs" type="button" aria-pressed="false">{fs_off}</button>
  </div>

  <div class="frame" tabindex="-1">
    <object id="fig" data="{slug}.svg" type="image/svg+xml" aria-label="{html.escape(heading)}">
      <a href="{slug}.svg">{html.escape(heading)} (SVG)</a>
    </object>
  </div>

  <h2>{repro_h}</h2>
  <pre><code>{repro}</code></pre>
  <p>{repro_note}</p>

  <footer>
    {foot} <a href="https://sprezzature.ai/figures.html">sprezzature.ai/figures.html</a>
  </footer>
</main>

<script>
  // The page's only script, and none of it is the figure's: the tooltips are
  // pure CSS and keep working with scripting switched off.
  const frame = document.querySelector('.frame');
  const fig = document.getElementById('fig');
  const fsBtn = document.getElementById('fs');

  fsBtn.addEventListener('click', () => {{
    if (document.fullscreenElement) document.exitFullscreen();
    else if (frame.requestFullscreen) frame.requestFullscreen();
  }});

  // Label follows the real mode, including when the reader leaves with Escape.
  // Focusing the frame is what lets the arrow keys scroll it in fullscreen.
  document.addEventListener('fullscreenchange', () => {{
    const on = document.fullscreenElement === frame;
    fsBtn.textContent = on ? '{fs_on}' : '{fs_off}';
    fsBtn.setAttribute('aria-pressed', String(on));
    if (on) frame.focus();
  }});

  // Escape unpins a latched tooltip. The pin is :focus inside the SVG, so this
  // only has to blur — and it needs same-origin access, which a file:// page
  // does not have. Clicking elsewhere unpins either way.
  document.addEventListener('keydown', e => {{
    if (e.key !== 'Escape') return;
    try {{
      const inner = fig.contentDocument && fig.contentDocument.activeElement;
      if (inner && inner.blur) inner.blur();
    }} catch (_) {{ /* cross-origin under file://; the click path still works */ }}
  }});
</script>
</body>
</html>
"""

def readme_text(
    slug: str,
    module: str,
    pins: Sequence[str],
    *,
    french: bool,
    bilingual: bool = False,
    rows: Sequence[dict] = (),
) -> str:
    """
    The kit's README, in English or French.

    Both say the same four things: what is in the box, how to run it, how to
    look at the result, and the one caveat that bites (an ``<img>`` tag will
    not load the linked fonts).

    Parameters
    ----------
    slug : str
        Gallery slug, used for the figure and SVG names.
    module : str
        The generator's file name.
    pins : sequence of str
        Pinned requirement lines, or empty for a stdlib-only kit.
    french : bool
        Write ``LISEZMOI.md`` rather than ``README.md``.
    rows : sequence of dict, optional
        The figure's rows, consulted only to name the data file in the table.
    bilingual : bool, optional
        Whether the generator carries French chrome text, in which case the
        README says so. This is why one kit serves both gallery pages.
    """
    install = (
        "python3 -m pip install -r requirements.txt"
        if pins
        else "# nothing to install — the standard library is enough"
    )
    # A kit with no third-party imports ships no requirements.txt at all, so
    # the file table must not list one.
    if pins:
        requirements_row = (
            "| `requirements.txt` | Versions épinglées, exactement celles vérifiées. |"
            if french
            else "| `requirements.txt` | Pinned to the exact versions this was verified against. |"
        )
    else:
        requirements_row = (
            "| — | Aucune dépendance : ce kit tourne sur la bibliothèque standard seule. |"
            if french
            else "| — | No dependencies: this kit runs on the standard library alone. |"
        )
    page_row = (
        "| `index.html` | La page qui ouvre la figure : plein écran, survol, clic, clavier. |"
        if french
        else "| `index.html` | The page that opens the figure: fullscreen, hover, click, keyboard. |"
    )
    # CSV where the rows are a real table, JSON where they carry lists: a
    # list flattened into a spreadsheet cell is the one thing CSV cannot show.
    data_name = data_filename(rows) if rows else "data.csv"
    tabular = data_name.endswith(".csv")
    data_why_fr = "" if tabular else " (en JSON : chaque ligne porte une liste)"
    data_why_en = "" if tabular else " (JSON, because each row carries a list)"
    if french:
        language_note = (
            f"\nLa figure existe aussi en français : `python3 {module} --language fr`.\n"
            if bilingual
            else ""
        )
    else:
        language_note = (
            f"\nThe figure also speaks French: `python3 {module} --language fr`.\n"
            if bilingual
            else ""
        )
    if french:
        return f"""# {slug} — figure autonome

La figure `{slug}` de la galerie Sprezzature, avec de quoi la refabriquer et
la modifier. Rien à compiler, pas de compte, pas de framework.

## Contenu

| Fichier | Rôle |
|---|---|
| `{module}` | Le générateur. C'est le fichier intéressant : il calcule la géométrie et écrit le SVG balise par balise. |
| `sprezzature_svg.py` | Le moteur de dessin : échelles, chemins SVG, palette, placement des étiquettes, survol. |
| `{data_name}` | Les données{data_why_fr}. Modifiez-les, relancez, la figure change. |
| `LICENSE` | Le texte de la licence. Conservez-le si vous redistribuez. |
| `{slug}.svg` | La figure déjà produite, interactive. |
{page_row}
{requirements_row}

## Lancer

```sh
{install}
python3 {module}
# → wrote {slug}.svg
```

## Regarder le résultat

Le SVG s'ouvre **dans un navigateur**, comme une page :

```sh
open {slug}.svg        # macOS
xdg-open {slug}.svg    # Linux
start {slug}.svg       # Windows
```

C'est là que la figure prend vie : les infobulles au survol sont écrites dans
le SVG lui-même, en CSS, sans une ligne de JavaScript. Un double-clic depuis
l'explorateur de fichiers marche aussi. Pour l'intégrer dans une page web,
utilisez `<object data="{slug}.svg"></object>` ou collez le SVG directement
dans le HTML.
{language_note}
**Le seul piège** : dans une balise `<img>`, le navigateur bloque les requêtes
externes, donc les polices Google Fonts liées par le SVG ne se chargent pas et
la figure retombe sur une police système. Tout le reste s'affiche normalement.

## Modifier

Changez les nombres de `{data_name}` et relancez. Pour aller plus loin,
`python3 {module} --help` liste les options disponibles (titre, dimensions,
niveau d'accessibilité, thème…).


## Sources

Par courtoisie, pas par obligation. Rien ici n'exige de crédit ; c'est
nommé parce que le travail s'en est servi, et le dire ne coûte rien.

| Élément | Origine |
|---|---|
| Typographies | Roboto et Roboto Mono, Christian ROBERTSON, sous SIL Open Font License |
| Données de la figure | synthétiques, engendrées par `make_data.py` — aucune observation réelle |

## Licence

**BSD-3-Clause**, la même que scikit-learn ou NumPy : faites-en ce que vous
voulez, y compris commercialement, à une condition — gardez l'avis de
copyright et le texte de la licence avec le code. Le fichier `LICENSE` de ce
dossier est ce texte ; il vous suffit de ne pas le supprimer.

---

Extrait de [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures) ·
Galerie complète : <https://sprezzature.ai/figures.html> ·
Warith HARCHAOUI, Ph.D.
"""
    return f"""# {slug} — standalone figure

The `{slug}` figure from the Sprezzature gallery, with everything needed to
rebuild and change it. Nothing to compile, no account, no framework.

## What is in here

| File | Role |
|---|---|
| `{module}` | The generator. This is the interesting one: it computes the geometry and writes the SVG tag by tag. |
| `sprezzature_svg.py` | The drawing engine: scales, SVG paths, palette, label placement, hover chrome. |
| `{data_name}` | The data{data_why_en}. Edit it, re-run, the figure changes. |
| `LICENSE` | The licence text. Keep it if you redistribute. |
| `{slug}.svg` | The figure as built, interactive. |
{page_row}
{requirements_row}

## Run it

```sh
{install}
python3 {module}
# → wrote {slug}.svg
```

## Look at the result

The SVG opens **in a browser**, like a page:

```sh
open {slug}.svg        # macOS
xdg-open {slug}.svg    # Linux
start {slug}.svg       # Windows
```

That is where the figure comes alive: the hover tooltips are written into the
SVG itself, in CSS, with no JavaScript at all. Double-clicking it from a file
manager works too. To put it in a web page, use
`<object data="{slug}.svg"></object>` or paste the SVG straight into the HTML.
{language_note}
**The one gotcha**: inside an `<img>` tag a browser blocks external requests,
so the Google Fonts the SVG links will not load and the figure falls back to a
system typeface. Everything else renders normally.

## Change it

Edit the numbers in `{data_name}` and run it again. Beyond that,
`python3 {module} --help` lists the options available (title, dimensions,
accessibility level, theme, …).


## Sources

Out of courtesy, not obligation. Nothing here requires a credit; it is named
because the work drew on it, and saying so costs nothing.

| Item | Origin |
|---|---|
| Typefaces | Roboto and Roboto Mono, Christian ROBERTSON, under the SIL Open Font License |
| The figure's data | synthetic, written by `make_data.py` — no real observation |

## Licence

**BSD-3-Clause**, the same licence as scikit-learn or NumPy: do what you like
with this, commercially included, on one condition — keep the copyright
notice and the licence text with the code. The `LICENSE` file in this folder
is that text; you only have to not delete it.

---

From [sprezzature-figures](https://github.com/warith-harchaoui/sprezzature-figures) ·
Full gallery: <https://sprezzature.ai/figures.html> ·
Warith HARCHAOUI, Ph.D.
"""


#: The download chip appended to a gallery card's caption. Sized in the label
#: because a reader deciding whether to click deserves to know, and carrying
#: the figure's own name in ``aria-label`` because a screen-reader user tabs
#: past 121 siblings and "Download" alone tells them nothing.
#:
#: Every class here exists in the committed ``css/app.css``. That build is a
#: Tailwind scan of the pages as they were, so a class nobody used yet — the
#: obvious ``inline-flex w-fit`` for a chip — simply is not in the file and
#: silently does nothing: the anchor stays inline, and a long caption wraps
#: *inside* the button box, splitting its border across two lines. A block
#: wrapper plus ``inline-block`` gets the same result out of classes that are
#: already compiled, and leaves the CSS untouched.
_KIT_LINK: str = (
    '<div class="mt-2"><a href="{prefix}{slug}.zip" download '
    'class="inline-block rounded-lg border border-neutral-200 px-2.5 py-1 '
    "text-xs text-neutral-600 hover:border-brand-blue hover:text-brand-linktext "
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue "
    'dark:border-neutral-700 dark:text-neutral-400" '
    'aria-label="{aria}">{label}</a></div>'
)

#: Finds an already-linked chip so a rebuild refreshes the size in place
#: rather than stacking a second link onto every card. Tolerates the
#: unwrapped shape an earlier build wrote.
_EXISTING_LINK = re.compile(
    r'\s*(?:<div class="mt-2">)?<a href="(?:\.\./)?kits/(?:fr/)?[a-z0-9_-]+\.zip".*?</a>(?:</div>)?',
    re.DOTALL,
)

#: One gallery card.
_FIGURE_BLOCK = re.compile(r"<figure\b.*?</figure>", re.DOTALL)

#: The slug a card points at, on either language's page.
_CARD_SLUG = re.compile(r'data-src="(?:\.\./)?img/figures/(?:fr/)?([a-z0-9_-]+)\.svg"')


def link_gallery(page: Path, sizes: dict[str, int], *, french: bool) -> int:
    """
    Put a kit download link on every card of a gallery page.

    Both language pages link the same zip: the generator inside it takes a
    ``--language`` flag, so one artifact serves both readers rather than
    doubling 122 downloads into 244.

    Parameters
    ----------
    page : Path
        The gallery page to rewrite, in place.
    sizes : dict of str to int
        Slug to zip size in bytes, for the label.
    french : bool
        Whether to write the French label.

    Returns
    -------
    int
        How many cards were linked.
    """
    # French cards point into kits/fr/, so a reader who found the figure on the
    # French page does not open the zip into English prose.
    prefix = "../kits/fr/" if french else "kits/"
    html = page.read_text(encoding="utf-8")
    linked = 0

    def rewrite(match: re.Match[str]) -> str:
        nonlocal linked
        block = _EXISTING_LINK.sub("", match.group(0))
        slug_match = _CARD_SLUG.search(block)
        if slug_match is None or slug_match.group(1) not in sizes:
            return block
        slug = slug_match.group(1)
        name_match = re.search(r'<span class="font-medium">([^<]+)</span>', block)
        name = name_match.group(1) if name_match else slug
        kb = round(sizes[slug] / 1024)
        if french:
            label = f"↓ Kit Python + CSV + SVG ({kb} Ko)"
            aria = f"Télécharger le kit de la figure {name} : Python, CSV et SVG, {kb} Ko"
        else:
            label = f"↓ Python + CSV + SVG kit ({kb} KB)"
            aria = f"Download the {name} kit: Python, CSV and SVG, {kb} KB"
        chip = _KIT_LINK.format(prefix=prefix, slug=slug, aria=aria, label=label)
        linked += 1
        return block.replace("</figcaption>", f"\n            {chip}</figcaption>", 1)

    page.write_text(_FIGURE_BLOCK.sub(rewrite, html), encoding="utf-8")
    return linked


def build_kit(
    slug: str,
    scripts: Path,
    bundle: str,
    out_dir: Path,
    *,
    check: bool,
    title: str = "",
    language: str = "en",
) -> tuple[bool, str]:
    """
    Build one kit: assemble it, run it, and zip what ran.

    The kit is assembled in a scratch folder and its generator is executed
    there, with the repo kept off ``sys.path``, so the run proves the kit is
    genuinely self-contained rather than quietly borrowing the checkout. Only
    a kit that produced its own SVG gets zipped.

    Parameters
    ----------
    slug : str
        Gallery slug.
    scripts : Path
        The standalone repo's ``scripts/`` folder.
    bundle : str
        Text of ``sprezzature_svg.py``, built once and shared.
    out_dir : Path
        Where ``<slug>.zip`` lands.
    check : bool
        Verify only; write no zip.
    title : str, optional
        The name the gallery card shows, used as the page heading. Falls back
        to the slug when the card could not be read.
    language : str, optional
        ``"en"`` or ``"fr"``. A reader who found the figure on the French page
        should not open the zip into English prose, so each language gets its
        own archive: its own README, its own page, and — for the generators
        that take a ``--language`` flag — its own chrome text in the SVG.

    Returns
    -------
    tuple of (bool, str)
        Success flag and a one-line report.
    """
    import shutil
    import tempfile

    generator = resolve_generator(slug, scripts)
    module = f"make_{slug.replace('-', '_')}.py"
    title = title or slug
    french = language == "fr"

    sys.path.insert(0, str(scripts))
    try:
        import importlib
        import inspect

        module_obj = importlib.import_module(generator.stem)
        demo = getattr(module_obj, "DEMO_DATA", None)
        # A generator that takes a ``language`` keyword carries its own French
        # chrome text, which is what lets one kit serve both gallery pages.
        builder = getattr(module_obj, "build_svg", None)
        bilingual = bool(builder) and "language" in inspect.signature(builder).parameters
    except Exception as exc:  # noqa: BLE001 - a broken generator is a report, not a crash
        return False, f"{slug}: cannot import {generator.name} ({exc})"
    finally:
        sys.path.remove(str(scripts))

    if not (isinstance(demo, list) and demo and all(isinstance(r, dict) for r in demo)):
        return False, f"{slug}: DEMO_DATA is not a table of rows; no CSV to ship"

    source = generator_source(generator, demo)
    pins = detect_requirements([source, bundle])

    staging = Path(tempfile.mkdtemp(prefix=f"kit-{slug}-"))
    try:
        kit = staging / slug
        kit.mkdir()
        for relative in kit_assets(source):
            origin = scripts.parent / "assets" / relative
            if not origin.is_file():
                return False, f"{slug}: missing asset {origin}"
            target = kit / "assets" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, target)
        (kit / module).write_text(source, encoding="utf-8")
        (kit / "sprezzature_svg.py").write_text(bundle, encoding="utf-8")
        # The licence travels with the code. A kit is made to be passed
        # around — emailed, dropped in a shared folder, committed into
        # someone else's project — and from inside that folder the
        # repository it came from is not reachable. BSD-3-Clause is
        # permissive on condition that the notice is retained, so shipping
        # the code without it is the one thing the licence forbids.
        licence = scripts.parent / "LICENSE"
        if not licence.is_file():
            return False, f"{slug}: sprezzature-figures has no LICENSE to ship"
        shutil.copy2(licence, kit / "LICENSE")
        data_name = data_filename(demo)
        payload = rows_to_csv(demo) if data_name.endswith(".csv") else rows_to_json(demo)
        (kit / data_name).write_text(payload, encoding="utf-8")
        (kit / "make_data.py").write_text(
            data_script(slug, module, demo, french=french), encoding="utf-8"
        )
        if pins:
            (kit / "requirements.txt").write_text(requirements_text(pins), encoding="utf-8")
        readme_name = "LISEZMOI.md" if french else "README.md"
        (kit / readme_name).write_text(
            readme_text(slug, module, pins, french=french, bilingual=bilingual, rows=demo),
            encoding="utf-8",
        )
        (kit / "index.html").write_text(
            kit_page(slug, title, module, pins, french=french, rows=demo), encoding="utf-8"
        )

        # Run it the way a reader would: plain python, from inside the kit,
        # with PYTHONPATH cleared so nothing resolves back to the checkout.
        argv = [sys.executable, module]
        if bilingual:
            argv += ["--language", language]
        result = subprocess.run(
            argv,
            cwd=kit,
            capture_output=True,
            text=True,
            timeout=180,
            env={"PATH": "/usr/bin:/bin", "HOME": str(staging), "PYTHONPATH": ""},
        )
        if result.returncode != 0:
            tail = (result.stderr.strip().splitlines() or ["(no output)"])[-1]
            return False, f"{slug}: generator failed — {tail}"

        svg = kit / f"{slug}.svg"
        if not svg.is_file():
            produced = sorted(p.name for p in kit.glob("*.svg"))
            if len(produced) != 1:
                return False, f"{slug}: expected one SVG, found {produced}"
            (kit / produced[0]).rename(svg)

        # An SVG is XML, and a browser refuses the whole document over one
        # malformed character rather than degrading. Parsing it here is what
        # separates "the generator exited 0" from "a reader sees a figure";
        # it caught a raw ``&`` in the font-link URL that would otherwise
        # have shipped 122 blank figures.
        try:
            ElementTree.parse(svg)
        except ElementTree.ParseError as exc:
            return False, f"{slug}: SVG is not well-formed XML — {exc}"

        size_kb = svg.stat().st_size / 1024
        if check:
            return True, f"{slug}: ok ({size_kb:.0f} KB SVG, {', '.join(pins) or 'stdlib only'})"

        target_dir = out_dir / "fr" if french else out_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        archive = target_dir / f"{slug}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(kit.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    zf.write(path, Path(slug) / path.relative_to(kit))
        return True, f"{slug}: {archive.stat().st_size / 1024:.0f} KB zip ({', '.join(pins) or 'stdlib only'})"
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def build_all(slugs: Sequence[str], scripts: Path, out_dir: Path, *, check: bool) -> int:
    """
    Build every kit, link them into both gallery pages, and report.

    The gallery is only rewritten on a full, clean build: a partial run
    (``--only`` while iterating) would otherwise strip the links from every
    card it did not rebuild.
    """
    bundle = bundle_source(scripts.parent)
    titles = {
        "en": card_titles(REPO_ROOT / GALLERY_PAGES[0]),
        "fr": card_titles(REPO_ROOT / GALLERY_PAGES[1]),
    }
    failures: list[str] = []
    for language in ("en", "fr"):
        print(f"\n── {language} ──")
        for slug in slugs:
            ok, report = build_kit(
                slug,
                scripts,
                bundle,
                out_dir,
                check=check,
                title=titles[language].get(slug, ""),
                language=language,
            )
            print(("  " if ok else "  FAIL ") + report)
            if not ok:
                failures.append(f"{language}/{report}")
    built = len(slugs) * 2 - len(failures)
    print(f"\n{built}/{len(slugs) * 2} kit(s) built ({len(slugs)} figures x 2 languages)")
    if failures:
        print(f"{len(failures)} failed", file=sys.stderr)
        return 1
    if check:
        return 0

    sizes = {
        "en": {s: (out_dir / f"{s}.zip").stat().st_size for s in slugs if (out_dir / f"{s}.zip").is_file()},
        "fr": {
            s: (out_dir / "fr" / f"{s}.zip").stat().st_size
            for s in slugs
            if (out_dir / "fr" / f"{s}.zip").is_file()
        },
    }
    if len(sizes["en"]) < len(discover_cards(REPO_ROOT / GALLERY_PAGES[0])):
        print("partial build: gallery pages left untouched")
        return 0
    for relative in GALLERY_PAGES:
        page = REPO_ROOT / relative
        french = relative.startswith("web/fr/")
        count = link_gallery(page, sizes["fr" if french else "en"], french=french)
        print(f"  linked {count} card(s) in {relative}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. See the module docstring for usage."""
    parser = argparse.ArgumentParser(description="Build one runnable kit zip per gallery card.")
    parser.add_argument("--figures-repo", type=Path, default=DEFAULT_FIGURES_REPO)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / KITS_DIR)
    parser.add_argument("--only", default="", help="comma-separated slugs, for iterating")
    parser.add_argument("--check", action="store_true", help="build into a temp dir and report, writing no zips")
    args = parser.parse_args(argv)

    scripts: Path = args.figures_repo / "scripts"
    if not scripts.is_dir():
        print(f"error: no generators at {scripts}", file=sys.stderr)
        return 64

    slugs = discover_cards(REPO_ROOT / GALLERY_PAGES[0])
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        slugs = [s for s in slugs if s in wanted]
    if not slugs:
        print("error: no cards selected", file=sys.stderr)
        return 64

    print(f"→ {len(slugs)} gallery card(s) from {GALLERY_PAGES[0]}")
    return build_all(slugs, scripts, args.out_dir, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
