# The figure catalogue: what actually renders each of the 124 kinds

Every visual this package produces is SVG markup written directly by the
code that computes the geometry. There is no charting library underneath,
in any tier, on any code path — not for the catalogue, not for the
explainability plots, not for the causal diagrams. This file documents
what ships, kind by kind, and where the approach stops.

## What the 124-kind catalogue actually is

Every entry in `sprezzature_figures/catalog/figures.json` lists
`"renderer": "svg"`, with no other value appearing anywhere in the file.
Each `scripts/make_*.py` generator computes its own layout — bar bands,
wedge angles, KDE grids, force relaxations, painter's-algorithm depth
sorting — and emits the markup itself, leaning on a shared helper module,
`_svg.py`, for the pieces every chart needs: path generators for bars and
rounded rectangles, an adaptive number formatter for axis ticks and
tooltip text, XML escaping, and word-wrapping for tooltip text.

The interactivity this buys is real, but it is CSS, not a JavaScript
runtime: each hoverable mark and its tooltip bubble share a `.hit:hover ~
.tip { opacity: 1 }` pattern, a pure-CSS hover-reveal with no script tag
and no client-side library. The resulting SVG is a single self-contained
file, droppable into any HTML page or opened directly, with working hover
tooltips and no external dependency at view time.

The tradeoff, documented in `_svg.py`'s own module notes, is that this
per-element hover wrapping is deliberately *not* factored into a single
shared helper. Each generator writes its own `<g tabindex=…><title>…`
blocks, because the exact hover behaviour — which mark's tooltip shows,
what text it carries — is specific enough per chart type that a
one-size-fits-all helper kept producing subtly wrong behaviour.

## The explainability and causality plots: what actually draws them

The same rule holds outside the catalogue, and it is worth spelling out
because these libraries all ship plotting entry points of their own that
this package deliberately does not call.

`explain_model.py` computes raw SHAP values via `shap.Explainer(...)` and
hands them to its own SVG renderers. `_write_shap_bar_svg` and
`_write_shap_waterfall_svg` reuse the catalogue's `make_bar.py` /
`make_waterfall.py` generators directly, because their data shape is a
genuine fit. `_write_shap_beeswarm_svg` and `_write_shap_dependence_svg`
are bespoke, built from the same shared `_svg` / `_style` primitives every
catalogue generator uses, because SHAP's beeswarm (one swarm row per
feature, continuous colour by raw feature value) and its dependence
scatter (arbitrary x/y roles) do not fit either catalogue generator's
fixed data contract.

TimeSHAP's own plotting entry points (`timeshap.plot.*`) are likewise
never called; `local_report()`'s returned dataframes are re-plotted by
hand, best-effort, wherever their shape carries a `Shapley Value` column.
LIME writes its own standalone interactive HTML per row and is used as-is.
Shapash's `SmartExplainer.compile()` is called and fed this run's own SHAP
contributions, for its consistency checks, but its `generate_report()`
dashboard is not: `report.html` is a static page `explain_model.py`
assembles itself from the same SVG plots the plain `shap` engine produces.

The causal DAG (`dag.svg`) is a hand-written layered (Sugiyama-style)
layout: nodes ranked by longest path from a source, edges drawn as lines
with a hand-computed arrowhead triangle, no external graph-drawing engine
at all. The forest plot (`forest_plot.svg`) is hand-authored SVG too.

`tests/test_no_third_party_plotting.py` sweeps every module in the package
and fails on an import of — or even a mention of — a charting library, so
none of the above can quietly drift back.

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
| Shapash report (`explain_model.py --report shapash`) | Static HTML page embedding this module's own SVG plots | Yes, via each embedded SVG's native hover tooltips |
| LIME explanations (`explain_model.py --engine lime`) | Standalone HTML per row | Yes |
| Causal DAG (`causal_estimate.py`) | Hand-authored SVG, layered layout | Yes, CSS-only hover on nodes |
| Forest plot (`causal_estimate.py`) | Hand-authored SVG | Yes, CSS-only hover on rows |

## What none of these renderers can do

Anything genuinely three-dimensional, rendered as true 3-D geometry with a
camera and depth sorting, is out of reach: the catalogue's `3d`-named kinds
(`bar3d`, `scatter3d`, `surface3d`, `wireframe3d`) are 2-D projections drawn
to look three-dimensional, not an actual 3-D scene graph, and the same holds
for any future explainability or causality plot built the same way.

The causal DAG layout is deliberately modest — one barycenter pass for
crossing reduction, not an iterative or force-directed general
graph-drawing engine. It is sized for the small graphs a causal analysis
actually has (a handful of confounders around one treatment/outcome pair),
not for a large or densely connected one.

`render_diagram.py`'s SVG path is the escape hatch for effects the
catalogue generators do not reach for: a smoothing filter, arrowhead
markers, a gradient. It rasterises whatever SVG you hand it, whatever drew
it.
