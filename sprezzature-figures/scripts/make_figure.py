#!/usr/bin/env python3
"""
make_figure
===========

Emit a data-science figure in the front-* house style.

The script accepts a CSV / JSON / Parquet input and a small spec (which
columns, which chart kind, which polarity) and emits one of:

* a Vega-Lite v5 JSON spec (default, ``--emit vega``)
* a matplotlib PNG or SVG (``--emit png`` / ``--emit svg``)

The house style is enforced through :mod:`_style`:

* Colors from the curated palette CSV (co-installed with ``sprezzature-colors``
  when present; the built-in Apple-inspired 8 + 4 neutrals otherwise).
* Roboto / Roboto Serif / Roboto Mono typography.
* No top / right spines, no ticks, no gridlines.
* Automatic polarity tag on the y-axis when the metric name matches a
  known "higher/lower is better" pattern (see :data:`_style.POLARITY_HINTS`).
* Dark-mode aware — pass ``--dark`` or set ``SPREZZATURE_DARK=1``.
* On ``--emit png|svg``: writes a sibling ``*.alt.txt`` stub with the
  chart title + polarity for later refinement (via
  ``sprezzature-vision/scripts/alt_from_ollama.py --kind complex``).

Chart-kind dispatch matches
``references/dataviz-decision-tree.md``:

    bar / bar-h / bar-stacked
    line / step
    scatter / hexbin
    hist / density
    box / violin
    heatmap / heatmap-count
    map (Vega-only; requires --topojson)

Usage
-----
::

    # Vega-Lite JSON (default)
    python make_figure.py data.csv --x date --y latency_ms --kind line \\
        --polarity lower-better --out fig.json

    # Matplotlib SVG at publication preset
    python make_figure.py data.csv --x quarter --y revenue --kind bar \\
        --preset publication --emit svg --out fig.svg

    # Axis-title language auto-detected from the column names / title;
    # pass --lang to force one
    python make_figure.py data.csv --x date --y conversion_rate \\
        --kind line --lang fr

Notes
-----
* Python 3.10+.
* ``pip install -r requirements-dataviz.txt`` for pandas / matplotlib /
  seaborn / altair.
* The Vega-Lite path uses ``json.dumps`` and does not require altair;
  the matplotlib path requires matplotlib + pandas.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _lang import detect_language  # noqa: E402
from _style import (  # noqa: E402
    infer_polarity,
    matplotlib_rc,
    polarity_color,
    polarity_tag,
    qualitative_sequence,
    vega_config,
)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = make_parser(
        prog="make_figure",
        description=(
            "Emit a data-science figure in the front-* house style. Default "
            "output is a Vega-Lite v5 JSON spec; --emit png/svg switches to "
            "the matplotlib backend."
        ),
        epilog=(
            "Chart kinds: bar, bar-h, bar-stacked, bar-grouped, line, step, "
            "scatter, hexbin, hist, density, box, violin, heatmap, "
            "heatmap-count, map. Specialized figures (treemap, parallel "
            "coordinates, candlestick/OHLC, lollipop, error bars, and more) "
            "ship as runnable specs in assets/vega-examples/ — render them "
            "with render_diagram.py."
        ),
    )
    parser.add_argument("data", help="Input CSV / JSON / Parquet.")
    parser.add_argument("--x", required=True, help="Column for the x-axis.")
    parser.add_argument("--y", default=None, help="Column for the y-axis (optional for hist / value_counts).")
    parser.add_argument("--color", default=None, help="Column for the color encoding.")
    parser.add_argument("--facet", default=None, help="Column for small-multiple faceting.")
    parser.add_argument("--kind", default="auto", help="Chart kind (see epilog). auto = pick by dtypes.")
    parser.add_argument("--title", default=None, help="Chart title.")
    parser.add_argument("--subtitle", default=None, help="Chart subtitle.")
    parser.add_argument("--polarity", default=None,
                        help='Axis polarity: "higher-better", "lower-better", '
                             '"target=<N>", or "auto" (inferred from column name).')
    parser.add_argument("--preset", default=None, help="Publication preset (see references/publication-presets.md).")
    parser.add_argument("--emit", choices=("vega", "png", "svg"), default="vega",
                        help="Output format (default: vega).")
    parser.add_argument("--engine", choices=("auto", "vega", "matplotlib"), default="auto",
                        help="Rendering engine. auto = derive from --emit.")
    parser.add_argument("--out", default=None, help="Output path. Defaults to stdout for --emit vega.")
    parser.add_argument("--lang", default=None, help="BCP-47 base tag (en, fr, de, ...).")
    parser.add_argument("--dark", action="store_true", help="Use the dark-mode variant.")
    parser.add_argument("--bins", default="auto", help="Bin count for histograms.")
    parser.add_argument("--alt-from-title", action="store_true",
                        help="Write a sibling .alt.txt stub with chart title + polarity.")
    parser.add_argument("--dry-run", action="store_true", help="Print the spec to stdout without writing to disk.")
    return parser


# ------------------------------------------------------------------
# Data loading (deferred pandas import for --emit vega without pandas)
# ------------------------------------------------------------------
def load_data(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Load rows and dtypes from a CSV / JSON / Parquet path.

    Parameters
    ----------
    path : str
        Filesystem path to the input.

    Returns
    -------
    rows : list of dict
        Row-oriented records.
    dtypes : dict of str to str
        Per-column dtype tag: ``"quantitative"``, ``"nominal"``, or
        ``"temporal"``.
    """
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        try:
            import pandas as pd
            df = pd.read_csv(path)
        except ImportError:
            return _load_csv_stdlib(path)
    elif ext == ".json":
        try:
            import pandas as pd
            df = pd.read_json(path)
        except ImportError:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            rows = data if isinstance(data, list) else [data]
            return rows, _infer_dtypes_from_rows(rows)
    elif ext in {".parquet", ".pq"}:
        import pandas as pd  # required
        df = pd.read_parquet(path)
    else:
        raise SystemExit(f"Unsupported input format: {ext}. Use .csv / .json / .parquet.")

    dtypes: Dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        if str(s.dtype).startswith(("int", "float")):
            dtypes[col] = "quantitative"
        elif str(s.dtype).startswith(("datetime", "period")):
            dtypes[col] = "temporal"
        else:
            dtypes[col] = "nominal"
    return df.to_dict(orient="records"), dtypes


def _load_csv_stdlib(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Stdlib CSV loader when pandas is not available."""
    import csv as _csv
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = _csv.DictReader(fh)
        rows = list(reader)
    return rows, _infer_dtypes_from_rows(rows)


def _infer_dtypes_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Guess a Vega-Lite dtype per column from the first N rows."""
    dtypes: Dict[str, str] = {}
    if not rows:
        return dtypes
    sample = rows[:200]
    for col in rows[0].keys():
        vals = [r.get(col) for r in sample if r.get(col) not in (None, "")]
        if not vals:
            dtypes[col] = "nominal"
            continue
        is_number = all(_is_number(v) for v in vals)
        is_temporal = any(_is_temporal(v) for v in vals)
        dtypes[col] = "quantitative" if is_number else ("temporal" if is_temporal else "nominal")
    return dtypes


def _is_number(v: Any) -> bool:
    """Return True if ``v`` parses as a number."""
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _is_temporal(v: Any) -> bool:
    """Heuristic: does ``v`` look like an ISO date or datetime?"""
    if not isinstance(v, str):
        return False
    return len(v) >= 8 and (v[4:5] == "-" or v[2:3] in ("/", "-"))


# ------------------------------------------------------------------
# --kind auto: pick by dtypes
# ------------------------------------------------------------------
def pick_kind(x_type: str, y_type: Optional[str], n_rows: int) -> str:
    """Pick a chart kind from dtypes; mirrors dataviz-decision-tree.md."""
    if x_type == "temporal" and y_type == "quantitative":
        return "line"
    if x_type == "nominal" and y_type == "quantitative":
        return "bar-h"
    if x_type == "quantitative" and y_type == "quantitative":
        return "hexbin" if n_rows >= 10_000 else "scatter"
    if x_type == "quantitative" and y_type is None:
        return "hist"
    if x_type == "nominal" and y_type is None:
        return "bar-h"
    return "scatter"


# ------------------------------------------------------------------
# Vega-Lite spec builder
# ------------------------------------------------------------------
def build_vega_spec(spec_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Vega-Lite v5 JSON spec from a context dict.

    Parameters
    ----------
    spec_ctx : dict
        Context bag with keys ``rows``, ``dtypes``, ``x``, ``y``,
        ``color``, ``facet``, ``kind``, ``title``, ``subtitle``,
        ``polarity``, ``dark``, ``lang``.

    Returns
    -------
    dict
        Vega-Lite v5 spec ready for ``json.dumps``.
    """
    rows = spec_ctx["rows"]
    dtypes = spec_ctx["dtypes"]
    x = spec_ctx["x"]
    y = spec_ctx["y"]
    color = spec_ctx.get("color")
    facet = spec_ctx.get("facet")
    kind = spec_ctx["kind"]
    lang = spec_ctx.get("lang", "en")

    y_polarity = spec_ctx.get("polarity")
    if y_polarity == "auto":
        y_polarity = infer_polarity(y or "")

    x_title = _label_for(x, lang, is_time=(dtypes.get(x) == "temporal"))
    y_title = _label_for(y, lang) + polarity_tag(y_polarity, lang=lang) if y else None

    encoding: Dict[str, Any] = {
        "x": {"field": x, "type": dtypes.get(x, "nominal"), "axis": {"title": x_title}},
    }
    if y:
        encoding["y"] = {"field": y, "type": dtypes.get(y, "quantitative"), "axis": {"title": y_title}}
    if color:
        encoding["color"] = {"field": color, "type": dtypes.get(color, "nominal")}
    if facet:
        encoding["facet"] = {"field": facet, "type": dtypes.get(facet, "nominal"), "columns": 3}

    mark = _mark_for_kind(kind)

    # Polarity encoding — apply only when the caller has neither passed
    # a --color column nor turned polarity coloring off. Green for
    # goal-directed metrics (higher/lower is better), Blue for
    # target-with-tolerance. See references/polarity-and-color.md +
    # <https://harchaoui.org/warith/colors/> for the rationale. Text
    # tag on the axis remains the primary signal (CVD-safe).
    if color is None and mark.get("type") in {"bar", "line", "point", "rect", "area"}:
        pc = polarity_color(y_polarity, dark=bool(spec_ctx.get("dark")))
        if pc:
            mark = {**mark, "color": pc}

    spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "config": vega_config(dark=bool(spec_ctx.get("dark"))),
        "data": {"values": rows},
        "mark": mark,
        "encoding": encoding,
    }
    if spec_ctx.get("title") or spec_ctx.get("subtitle"):
        spec["title"] = {"text": spec_ctx.get("title") or "", "subtitle": spec_ctx.get("subtitle") or ""}
    if kind == "bar-h":
        spec["encoding"]["y"], spec["encoding"]["x"] = spec["encoding"].get("x"), spec["encoding"].get("y")
    if kind == "bar-stacked":
        spec["encoding"]["y"]["stack"] = "normalize"
    if kind == "bar-grouped" and color:
        # Dodge the bars of each x-group side by side, one sub-bar per
        # color category (Vega-Lite xOffset). Without --color there is
        # nothing to group by, so it degrades to a plain bar.
        spec["encoding"]["xOffset"] = {"field": color, "type": dtypes.get(color, "nominal")}
    if kind == "hist":
        spec["mark"] = {"type": "bar", "cornerRadiusEnd": 4}
        spec["encoding"]["x"] = {"field": x, "bin": True, "axis": {"title": x_title}}
        spec["encoding"]["y"] = {"aggregate": "count", "axis": {"title": _label_for("count", lang)}}
    return spec


def _mark_for_kind(kind: str) -> Dict[str, Any]:
    """Map a --kind flag to a Vega-Lite mark dict."""
    marks: Dict[str, Dict[str, Any]] = {
        "bar":           {"type": "bar", "cornerRadiusEnd": 4},
        "bar-h":         {"type": "bar", "cornerRadiusEnd": 4},
        "bar-stacked":   {"type": "bar", "cornerRadiusEnd": 4},
        "bar-grouped":   {"type": "bar", "cornerRadiusEnd": 4},
        "line":          {"type": "line", "point": True, "strokeWidth": 2},
        "step":          {"type": "line", "interpolate": "step-after", "strokeWidth": 2},
        "scatter":       {"type": "point", "filled": True, "size": 40},
        "hexbin":        {"type": "point", "filled": True, "size": 20, "opacity": 0.5},
        "hist":          {"type": "bar", "cornerRadiusEnd": 4},
        "density":       {"type": "area", "opacity": 0.5, "interpolate": "monotone"},
        "box":           {"type": "boxplot", "extent": 1.5},
        "violin":        {"type": "area", "orient": "horizontal", "opacity": 0.6},
        "heatmap":       {"type": "rect"},
        "heatmap-count": {"type": "rect"},
    }
    return marks.get(kind, {"type": "point"})


def _label_for(name: Optional[str], lang: str, is_time: bool = False) -> str:
    """Prettify a column name for use as an axis title.

    Parameters
    ----------
    name : str or None
        Column name.
    lang : str
        BCP-47 base tag; controls the "Count" translation.
    is_time : bool, optional
        When True, do not lowercase the initial letter (dates stay
        title-cased).
    """
    if name is None:
        return ""
    if name == "count":
        return {"en": "Count", "fr": "Décompte", "de": "Anzahl", "es": "Recuento"}.get(lang, "Count")
    return name.replace("_", " ").strip().capitalize()


# ------------------------------------------------------------------
# Matplotlib backend
# ------------------------------------------------------------------
def render_matplotlib(spec_ctx: Dict[str, Any], out_path: str, fmt: str) -> None:
    """Render the same chart via matplotlib.

    Deferred imports keep the auditor stdlib-only when this function
    is not called.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    plt.rcParams.update(matplotlib_rc(dark=bool(spec_ctx.get("dark"))))

    preset = spec_ctx.get("preset")
    width_in, dpi = _preset_dims(preset)

    df = pd.DataFrame(spec_ctx["rows"])
    kind = spec_ctx["kind"]
    x = spec_ctx["x"]
    y = spec_ctx["y"]
    lang = spec_ctx.get("lang", "en")

    fig, ax = plt.subplots(figsize=(width_in, width_in * 0.62))

    palette = qualitative_sequence(max(1, len(df[spec_ctx["color"]].unique()) if spec_ctx.get("color") else 1))
    # Polarity color wins over the qualitative sequence when there is
    # no --color faceting; see references/polarity-and-color.md.
    y_polarity_raw = spec_ctx.get("polarity")
    if y_polarity_raw == "auto":
        y_polarity_raw = infer_polarity(y or "")
    if not spec_ctx.get("color"):
        pc = polarity_color(y_polarity_raw, dark=bool(spec_ctx.get("dark")))
        if pc:
            palette = [pc]

    if kind in ("bar", "bar-h"):
        _render_bar(ax, df, x, y, kind == "bar-h", palette[0])
    elif kind in ("line", "step"):
        ax.plot(df[x], df[y], drawstyle=("steps-post" if kind == "step" else "default"),
                color=palette[0], linewidth=2)
    elif kind == "scatter":
        ax.scatter(df[x], df[y], color=palette[0], s=25, alpha=0.7)
    elif kind == "hist":
        ax.hist(df[x], bins=(spec_ctx["bins"] if spec_ctx["bins"] != "auto" else "auto"),
                color=palette[0], edgecolor="none")
    elif kind == "box":
        ax.boxplot(df[y] if y else df[x], showfliers=True)
    else:
        raise SystemExit(f"matplotlib backend does not support --kind {kind}; pick --emit vega instead.")

    y_polarity = spec_ctx.get("polarity")
    if y_polarity == "auto":
        y_polarity = infer_polarity(y or "")
    ax.set_xlabel(_label_for(x, lang, is_time=False))
    if y:
        ax.set_ylabel(_label_for(y, lang) + polarity_tag(y_polarity, lang=lang))
    if spec_ctx.get("title"):
        ax.set_title(spec_ctx["title"])

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(length=0)

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def _render_bar(ax: Any, df: Any, x: str, y: str, horizontal: bool, color: str) -> None:
    """Draw a bar chart (horizontal or vertical) in the house style."""
    if horizontal:
        ax.barh(df[x], df[y], color=color, edgecolor="none")
    else:
        ax.bar(df[x], df[y], color=color, edgecolor="none")


def _preset_dims(preset: Optional[str]) -> Tuple[float, int]:
    """Return ``(width_in, dpi)`` for a publication preset.

    See ``references/publication-presets.md`` for the full list.
    """
    presets = {
        None:              (6.4, 150),
        "publication":     (3.5, 300),
        "nature-single":   (3.5, 300),
        "nature-double":   (7.2, 300),
        "science-single":  (2.17, 300),
        "science-double":  (4.72, 300),
        "plos":            (7.5, 300),
        "ieee-single":     (3.5, 300),
        "ieee-double":     (7.16, 300),
        "slide-16-9":      (13.33, 96),
        "web-hero":        (12.0, 144),
    }
    return presets.get(preset, presets[None])


# ------------------------------------------------------------------
# Alt-text stub
# ------------------------------------------------------------------
def write_alt_stub(out_path: str, spec_ctx: Dict[str, Any]) -> None:
    """Write a sibling ``<stem>.alt.txt`` stub summarising the chart.

    Parameters
    ----------
    out_path : str
        Path to the emitted figure (PNG / SVG / JSON).
    spec_ctx : dict
        The spec context used to render the figure.
    """
    stem = Path(out_path).with_suffix("")
    alt_path = Path(str(stem) + ".alt.txt")
    parts = []
    if spec_ctx.get("title"):
        parts.append(spec_ctx["title"])
    if spec_ctx.get("subtitle"):
        parts.append(spec_ctx["subtitle"])
    y = spec_ctx.get("y")
    polarity = spec_ctx.get("polarity")
    if polarity == "auto":
        polarity = infer_polarity(y or "")
    if y:
        parts.append(f"y = {y}{polarity_tag(polarity, lang=spec_ctx.get('lang', 'en'))}")
    if spec_ctx.get("x"):
        parts.append(f"x = {spec_ctx['x']}")
    parts.append(f"kind = {spec_ctx.get('kind')}")
    alt_path.write_text(" — ".join(parts) + "\n", encoding="utf-8")


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)

    # Language: explicit --lang wins; else detect from the chart's own text
    # (title / subtitle / axis column names) — no configured default.
    _lang_hint = " ".join(t for t in (args.title, args.subtitle, args.x, args.y) if t)
    lang = args.lang or detect_language(_lang_hint, fmt="text")
    dark = bool(args.dark) or os.environ.get("SPREZZATURE_DARK", "") == "1"

    rows, dtypes = load_data(args.data)
    if not rows:
        print("No rows loaded from input.", file=sys.stderr)
        return 2

    kind = args.kind
    if kind == "auto":
        kind = pick_kind(dtypes.get(args.x, "nominal"), dtypes.get(args.y, None) if args.y else None, len(rows))

    spec_ctx = {
        "rows": rows,
        "dtypes": dtypes,
        "x": args.x,
        "y": args.y,
        "color": args.color,
        "facet": args.facet,
        "kind": kind,
        "title": args.title,
        "subtitle": args.subtitle,
        "polarity": args.polarity or "auto",
        "dark": dark,
        "preset": args.preset,
        "lang": lang,
        "bins": args.bins,
    }

    engine = args.engine
    if engine == "auto":
        engine = "matplotlib" if args.emit in ("png", "svg") else "vega"

    if engine == "vega":
        spec = build_vega_spec(spec_ctx)
        payload = json.dumps(spec, indent=2, ensure_ascii=False, default=str)
        if args.dry_run or not args.out:
            print(payload)
        else:
            Path(args.out).write_text(payload + "\n", encoding="utf-8")
            print(f"wrote {args.out}", file=sys.stderr)
            if args.alt_from_title:
                write_alt_stub(args.out, spec_ctx)
        return 0

    if not args.out:
        print("--emit png/svg requires --out.", file=sys.stderr)
        return 2
    render_matplotlib(spec_ctx, args.out, args.emit)
    print(f"wrote {args.out}", file=sys.stderr)
    if args.alt_from_title:
        write_alt_stub(args.out, spec_ctx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
