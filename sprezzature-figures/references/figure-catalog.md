# The figure catalogue: what actually renders each of the 124 kinds

`SKILL.md` used to frame this skill as "Vega-Lite-first": prefer Vega-Lite
over matplotlib because a spec carries its own data and is natively
interactive. That framing described an earlier version of this package.
Reading every `scripts/make_*.py` generator (all 124 of them import from
the shared `_svg` module; none import `vl_convert`, `altair`, or any
other Vega-Lite binding for actual rendering) shows the catalogue has
since migrated away from Vega-Lite entirely; `SKILL.md` has since been
corrected to match. This file documents the system that ships today in
full detail and covers where Vega genuinely is still used in this
package, which is a different code path from the 124-kind catalogue.

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

## Vega-Lite has been fully removed

An earlier version of this file documented a second Vega-Lite code path:
`render_diagram.py` rasterizing a user-supplied `.vl.json`/`.vg.json`
spec via `vl-convert-python`. That path is gone. Reading
`render_diagram.py` today shows `KINDS = ("tikz", "mermaid", "svg")`,
three entries, no `"vega"`; the `render_vega()` function, the
`vl-convert-python` dependency, and the JSON-spec auto-detection branch
were all deleted. A caller with an existing Vega-Lite spec must convert
or re-author it as TikZ, Mermaid, or raw SVG before this renderer will
touch it. There is no longer anywhere in this package that imports
`vl_convert`; `tests/test_no_third_party_plotting.py` grep-guards
`render_diagram.py` (and every other migrated script) against that
import returning.

## The explainability and causality plots: what actually draws them

`SKILL.md`'s references list used to describe "extractable
explainability plots (SHAP, LIME, importance, PD/ICE, DAG) that replace
matplotlib / seaborn / pyplot," a claim that used to be backwards: SHAP's
own plotting functions were matplotlib-backed internally and
`explain_model.py` called them directly. Reading `explain_model.py` and
`causal_estimate.py` today shows that dependency has been cut instead of
corrected in prose. `shap.plots.bar` / `.beeswarm` / `.scatter` /
`.waterfall` are never called; `explain_model.py` computes raw SHAP
values via `shap.Explainer(...)` and hands them to its own hand-authored
SVG renderers, `_write_shap_bar_svg` and `_write_shap_waterfall_svg`
reuse the catalogue's `make_bar.py` / `make_waterfall.py` generators
directly (their data shape is a genuine fit), `_write_shap_beeswarm_svg`
and `_write_shap_dependence_svg` are bespoke, built from the same shared
`_svg` / `_style` primitives every catalogue generator uses, because
SHAP's beeswarm (one swarm row per feature, continuous colour by raw
feature value) and its dependence scatter (arbitrary x/y roles) do not
fit either catalogue generator's fixed data contract. TimeSHAP's
matplotlib-backed plotting functions (`timeshap.plot.*`) are never
called either; `local_report()`'s own returned dataframes are re-plotted
by hand, best-effort, wherever their shape carries a `Shapley Value`
column. LIME already sidestepped matplotlib before this pass (it writes
its own standalone interactive HTML per row) and is unchanged. Shapash's
`SmartExplainer.compile()` is still called, fed this run's own SHAP
contributions, but its own plotly-backed `generate_report()` is never
called; `report.html` is a static page `explain_model.py` assembles
itself from the same SVG plots the plain `shap` engine produces. The
causal DAG (`dag.svg`) no longer goes through `graphviz.Digraph`: it is a
hand-written layered (Sugiyama-style) layout, nodes ranked by longest
path from a source, edges drawn as lines with a hand-computed arrowhead
triangle, no external graph-drawing library at all. The forest plot
(`forest_plot.svg`) is hand-authored SVG too, not matplotlib. None of
this ever routed through Vega-Lite, and now none of it routes through
matplotlib, plotly, or graphviz either.

## A practical map of what renders with what, today

| Output | Renderer | Interactive at view time? |
|---|---|---|
| Any of the 124 `make-figure` catalogue kinds | Hand-built SVG (`_svg.py` helpers) | Yes, CSS-only hover tooltips, no script tag |
| A TikZ figure, via `render_diagram.py` | `tectonic` / `pdflatex` + `pdftoppm` | No, static raster/vector |
| A Mermaid diagram, via `render_diagram.py` | `mmdc` | No, static raster/vector |
| A raw hand-authored SVG, via `render_diagram.py` | `rsvg-convert` / ImageMagick | No, static raster (the source SVG itself may be interactive; the rasterized companion is not) |
| SHAP summary bar / waterfall (`explain_model.py`) | Hand-authored SVG, reusing `make_bar.py` / `make_waterfall.py` | Yes, CSS-only hover tooltips |
| SHAP beeswarm / dependence scatter (`explain_model.py`) | Hand-authored SVG, bespoke | Yes, CSS-only hover tooltips |
| TimeSHAP attribution plots (`explain_model.py`) | Hand-authored SVG, best-effort, reusing `make_bar.py` | Yes, where rendered |
| Shapash report (`explain_model.py --report shapash`) | Static HTML page embedding this module's own SVG plots | Yes, via each embedded SVG's native hover tooltips; no plotly |
| LIME explanations (`explain_model.py --engine lime`) | Standalone HTML per row | Yes |
| Causal DAG (`causal_estimate.py`) | Hand-authored SVG, layered layout | Yes, CSS-only hover on nodes |
| Forest plot (`causal_estimate.py`) | Hand-authored SVG | Yes, CSS-only hover on rows |

## What none of these renderers can do

Every renderer in this package now shares hand-authored SVG's usual
limits for anything genuinely three-dimensional rendered as true 3D
geometry with a camera and depth sorting: the catalogue's `3d`-named
kinds (`bar3d`, `scatter3d`, `surface3d`, `wireframe3d`) are 2-D
projections drawn to look three-dimensional, not an actual 3-D scene
graph, and the same is true of any future explainability or causality
plot built the same way. `render_diagram.py`'s own SVG path is
documented as "the escape hatch for figures Vega cannot express: a
smoothing filter, arrowhead markers, a gradient," a leftover phrase from
when Vega was still the catalogue's renderer; today it means the same
thing for any diagram surface, not specifically Vega, since the
catalogue itself already handles those cases directly by hand. The
causal DAG layout is deliberately modest, one barycenter pass for
crossing reduction, not an iterative or force-directed general
graph-drawing engine, sized for the small graphs a causal analysis
actually has (a handful of confounders around one treatment/outcome
pair), not for a large or densely connected graph.

## If you came here expecting a Vega-Lite gallery

`SKILL.md`'s frontmatter description, decision-tree row, tier table, and
References bullet used to carry a "Vega-first" framing that predated the
SVG migration documented above. All four have since been corrected to
state plainly that the catalogue is hand-authored SVG, not Vega-backed,
and to point Vega-Lite questions at `render_diagram.py` instead.
