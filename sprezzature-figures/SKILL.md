---
name: sprezzature-figures
description: >-
  Figures, diagrams and the Ralph Eyeball Loop: 168 hand-authored, often
  interactive and animated SVG chart types whose markup is written directly,
  flow diagrams (flowchart) included, plus explainability (SHAP / Shapash /
  LIME) and causal DAGs (DoWhy). check finds overlapping labels in any SVG,
  with no model. The loop reads any visual from code (figure, TikZ, a whole
  HTML page) as an agent or --local (qwen3-vl:8b, offline). redraw() redraws a
  picture of a chart here, never inventing the numbers. Never ASCII art. Use
  it when you are holding numbers you want somebody to SEE, or a chart that is
  hard to read. Trigger phrases: "make a figure", "chart this", "plot this",
  "heatmap", "treemap", "sankey", "mermaid diagram", "no ascii art", "ralph
  eyeball loop", "SHAP plot", "DAG", "waterfall chart", "redraw this chart",
  "audit this figure". Output: SVG, PNG, PDF, JPG or HTML. Not this one when:
  the numbers are attached to real PLACES (sprezzature-maps). The exhaustive
  trigger catalogue is in `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10 to 3.13; one
  ``pip install sprezzature-figures`` carries the generators, the
  explainability and causal stacks, the editor, the HTTP API and the MCP
  server. The static auditor needs only the standard library. The render_diagram.py
  renderer needs, per kind: tectonic/pdflatex + pdftoppm/magick (TikZ),
  rsvg-convert/magick (SVG), all optional, fail loud. No
  network needed once installed.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.3
---

> The deterministic tools below now ship as the standalone package [`sprezzature-figures`](https://github.com/warith-harchaoui/sprezzature-figures) (one `pip install sprezzature-figures`, no feature extras), invoked as `sprezzature-figures …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

## Five surfaces

| Surface | Entry point |
|---|---|
| Library | `from sprezzature_figures import make_figure, check_render, redraw, list_kinds, get_figure_definition` |
| CLI (Click) | `sprezzature-figures` (also installed as `make-figure`, the same group): `list`, `render`, `describe`, `recommend`, `redraw`, `check` |
| HTTP API (FastAPI), Docker, Compose | `uvicorn sprezzature_figures.api:app`; `docker compose up` runs `sprezzature-figures-mcp`, which serves the API and `/mcp` on the same port (8000) |
| MCP | `sprezzature-figures-mcp` (endpoint `/mcp`), eight tools named by `operation_id`: `health`, `list_kinds`, `get_kind`, `list_kind_options`, `recommend_figures`, `render_figure`, `redraw_figure`, `check_render` |
| Skill | this file |

Two numbers, both deliberate: the catalogue holds 168 kinds (`sprezzature-figures list`); the web gallery on sprezzature.ai shows 161 of them, because the five glyph maps sit on the maps page and the two Gapminder figures on the Hans ROSLING page.

# sprezzature-figures: data-viz, explainability, and causality figures

## Audience and positioning

Solo developers, data scientists, and small teams who:

- Ship **figures** (charts in a docs site, feature-importance plots in
  a model report, DAGs in a causal analysis) and want them to look
  consistent with the rest of the `sprezzature-*` stack (Roboto, curated
  palette, dark-mode peer, `role="img"`, alt text stub).
- Want **model explainability** without picking a library the hard way.
  SHAP for tree models, **Shapash** for a full HTML report a business
  stakeholder can read, **TimeSHAP** when the model is a recurrent /
  transformer time-series predictor, LIME when the model is a black-box
  classifier.
- Want **causal-effect estimation** using an opinionated pipeline
  (DoWhy → EconML → refuters), not a hand-rolled Rubin causal model,
  and want the resulting DAG rendered in the same house style.
- Want a **pre-commit gate** that fails fast on the small set of
  data-viz mistakes that survive review and are decidable from the
  markup: 3D pies, rainbow palettes, drop-shadow chartjunk, ticks left
  as raw magnitudes or raw ISO dates, a `<figure>` with neither
  `role="img"` nor a caption (`audit_figure.py`); and labels colliding,
  text off the canvas, a dropped title (`sprezzature-figures check`).
  Neither reads polarity, axis truncation or colour-vision safety; those
  stay with the eyeball loop and `sprezzature-colors`.

This skill is **not** a substitute for a real analyst's judgement.
The auditor catches mechanical mistakes; it does not know whether the
chart answers the right question. `explain_model.py` drafts SHAP
plots; you still have to read them. `causal_estimate.py` runs DoWhy's
identify → estimate → refute loop and prints an effect number, but
the effect is only as good as the DAG you supplied.

## Two modes: make and audit

The `sprezzature-*` repo is a toolkit for **making** artifacts and
**auditing** them. This skill ships both halves of that loop for
data-science figures:

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — plot a dataset in the house style | `sprezzature-figures render` (same as `make-figure render`) | Renders one of the catalogue's chart kinds (`sprezzature-figures list` prints all of them, e.g. `treemap`, `funnel`, `waterfall`) from your own data (`--data file.csv`, columns bound with `--map role=column`) or its built-in demo data, in the same palette and typography as `sprezzature-ui`. `sprezzature-figures recommend --data file.csv` ranks which chart kinds your data can fill before you pick one. |
| **Make** — explain a fitted model | `explain_model.py` | Dispatches to SHAP / Shapash / TimeSHAP / LIME by model type (tree / linear / sequence / black-box). Writes summary + dependence + waterfall plots; drops a Shapash HTML report when `--report shapash`. |
| **Make** — estimate a causal effect + draw the DAG | `causal_estimate.py` | End-to-end DoWhy loop: model → identify → estimate (EconML backend when treatment is continuous) → refute. Renders the DAG as a hand-authored, layered SVG (no external layout engine) + writes the effect table to JSON. |
| **Make** — an areas-of-control situation map, or a choropleth on a real basemap | `sprezzature-maps` (standalone package, see note below) | `make_situation_map.py` and `build_situation_examples.py` no longer ship inside `sprezzature-figures`; they were split out into the standalone [`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps) package alongside `make_choropleth.py`, which draws on a real basemap (Natural Earth): the world choropleth in Equal Earth, the situation plate in an auto-centred Lambert conformal conic. `pip install sprezzature-maps`, then `make-map situation-map --config my-region.yaml --out region.svg` or `make-map choropleth --out world.svg`. `sprezzature-figures` keeps only the schematic, binned map kinds (`binned-grid-map`, `dotdensity`, `hexbin-map`, `hexmap`, `spike-map`), which plot points or grid cells, not real coastlines. |
| **Make** — somebody else's chart, from a picture of it | `sprezzature-figures redraw` | Takes a screenshot (PNG/JPEG/GIF/WebP/SVG) of an existing chart, has a vision model read what kind it is and what costs the reader effort, and draws it here. **Never invents numbers**: `data_origin` reports `your-data` (rows you passed), `read-from-image` (printed on the original and read back, approximate) or `demo` (nothing readable — the redesign on sample rows, captioned as such on the figure itself). Pass `--data` to get a figure worth publishing. |
| **Loop** — [Ralph Eyeball Loop](references/ralph-eyeball-loop.md) on any visual source | `ralph_eyeball_loop.py` | Universal visual-quality technique: renders **any** visual-from-code artifact (HTML web page, TikZ figure, hand-authored SVG) to a PNG, then writes / extends `.private/ralph-loop/assessment-<hash>.md` for honest critique. For HTML: headless Chrome. For diagrams: delegates to `render_diagram.py`. Applies to the whole `sprezzature-*` repo; data viz is one application, not the scope. |
| **Render** — diagram source → image (diagram surfaces only) | `render_diagram.py` | Rasterises a TikZ figure or a raw SVG to PNG. TikZ is palette-themed from `sprezzature-colors`; background white / transparent / dark selectable. Called internally by `ralph_eyeball_loop.py`; use directly when you want the PNG without the assessment file. |
| **Audit** — is the figure you just rendered legible, with no model at all | `sprezzature-figures check` | Reads the rendered SVG and reports what is decidable from the markup: labels colliding, text running off the canvas, a generator's demo chrome ("Region", "Quarterly figures") left over real data, a light card in the middle of a dark-mode figure, a title the generator dropped, a missing accessible title or description. Exit 1 on any finding. **Reach for this after every render whose result goes to someone other than you** — it is the eyeball loop's questions answered without a vision model, which is the only version available when you have none. It judges facts, never taste: an empty report does not mean the chart type suits the question. |
| **Audit** — gate before ship | `audit_figure.py` | Static parser flags data-viz anti-patterns in an SVG chart or a rendered `<figure>` block in HTML. Findings as `error` or `warning`; exit non-zero when an `error` is present, and on warnings too with `--strict`. |
| **Install** — one-shot setup of the tiered stack | `install_figures.py` | Installs the pinned dataviz / explainability / causality tiers of `requirements-*.txt` as requested; the base install already carries those libraries, so this is for pinning, not for enabling. Idempotent. Detects the active env manager (uv / poetry / pixi / conda / pip) and defers to it. |

## Honest framing of what each tool covers

| Tool | Catches | Misses |
|---|---|---|
| `sprezzature-figures render` | Chart kinds from a fixed, growing catalogue (`sprezzature-figures list [--status stable]`), each in the `sprezzature-ui` house style (rounded corners, no top/right spine, no rainbows, palette from `sprezzature-colors/references/palette.csv`); binds your own CSV / TSV / JSON / JSONL columns to the kind's roles via `--map role=column`, or falls back to built-in demo data. | Does not invent the right chart; the catalogue is closed-set (`sprezzature-figures list` shows what exists today), not an open x/y/kind combinator. For chart-type selection see `sprezzature-ui/references/dataviz-chart-selection.md`. Does not do map projections beyond what a given catalogue kind supports; for choropleths see `sprezzature-ui/references/dataviz-maps.md`. |
| `sprezzature-figures redraw` | The **design** of a chart in a picture: which of the catalogue's kinds shows the same thing, the text printed on it, and what makes it harder to read than it needs to be. Chooses only from the catalogue — a kind outside the candidate list is a hard error, not a result. | The **data**. A chart drawn without data labels does not contain its numbers, and this refuses to estimate them from mark size: without `--data` you get the redesign on sample rows, and the figure says so. Read `data_origin` before sharing the output. A local 7B vision model takes ~90 s and reads fewer issues than a larger one. |
| `explain_model.py` | Model-agnostic SHAP for tree / linear / kernel models (via `shap.Explainer`), Shapash HTML report for a full business-facing writeup, TimeSHAP for recurrent / attention-based time-series models, LIME as fallback for opaque classifiers. Writes summary plot + top-N dependence plots + one waterfall for the row with the largest absolute prediction. | Does not train models. Does not evaluate them; use `probabl-ai/skills/evaluate-ml-pipeline` or `scikit-learn`'s report utilities. Does not do counterfactual reasoning; see `alibi` or `DiCE`. |
| `causal_estimate.py` | DoWhy's four-step loop end-to-end (model → identify → estimate → refute); EconML `DML`, `DR-learner`, and `CausalForest` estimators when treatment is continuous; a hand-authored, layered SVG DAG (no external layout engine); a JSON effect table for CI. | Does not discover the DAG; you supply it as a gml / networkx / DoWhy string. For discovery, use `causal-learn` or `causallearn`. Does not do interrupted-time-series or synthetic controls; for those see `CausalImpact` or `SparseSC` (out of scope). |
| `sprezzature-figures check` | The factual half of "does this read?": overlapping labels, sibling labels whose baselines nearly but not quite line up (`baseline_near_miss`), text outside the canvas, leftover demo chrome, a light surface on a dark figure, an `expected_title` the generator ignored, a missing `<title>` / `<desc>`. Deterministic, no model, works offline. Measures text with the same calibrated table the generators lay out with, so a string a generator fitted is never reported as overflowing. | Anything that needs eyes or judgement: whether the chart type answers the question, whether the colours carry meaning, whether the story is the right one. Use the Ralph Eyeball Loop for those. It also cannot see a glyph the embedded font lacks, only the width it would take. |
| `audit_figure.py` | SVG charts and HTML `<figure>` blocks. Rules: perspective-transformed (3D) pie / donut; rainbow palette (viridis is fine; jet / hsv / rainbow are not); chartjunk (drop shadow, blur filter); corner radius over the 16 px cap; axis ticks left as raw magnitudes (`200000` rather than `200k`); ticks left as raw ISO dates; missing `role="img"` / alt-text stub on the surrounding `<figure>`. | Reads what the markup literally says, and nothing more: a chart can pass every rule and still encode the wrong thing. Does not verify whether the *right chart* was chosen (a design decision, not a mechanical one), and does not evaluate statistical soundness (baseline choice, confidence-interval computation). Loop a data-viz reviewer in for the final call. |
| `make_situation_map.py` (now in `sprezzature-maps`) | A professional-desk layered plate from one YAML config for any region (real national outline from the vendored Natural Earth basemap, per-layer PNG/SVG exports). | Moved to the standalone [`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps) package, run as `make-map situation-map --config … --out …` (`situation_map` is the same command). Does not ship inside `sprezzature-figures` any more; point users at `sprezzature-maps` for this capability. |

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "chart this" / "plot the data" / "make a figure" / "dashboard tile" | `sprezzature-figures render` | `sprezzature-figures list` to see the catalogue, `sprezzature-figures describe <kind>` for its roles and options, then `sprezzature-figures render <kind> --data <data.csv> [--map role=column ...] [--out fig.svg] [--title T]`. Without `--out` it writes `<kind>.svg` in the current directory; the extension of `--out` picks SVG, PNG, PDF, JPG or HTML. `<kind>` is a catalogue name (e.g. `bar`, `treemap`, `funnel`), not a free `--x/--y/--kind` combination. |
| "which chart fits my data" / "recommend a chart" | `sprezzature-figures recommend` | `sprezzature-figures recommend --data <data.csv> [--intent comparison\|trend\|distribution\|...] [--render out.svg]`: ranks catalogue kinds your data can fill, best first; `--render` also draws the top pick. |
| "redraw this chart" / "make this ugly chart better" / "a colleague sent me this graph" / "rends ce graphique plus lisible" | `sprezzature-figures redraw` | `sprezzature-figures redraw <image.png> [--data rows.csv] [--kind <kind>] [--out fig.svg] [--language en|fr]` (without `--out`: `<kind>-redrawn.svg`). Report back what `data_origin` says: if it is `demo`, tell the user the numbers are sample data and ask for theirs — do not let a mock-up be mistaken for their figure. |
| "explain this model" / "SHAP plot" / "feature importance" | `explain_model.py` | `python -m sprezzature_figures_scripts.explain_model --model model.pkl --data X.csv [--engine auto\|shap\|shapash\|timeshap\|lime] [--out ./explain/]` |
| "shapash report" / "give a stakeholder-facing explanation" | `explain_model.py` | `python -m sprezzature_figures_scripts.explain_model --model model.pkl --data X.csv --engine shapash --report shapash --out ./explain/`: writes a full HTML report. |
| "timeshap" / "explain my LSTM / transformer sequence model" | `explain_model.py` | `python -m sprezzature_figures_scripts.explain_model --model seq_model.pkl --data X.npy --engine timeshap --sequence-cols "t_0,t_1,...,t_N" --out ./explain/` |
| "causal effect" / "average treatment effect" / "DAG" / "DoWhy" | `causal_estimate.py` | `python -m sprezzature_figures_scripts.causal_estimate --data d.csv --treatment T --outcome Y --confounders "X1,X2,X3" --dag dag.gml [--estimator dml\|dr\|causal-forest\|linear] [--refute all\|placebo\|subset\|random-cause]` |
| "situation map" / "areas of control" / "who controls what" / "conflict map" / "control map" | `sprezzature-maps` | Not in this package: the situation map moved to [`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps) (`make-map situation-map --config region.yaml --out region.svg`). Route there. |
| "is this figure readable" / "check my chart" / "did the title make it" / "I have no vision model" | `sprezzature-figures check` | `sprezzature-figures check fig.svg [--dark] [--expect-title "..."] [--forbid "placeholder"] [--kind <kind>] [--format json]`; from Python it is `check_render`, over HTTP `POST /check_render`, over MCP the `check_render` tool. Exit 1 on any finding, so it gates a commit. Pass `--expect-title` whenever you asked for a title: a generator that silently drops the parameter is the failure nothing else catches. |
| "ralph eyeball loop" / "eyeball this" / "screenshot the page" / "render web page" / "look at the PNG" | `ralph_eyeball_loop.py` | `python -m sprezzature_figures_scripts.ralph_eyeball_loop <source> [--width 1440] [--height 900] [--bg white\|transparent\|dark]`: kind auto-detected from suffix (.html → Chrome headless; others → render_diagram.py). Assessment file at `.private/ralph-loop/assessment-<hash>.md`. |
| "mermaid diagram" / "flow diagram" / "boxes and arrows" | `flowchart` kind | `sprezzature-figures render flowchart --data arrows.csv --out flow.svg`: one row per arrow (`source`, `target`, optional `label`, `source_group`, `target_group`, `back`, `dashed`). No other diagram language is read. |
| "render this diagram" / "tikz to png" / "iterate on a figure" | `render_diagram.py` | `python -m sprezzature_figures_scripts.render_diagram <source> --out fig.png [--background white\|transparent\|dark]`: kind (tikz / svg) auto-detected. Use directly for a one-shot render; use `ralph_eyeball_loop.py` for the full loop with assessment. |
| user asks for a named charting library ("do this in <library>") | `sprezzature-figures render` + `sprezzature-figures list` | There is no such backend here and no plan for one: all 168 kinds are SVG authored directly, and so are the explainability and causal plots. Say that plainly and draw the figure, rather than promising output from a library this package does not use. |
| "audit this figure" / "is this chart misleading" | `audit_figure.py` | `python -m sprezzature_figures_scripts.audit_figure <path> [--json] [--strict] [--ignore r1,r2] [--only r1,r2]`: accepts an SVG chart, an HTML file with `<figure>` blocks, or a directory of them. |
| "colorblind-safe palette on the figure" | `sprezzature-colors` | `audit_figure.py` does not judge colour-vision safety (it only refuses the rainbow ramps); run `sprezzature-colors-cvd` on the rendered PNG for a preview and `sprezzature-colors-contrast` on the colours. |
| "first-time setup" / "install the data-viz stack" | `install_figures.py` | `python -m sprezzature_figures_scripts.install_figures --tier dataviz+explain+causal`: installs pinned versions of each tier. |

## The four figure tiers (pinning only)

| Tier | Libraries | When to install | Key scripts |
|---|---|---|---|
| **dataviz** | `pandas`, `networkx`, `scikit-learn`, `pyyaml` | Tables, graphs and models — nothing in it draws. | `sprezzature-figures`, `audit_figure.py` |
| **explain** | `shap`, `shapash`, `timeshap`, `lime`, `scikit-learn` | You have a fitted model and want to explain it. | `explain_model.py` |
| **causal** | `dowhy`, `econml`, `networkx`, `pydot`, `scikit-learn`, `scipy` | You are estimating a causal effect from observational data; `pydot` reads a `--dag x.dot`. | `causal_estimate.py` |
| **install-only** | `pip` / `uv` / `poetry` / `conda` (whichever the project uses) | First-time setup on a fresh machine. | `install_figures.py` |

All of these libraries are base dependencies since 2026-11-01, so `pip install sprezzature-figures` already carries every tier; `install_figures.py` only pins the versions listed in `requirements-*.txt`. The tiers are **additive**. `install_figures.py --tier dataviz` installs
only the base data stack (and is the default); `--tier dataviz+explain` adds SHAP /
Shapash / TimeSHAP / LIME; `--tier dataviz+explain+causal` (or `--tier all`) adds DoWhy /
EconML / pydot. `--manager` forces a package manager and `--dry-run` prints the command. No tier contains a charting library: the catalogue, the
explainability plots, and the causal DAG/forest plot are all SVG authored
directly. The auditor itself is stdlib only, so you can run
`audit_figure.py` on any SVG or HTML page without installing a tier at
all.

## House style — figures that match `sprezzature-ui`

Every figure `sprezzature-figures render` emits inherits the sprezzature-* design tokens:

1. **Colors** from `sprezzature-colors/references/palette.csv`: no rainbows,
   no library defaults. Sequential → `viridis`; diverging → `RdBu_r`;
   qualitative → the curated Apple-inspired palette.
2. **Roboto** everywhere (Serif for publication presets; Mono for
   tabular value labels and tick numbers); **tabular numerals**.
3. **No top/right spine, no tick marks, no gridlines** (heatmaps
   excepted), **no 3D / shadows / gradients** (bar one area fill),
   matching `sprezzature-ui/references/charts-svg.md`.
4. **Dark-mode aware**: an additive `@media (prefers-color-scheme: dark)`
   block, embedded directly in the SVG, inverts paper/ink and flips blend
   modes (`_style.py`'s `os_dark_style()`) for the 168-kind catalogue.
   `explain_model.py`'s and `causal_estimate.py`'s hand-authored plots take
   an explicit `--dark` flag instead and bake the dark canvas directly.
5. **Polarity stated** on every quantitative axis with a well-defined
   good direction: `(higher is better)` / `(lower is better)` /
   `(target = N)`, reinforced (never carried) by a semantic palette
   colour. Full mapping: `references/polarity-and-color.md`.
6. **`role="img"` + `<figcaption>`** on every `<figure>`; `audit_figure.py`
   flags a figure that lacks them.
7. **Wrapping never moves a first line.** Sibling text blocks (a row of
   cards, the boxes of one flow layer, the leaves of one treemap strip,
   legend entries, category labels) are laid out from ONE block height, the
   max over the siblings, and ONE font size, the min over the siblings after
   any shrink. Every first line sits on one baseline; a wrapped line only
   adds lines below. Under bars, align the first baselines too. Never centre
   each block on its own line count. `sprezzature-figures check` reports a
   miss as `baseline_near_miss` (warning: same size and weight, side by side,
   baselines 1.5 px to 0.9 em apart); confirm by eye with the
   [Ralph Eyeball Loop](references/ralph-eyeball-loop.md).
8. **Colour = meaning.** Before giving a series, card or label a colour,
   read what it says and pick the hue whose psychological dimension matches
   ([deraison.ai/colors/academic](https://deraison.ai/colors/academic)):

   | Hue | Name | Positive | Negative |
   |---|---|---|---|
   | `#D55E00` | `Red` | power, energy | danger, warning, anger |
   | `#E69F00` | `Orange` | courage, warmth, innovation | frustration |
   | `#F0E442` | `Yellow` | optimism, creativity | caution, anxiety |
   | `#009E73` | `Green` | health, hope, growth, nature | stagnation, sickness |
   | `#56B4E9` | `Teal` | communication, clarity, calm | secrecy, unreliability |
   | `#0072B2` | `Blue` | trust, dependability, logic, security | coldness |
   | `#CC79A7` | `Purple` | wisdom, imagination, sophistication | fear |
   | `#A52A2A` | `Brown` | seriousness, earthiness | heaviness |
   | black | `Black` | authority | menace |
   | grey | `Gray` | neutrality, balance | lack of energy |

   `semantic_colors(labels, theme=...)` does it for you, in English and
   French (risque / erreur → `Red`, confiance / fiable / sûr → `Blue`,
   santé / croissance / gain → `Green`, ...), and falls back to the usual
   cycle for labels that name no meaning. Pass its result to the figure's
   own colour option; it never changes a default. Full rule:
   `references/polarity-and-color.md`.

## Explainability, causality, and auditor rules: see references

The detailed catalogues live in `references/` (progressive disclosure;
load the one you need). Seven of the eight files below are written from
the actual source (`explain_model.py`, `causal_estimate.py`,
`audit_figure.py`, `ralph_eyeball_loop.py`, `_style.py`, and the 168-entry
`figures.json` catalog), not from this summary; where the code disagreed
with what this SKILL.md used to claim, the reference file says so
plainly rather than restating the stale claim (see in particular
`references/figure-catalog.md`, which corrects an earlier framing of this
skill). The eighth, `references/publication-presets.md`,
documents that the journal presets promised below are not implemented in
the standalone package as of this writing, rather than inventing plausible
values.

- **Explainability.** `explain_model.py` dispatches to SHAP (default,
  tree/linear/kernel) / Shapash (stakeholder HTML report) / TimeSHAP
  (recurrent / attention time-series) / LIME (black-box fallback);
  `--engine auto` inspects the model, `--engine` overrides, `--report
  shapash` always adds the HTML report. Full engine-selection matrix and
  per-engine output contract: `references/explainability.md`.
- **Causality.** `causal_estimate.py` runs DoWhy's model → identify →
  estimate → refute loop (EconML backends for continuous treatment;
  placebo / random-common-cause / data-subset refuters unless `--refute
  none`), writing `effect.json` + a house-styled `dag.svg`. Backends,
  DAG encodings, and the refutation battery: `references/causality.md`.
- **Auditor rules.** `audit_figure.py` flags `pie-3d`, `rainbow-palette`,
  `chartjunk`, `radius-over-cap`, `unformatted-tick`, `iso-date-tick`,
  `role-img-missing`, and `alt-missing`, each with a severity and an
  `--ignore` escape. Full rule catalogue with
  false-positive notes: `references/audit-figure.md`.
- **Ralph Eyeball Loop.** The repo-wide visual-quality weapon: render any
  visual-from-code artifact (web page, TikZ figure, hand-authored SVG) to PNG, critique it honestly, edit the source, loop.
  `ralph_eyeball_loop.py` is the primary tool (all surfaces);
  `render_diagram.py` is the diagram-only renderer it delegates to (TikZ /
  SVG only).
  Protocol, assessment file format, per-surface critique dimensions, and why
  data viz is one application of the loop (not its scope):
  `references/ralph-eyeball-loop.md`.
- **Figure catalogue.** All 168 `make-figure` kinds render as hand-authored,
  CSS-interactive SVG (`_svg.py` helpers). SHAP / Shapash's underlying
  contributions, TimeSHAP, and the causal DAG / forest plot all render as
  hand-authored SVG too; no charting library is involved anywhere in this
  package, and a test sweeps the whole tree to keep it that way. LIME and
  the Shapash report are
  their own standalone HTML. Full breakdown of what renders what, and what
  none of these renderers can do:
  `references/figure-catalog.md`.

## Curated defaults — user data wins

The canonical palette lives in `sprezzature-colors` (see
`sprezzature-colors/references/palette.csv`); `sprezzature-figures` reads it at
runtime when co-installed. When the user has not specified a
palette, `sprezzature-figures render` reaches for the curated set. Mirror of the
three-Roboto rule in `sprezzature-ui/SKILL.md`:

- **Generation, no user palette specified:** use the curated CSV.
- **User names colors or supplies a palette** ("our brand is `#8B5CF6`",
  "we already have a tailwind.config.js with our tokens"): use theirs.
- **Audit mode:** respect the existing colors; do not refactor to the
  CSV unless the user asks. Judge colour-vision safety against the
  user's palette, not against ours, with `sprezzature-colors-cvd`;
  `audit_figure.py` has no CVD rule.

## Tool composition

For a data-science deliverable end-to-end:

```bash
# 1. Explore + plot in the house style. `line` needs the roles `month`
#    (its ordinal/temporal axis) and `value`; `sprezzature-figures describe
#    <kind>` shows any kind's roles.
sprezzature-figures render line --data data.csv \
    --map month=date --map value=conversion_rate \
    --out fig.svg

# 2. Explain the model.
python -m sprezzature_figures_scripts.explain_model \
    --model model.pkl --data X.csv --engine auto \
    --report shapash --out ./explain/

# 3. Estimate the causal effect + draw the DAG.
python -m sprezzature_figures_scripts.causal_estimate \
    --data d.csv --treatment T --outcome Y \
    --confounders "X1,X2,X3" --dag dag.gml \
    --estimator dml --refute all --out ./causal/

# 4. Audit the emitted figures.
python -m sprezzature_figures_scripts.audit_figure fig.svg
python -m sprezzature_figures_scripts.audit_figure ./explain/
python -m sprezzature_figures_scripts.audit_figure ./causal/dag.svg

# 5. Preview colorblind rendering.
sprezzature-colors-cvd fig.png --grid

# 6. Draft alt text for the surrounding page.
make-alt --kind complex \
    --context "Weekly conversion rate, higher is better" fig.png

# 7. Static a11y lint on the page that hosts the figure.
sprezzature-accessibility-lint public/report.html
```

## When NOT to use this skill

- You need a **live dashboard** (streaming metrics, WebSocket
  refresh); `sprezzature-figures` emits static specs / files. Use
  Grafana, Superset, or Streamlit.
- You need **notebook-first** exploration; the make scripts are
  pipe-ready CLIs, not Jupyter widgets. Use `jupyter-notebook`
  (Anthropic) or `working-in-notebooks` (legout) skills.
- You need **counterfactual explanations**; see `alibi`, `DiCE`, or
  the WhatIf tool. SHAP / Shapash / LIME answer *"why did the model
  predict this"*; counterfactuals answer *"what would flip the
  prediction"*.
- You need **causal discovery** (learning the DAG from data); see
  `causal-learn` or `causal-discovery-toolbox`. This skill assumes
  the DAG is supplied.
- You need **interrupted-time-series** or **synthetic-control**
  analyses; see `CausalImpact` (Bayesian ITS) or `SparseSC`
  (synthetic controls). Out of scope here.
- Your team already uses Style Dictionary / Theo / Tokens Studio and
  a designed dashboard framework; those are more powerful, and this
  skill is a deterministic pre-commit gate + a house-styled emitter.

## References

- `references/dataviz-decision-tree.md` — Which chart type for which
  question (frequency, comparison, part-of-whole, time series,
  distribution, correlation, geospatial).
- `references/polarity-and-color.md` — Why every quantitative axis
  gets a `(higher is better)` / `(lower is better)` / `(target = N)`
  tag; how the polarity color is picked from the palette's
  Psychology-Positive / Negative projections; Emotion / Concept
  accessors. Source of the semantic mapping:
  <https://deraison.ai/colors/>.
- `references/explainability.md` — SHAP / Shapash / TimeSHAP / LIME
  engine choice; per-engine output contract; when to prefer each.
- `references/causality.md` — DoWhy's four-step loop; EconML backends;
  refutation battery; how to encode a DAG in gml / DoWhy string form.
- `references/audit-figure.md` — Full rule catalogue for
  `audit_figure.py` with false-positive notes.
- `references/publication-presets.md` — Why there are no journal
  presets yet (Nature, Science, PLOS, IEEE), and what exists beside
  them: `--scale`, `render_diagram.py --dpi`, and the maps' `print_width`.
- `references/ralph-eyeball-loop.md` — The loop's protocol, surfaces
  and assessment file.
- `references/figure-catalog.md` — What renders what, and what no
  renderer here can do.

## Scripts

Shipped by the standalone [`sprezzature-figures`](https://github.com/warith-harchaoui/sprezzature-figures)
package (`pip install sprezzature-figures`), not by this monorepo. Two
generations of tooling coexist there: the console scripts
`sprezzature-figures` / `make-figure` (one Click group),
`sprezzature-figures-mcp` and `sprezzature-figures`, and the older per-purpose `scripts/*.py` (explainability,
causality, audit, install), packaged as `sprezzature_figures_scripts` with
no console-script entries of their own, so they run as `python -m
sprezzature_figures_scripts.<module>`.

| Script | Install | Purpose |
|---|---|---|
| `sprezzature-figures` / `make-figure` (console scripts, one Click group) | `pip install sprezzature-figures` | `list` / `describe` / `render` / `recommend` / `redraw` / `check`: the catalogue, one kind's roles and options, a render, a kind recommender, a redraw from a picture, and a render checker. **No extra is needed for any of them**: click became a base dependency on 2026-10-25, when the argparse front door was dropped, so the base install carries the whole command line. Until then these commands refused with a one-line message naming a `[cli]` extra; that extra no longer exists, and asking pip for it gets a warning and nothing else. |
| `explain_model.py` | `sprezzature-figures` | Model-agnostic explainability dispatcher: SHAP / Shapash / TimeSHAP / LIME. Auto-picks by model type; `--engine` overrides. |
| `causal_estimate.py` | `sprezzature-figures` | DoWhy loop (model → identify → estimate → refute) with EconML backends. Renders DAG in sprezzature-* house style; writes `effect.json`. |
| `audit_figure.py` | stdlib only | Static auditor for SVG charts and HTML `<figure>` blocks. Deterministic; no model, no network. |
| `install_figures.py` | subprocess to project env manager | Idempotent installer that pins the three tiers (dataviz / explain / causal). Detects uv / poetry / pixi / conda / pip. |
| `make_situation_map.py`, `build_situation_examples.py`, `make_choropleth.py` | *(moved out)* | Split into the standalone [`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps) package (`make-map` / `sprezzature-maps` console scripts). No longer part of `sprezzature-figures`. |
| `_argparse.py`, `_lang.py`, `_svg.py`, `_render.py`, `_interactive.py` | (internal helpers) | The scripts' argument parser factory, language detection, SVG primitives, rasterisation, the fullscreen control. |
| `_style.py` | stdlib only | Shared style tokens (palette lookup, dark-mode CSS block, Roboto stack). Reads `sprezzature-colors/references/palette.csv` when co-installed. |

## Companion skills

| You also need… | Install |
|---|---|
| Vanilla-JS + Tailwind UI generation (house style, tokens, components) | `sprezzature-ui` |
| Wrap the CLIs in a GUI (argparse or Click → web form) | `sprezzature-cli-gui` |
| Markdown → website + meta + favicons + indexes | `sprezzature-publish` |
| Static HTML a11y lint on the page hosting the figure | `sprezzature-accessibility` |
| WCAG contrast audit + CVD simulation on the rendered PNG | `sprezzature-colors` |
| W3C alt text for the rendered figure (local Ollama vision) | `sprezzature-accessibility` |
| Local WebVTT / SRT captions for an accompanying video | `sprezzature-audio` |
| Laws-of-UX audit on the surrounding page | `sprezzature-ux-laws` |
