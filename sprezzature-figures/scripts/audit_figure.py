#!/usr/bin/env python3
"""
audit_figure
============

Static auditor for data-science figures. Reads a Vega-Lite v5 JSON
spec, a matplotlib-emitted SVG, or an HTML file containing
``<figure>`` blocks, and reports the small set of data-viz mistakes
that survive review:

    missing-axis-title     dual-y-axis         truncated-baseline
    pie-3d                 rainbow-palette     cvd-unsafe
    missing-polarity       chartjunk           role-img-missing
    alt-missing            pie-too-many-slices zero-encoded-as-null

Each finding carries a severity (``error`` / ``warning`` / ``info``).
Exit codes:

* ``0`` — no errors (warnings only or clean).
* ``1`` — one or more errors, or any finding under ``--strict``.
* ``2`` — CLI or parse error.

The auditor is **stdlib + PyYAML** only — no browser, no model, no
network. Vega-Lite specs are parsed with ``json``; SVG / HTML use
``xml.etree`` and ``html.parser``.

Usage
-----
::

    python audit_figure.py fig.json                       # human-readable
    python audit_figure.py public/*.html --json           # CI
    python audit_figure.py fig.svg --strict               # warnings → errors
    python audit_figure.py fig.json --ignore truncated-baseline,chartjunk

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _style import POLARITY_HINTS  # noqa: E402


# ------------------------------------------------------------------
# Finding model
# ------------------------------------------------------------------
def make_finding(rule: str, severity: str, message: str, path: str = "", line: int = 1) -> Dict[str, Any]:
    """Build a finding dict."""
    return {"path": path, "line": line, "rule": rule, "severity": severity, "message": message}


# ------------------------------------------------------------------
# Rule set
# ------------------------------------------------------------------
RAINBOW_SCHEMES = {"rainbow", "sinebow", "hsv", "hsl", "jet"}
CATEGORY_RED_HINT = {"#FF0000", "#F00", "#E11", "#D22", "#D00", "#FF3B30", "#EF4444", "#DC2626"}
CATEGORY_GREEN_HINT = {"#00FF00", "#0F0", "#22C55E", "#34C759", "#16A34A", "#059669"}
POLARISED_METRIC_SUBSTRINGS = tuple(POLARITY_HINTS.keys())


def _iter_units(spec: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """
    Yield every *unit* spec (one carrying a ``mark``) inside a possibly nested
    Vega-Lite spec.

    Descends through ``layer`` / ``concat`` / ``hconcat`` / ``vconcat`` arrays
    and the single ``spec`` child that ``facet`` and ``repeat`` wrap. This is
    what lets the per-encoding rules reach encodings that live *inside* layers,
    facets, and concatenations rather than only at the top level.
    """
    if not isinstance(spec, dict):
        return
    container_keys = ("layer", "concat", "hconcat", "vconcat", "facet", "repeat")
    is_container = any(k in spec for k in container_keys)
    # A unit is a spec that carries a mark, or a bare encoding spec with no
    # layering children (a plain single-view chart — its mark may be implicit).
    if "mark" in spec or ("encoding" in spec and not is_container):
        yield spec
    for key in ("layer", "concat", "hconcat", "vconcat"):
        children = spec.get(key)
        if isinstance(children, list):
            for child in children:
                yield from _iter_units(child)
    child = spec.get("spec")
    if isinstance(child, dict):
        yield from _iter_units(child)


def _iter_specs(spec: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Yield the top spec and every nested container/unit spec — used for
    composition-level checks (an ``independent`` y-scale resolve can sit at any
    layering level)."""
    if not isinstance(spec, dict):
        return
    yield spec
    for key in ("layer", "concat", "hconcat", "vconcat"):
        children = spec.get(key)
        if isinstance(children, list):
            for child in children:
                yield from _iter_specs(child)
    child = spec.get("spec")
    if isinstance(child, dict):
        yield from _iter_specs(child)


def _unit_rules(spec: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
    """Rules that apply to a single unit spec — its own ``mark`` + ``encoding``."""
    findings: List[Dict[str, Any]] = []
    enc = spec.get("encoding") or {}
    mark = spec.get("mark")
    mark_type = mark if isinstance(mark, str) else (mark or {}).get("type")

    # truncated-baseline
    if mark_type in ("bar", "rect"):
        y_enc = enc.get("y") or {}
        scale = y_enc.get("scale") or {}
        scale_type = scale.get("type", "linear")
        if scale.get("zero") is False and scale_type not in {"log", "pow", "sqrt", "symlog"}:
            findings.append(make_finding(
                "truncated-baseline", "warning",
                "bar chart y-axis has zero=false on a linear scale",
                path,
            ))

    # pie-3d + too-many-slices
    if mark_type == "arc":
        transforms = spec.get("transform") or []
        if any("angle" in t and "rotate" in json.dumps(t).lower() for t in transforms):
            findings.append(make_finding("pie-3d", "error", "arc mark with rotate/perspective transform", path))
        data_values = (spec.get("data") or {}).get("values") or []
        if isinstance(data_values, list) and len(data_values) > 4:
            findings.append(make_finding(
                "pie-too-many-slices", "warning",
                f"pie/donut with {len(data_values)} categories — use a table or bar chart",
                path,
            ))

    # rainbow-palette + cvd-unsafe
    for axis in ("color", "fill", "stroke"):
        ax_enc = enc.get(axis) or {}
        scheme = (ax_enc.get("scale") or {}).get("scheme")
        if isinstance(scheme, str) and scheme.lower() in RAINBOW_SCHEMES:
            findings.append(make_finding(
                "rainbow-palette", "error",
                f"{axis} scale uses rainbow scheme '{scheme}'",
                path,
            ))
        rng = (ax_enc.get("scale") or {}).get("range") or []
        if isinstance(rng, list):
            upper = {str(c).upper() for c in rng if isinstance(c, str)}
            has_red = any(c in upper for c in CATEGORY_RED_HINT)
            has_green = any(c in upper for c in CATEGORY_GREEN_HINT)
            if has_red and has_green:
                findings.append(make_finding(
                    "cvd-unsafe", "warning",
                    "categorical range mixes red + green without a third channel",
                    path,
                ))

    # missing-polarity (per unit that carries a polarised axis title)
    for axis in ("x", "y"):
        ax_enc = enc.get(axis) or {}
        if ax_enc.get("type") != "quantitative":
            continue
        title = ((ax_enc.get("axis") or {}).get("title") or "").lower()
        if not title:
            continue
        if any(sub in title for sub in POLARISED_METRIC_SUBSTRINGS):
            if not any(kw in title for kw in ("higher is better", "lower is better", "target", "plus haut", "plus bas", "cible")):
                findings.append(make_finding(
                    "missing-polarity", "warning",
                    f"axis title '{title}' looks polarised but has no direction tag",
                    path,
                ))

    # chartjunk — mark-level shadow
    if isinstance(mark, dict) and mark.get("shadow"):
        findings.append(make_finding("chartjunk", "warning", "mark has a shadow effect", path))

    return findings


def rules_for_vega(spec: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
    """
    Run all applicable rules against a Vega-Lite v5 JSON spec.

    Recurses into ``layer`` / ``facet`` / ``concat`` / ``repeat`` so encodings
    nested below the top level are audited too — not just a flat top-level spec.
    Two kinds of rule:

    * **Composition** (whole-chart): a genuine dual y-axis, and axis-title
      presence. Vega-Lite *shares* scales across layers by default, so two
      layers that both encode ``y`` (a confidence band and its line, an error
      bar and its point) are **not** a dual axis — only an explicit
      ``resolve.scale.y = "independent"`` is. Likewise an axis title only needs
      to be set on *one* layer, so the title check is chart-wide, not per-layer.
    * **Unit** (per ``mark``): truncated baseline, pie hazards, rainbow / CVD
      palette, polarity, mark shadow — run on every mark-bearing spec.
    """
    findings: List[Dict[str, Any]] = []

    # Composition: a TRUE dual y-axis is an explicit independent y-scale resolve
    # at some layering level. (The old "two layers both encode y" heuristic
    # false-flagged every confidence band and error bar — removed.)
    for node in _iter_specs(spec):
        resolve_y = ((node.get("resolve") or {}).get("scale") or {}).get("y")
        if resolve_y == "independent":
            findings.append(make_finding("dual-y-axis", "error", "two independent y scales", path))

    # Composition: a quantitative x/y axis must have a title *somewhere* in the
    # chart. Gather across units so a titled main layer covers an untitled
    # reference-line / diagonal layer (which is idiomatic and correct).
    units = list(_iter_units(spec))
    for axis in ("x", "y"):
        # A quantitative channel needs a title — unless its axis is explicitly
        # hidden (``"axis": null`` / ``false``), which is legitimate for vector
        # fields, small-multiple insets, and glyph charts. A title counts whether
        # it is set the long way (``axis.title``) or via the channel-level
        # ``title`` shorthand (both valid Vega-Lite). One titled layer covers the
        # whole shared axis.
        visible_untitled = []
        any_titled = False
        for u in units:
            ch = (u.get("encoding") or {}).get(axis) or {}
            if ch.get("type") != "quantitative":
                continue
            ax = ch.get("axis", "__default__")
            has_title = bool((ch.get("title") or "").strip()) or bool(
                (ax.get("title") if isinstance(ax, dict) else "") or ""
            )
            if has_title:
                any_titled = True
            elif ax is not None and ax is not False:  # visible but untitled
                visible_untitled.append(ch)
        if visible_untitled and not any_titled:
            findings.append(make_finding(
                "missing-axis-title", "error",
                f"{axis} axis has no title on any visible layer",
                path,
            ))

    # Composition: gradient background is chart junk.
    config = spec.get("config") or {}
    background = config.get("background") or spec.get("background") or ""
    if isinstance(background, str) and "gradient" in background.lower():
        findings.append(make_finding("chartjunk", "warning", "background uses a gradient", path))

    # Unit rules on every mark-bearing spec (top-level or nested).
    for unit in units:
        findings.extend(_unit_rules(unit, path))

    return findings


# ------------------------------------------------------------------
# HTML parsing
# ------------------------------------------------------------------
class _FigureScanner(HTMLParser):
    """Collect ``<figure>`` blocks and inner ``<img>`` tags."""

    def __init__(self) -> None:
        """Initialise the ``<figure>`` collector with empty figure list and stack."""
        super().__init__(convert_charrefs=True)
        self.figures: List[Dict[str, Any]] = []
        self._stack: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """Track ``<figure>`` / ``<figcaption>`` / ``<img>`` openings and their nesting."""
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag == "figure":
            entry = {"role": attr_map.get("role", ""), "has_caption": False, "imgs": [], "line": self.getpos()[0]}
            self.figures.append(entry)
            self._stack.append(entry)
        elif tag == "figcaption" and self._stack:
            self._stack[-1]["has_caption"] = True
        elif tag == "img" and self._stack:
            self._stack[-1]["imgs"].append({"alt": attr_map.get("alt", None), "line": self.getpos()[0]})

    def handle_endtag(self, tag: str) -> None:
        """Pop the current ``<figure>`` off the stack when it closes."""
        if tag == "figure" and self._stack:
            self._stack.pop()


def rules_for_html(text: str, path: str) -> List[Dict[str, Any]]:
    """Scan an HTML document for figure-level a11y and viz sins."""
    findings: List[Dict[str, Any]] = []
    scanner = _FigureScanner()
    scanner.feed(text)
    for fig in scanner.figures:
        if fig["role"] != "img" and not fig["has_caption"]:
            findings.append(make_finding(
                "role-img-missing", "error",
                "<figure> without role=\"img\" and no <figcaption>",
                path, fig["line"],
            ))
        for img in fig["imgs"]:
            if img["alt"] is None:
                findings.append(make_finding(
                    "alt-missing", "error",
                    "<img> inside <figure> has no alt attribute",
                    path, img["line"],
                ))
    return findings


# ------------------------------------------------------------------
# SVG parsing (matplotlib output)
# ------------------------------------------------------------------
def rules_for_svg(text: str, path: str) -> List[Dict[str, Any]]:
    """Best-effort rules against a matplotlib-emitted SVG."""
    findings: List[Dict[str, Any]] = []

    # rainbow palette heuristic
    if re.search(r"\b(jet|hsv|rainbow)\b", text, re.IGNORECASE):
        findings.append(make_finding(
            "rainbow-palette", "error",
            "SVG references a rainbow colormap (jet/hsv/rainbow)",
            path,
        ))

    # chartjunk — shadows / filter blurs
    if "<filter" in text and ("feDropShadow" in text or "feGaussianBlur" in text):
        findings.append(make_finding("chartjunk", "warning", "SVG uses a drop-shadow / blur filter", path))

    # pie-3d — perspective transform
    if re.search(r"transform=\"matrix\([^\"]*perspective", text, re.IGNORECASE):
        findings.append(make_finding("pie-3d", "error", "SVG uses a perspective transform", path))

    return findings


# ------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------
def format_human(findings: List[Dict[str, Any]]) -> str:
    """Human-readable finding summary."""
    if not findings:
        return "clean"
    lines = []
    counts = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f["severity"]] += 1
        lines.append(f"  {f['path']}:{f['line']}:1  {f['severity']:<8} {f['rule']:<24} {f['message']}")
    lines.append(f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} info")
    return "\n".join(lines)


def format_json(findings: List[Dict[str, Any]]) -> str:
    """JSON finding summary."""
    counts = {"errors": 0, "warnings": 0, "info": 0}
    for f in findings:
        key = f["severity"] + ("s" if f["severity"] != "info" else "")
        counts[key] += 1
    return json.dumps({"findings": findings, "summary": counts}, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = make_parser(
        prog="audit_figure",
        description=(
            "Static auditor for Vega-Lite JSON, matplotlib SVG, or HTML "
            "with <figure> blocks. Flags the small set of data-viz "
            "mistakes that survive review."
        ),
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to audit.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the human-readable summary.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors for the exit code.")
    parser.add_argument("--ignore", default="", help="Comma-separated rule IDs to skip.")
    parser.add_argument("--only", default="", help="Comma-separated rule IDs to keep (exclusive with --ignore).")
    return parser


def iter_files(paths: List[str]) -> List[Path]:
    """Expand paths (files or directories) into a flat file list."""
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for suffix in (".json", ".svg", ".html", ".htm"):
                out.extend(sorted(p.rglob(f"*{suffix}")))
        elif p.is_file():
            out.append(p)
    return out


def audit_one(path: Path) -> List[Dict[str, Any]]:
    """Dispatch to the right rule set based on file extension."""
    text = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if ext == ".json":
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as exc:
            return [make_finding("invalid-json", "error", str(exc), str(path))]
        return rules_for_vega(spec, str(path))
    if ext == ".svg":
        return rules_for_svg(text, str(path))
    if ext in (".html", ".htm"):
        return rules_for_html(text, str(path))
    return [make_finding("unsupported-format", "info", f"skipping {ext}", str(path))]


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    ignore = {s.strip() for s in args.ignore.split(",") if s.strip()}
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    all_findings: List[Dict[str, Any]] = []
    for p in iter_files(args.paths):
        findings = audit_one(p)
        for f in findings:
            if only and f["rule"] not in only:
                continue
            if f["rule"] in ignore:
                continue
            all_findings.append(f)

    if args.json:
        print(format_json(all_findings))
    else:
        print(format_human(all_findings))

    errors = sum(1 for f in all_findings if f["severity"] == "error")
    warnings = sum(1 for f in all_findings if f["severity"] == "warning")
    if errors > 0:
        return 1
    if args.strict and warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
