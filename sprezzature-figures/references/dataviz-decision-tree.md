# Dataviz decision tree — which chart for which question

Pick the chart from the **question**, not from the shape of the data.
The dispatcher in `make_figure.py --kind auto` follows the same tree
when the caller has not specified `--kind`.

Sources: [Vega-Lite gallery](https://vega.github.io/vega-lite/examples/),
[From Data to Viz](https://www.data-to-viz.com/), Cleveland &
McGill (1984), Tufte, and the sprezzature-ui house style in
`sprezzature-ui/references/dataviz-chart-selection.md`.

## The question → chart map

| Question the chart must answer | Chart type | `--kind` flag | House-style notes |
|---|---|---|---|
| **How does this change over time?** | Line chart | `line` | Roboto Mono for tick labels; state polarity on the y-axis. Use a step line for state-machine values (login count per hour is `line`; deployment state is `step`). |
| **How does A compare to B (ranked categories)?** | Horizontal bar chart | `bar-h` | Sort by value descending; use vertical bars only when the category axis is time or ordinal (weekdays). |
| **What is the part of a whole?** | Stacked bar (100 %) or a labelled table | `bar-stacked` | Never a pie beyond 3 slices. Prefer a table when the reader must compare small percentages. |
| **How is this variable distributed?** | Histogram / density | `hist` | Use `--bins auto` (Freedman-Diaconis by default). Overlay a rug for < 200 points. |
| **How do two variables relate?** | Scatter plot | `scatter` | Add a `--regression` overlay if the caller asks. Never a scatter with more than 10 000 points; switch to hex bins (`--kind hexbin`). |
| **Are these two distributions the same?** | Overlaid density / ridgeline | `density` | Use a small multiple (`--facet <col>`) when > 4 groups. |
| **What's the range and outliers of these groups?** | Box / violin plot | `box` / `violin` | Show individual points via `--jitter` when N < 100 per group. |
| **What's the relationship between many variables?** | Correlation heatmap | `heatmap` | Sequential `RdBu_r` when the values are correlations centred at 0. |
| **How do two categoricals interact?** | Contingency heatmap | `heatmap-count` | Annotate cells with counts when < 100 cells. |
| **Where on a map?** | Choropleth / bubble map | `map` | See `sprezzature-ui/references/dataviz-maps.md`; use Albers projection for US, Robinson for world. |
| **What contributed to this prediction?** | SHAP waterfall / summary | (via `explain_model.py`) | See `references/explainability.md`. |
| **What's the causal effect?** | DAG + forest plot of the effect | (via `causal_estimate.py`) | See `references/causality.md`. |

## Anti-patterns the auditor flags

- **Dual y-axis** — two independent scales overlaid on the same plot.
  Almost always misleading; the eye reads coincidence where there is
  none. Emit two small multiples instead.
- **Truncated baseline** on a bar chart — the y-axis does not start at
  zero, so a 5 % difference looks like 50 %. Exempt for ratio scales
  (`log`, `pow`, `sqrt`).
- **3D pie / donut** — visual perspective distorts every slice.
  Always wrong.
- **Rainbow palette** on a sequential encoding — the visible spectrum
  is not perceptually uniform; the reader sees banding at yellow /
  cyan and misreads magnitudes. Use `viridis`, `plasma`, `magma`, or
  `cividis` (all CVD-safe).
- **Red + green with no other channel** — ~8 % of male viewers cannot
  distinguish. Add lightness variation, an icon, or a text label.
- **Unlabeled polarity** on a metric axis where "higher = good" is not
  obvious (bug count, response time, cost per acquisition). Append a
  short tag: `"Response time (ms — lower is better)"`.
- **Chartjunk** — background gradients, drop shadows on marks, custom
  fonts on every element. See Tufte's *"data-ink ratio"* argument.

## `--kind auto` — when the caller doesn't specify

The dispatcher picks by column dtypes:

| Columns given | Chart |
|---|---|
| `--x` is temporal (`datetime64`), `--y` is quantitative | `line` |
| `--x` is nominal, `--y` is quantitative, ≤ 30 categories | `bar-h` |
| `--x` is nominal, `--y` is quantitative, > 30 categories | Warn: pick a top-N or a histogram of values instead. |
| `--x` and `--y` both quantitative, N < 10 000 | `scatter` |
| `--x` and `--y` both quantitative, N ≥ 10 000 | `hexbin` |
| `--x` is quantitative, no `--y` | `hist` |
| `--x` is nominal, no `--y` | Warn: this is a value_counts; use `--kind bar-h` with `--y count`. |
| Two nominal columns, no `--y` | `heatmap-count` |

If the auto choice looks wrong for the question, override with
`--kind`. The dispatcher is a starting point, not a verdict.
