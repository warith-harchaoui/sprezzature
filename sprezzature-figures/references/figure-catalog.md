# The figure catalogue: what actually renders each of the 124 kinds

`SKILL.md`'s frontmatter description and its "Curated defaults" section
both frame this skill as "Vega-Lite-first": prefer Vega-Lite over
matplotlib because a spec carries its own data and is natively
interactive. That framing describes an earlier version of this package.
Reading every `scripts/make_*.py` generator (all 124 of them import from
the shared `_svg` module; none import `vl_convert`, `altair`, or any
other Vega-Lite binding for actual rendering) shows the catalogue has
since migrated away from Vega-Lite entirely. This file documents the
system that ships today, states the migration plainly since it
contradicts a claim made elsewhere in this skill's own description, and
covers where Vega genuinely is still used in this package, which is a
different code path from the 124-kind catalogue.

## What the 124-kind catalogue actually is

Every entry in `sprezzature_figures/catalog/figures.json` lists
`"renderer": "svg"`, with no other value appearing anywhere in the file.
`make_bar.py`'s own docstring states the reason directly: "Previously
rendered via Vega-Lite (`vl_convert`); this module now builds the `<svg>`
markup by hand, not with Vega or matplotlib, so every bar carries a
native `<title>` tooltip and rounds only its free (top) end per the
Sprezzature Corner Policy." Every other generator in the catalogue
followed the same migration: they build SVG markup directly, using a
shared helper module, `_svg.py`, for the pieces every chart needs (path
generators for bars and rounded rectangles, an adaptive number formatter
for axis ticks and tooltip text, XML escaping, word-wrapping for
tooltip text).

The interactivity this buys is real, but it is CSS, not a JavaScript
runtime: each hoverable mark and its tooltip bubble share a `.hit:hover ~
.tip { opacity: 1 }` pattern, a pure-CSS hover-reveal with no script tag
and no client-side library, meaning the resulting SVG is a single
self-contained file, droppable into any HTML page or opened directly,
with working hover tooltips and no external dependency at view time. The
tradeoff, documented in `_svg.py`'s own module notes, is that this
per-element hover wrapping is deliberately *not* factored into a single
shared helper, each generator writes its own `<g tabindex=…><title>…`
blocks, because the exact hover behavior (which mark's tooltip shows,
what text it carries) is specific enough per chart type that a one-size
helper kept producing subtly wrong behavior.

## Where Vega-Lite is genuinely still used

Vega has not left the package, it has moved to a different job:
rendering a **user-supplied or diagram-source** Vega-Lite/Vega spec, not
producing the catalogue's own charts. `render_diagram.py`, the renderer
behind the Ralph Eyeball Loop for diagram surfaces (see
`references/ralph-eyeball-loop.md`), rasterizes a `.vl.json` or `.vg.json`
file you hand it via `vl-convert-python`, a self-contained wheel that
bundles its own Vega runtime, no browser, no Node, fully offline. That
path renders "the real spec that ships in the browser," in the script's
own words, useful when you have hand-authored or externally-generated
Vega you want to eyeball, and it can emit vector output at exact physical
dimensions for print (`--format svg` / `--format pdf`, with `width` /
`height` set in inches times DPI in the spec itself). This is the correct
place to reach for Vega-Lite in this package today; `make-figure` and
`sprezzature-figures render` are not it.

## The explainability and causality plots: what actually draws them

`SKILL.md`'s references list describes "extractable explainability plots
(SHAP, LIME, importance, PD/ICE, DAG) that replace matplotlib / seaborn /
pyplot." Reading `explain_model.py` and `causal_estimate.py` directly
shows the opposite dependency direction for two of the four: SHAP's own
plotting functions (`shap.plots.bar`, `shap.plots.beeswarm`,
`shap.plots.scatter`, `shap.plots.waterfall`) are matplotlib-backed
internally, `explain_model.py` calls `matplotlib.use("Agg")` and
`plt.savefig(...)` around every one of them, so SHAP output *uses*
matplotlib, it does not replace it. TimeSHAP's plots are matplotlib too.
LIME writes standalone interactive HTML per row
(`exp.save_to_file(...)`), no matplotlib involved, that one genuinely
sidesteps it. Shapash produces an HTML report that wraps SHAP internally.
The causal DAG (`dag.svg`) is drawn with `graphviz.Digraph`, a third
renderer distinct from both SVG-by-hand and matplotlib; the accompanying
forest plot (`forest_plot.svg`) is matplotlib again. None of this routes
through Vega-Lite either.

## A practical map of what renders with what, today

| Output | Renderer | Interactive at view time? |
|---|---|---|
| Any of the 124 `make-figure` catalogue kinds | Hand-built SVG (`_svg.py` helpers) | Yes, CSS-only hover tooltips, no script tag |
| A user-supplied Vega-Lite/Vega spec, via `render_diagram.py` | `vl-convert-python` | Only if you separately embed the Vega-Lite JS runtime in the page; the rasterized PNG/SVG/PDF output itself is static |
| A TikZ figure, via `render_diagram.py` | `tectonic` / `pdflatex` + `pdftoppm` | No, static raster/vector |
| A Mermaid diagram, via `render_diagram.py` | `mmdc` | No, static raster/vector |
| SHAP / TimeSHAP plots (`explain_model.py`) | matplotlib | No |
| Shapash report (`explain_model.py --report shapash`) | HTML wrapping SHAP | Yes, a real interactive report |
| LIME explanations (`explain_model.py --engine lime`) | Standalone HTML per row | Yes |
| Causal DAG (`causal_estimate.py`) | graphviz | No |
| Forest plot (`causal_estimate.py`) | matplotlib | No |

## What none of these renderers can do

The hand-built SVG catalogue and `graphviz` share matplotlib's usual
limits for anything genuinely three-dimensional rendered as true 3D
geometry with a camera and depth sorting, the catalogue's `3d`-named
kinds (`bar3d`, `scatter3d`, `surface3d`, `wireframe3d`) are 2-D
projections drawn to look three-dimensional, not an actual 3-D scene
graph. `render_diagram.py`'s own SVG path is documented as "the escape
hatch for figures Vega cannot express: a smoothing filter, arrowhead
markers, a gradient," which is really a statement about Vega-Lite's
declarative grammar specifically, not about this package's own SVG
catalogue, which already handles those cases directly since it is not
constrained by Vega-Lite's schema at all.

## If you came here expecting a Vega-Lite gallery

The "Vega-first" framing in `SKILL.md`'s frontmatter description and
House-style bullet 3 (which cites a `sprezzature-ui/references/charts-vega.md`
file that does not exist in the current `sprezzature-ui` skill, only
`charts-svg.md` does) predates the SVG migration documented above and has
not been updated to match. That is a discrepancy in this skill's own
top-level description, not something this reference file can fix on its
own, since it sits outside the eight `references/*.md` files, flagged
here so it does not get missed.
