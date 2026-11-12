# Figures — `sprezzature-figures`

Turn a table into a publication-quality figure: 168 chart types,
model-explainability plots (SHAP / Shapash / TimeSHAP / LIME), causal-effect
estimates (DoWhy / EconML) and flow or TikZ diagrams. Every chart is written
directly as Scalable Vector Graphics (SVG), with no charting library anywhere
in the package, and refined through the **Ralph Eyeball Loop** (render, look,
refine the source). `check` finds what is decidable from the markup alone
(labels on top of each other, text off the canvas, a dropped title), and
`redraw` redraws somebody else's chart from a picture of it without inventing
its numbers. Choropleths and areas-of-control situation maps live in
[`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps).

One install carries everything: `pip install sprezzature-figures`. It is
reachable as a library (`make_figure()`), a Click command line
(`sprezzature-figures`, also installed as `make-figure`), an HTTP API
(FastAPI, with Docker and Compose), an MCP server (`sprezzature-figures-mcp`,
eight tools) and the agent skill.

This is the human landing page. It points to the places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-figures/sprezzature_figures/skill/SKILL.md`](https://github.com/warith-harchaoui/sprezzature-figures/blob/main/sprezzature_figures/skill/SKILL.md))
  (the agent-facing spec: purpose, trigger phrases, the full tool surface).
- **See it rendered:** the [figures gallery](https://sprezzature.ai/figures.html)
  shows 161 of the 168 kinds on the house palette; the five glyph maps are on
  the maps page and the two Gapminder figures on the Hans ROSLING page. The
  written catalogue (one entry per kind, and when to use it) lives in the
  package's own
  [`FIGURES.md`](https://github.com/warith-harchaoui/sprezzature-figures/blob/main/FIGURES.md).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-figures`.
- **Go deeper:** [`sprezzature-figures/sprezzature_figures/skill/references/`](https://github.com/warith-harchaoui/sprezzature-figures/tree/main/sprezzature_figures/skill/references/)):
  the Ralph Eyeball Loop, the audit rules, explainability, causality, polarity
  and colour, and the trigger catalogue.
