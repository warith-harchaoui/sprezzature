#!/usr/bin/env python3
"""Generate an *embedding projector* figure as a single self-contained SVG.

An embedding projector — the interaction popularised by the TensorFlow
Embedding Projector — takes a high-dimensional embedding (word vectors,
image features, user profiles) projected down to two dimensions and lets
the reader *walk the neighbourhood*: point at any item and it lights up
its nearest neighbours, so "which things does the model think are alike?"
becomes a hover instead of a table lookup. Items that mean similar things
land near each other; a point's closest neighbours are its semantic kin.

This module builds the SVG string **by hand** (no d3 / three / plotly,
no Vega). The single artifact it writes is BOTH:

* a complete **still** figure — every word is a coloured dot on a
  poster-scale canvas, a handful of representative words per cluster carry
  always-on labels, a cluster legend keys the colours, and a communicative
  title plus a one-line takeaway are fully drawn. A static rasteriser
  (``rsvg-convert``) or an ``<img>`` embed shows a correct, self-explaining
  scatter with no animation and no grounding shadow; and

* an **interactive** figure — a framework-free vanilla-JavaScript block in
  a ``<script>`` element wires the projector's signature move. Hover,
  focus or tap a word to highlight it, draw thin connector lines to its
  ``k`` nearest neighbours, reveal the word's label and its neighbours'
  labels on soft pills, and dim every other point so the local
  neighbourhood pops. A cluster legend isolates one cluster on hover /
  focus. Points are keyboard-focusable, and a reduced-motion query drops
  the transitions.

The example data is illustrative but true-to-life: ~200 real English words
grouped into six everyday semantic families (Animals, Colours, Countries,
Fruits, Instruments, Sports). Each family is a Gaussian blob around a
spread centroid with a little inter-cluster overlap near the borders, so
the clusters read clearly while a point's nearest neighbours stay
semantically sensible — mostly same-family, occasionally a border word
from an adjacent family. The ``k = 6`` nearest neighbours per point are
precomputed from the 2D layout distance; that neighbour relation is the
"projector" the interaction reveals. A fixed seed makes the committed file
byte-reproducible.

Usage
-----
    python make_embedding_projector.py                 # writes the house SVG
    python make_embedding_projector.py --out other.svg
    python make_embedding_projector.py --seed 11

Style rules: numpy docstrings, full typing, dict-as-record over ad-hoc
classes, generous comments.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import load_palette, os_adaptive_style, os_dark_style  # noqa: E402
from _render import write_svg  # noqa: E402
from _interactive import fullscreen_control  # noqa: E402

# Repo-relative default output — the one SVG artifact this figure ships.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "svg-examples"
    / "embedding-projector.svg"
)

# House-style tokens (mirror _style.vega_config, kept literal so this
# generator needs no import of the dataviz tier at build time).
_INK = "#1D1D1F"        # primary text
_SECONDARY = "#6E6E73"  # subtitle / secondary text
_BG = "#FFFFFF"         # white ground
_FONT = "Roboto, system-ui, sans-serif"
_MONO = "Roboto Mono, ui-monospace, monospace"

# k nearest neighbours revealed for a focused word — the "projector" relation.
_K = 6

# Fixed seed so the committed SVG is byte-reproducible.
_SEED = 20260726


# --------------------------------------------------------------------------- #
# Illustrative data — six everyday semantic families of real words            #
# --------------------------------------------------------------------------- #
# Each family maps to one Apple-system palette key. The words are genuine
# vocabulary a reader recognises, never "Category A/B/C", so the neighbour
# read is intuitive: point at "violin" and its neighbours are other
# instruments, point at a border word and one neighbour may be a fruit.
_CLUSTERS: List[Tuple[str, str]] = [
    ("Animals", "Blue"),
    ("Colours", "Purple"),
    ("Countries", "Orange"),
    ("Fruits", "Green"),
    ("Instruments", "Teal"),
    ("Sports", "Red"),
]

_WORDS: Dict[str, List[str]] = {
    "Animals": [
        "dog", "cat", "horse", "elephant", "tiger", "lion", "wolf", "fox",
        "bear", "rabbit", "deer", "mouse", "otter", "badger", "hedgehog",
        "squirrel", "raccoon", "panda", "koala", "leopard", "cheetah",
        "giraffe", "zebra", "camel", "donkey", "goat", "sheep", "cow",
        "pig", "hamster", "ferret", "beaver", "moose", "bison",
    ],
    "Colours": [
        "red", "orange", "yellow", "green", "blue", "purple", "violet",
        "indigo", "crimson", "scarlet", "magenta", "turquoise", "teal",
        "cyan", "amber", "maroon", "olive", "lavender", "coral", "beige",
        "ivory", "azure", "emerald", "ruby", "sapphire", "cobalt",
        "charcoal", "khaki", "lilac", "peach", "mint", "salmon",
    ],
    "Countries": [
        "France", "Spain", "Italy", "Germany", "Portugal", "Greece",
        "Norway", "Sweden", "Poland", "Ireland", "Brazil", "Argentina",
        "Chile", "Mexico", "Canada", "Egypt", "Kenya", "Morocco",
        "Japan", "China", "India", "Vietnam", "Thailand", "Turkey",
        "Iceland", "Finland", "Austria", "Belgium", "Croatia", "Peru",
        "Nigeria", "Ghana", "Nepal", "Jordan",
    ],
    "Fruits": [
        "apple", "banana", "orange", "grape", "peach", "pear", "cherry",
        "plum", "mango", "melon", "lemon", "lime", "kiwi", "papaya",
        "apricot", "fig", "guava", "lychee", "coconut", "pineapple",
        "raspberry", "blueberry", "blackberry", "cranberry", "pomegranate",
        "nectarine", "tangerine", "clementine", "date", "olive", "avocado",
        "passionfruit", "starfruit", "quince",
    ],
    "Instruments": [
        "violin", "cello", "viola", "guitar", "banjo", "harp", "piano",
        "flute", "clarinet", "oboe", "bassoon", "trumpet", "trombone",
        "tuba", "saxophone", "drums", "timpani", "xylophone", "accordion",
        "mandolin", "ukulele", "harmonica", "organ", "sitar", "lute",
        "bagpipes", "recorder", "cymbal", "tambourine", "marimba",
        "kazoo", "fiddle",
    ],
    "Sports": [
        "soccer", "basketball", "tennis", "cricket", "rugby", "baseball",
        "hockey", "golf", "boxing", "cycling", "swimming", "rowing",
        "sailing", "skiing", "surfing", "climbing", "fencing", "archery",
        "judo", "karate", "wrestling", "volleyball", "badminton", "squash",
        "handball", "curling", "diving", "gymnastics", "marathon",
        "triathlon", "skating", "snowboarding",
    ],
}


# --------------------------------------------------------------------------- #
# Layout — spread centroids + Gaussian jitter with a little border overlap     #
# --------------------------------------------------------------------------- #
def _build_points(seed: int) -> List[Dict[str, Any]]:
    """Place every word at a 2D position and return per-point records.

    Each family is a Gaussian blob around a centroid arranged on a ring, so
    the six clusters spread out and read clearly. The per-blob spread is
    tuned so adjacent families brush at their borders — enough overlap that
    an occasional nearest neighbour comes from a neighbouring family, but
    not so much that the clusters merge. Positions live in a normalised
    ``[-1, 1] x [-1, 1]`` model space; the SVG scales them to the canvas.

    Parameters
    ----------
    seed : int
        Seed for the reproducible sample.

    Returns
    -------
    list of dict
        One record per word: ``{"word", "cluster", "ci", "x", "y"}`` with
        ``ci`` the cluster index and ``(x, y)`` the model-space position.
    """
    rng = random.Random(seed)
    n_clusters = len(_CLUSTERS)

    # Centroids on a ring so the blobs fan out around the canvas centre.
    # A wide ring keeps the six families clearly separated; the spread below
    # is tuned so adjacent blobs only brush at their borders.
    ring = 0.82
    centroids: List[Tuple[float, float]] = []
    for c in range(n_clusters):
        ang = 2.0 * math.pi * c / n_clusters - math.pi / 2.0
        centroids.append((ring * math.cos(ang), ring * math.sin(ang)))

    # Per-family spread. A touch of anisotropy keeps the blobs from reading
    # as perfect discs; the magnitude leaves a soft overlap at the borders so
    # an occasional nearest neighbour crosses into an adjacent family.
    spread = 0.205

    # Cap each jitter at ~2 sigma and resample past it: a Gaussian tail can
    # otherwise fling a word clear across the canvas into a distant family,
    # which makes its nearest neighbours semantically nonsensical (a "tiger"
    # ringed only by sports). Capping keeps the soft *border* overlap between
    # adjacent families while ruling out long-range outliers.
    sd_x, sd_y = spread * 1.05, spread * 0.92
    cap = 2.0

    def _capped(rng_: random.Random, sd: float) -> float:
        """Draw a Gaussian jitter clamped to +/- ``cap`` sigma (resample)."""
        for _ in range(16):
            v = rng_.gauss(0.0, sd)
            if abs(v) <= cap * sd:
                return v
        return max(-cap * sd, min(cap * sd, v))

    records: List[Dict[str, Any]] = []
    for ci, (name, _key) in enumerate(_CLUSTERS):
        cxm, cym = centroids[ci]
        for word in _WORDS[name]:
            # Independent capped-Gaussian jitter on each axis, mild anisotropy.
            x = cxm + _capped(rng, sd_x)
            y = cym + _capped(rng, sd_y)
            records.append({
                "word": word,
                "cluster": name,
                "ci": ci,
                "x": round(x, 4),
                "y": round(y, 4),
            })
    return records


def _nearest_neighbours(records: List[Dict[str, Any]], k: int) -> List[List[int]]:
    """Precompute each point's ``k`` nearest neighbours by 2D distance.

    This is the projector relation the interaction reveals: for word ``i``
    the ``k`` closest words in the 2D layout, ordered nearest-first. Because
    the layout places semantic families as blobs with soft borders, these
    neighbours are mostly same-family with the occasional border crossing —
    exactly the "similar things are near" story.

    Parameters
    ----------
    records : list of dict
        Point records from :func:`_build_points`.
    k : int
        Neighbours to keep per point.

    Returns
    -------
    list of list of int
        ``nbr[i]`` is the list of ``k`` neighbour indices for point ``i``.
    """
    n = len(records)
    xs = [float(r["x"]) for r in records]
    ys = [float(r["y"]) for r in records]
    neighbours: List[List[int]] = []
    for i in range(n):
        xi, yi = xs[i], ys[i]
        # (distance^2, index) for every other point; keep the k smallest.
        dists = [
            ((xs[j] - xi) ** 2 + (ys[j] - yi) ** 2, j)
            for j in range(n) if j != i
        ]
        dists.sort(key=lambda t: t[0])
        neighbours.append([j for _d, j in dists[:k]])
    return neighbours


# --------------------------------------------------------------------------- #
# Representative always-on labels                                             #
# --------------------------------------------------------------------------- #
def _representative_labels(records: List[Dict[str, Any]], per_cluster: int) -> List[int]:
    """Pick a few words per cluster to carry always-on labels in the still.

    The still must not be anonymous, so each cluster shows a handful of
    named words. To keep the labels legible we pick words spread across the
    blob (near-centre plus a couple toward the rim) rather than a random
    huddle, and cap the total so the poster stays uncluttered.

    Parameters
    ----------
    records : list of dict
        Point records from :func:`_build_points`.
    per_cluster : int
        How many words to label per cluster.

    Returns
    -------
    list of int
        Indices of the words that get an always-on label.
    """
    by_cluster: Dict[int, List[int]] = {}
    for i, r in enumerate(records):
        by_cluster.setdefault(int(r["ci"]), []).append(i)

    chosen: List[int] = []
    for ci, members in by_cluster.items():
        mx = sum(float(records[i]["x"]) for i in members) / len(members)
        my = sum(float(records[i]["y"]) for i in members) / len(members)
        # Order members by distance to the centroid.
        ordered = sorted(
            members,
            key=lambda i: (float(records[i]["x"]) - mx) ** 2 + (float(records[i]["y"]) - my) ** 2,
        )
        # One central word + a couple stepped toward the rim for spread.
        picks: List[int] = []
        if ordered:
            picks.append(ordered[0])
        step = max(1, len(ordered) // max(per_cluster, 1))
        for m in range(1, per_cluster):
            idx = min(len(ordered) - 1, m * step)
            if ordered[idx] not in picks:
                picks.append(ordered[idx])
        chosen.extend(picks[:per_cluster])
    return chosen


# --------------------------------------------------------------------------- #
# Palette                                                                     #
# --------------------------------------------------------------------------- #
_PALETTE = load_palette()
_FALLBACK = {
    "Blue": "#007AFF", "Purple": "#AF52DE", "Orange": "#FF9500",
    "Green": "#34C759", "Teal": "#5AC8FA", "Red": "#FF3B30",
}


def _hex(key: str, palette: Dict[str, str] | None = None) -> str:
    """Return the brand hex for a palette key, with a curated fallback.

    Parameters
    ----------
    key : str
        Palette key (e.g. ``"Blue"``).
    palette : dict of str to str, optional
        Palette to read from; defaults to the module-level ``_PALETTE``
        (the ``universal`` level). A caller passes an accessibility-remapped
        palette here to recolour without touching the module default.
    """
    pal = _PALETTE if palette is None else palette
    return pal.get(key, _FALLBACK[key])


def _lighten(hexv: str, t: float) -> str:
    """Blend ``hexv`` toward white by fraction ``t`` (0 = same, 1 = white)."""
    r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * t) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


# --------------------------------------------------------------------------- #
# Fit helpers                                                                 #
# --------------------------------------------------------------------------- #
def _fmt(v: float) -> str:
    """Format a float compactly for SVG (1 decimal, no trailing .0)."""
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _project_positions(
    records: List[Dict[str, Any]],
    *,
    plot_x: float,
    plot_y: float,
    plot_w: float,
    plot_h: float,
    pad: float,
) -> List[Tuple[float, float]]:
    """Scale model-space ``[-1, 1]`` positions into the canvas plot box.

    Preserves aspect ratio (a square model space maps to a square sub-box
    centred in the plot area) so the blobs never shear. Padding keeps the
    outermost dots and their labels off the plot edge.

    Parameters
    ----------
    records : list of dict
        Point records carrying model-space ``x`` / ``y``.
    plot_x, plot_y : float
        Top-left pixel corner of the plot area.
    plot_w, plot_h : float
        Pixel size of the plot area.
    pad : float
        Inner margin kept clear on every side.

    Returns
    -------
    list of tuple of float
        Pixel ``(px, py)`` per point.
    """
    xs = [float(r["x"]) for r in records]
    ys = [float(r["y"]) for r in records]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span_x = maxx - minx or 1.0
    span_y = maxy - miny or 1.0
    avail_w = plot_w - 2 * pad
    avail_h = plot_h - 2 * pad
    scale = min(avail_w / span_x, avail_h / span_y)
    off_x = plot_x + pad + (avail_w - span_x * scale) / 2.0
    off_y = plot_y + pad + (avail_h - span_y * scale) / 2.0
    out: List[Tuple[float, float]] = []
    for x, y in zip(xs, ys):
        px = off_x + (x - minx) * scale
        # SVG y grows downward: flip so model +y reads as "up".
        py = off_y + (maxy - y) * scale
        out.append((px, py))
    return out


# --------------------------------------------------------------------------- #
# The embedded interactive controller (vanilla JS, no dependency)             #
# --------------------------------------------------------------------------- #
def _script_svg(
    records: List[Dict[str, Any]],
    neighbours: List[List[int]],
    positions: List[Tuple[float, float]],
    colors: List[str],
) -> str:
    """Emit the ``<script>`` that makes the still figure interactive.

    The controller is deliberately framework-free ES5/ES6 (no d3 / three /
    plotly) and drives the projector's signature interaction on top of the
    already-drawn still:

    * **hover / focus / tap a point** — highlight it, draw thin curved
      connector lines to its ``k`` nearest neighbours, reveal the focused
      word's label and its neighbours' labels on soft pills, and dim every
      other point and label so the local neighbourhood pops. Built on
      **Pointer Events** with a ``mouseover`` / ``focusin`` pair so mouse,
      trackpad, touch, pen and the keyboard all reach the same code path;
    * **leave / blur** — restore the resting still;
    * a reduced-motion media query (honoured via a CSS class already in the
      document) drops the fade transitions.

    The point records, neighbour lists and pixel geometry are handed to JS
    as one JSON blob so the browser owns all the geometry; the pixel
    positions match the server-rendered still exactly, so the first
    highlighted frame is pixel-consistent with the static figure.

    Parameters
    ----------
    records : list of dict
        Point records (word + cluster).
    neighbours : list of list of int
        ``k`` nearest-neighbour indices per point.
    positions : list of tuple of float
        Pixel ``(px, py)`` per point, matching the drawn circles.
    colors : list of str
        Per-cluster hex, indexed by cluster id.

    Returns
    -------
    str
        A ``<script>`` element (CDATA-wrapped) ready to drop into the SVG.
    """
    cfg = {
        "pts": [
            {
                "w": r["word"],
                "c": int(r["ci"]),
                "px": round(positions[i][0], 1),
                "py": round(positions[i][1], 1),
            }
            for i, r in enumerate(records)
        ],
        "nbr": neighbours,
        "colors": colors,
        "k": _K,
        "vw": _VIEW_W,
        "vh": _VIEW_H,
    }

    js = r"""
var CFG = __CFG__;
var svg = document.currentScript && document.currentScript.ownerSVGElement;
if (!svg) { svg = document.querySelector('svg'); }
var NS = 'http://www.w3.org/2000/svg';
var pts = CFG.pts, nbr = CFG.nbr, colors = CFG.colors;
var N = pts.length;

// Overlay groups drawn on top of the resting still. Links go under pills.
var linkG = document.createElementNS(NS, 'g');
linkG.setAttribute('class', 'proj-links');
linkG.setAttribute('pointer-events', 'none');
var pillG = document.createElementNS(NS, 'g');
pillG.setAttribute('class', 'proj-pills');
pillG.setAttribute('pointer-events', 'none');
svg.appendChild(linkG);
svg.appendChild(pillG);

// Boxes of already-placed pills this frame, so a new pill can dodge them.
var PLACED = [];
function clearOverlay() {
  while (linkG.firstChild) linkG.removeChild(linkG.firstChild);
  while (pillG.firstChild) pillG.removeChild(pillG.firstChild);
  PLACED = [];
}

// Does box {x,y,w,h} overlap any already-placed pill (with a small gap)?
function collides(x, y, w, h) {
  for (var i = 0; i < PLACED.length; i++) {
    var b = PLACED[i];
    if (x < b.x + b.w + 3 && x + w + 3 > b.x &&
        y < b.y + b.h + 2 && y + h + 2 > b.y) return true;
  }
  return false;
}

// A soft rounded label pill: coloured dot + word on a white rounded rect.
function makePill(word, px, py, color, focused) {
  var g = document.createElementNS(NS, 'g');
  var text = document.createElementNS(NS, 'text');
  text.setAttribute('font-family', 'Roboto, system-ui, sans-serif');
  text.setAttribute('font-size', focused ? '19' : '16');
  text.setAttribute('font-weight', focused ? '700' : '600');
  text.setAttribute('fill', '#1D1D1F');
  text.textContent = word;
  // rough advance width; getComputedTextLength refines once in the DOM
  var fs = focused ? 19 : 16;
  var w = word.length * fs * 0.58 + 40;
  var h = focused ? 32 : 27;
  var rect = document.createElementNS(NS, 'rect');
  rect.setAttribute('rx', (h / 2).toFixed(1));
  rect.setAttribute('fill', '#FFFFFF');
  rect.setAttribute('fill-opacity', '0.96');
  rect.setAttribute('stroke', color);
  rect.setAttribute('stroke-opacity', focused ? '0.95' : '0.55');
  rect.setAttribute('stroke-width', focused ? '2' : '1.4');
  var dot = document.createElementNS(NS, 'circle');
  dot.setAttribute('r', focused ? '6' : '5');
  dot.setAttribute('fill', color);
  g.appendChild(rect); g.appendChild(dot); g.appendChild(text);
  pillG.appendChild(g);
  // measure and lay out: dot at left, text after it, box around both
  var tw = text.getComputedTextLength ? text.getComputedTextLength() : (w - 40);
  w = tw + (focused ? 44 : 40);
  var ox = px + 14, oy = py - h / 2;
  // keep the pill on-canvas (viewBox is 0..VW / 0..VH)
  if (ox + w > CFG.vw - 8) ox = px - w - 14;
  if (oy < 8) oy = 8;
  if (oy + h > CFG.vh - 8) oy = CFG.vh - 8 - h;
  // Nudge vertically to dodge an already-placed pill when neighbours pile up;
  // try downward then upward before giving up so labels stay readable.
  if (!focused) {
    var base = oy, moved = false;
    for (var s = 1; s <= 6 && collides(ox, oy, w, h); s++) {
      oy = base + s * (h + 4);
      if (oy + h > CFG.vh - 8) { oy = base - s * (h + 4); }
      moved = true;
    }
    if (moved && oy < 8) oy = 8;
  }
  PLACED.push({ x: ox, y: oy, w: w, h: h });
  rect.setAttribute('x', ox.toFixed(1));
  rect.setAttribute('y', oy.toFixed(1));
  rect.setAttribute('width', w.toFixed(1));
  rect.setAttribute('height', h.toFixed(1));
  dot.setAttribute('cx', (ox + (focused ? 18 : 16)).toFixed(1));
  dot.setAttribute('cy', (oy + h / 2).toFixed(1));
  text.setAttribute('x', (ox + (focused ? 32 : 28)).toFixed(1));
  text.setAttribute('y', (oy + h / 2 + fs * 0.35).toFixed(1));
  return g;
}

// Highlight point i: dim the rest, draw neighbour links + pills.
function focusPoint(i) {
  clearOverlay();
  svg.classList.add('proj-active');
  var p = pts[i];
  var col = colors[p.c];
  // Un-dim the focused point and its neighbours.
  var focusIds = {}; focusIds[i] = true;
  var list = nbr[i] || [];
  for (var n = 0; n < list.length; n++) focusIds[list[n]] = true;
  for (var id in focusIds) {
    var el = document.getElementById('pt' + id);
    if (el) el.classList.add('proj-lit');
  }
  // Curved connector lines from the focused point to each neighbour.
  for (var n2 = 0; n2 < list.length; n2++) {
    var q = pts[list[n2]];
    var mx = (p.px + q.px) / 2, my = (p.py + q.py) / 2;
    // gentle perpendicular bow so overlapping links stay legible
    var dx = q.px - p.px, dy = q.py - p.py;
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    var bow = Math.min(26, len * 0.16);
    var cxp = mx - dy / len * bow, cyp = my + dx / len * bow;
    var path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M' + p.px + ',' + p.py + ' Q' + cxp.toFixed(1) +
      ',' + cyp.toFixed(1) + ' ' + q.px + ',' + q.py);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', colors[q.c]);
    path.setAttribute('stroke-width', '2');
    path.setAttribute('stroke-opacity', '0.75');
    path.setAttribute('stroke-linecap', 'round');
    linkG.appendChild(path);
  }
  // Neighbour pills first (under), focused pill last (on top).
  for (var n3 = 0; n3 < list.length; n3++) {
    var qq = pts[list[n3]];
    makePill(qq.w, qq.px, qq.py, colors[qq.c], false);
  }
  makePill(p.w, p.px, p.py, col, true);
}

function blur() {
  svg.classList.remove('proj-active');
  clearOverlay();
  var lit = svg.querySelectorAll('.proj-lit');
  for (var i = 0; i < lit.length; i++) lit[i].classList.remove('proj-lit');
}

// --- event wiring: pointer + keyboard both reach focusPoint ------------
function idFromTarget(t) {
  while (t && t !== svg) {
    if (t.id && t.id.indexOf('pt') === 0) {
      var n = parseInt(t.id.slice(2), 10);
      if (!isNaN(n)) return n;
    }
    t = t.parentNode;
  }
  return -1;
}
svg.addEventListener('pointerover', function (e) {
  var i = idFromTarget(e.target);
  if (i >= 0) focusPoint(i);
});
svg.addEventListener('pointerout', function (e) {
  var i = idFromTarget(e.target);
  var to = idFromTarget(e.relatedTarget);
  if (i >= 0 && to < 0) blur();
});
// tap on touch: focus, and let a tap elsewhere clear it
svg.addEventListener('pointerdown', function (e) {
  if (e.pointerType === 'touch') {
    var i = idFromTarget(e.target);
    if (i >= 0) { focusPoint(i); if (e.cancelable) e.preventDefault(); }
    else blur();
  }
});
// keyboard: focusing a point (Tab) lights its neighbourhood
svg.addEventListener('focusin', function (e) {
  var i = idFromTarget(e.target);
  if (i >= 0) focusPoint(i);
});
svg.addEventListener('focusout', function (e) {
  var i = idFromTarget(e.target);
  var to = idFromTarget(e.relatedTarget);
  if (i >= 0 && to < 0) blur();
});
"""
    data = json.dumps(cfg, separators=(",", ":"))
    js = js.replace("__CFG__", data)
    return f'<script type="text/javascript"><![CDATA[{js}]]></script>'


# --------------------------------------------------------------------------- #
# Canvas geometry (module-level so the JS clamp can read it)                   #
# --------------------------------------------------------------------------- #
_VIEW_W = 1400
_VIEW_H = 1120
_M_TOP = 150       # y where the plot area begins (below the header)
_M_LEFT = 64
_M_RIGHT = 64
_LEGEND_H = 70     # reserved strip at the bottom for the legend


# --------------------------------------------------------------------------- #
# SVG assembly                                                                 #
# --------------------------------------------------------------------------- #
def build_svg(
    seed: int = _SEED,
    mode: str = "self-contained",
    accessibility: str = "universal",
) -> str:
    """Assemble the full embedding-projector SVG document as a string.

    The document is a complete still — every word as a coloured dot, a few
    always-on labels, a cluster legend, a communicative header — *and*
    carries an embedded ``<script>`` that wires the hover / focus / tap
    projector interaction. No SMIL animation and no grounding shadow: a
    static rasteriser sees exactly the resting frame.

    Parameters
    ----------
    seed : int, optional
        Random seed for the reproducible word layout.
    mode : str, optional
        Interactivity mode for the shared fullscreen control (see
        :mod:`_interactive`). Three modes: ``"self-contained"`` (default) ships
        a self-carrying fullscreen button and its wiring script; ``"external"``
        ships no internal button and defers to a page-level module; ``"static"``
        ships no interactivity at all. The static PNG raster is byte-identical
        across modes because the button starts hidden.
    accessibility : str, optional
        Palette accessibility level (``"universal"``, ``"high-contrast"``,
        ``"monochrome"``, ``"deuteranopia"``, ``"protanopia"`` or
        ``"tritanopia"``). Defaults to ``"universal"``, the
        colour-vision-safe standard, which reuses the module-level palette so
        the emitted SVG stays unchanged; any other level remaps the cluster
        colours.

    Returns
    -------
    str
        A complete, self-contained SVG document.
    """
    records = _build_points(seed)
    neighbours = _nearest_neighbours(records, _K)
    n = len(records)

    # ``universal`` reuses the module-level _PALETTE (output byte-identical);
    # any other level re-reads the palette at that accessibility level.
    palette = None if accessibility == "universal" else load_palette(accessibility)
    colors = [_hex(key, palette) for _name, key in _CLUSTERS]
    fills = [_lighten(c, 0.30) for c in colors]  # slightly washed dot fill

    plot_x = _M_LEFT
    plot_y = _M_TOP
    plot_w = _VIEW_W - _M_LEFT - _M_RIGHT
    plot_h = _VIEW_H - _M_TOP - _LEGEND_H
    positions = _project_positions(
        records, plot_x=plot_x, plot_y=plot_y,
        plot_w=plot_w, plot_h=plot_h, pad=54,
    )

    rep = set(_representative_labels(records, per_cluster=4))

    title_txt = "Words that mean similar things land nearby"
    subtitle_txt = (
        "An embedding of 200 words projected to 2D · point at a word to "
        "light up its 6 nearest neighbours · illustrative data"
    )
    desc_txt = (
        "Interactive embedding projector. Two hundred everyday English "
        "words from six semantic families (Animals, Colours, Countries, "
        "Fruits, Instruments, Sports) are shown as coloured dots, each "
        "placed by a high-dimensional word embedding projected down to two "
        "dimensions, so words that mean similar things land near one "
        "another and form six visible clusters. A handful of representative "
        "words per family carry always-on labels. Hover, focus with the "
        "keyboard, or tap any dot to highlight it, draw thin curved lines "
        "to its six nearest neighbours, reveal the word and its neighbours' "
        "labels, and dim the rest so the local neighbourhood stands out; "
        "most neighbours belong to the same family, with the occasional "
        "border word from a neighbouring family. A cluster legend at the "
        "bottom isolates one family on hover. The figure is shown as a "
        "static scatter when scripting is off."
    )

    parts: List[str] = []
    parts.append(
        f'<svg role="img" aria-labelledby="ep-title ep-desc" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" height="100%" '
        f'viewBox="0 0 {_VIEW_W} {_VIEW_H}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:100%;height:auto;touch-action:manipulation" '
        f'font-family="{_FONT}">'
    )
    parts.append(f'<title id="ep-title">{escape(title_txt)}</title>')
    parts.append(f'<desc id="ep-desc">{escape(desc_txt)}</desc>')

    # --- CSS: dot state transitions + the projector dimming.
    #     .proj-active dims every point except those tagged .proj-lit, and
    #     dims the always-on labels; a reduced-motion query drops the fade. ---
    css = (
        ".pt{transition:opacity .16s ease}"
        ".pt-halo{transition:opacity .16s ease}"
        ".rep-label{transition:opacity .16s ease}"
        ".legend g{cursor:pointer}"
        ".legend g:focus{outline:none}"
        # Projector focus: dim everything, then restore lit points.
        ".proj-active .pt{opacity:.12}"
        ".proj-active .pt-halo{opacity:.10}"
        ".proj-active .rep-label{opacity:.10}"
        ".proj-active .pt.proj-lit{opacity:1}"
        ".proj-active .pt-halo.proj-lit{opacity:1}"
        # Legend hover-isolate (pure CSS, like sfdp): fade non-matching clusters.
        + "".join(
            f"#ep:has(.legend .sw-{c}:is(:hover,:focus)) .pt:not(.c-{c}){{opacity:.10}}"
            f"#ep:has(.legend .sw-{c}:is(:hover,:focus)) .pt-halo:not(.c-{c}){{opacity:.08}}"
            f"#ep:has(.legend .sw-{c}:is(:hover,:focus)) .rep-label:not(.rl-{c}){{opacity:.10}}"
            for c in range(len(_CLUSTERS))
        )
        + ".pt:focus{outline:none}"
        ".pt:focus-visible .pt-core{stroke:#1D1D1F;stroke-width:2.4}"
        "@media (prefers-reduced-motion:reduce){"
        ".pt,.pt-halo,.rep-label{transition:none}}"
    )
    # OS-adaptive overrides (additive; the default render stays byte-identical
    # because every rule below lives inside an @media query, and a descendant
    # class rule only outranks the inline core/legend fill+stroke once the query
    # matches). Under prefers-contrast the six semantic-family hues deepen to
    # their high-contrast versions on the point cores, the legend swatches and
    # the representative-label dots. forced=True is safe: each family reads as a
    # spatial blob (position) and carries an always-visible legend label plus a
    # few named word pills, so cluster identity survives with no colour.
    cluster_series = {
        f".c-{c} .pt-core,.sw-{c} circle,.rl-{c} circle": colors[c]
        for c in range(len(_CLUSTERS))
    }
    css += os_adaptive_style(cluster_series, role="both", forced=True)
    # Additive dark mode: flip paper + the two ink tiers (data hues untouched).
    css += os_dark_style()
    parts.append(f"<style>{css}</style>")

    # --- background ---
    parts.append(f'<rect width="{_VIEW_W}" height="{_VIEW_H}" fill="{_BG}"/>')

    # --- header ---
    parts.append(
        f'<text x="{_M_LEFT}" y="66" font-size="40" font-weight="700" '
        f'fill="{_INK}">{escape(title_txt)}</text>'
    )
    parts.append(
        f'<text x="{_M_LEFT}" y="102" font-size="21" fill="{_SECONDARY}">'
        f'{escape(subtitle_txt)}</text>'
    )
    parts.append(
        f'<text x="{_M_LEFT}" y="130" font-size="16" fill="{_SECONDARY}">'
        f'Colour marks the semantic family · hover a legend swatch to isolate '
        f'one family</text>'
    )

    parts.append('<g id="ep">')

    # --- points. Each is a focusable <g> carrying a WHITE halo (never a
    #     dark ring) under a coloured core, plus a native <title> tooltip.
    #     Painter order is by cluster so same-family dots layer cleanly. ---
    parts.append('<g id="points">')
    order = sorted(range(n), key=lambda i: int(records[i]["ci"]))
    for i in order:
        r = records[i]
        ci = int(r["ci"])
        px, py = positions[i]
        word = escape(str(r["word"]))
        cluster = escape(str(r["cluster"]))
        parts.append(
            f'<g id="pt{i}" class="pt c-{ci}" tabindex="0" role="listitem" '
            f'aria-label="{word}, {cluster}">'
            f'<title>{word} — {cluster}</title>'
            # WHITE halo for separation in dense areas (no dark grounding ring).
            f'<circle class="pt-halo c-{ci}" cx="{_fmt(px)}" cy="{_fmt(py)}" '
            f'r="8.5" fill="{_BG}"/>'
            f'<circle class="pt-core" cx="{_fmt(px)}" cy="{_fmt(py)}" r="6.4" '
            f'fill="{fills[ci]}" stroke="{colors[ci]}" stroke-width="1.6"/>'
            f'</g>'
        )
    parts.append("</g>")

    # --- always-on representative labels so the still isn't anonymous.
    #     Small pale-white pill behind ink text; classed per cluster so the
    #     legend-isolate CSS can fade the non-matching ones. ---
    # pointer-events:none so an always-on label pill never steals the hover
    # from a dot beneath it — the dots must always own the pointer.
    parts.append('<g id="rep-labels" pointer-events="none">')
    for i in sorted(rep):
        r = records[i]
        ci = int(r["ci"])
        px, py = positions[i]
        word = escape(str(r["word"]))
        pill_w = 12.0 + 10.4 * len(str(r["word"])) + 14
        pill_h = 26
        # Place the pill on the side of the dot that faces open canvas: below
        # for dots in the upper half, above otherwise, and offset horizontally
        # away from the plot centre. Clamp to the canvas.
        mid_y = plot_y + plot_h / 2.0
        lx = px + 10 if px < plot_x + plot_w / 2.0 else px - pill_w - 10
        ly = py + 10 if py < mid_y else py - pill_h - 8
        lx = min(_VIEW_W - _M_RIGHT - pill_w, max(_M_LEFT, lx))
        ly = min(_VIEW_H - _LEGEND_H - pill_h, max(_M_TOP - 8, ly))
        parts.append(
            f'<g class="rep-label rl-{ci}">'
            f'<rect x="{_fmt(lx)}" y="{_fmt(ly)}" width="{_fmt(pill_w)}" '
            f'height="{pill_h}" rx="{pill_h / 2:.1f}" fill="{_BG}" '
            f'fill-opacity="0.90" stroke="{colors[ci]}" stroke-opacity="0.45" '
            f'stroke-width="1.2"/>'
            f'<circle cx="{_fmt(lx + 15)}" cy="{_fmt(ly + pill_h / 2)}" r="5" '
            f'fill="{colors[ci]}"/>'
            f'<text x="{_fmt(lx + 27)}" y="{_fmt(ly + pill_h / 2 + 5)}" '
            f'font-size="16" font-weight="600" fill="{_INK}">{word}</text>'
            f'</g>'
        )
    parts.append("</g>")

    # --- legend (bottom row): one focusable swatch per family, wired to the
    #     pure-CSS hover-isolate. Kept INSIDE #ep so :has() sees the swatch. ---
    ly = _VIEW_H - 28
    parts.append('<g class="legend">')
    cursor = float(_M_LEFT)
    counts = {name: len(words) for name, words in _WORDS.items()}
    for c, (name, _key) in enumerate(_CLUSTERS):
        seg = f"{name} ({counts[name]})"
        parts.append(
            f'<g class="sw-{c}" tabindex="0" role="button" '
            f'aria-label="Isolate the {escape(name)} family">'
            f'<title>Isolate the {escape(name)} family '
            f'({counts[name]} words)</title>'
            f'<circle cx="{cursor + 10:.1f}" cy="{ly - 6:.1f}" r="10" '
            f'fill="{colors[c]}"/>'
            f'<text x="{cursor + 28:.1f}" y="{ly:.1f}" font-size="19" '
            f'fill="{_INK}">{escape(seg)}</text>'
            f'</g>'
        )
        cursor += 40 + 11.0 * len(seg) + 30
    parts.append("</g>")  # /legend

    parts.append("</g>")  # /ep

    # --- the interactive controller ---
    parts.append(_script_svg(records, neighbours, positions, colors))

    # --- shared fullscreen control (top-right is open canvas here) ---
    parts.append(fullscreen_control(_VIEW_W, _VIEW_H, mode))

    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = argparse.ArgumentParser(
        prog="make_embedding_projector",
        description="Write the house-style still-plus-interactive embedding-projector SVG.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help="Destination SVG path (default: the shipped example).",
    )
    parser.add_argument(
        "--seed", type=int, default=_SEED, help="Random seed for the word layout."
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="Interactivity mode for the shared fullscreen control.",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal",
            "high-contrast",
            "monochrome",
            "deuteranopia",
            "protanopia",
            "tritanopia",
        ),
        default="universal",
        help="Palette accessibility level (default: universal, the CVD-safe standard).",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    """CLI entry point: build the SVG and write it to disk."""
    args = _build_parser().parse_args(argv)
    svg = build_svg(seed=args.seed, mode=args.mode, accessibility=args.accessibility)
    write_svg(args.out, svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
