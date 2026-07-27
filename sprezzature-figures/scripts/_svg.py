"""
_svg — tiny, output-identical SVG primitives shared by the make_* generators.

Every ``make_<id>.py`` generator hand-writes its SVG as f-strings. A
handful of primitives recurred verbatim across three or more of them and
are the *only* things factored out here, because each can be made
byte-for-byte identical to the inline code it replaces:

* :func:`xml_escape` — the three-``replace`` XML-metacharacter escape
  (``&`` → ``&amp;``, ``<`` → ``&lt;``, ``>`` → ``&gt;``) that ~11
  generators defined privately as ``_xml`` / ``_esc``.
* :func:`point_on_circle` — the polar-to-Cartesian point
  ``(cx + r*cos(theta), cy + r*sin(theta))`` (``theta`` already in
  radians) that several circular-layout generators (chord, windrose,
  radviz, speaking-time) spelled out inline.
* :func:`fmt_compact` — the ``f"{v:.1f}".rstrip("0").rstrip(".")``
  path-data float formatter that the streamgraph, difference-chart and
  bollinger generators each carried as a private ``_fmt``.
* :func:`catmull_rom_beziers` — the Catmull-Rom → cubic-Bézier ``C``
  command run those same three generators carried as a private
  ``_catmull_rom``. The caller passes its own formatter so the emitted
  string stays byte-identical (streamgraph/difference-chart/bollinger
  all pass :func:`fmt_compact`).
* :func:`hex_to_rgb` — the ``#RRGGBB`` → ``(r, g, b)`` int triple that
  the hexbin-map, binned-grid-map and circle-packing generators each
  spelled out as a private ``_hex_to_rgb``.
* :func:`svg_open` — the responsive, accessible ``<svg ...>`` root tag
  (explicit width/height, a matching ``viewBox`` so the graphic scales
  fluidly, the house font, and ``role``/``aria-labelledby`` wiring) that
  ~46 generators opened their document with verbatim. Only the exact
  shared template is emitted; generators whose root uses a different
  attribute order (e.g. andrews, which leads with ``aria-label``) keep
  their inline tag, so every adoption stays byte-identical.

Deliberately *not* extracted: the per-element hover/tooltip wrappers
(the ``<g tabindex=…><title>…`` blocks and their ``:hover`` CSS) and the
pill-label backgrounds. Those differ in class names, ARIA wiring, and
rounding across generators, so a shared helper could not be made
output-identical without editing rendered bytes — which the DRY refactor
must never do. Callers keep their own float formatting; these helpers
only return the raw string / floats the inline code produced.

Other tempting-but-rejected candidates (kept inline because they fail
either the rule of three *or* the byte-identical test): the annular
arc/sector path (rose == radial-bar only — two callers); the ``_polar``
clock-bearing helpers (behaviour splits by signature and all already
delegate to :func:`point_on_circle`); the Equal-Earth map projection
(spike-map and hexbin-map differ, and windbarb is equirectangular); the
flow-ribbon paths (three unrelated implementations); the sequential
colour ramp (hexbin vs binned differ in stops, gamma and light anchor);
and the ``convex_hull`` scan (only one of these generators uses it).

The module is **stdlib-only** — it imports nothing but :mod:`math` — so
it stays importable everywhere ``_style.py`` is (no dataviz tier needed).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
from typing import Callable, Sequence, Tuple


def xml_escape(text: str) -> str:
    """Escape the three XML metacharacters for safe inclusion in an SVG.

    Replaces ``&``, ``<`` and ``>`` with their entity forms, in that
    order (ampersand first so the ``&`` introduced by ``&lt;`` / ``&gt;``
    is not double-escaped). This is byte-identical to the private
    ``_xml`` / ``_esc`` helpers the generators previously carried; it is
    intentionally minimal (no quote escaping) because generator text only
    ever lands in element content, never inside an attribute value.

    Parameters
    ----------
    text : str
        Raw text (a label, place name, category, …) to embed as SVG
        element content.

    Returns
    -------
    str
        ``text`` with ``&`` → ``&amp;``, ``<`` → ``&lt;``, ``>`` →
        ``&gt;``.

    Examples
    --------
    >>> xml_escape("Tom & Jerry <3")
    'Tom &amp; Jerry &lt;3'
    """
    # Order matters: escape "&" first, otherwise the "&" in "&lt;" / "&gt;"
    # produced by the later replacements would itself get re-escaped.
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def point_on_circle(cx: float, cy: float, r: float, theta_rad: float) -> Tuple[float, float]:
    """Cartesian point at radius ``r`` and angle ``theta_rad`` about a centre.

    Standard math convention: ``theta_rad = 0`` points along +x (3
    o'clock) and grows counter-clockwise in a conventional axis — but in
    SVG's y-down space it reads as clockwise. Callers that want "0 = up"
    pass a pre-rotated angle (e.g. ``math.radians(deg - 90.0)``); this
    helper does no rotation of its own, so it returns exactly the pair
    the inline ``cx + r*cos(theta), cy + r*sin(theta)`` produced.

    Parameters
    ----------
    cx : float
        Centre x-coordinate, in user-space pixels.
    cy : float
        Centre y-coordinate, in user-space pixels.
    r : float
        Radius (distance from the centre), in user-space pixels.
    theta_rad : float
        Angle **in radians** (already converted from degrees by the
        caller if needed).

    Returns
    -------
    tuple of float
        The ``(x, y)`` point. Unformatted floats — the caller keeps its
        own ``:.1f`` / ``:.2f`` formatting so output stays identical.

    Examples
    --------
    >>> x, y = point_on_circle(100.0, 100.0, 50.0, 0.0)
    >>> round(x, 6), round(y, 6)
    (150.0, 100.0)
    """
    return cx + r * math.cos(theta_rad), cy + r * math.sin(theta_rad)


def fmt_compact(v: float) -> str:
    """Format a float compactly for SVG path data: one decimal, no trailing zero.

    Rounds to a single decimal place, then strips a trailing ``0`` and a
    now-dangling ``.`` so ``12.0`` prints as ``12`` and ``12.30`` as
    ``12.3``. This is byte-identical to the private ``_fmt`` the
    streamgraph, difference-chart and bollinger generators each carried,
    and the callers pass it straight into :func:`catmull_rom_beziers`.

    Parameters
    ----------
    v : float
        A pixel coordinate (or any path-data number).

    Returns
    -------
    str
        The compact decimal string.

    Examples
    --------
    >>> fmt_compact(12.0)
    '12'
    >>> fmt_compact(12.34)
    '12.3'
    """
    # ``:.1f`` first (so 12.34 -> "12.3"), then drop a trailing zero and the
    # orphaned dot it leaves behind ("12.0" -> "12", "12" stays "12").
    return f"{v:.1f}".rstrip("0").rstrip(".")


def catmull_rom_beziers(
    pts: Sequence[Tuple[float, float]],
    fmt: Callable[[float], str],
    tension: float = 6.0,
) -> str:
    """Return SVG ``C`` commands for a smooth Catmull-Rom spline through ``pts``.

    The caller has already emitted the ``M`` (or ``M``/``L``) to
    ``pts[0]``; this appends the cubic-Bézier segments that flow through
    every later point. End tangents are clamped to the terminal points so
    the curve neither drifts nor over-shoots off the ends. Below three
    points it degrades to plain ``L`` line-tos, exactly as the inline
    ``_catmull_rom`` did.

    The float formatter is injected (rather than hard-coded) so the
    emitted string is byte-for-byte identical to each caller's private
    copy: the streamgraph, difference-chart and bollinger generators all
    pass :func:`fmt_compact`, so the ``C``/``L`` numbers match what they
    produced before the extraction.

    Parameters
    ----------
    pts : sequence of (float, float)
        The sample points, in pixel coordinates. ``pts[0]`` is assumed to
        have already been emitted by the caller (as an ``M``/``L``).
    fmt : callable
        The float-to-string formatter to apply to every coordinate — the
        caller's own ``_fmt`` (typically :func:`fmt_compact`). Injecting
        it keeps the output identical to the inline code.
    tension : float, optional
        Catmull-Rom denominator; ``6`` is the standard uniform spline.

    Returns
    -------
    str
        A run of SVG ``C`` path commands (a plain line-to run when fewer
        than three points are supplied).
    """
    n = len(pts)
    # Fewer than three points cannot form a spline — fall back to straight
    # line-tos through the tail (the caller already emitted pts[0]).
    if n < 3:
        return "".join(f" L{fmt(x)},{fmt(y)}" for x, y in pts[1:])
    seg = []
    for i in range(n - 1):
        # p0..p3 are the four points the uniform Catmull-Rom segment needs;
        # the ends are clamped (repeat the terminal point) so the curve does
        # not swing past the first/last sample.
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        # Catmull-Rom -> Bézier control points: the tangent at each anchor is
        # the neighbour-difference scaled by 1/tension.
        c1x, c1y = p1[0] + (p2[0] - p0[0]) / tension, p1[1] + (p2[1] - p0[1]) / tension
        c2x, c2y = p2[0] - (p3[0] - p1[0]) / tension, p2[1] - (p3[1] - p1[1]) / tension
        seg.append(
            f" C{fmt(c1x)},{fmt(c1y)} {fmt(c2x)},{fmt(c2y)} {fmt(p2[0])},{fmt(p2[1])}"
        )
    return "".join(seg)


def svg_open(
    width: object,
    height: object,
    title_id: str,
    desc_id: str,
    *,
    font_family: str = "Roboto, system-ui, sans-serif",
) -> str:
    """Return the responsive, accessible ``<svg>`` opening tag the figures share.

    Nearly every ``make_<id>.py`` generator opens its document with the *same*
    root element: an explicit ``width``/``height`` for a sensible intrinsic
    size, a ``viewBox="0 0 width height"`` so the graphic scales fluidly to any
    container (this is what makes the SVG **responsive** — a viewer can set
    ``width:100%`` and the coordinates rescale), the house ``font-family``, and
    ``role="img"`` + ``aria-labelledby`` wiring the ``<title>``/``<desc>`` pair
    that follows into one accessible name for screen readers. The ``<title>``
    also surfaces as the browser's native hover tooltip.

    This returns exactly the string those generators assembled inline, so
    adopting it leaves the rendered bytes unchanged. The ``<title>`` and
    ``<desc>`` elements themselves stay in the caller (their text is
    figure-specific); this helper only emits the root tag that references them
    by the two ids passed here.

    Parameters
    ----------
    width : object
        Canvas width in user-space pixels. Stringified as-is (an ``int`` prints
        without a decimal point), matching the inline ``f"{width}"``.
    height : object
        Canvas height in user-space pixels. Stringified as-is.
    title_id : str
        The ``id`` of the ``<title>`` element the caller emits next (e.g.
        ``"vn-title"``); becomes the first token of ``aria-labelledby``.
    desc_id : str
        The ``id`` of the ``<desc>`` element (e.g. ``"vn-desc"``); the second
        ``aria-labelledby`` token.
    font_family : str, optional
        CSS font stack for the whole document. Defaults to the house stack
        ``"Roboto, system-ui, sans-serif"``; pass a different string for the
        (few) generators that inject their own.

    Returns
    -------
    str
        The single ``<svg ...>`` opening tag, byte-identical to the inline form.

    Examples
    --------
    >>> svg_open(800, 600, "vn-title", "vn-desc")
    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600" font-family="Roboto, system-ui, sans-serif" role="img" aria-labelledby="vn-title vn-desc">'
    """
    # One f-string so the emitted bytes match the generators' multi-fragment
    # concatenation exactly; the viewBox mirrors width/height so the graphic
    # scales to its container without distortion.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{font_family}" role="img" '
        f'aria-labelledby="{title_id} {desc_id}">'
    )


def hex_to_rgb(hexv: str) -> Tuple[int, int, int]:
    """Convert a ``#RRGGBB`` string to an ``(r, g, b)`` integer triple.

    Strips an optional leading ``#`` then reads the three hex byte pairs.
    Byte-identical to the private ``_hex_to_rgb`` the hexbin-map,
    binned-grid-map and circle-packing generators each carried (one used
    the parameter name ``h``, but the returned triple is the same).

    Parameters
    ----------
    hexv : str
        A colour as ``#RRGGBB`` (the leading ``#`` is optional).

    Returns
    -------
    tuple of int
        The ``(r, g, b)`` channels, each ``0..255``.

    Examples
    --------
    >>> hex_to_rgb("#FF9500")
    (255, 149, 0)
    """
    h = hexv.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
