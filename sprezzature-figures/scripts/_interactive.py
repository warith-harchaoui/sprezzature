"""
_interactive — the interactivity MODE layer shared by the make_* generators.

A figure can ship in one of three interactivity *modes*, and the choice is a
plain argument on the generator (default ``"self-contained"``):

* ``"self-contained"`` — the SVG carries its own fullscreen button and the
  script that wires it. Opened directly, served via ``<object>`` or inlined, the
  figure is fully usable on its own, with no page JavaScript. This is the
  default because the SVG is the deliverable.
* ``"external"`` — the SVG ships *without* an internal button; a page-level
  module (``figure-fullscreen.js``) supplies the button and a rich tooltip and
  drives fullscreen for a whole dashboard. The internal layer stands down so the
  two never duplicate.
* ``"static"`` — no interactivity at all, only the responsive ``viewBox`` that
  :func:`_svg.svg_open` already gives. For print or plain ``<img>`` embedding.

This module owns the *only* piece that is identical across figures: the
fullscreen control (a small top-right button plus a generic script). The
figure-specific hit regions and tooltips stay in each generator.

Why this is output-safe for the gallery: the button starts ``display:none`` and
the script reveals it *only* when the SVG is a live document (``<object>`` or
inlined) AND not managed by a page module. A ``<img>``-embedded SVG never runs
the script, and a PNG raster (``vl_convert``) honours ``display:none`` — so the
button is invisible in every thumbnail. It appears only where it works.

The module is **stdlib-only** (no imports) so it loads wherever the generators
do. Composes with :func:`_svg.svg_open` (the responsive, accessible root) and
mirrors the contract in ``sprezzature-ui/assets/components/figure-fullscreen.html``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

#: The three supported interactivity modes (see the module docstring).
MODES = ("self-contained", "external", "static")

#: Generic fullscreen script, identical for every figure. It runs only when the
#: SVG is a live document; it stands down inside a page-module-managed card
#: (``[data-fs-target]``) and hides itself when there is no Fullscreen API
#: (e.g. an ``<img>``-embedded SVG, where it never runs at all).
_FS_SCRIPT = (
    "(function(){"
    "var me=document.currentScript,svg=me.ownerSVGElement||me.parentNode;"
    # A page module owns this figure (dashboard): let it drive; do nothing here.
    "if(svg.closest&&svg.closest('[data-fs-target]'))return;"
    "var btn=svg.querySelector('[data-fs-internal]');"
    "var req=svg.requestFullscreen||svg.webkitRequestFullscreen;"
    "if(!btn||!req)return;"           # no Fullscreen API: leave the button hidden
    "btn.style.display='';"           # live + self-contained: reveal the button
    "function t(){var f=document.fullscreenElement||document.webkitFullscreenElement;"
    "if(f===svg)(document.exitFullscreen||document.webkitExitFullscreen).call(document);"
    "else req.call(svg);}"
    "btn.addEventListener('click',t);"
    "btn.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();t();}});"
    "})();"
)


def fullscreen_control(
    width: float,
    height: float,
    mode: str = "self-contained",
    *,
    inset: float = 14.0,
) -> str:
    """Return the fullscreen control markup for a figure, per interactivity mode.

    Append the result just before the closing ``</svg>`` of a generator's
    document. In ``"self-contained"`` mode it is a small top-right button plus
    the generic wiring script (hidden until the script confirms the SVG is a
    live, unmanaged document). In ``"external"`` and ``"static"`` modes it is the
    empty string, so no button ships.

    Parameters
    ----------
    width : float
        The SVG canvas width in user-space pixels (the ``viewBox`` width). The
        button is placed near the top-right corner from this.
    height : float
        The canvas height. Unused for placement today (the button hugs the top
        edge) but kept in the signature so callers pass the full canvas box and
        future placements stay source-compatible.
    mode : str, optional
        One of :data:`MODES`. Defaults to ``"self-contained"``.
    inset : float, optional
        Distance in pixels from the top and right edges to the button. Raise it
        on figures whose top-right corner already holds a legend or label.

    Returns
    -------
    str
        The SVG fragment (button ``<g>`` + ``<script>``), or ``""`` for the
        non-self-contained modes.

    Raises
    ------
    ValueError
        If ``mode`` is not one of :data:`MODES`.

    Examples
    --------
    >>> fullscreen_control(800, 600, "static")
    ''
    >>> fullscreen_control(800, 600, "external")
    ''
    >>> "data-fs-internal" in fullscreen_control(800, 600)
    True
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    # External mode defers to the page module; static ships no interactivity.
    if mode != "self-contained":
        return ""

    # Fixed 34 px hit target, hugged into the top-right corner. The icon path is
    # the four bracket corners of a "expand" glyph (matches the sprezzature-ui
    # component so the button reads the same everywhere).
    size = 34.0
    x = float(width) - inset - size
    y = float(inset)
    _ = height  # placement is top-edge only today; see the docstring note.
    return (
        f'<g data-fs-internal="" role="button" tabindex="0" aria-label="Toggle fullscreen" '
        f'transform="translate({x:.0f},{y:.0f})" style="display:none;cursor:pointer">'
        f'<rect x="0" y="0" width="34" height="34" rx="8" fill="#F2F3F5"/>'
        f'<path d="M6 13 V6 h7 M28 13 V6 h-7 M6 21 v7 h7 M28 21 v7 h-7" '
        f'fill="none" stroke="#1D1D1F" stroke-width="2" stroke-linecap="round"/>'
        f'</g>'
        f'<script><![CDATA[{_FS_SCRIPT}]]></script>'
    )
