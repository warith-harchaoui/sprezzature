# Figure catalog — Vega-first, SVG fallback, thematic maps

This is the catalog of everything the engines can draw and how each one is
built: everyday and statistical charts as Vega-Lite, the harder cases as
full-Vega, the genuine escape-hatches as hand-authored Scalable Vector Graphics
(SVG), and a full set of thematic maps. It stays in sync with the capability
tracker `.private/data-viz-capabilities.csv` (gitignored) and the rendered
gallery in `docs/FIGURES.md`; the complete list of runnable specs is at the
bottom under "Shipped runnable specs".

**Prefer Vega-Lite.** For any chart it can express, reach for a Vega-Lite
v5 spec before matplotlib, seaborn, or pyplot, because the spec carries
its own data (figure + data + encoding in one auditable, diffable,
re-traceable file), it themes to the house style via `_style.vega_config`,
it drops straight into a sprezzature-ui page, and the [Ralph Eyeball
Loop](ralph-eyeball-loop.md) rasterises the *actual* spec that ships.

Every skeleton below is `mark` + `encoding` (+ `transform` where it does
real work), with `"data": {"name": "table"}` as a placeholder. In
production, add `"$schema": "https://vega.github.io/schema/vega-lite/v5.json"`
and merge `_style.vega_config(dark=…)` into `config`; render with
`scripts/render_diagram.py fig.vl.json --out fig.png`.

Type fields: `nominal` (categorical), `ordinal` (ordered), `quantitative`
(numeric), `temporal` (dates).

Sources: [Vega-Lite gallery](https://vega.github.io/vega-lite/examples/),
[Vega gallery](https://vega.github.io/vega/examples/),
[vl-convert](https://github.com/vega/vl-convert).

## Why this replaces matplotlib / seaborn / pyplot

Default matplotlib is ugly; it takes a lot of tuning to look presentable.
A house-styled Vega spec (`_style.vega_config`: rounded bars, no top/right
spines, CVD-safe palette, Roboto) is good-looking by default, for free. The
rest of the win: the spec carries its own data (reproducible), it drops into a
sprezzature-ui page, and the [Ralph Eyeball Loop](ralph-eyeball-loop.md) rasterises
the real spec.

The claim "replace matplotlib / seaborn / pyplot" only holds if the base API
of all three is covered. Here is the honest map: clean (idiomatic Vega-Lite),
full-Vega (needs the Vega spec, see "Closing the residue" below), or the small
set that genuinely stays in matplotlib.

| pyplot / matplotlib | seaborn | Vega verdict |
|---|---|---|
| `plot` | `lineplot` / `relplot` | clean |
| `scatter` | `scatterplot` | clean |
| `bar` / `barh` | `barplot` / `countplot` | clean |
| `hist` | `histplot` | clean |
| `hist2d` | `displot` (2D) | clean |
| `boxplot` | `boxplot` | clean |
| `violinplot` | `violinplot` | clean (mirror = faceted trick) |
| `pie` | — | clean (auditor discourages > 3 slices) |
| `stackplot` | — | clean (stacked / streamgraph) |
| `fill_between` | `kdeplot` fill / regplot CI | clean |
| `step` / `stairs` | `ecdfplot` | clean |
| `errorbar` | `pointplot` / barplot CI | clean |
| `stem` | — | clean (lollipop) |
| `axhline` / `axvline` / `hlines` / `vlines` | — | clean (`rule`) |
| `loglog` / `semilogx` / `semilogy` | — | clean (`scale.type: log`) |
| `subplots` | `FacetGrid` / `relplot` / `PairGrid` | clean (facet / concat / repeat) |
| `annotate` / `text` | — | clean (`text` mark) |
| — | `stripplot` | clean (jitter) |
| — | `rugplot` | clean (`tick`) |
| — | `ecdfplot` | clean (cumulative window) |
| — | `jointplot` | clean (concat marginals) |
| — | `pairplot` / SPLOM | clean (`repeat`) |
| — | `heatmap` (annotated) | clean (`rect` + `text`) |
| `hexbin` | `jointplot(kind="hex")` | full-Vega or offline hex + hexagon shape |
| `contour` / `contourf` | `kdeplot` 2D | full-Vega (`kde2d` + `isocontour`) |
| — | `swarmplot` | full-Vega (`force` + `collide`) |
| — | `clustermap` | offline linkage + Vega heatmap + `rule` dendrograms |
| `quiver` | — | Vega-Lite `angle` on a triangle mark |
| `regplot` / `lmplot` CI band | `regplot` | offline fit + CI, then `area` band |
| `imshow` (gridded) / `pcolormesh` | `heatmap` | clean (`rect`, no interpolation) |
| `plot_surface` / `plot_wireframe` / 3D scatter | — | static 3D via offline projection + full-Vega polygons (below); live-rotatable 3D not possible |
| `streamplot` | — | offline streamlines only (not shipped) |
| `imshow` (interpolated raster) | — | not native (hard cells only) |
| `twinx` (dual axis) | — | possible but discouraged (auditor flags) |
| `table` | — | not a chart (render as HTML) |

The full-Vega and offline-compute rows are all worked out with runnable,
rendered examples in "Closing the residue — the hard cases, done" below.

## 1. Bar

| Chart | seaborn / matplotlib | Key |
|---|---|---|
| Vertical bar | `sns.barplot` / `plt.bar` | `x` N, `y` Q |
| Horizontal bar | `sns.barplot(orient="h")` | swap x/y; prefer for ranked categories |
| Grouped bar | `sns.barplot(hue=…)` | `xOffset` (v5 idiom) |
| Stacked bar | `sns.histplot(multiple="stack")` | `color` adds the series |
| 100 % stacked | `multiple="fill"` | `"stack": "normalize"` |

```json
{"data":{"name":"table"},"mark":"bar","encoding":{"y":{"field":"cat","type":"nominal","sort":"-x"},"x":{"field":"val","type":"quantitative"}}}
```
```json
{"data":{"name":"table"},"mark":"bar","encoding":{"x":{"field":"cat","type":"nominal"},"y":{"field":"val","type":"quantitative"},"xOffset":{"field":"grp","type":"nominal"},"color":{"field":"grp","type":"nominal"}}}
```

## 2. Line

| Chart | seaborn / matplotlib | Key |
|---|---|---|
| Line | `sns.lineplot` | `x` T, `y` Q |
| Multi-series | `sns.lineplot(hue=…)` | `color` N |
| Line + point | `marker="o"` | `{"type":"line","point":true}` |
| Step | `drawstyle="steps"` | `"interpolate":"step-after"` |

```json
{"data":{"name":"table"},"mark":{"type":"line","point":true},"encoding":{"x":{"field":"t","type":"temporal"},"y":{"field":"val","type":"quantitative"},"color":{"field":"series","type":"nominal"}}}
```

## 3. Area

| Chart | matplotlib | Key |
|---|---|---|
| Area | `fill_between` | `mark:"area"` |
| Stacked area | `stackplot` | + `color` |
| Streamgraph | `stackplot(baseline="wiggle")` | `"stack":"center"` |

```json
{"data":{"name":"table"},"mark":"area","encoding":{"x":{"field":"t","type":"temporal"},"y":{"field":"val","type":"quantitative","stack":"center"},"color":{"field":"series","type":"nominal"}}}
```

## 4. Scatter

| Chart | seaborn | Key |
|---|---|---|
| Scatter | `sns.scatterplot` | `x` Q, `y` Q |
| Bubble | `size=…` | + `size` Q |
| By category | `hue=…` | + `color` N |

```json
{"data":{"name":"table"},"mark":"point","encoding":{"x":{"field":"x","type":"quantitative"},"y":{"field":"y","type":"quantitative"},"size":{"field":"mag","type":"quantitative"},"color":{"field":"cat","type":"nominal"}}}
```

## 5. Histogram / density

| Chart | seaborn | Key |
|---|---|---|
| Histogram | `sns.histplot` | `"bin":true` + `"aggregate":"count"` |
| Density (KDE) | `sns.kdeplot` | `density` transform (Gaussian, a real KDE) |

```json
{"data":{"name":"table"},"mark":"bar","encoding":{"x":{"field":"val","type":"quantitative","bin":true},"y":{"aggregate":"count"}}}
```
```json
{"data":{"name":"table"},"transform":[{"density":"val","bandwidth":0.3}],"mark":"area","encoding":{"x":{"field":"value","type":"quantitative"},"y":{"field":"density","type":"quantitative"}}}
```

## 6. Box / strip

```json
{"data":{"name":"table"},"mark":{"type":"boxplot","extent":"min-max"},"encoding":{"x":{"field":"grp","type":"nominal"},"y":{"field":"val","type":"quantitative"}}}
```
Strip / jitter (`sns.stripplot`) via a random `xOffset`:
```json
{"data":{"name":"table"},"transform":[{"calculate":"random()","as":"jitter"}],"mark":{"type":"point","size":8},"encoding":{"x":{"field":"grp","type":"nominal"},"y":{"field":"val","type":"quantitative"},"xOffset":{"field":"jitter","type":"quantitative","axis":null}}}
```

## 7. Heatmap

```json
{"data":{"name":"table"},"mark":"rect","encoding":{"x":{"field":"col","type":"nominal"},"y":{"field":"row","type":"nominal"},"color":{"field":"val","type":"quantitative"}}}
```
2D binned density (`plt.hist2d`): bin both axes, `"aggregate":"count"` on color.

## 8. Small multiples

```json
{"data":{"name":"table"},"mark":"line","encoding":{"x":{"field":"t","type":"temporal"},"y":{"field":"val","type":"quantitative"},"facet":{"field":"grp","type":"nominal","columns":3}}}
```
Use `column` × `row` for a full grid (`sns.FacetGrid`).

## 9. Layered composite

Bar + mean rule (replaces a manual `axhline`):
```json
{"data":{"name":"table"},"layer":[
  {"mark":"bar","encoding":{"x":{"field":"cat","type":"nominal"},"y":{"field":"val","type":"quantitative"}}},
  {"mark":"rule","encoding":{"y":{"aggregate":"mean","field":"val","type":"quantitative"}}}
]}
```

## 10. Error bars / CI

The composite marks compute the interval from raw rows (`extent` = `ci` /
`stderr` / `stdev` / `iqr`), the seaborn `errorbar=` default, done in-spec:
```json
{"data":{"name":"table"},"mark":{"type":"errorband","extent":"ci"},"encoding":{"x":{"field":"t","type":"temporal"},"y":{"field":"val","type":"quantitative","title":"mean ± CI"}}}
```
Hold precomputed `lo`/`hi` instead? Use a `rule` with `y`/`y2`.

## 11. Ranged dot / lollipop / dumbbell

```json
{"data":{"name":"table"},"encoding":{"y":{"field":"cat","type":"nominal"},"x":{"field":"val","type":"quantitative"}},"layer":[
  {"mark":"rule"},
  {"mark":{"type":"point","filled":true,"size":100}}
]}
```

## Explainability & causality — from extracted model data

These replace `shap.plots.*` and DoWhy's graphviz output. You extract the
numbers from the model and drive Vega yourself; the plot is just data.

- **SHAP beeswarm** — melt `shap_values.values` to long rows
  `{feature, shap, feat_val_norm}`; `circle` mark, `x`=shap, `y`=feature,
  `color`=normalised feature value, random `yOffset` as jitter. (Vega-Lite
  has no true swarm packing; jitter is the honest approximation.)
- **SHAP / permutation importance** — `mean(|shap|)` per feature → sorted
  horizontal bar (`"sort":"-x"`). Clean.
- **SHAP waterfall** — one row's contributions; running sum via a `window`
  transform, floating bars with `x`/`x2`. Workable, the most awkward.
- **LIME weights** — `explanation.as_list()` → diverging horizontal bar,
  color by sign. Clean.
- **Partial dependence / ICE** — faint per-sample `line` layer (`detail`
  = line id) under a bold PD average line. Clean.
- **Causal DAG** — precompute the layout in Python (`networkx`
  `graphviz_layout`/`spring_layout`), emit nodes `{id,x,y}` and edges
  `{x,y,x2,y2}`; layer `rule` (edges) + `circle` (nodes) + `text`
  (labels). Reproducible. (Auto-layout needs full Vega's `force`
  transform, non-deterministic; prefer precomputed coordinates.)

```json
{"data":{"name":"table"},"transform":[{"calculate":"random()","as":"jit"}],"mark":{"type":"circle","size":14,"opacity":0.6},"encoding":{"x":{"field":"shap","type":"quantitative","title":"SHAP value"},"y":{"field":"feature","type":"nominal","sort":{"field":"imp","order":"descending"}},"yOffset":{"field":"jit","type":"quantitative","axis":null},"color":{"field":"feat_val_norm","type":"quantitative","title":"feature value"}}}
```

## Print & vector output

`vl-convert` emits **PNG, SVG, and vector PDF**, journal-ready. Hit exact
physical dimensions by setting `width`/`height` in the spec to
inches × dpi (e.g. Nature single column = 89 mm ≈ 3.5 in → 1050 px at
300 dpi) and rendering `--format pdf` / `--format svg`. Contour / 2D
density fields need **full Vega** (`isocontour` / `kde2d` transforms),
not Vega-Lite.

## Closing the residue — the hard cases, done

These are the plots people assume need matplotlib. Each is a real Vega or
full-Vega spec, rendered and eyeballed through the Ralph Eyeball Loop. The
runnable specs (data inline) live in `assets/vega-examples/`; render any with
`python scripts/render_diagram.py assets/vega-examples/<file> --out /tmp/x.png`.

| seaborn / pyplot | how | example |
|---|---|---|
| `regplot` / `lmplot` CI band | fit + 95% CI offline, then `area` (y/y2) + `line` + `point` layers | `regression-ci-band.vl.json` |
| `hexbin` / `jointplot(kind="hex")` | hex-bin offline, then a `point` with a hexagon SVG `shape`, color = count | `hexbin.vl.json` |
| `kdeplot` 2D / `contourf` | full Vega `kde2d` → `isocontour` → filled `path` levels over a faint scatter | `kde2d-contour.vg.json` |
| `swarmplot` (true packing) | full Vega `force` + `collide`, x = value focus | `beeswarm.vg.json` |
| `clustermap` | scipy linkage offline, then a heatmap with rows/cols `sort`ed by leaf order (margin dendrograms as `rule` marks from the linkage coords) | `clustermap.vl.json` |
| `quiver` / vector field | a `point` `shape:"triangle"` with an `angle` encoding = direction, color/size = magnitude | `quiver.vl.json` |
| `plot_surface` / 3D surface | project the mesh offline (isometric), painter's-sort the faces, shade each by its normal, draw as full-Vega `path` polygons | `surface-3d.vg.json` |
| `squarify` treemap / plotly `treemap` | full Vega `stratify` → `treemap` (squarify) → `rect` + `text`, leaves colored by parent family | `treemap.vg.json` |
| pandas `parallel_coordinates` / plotly `parcoords` | full Vega: one linear scale per field, a shared point scale for the axes, `line` per row through `y = scale[field]` | `parcoords.vg.json` |
| `mplfinance` / plotly `Candlestick` / `Ohlc` | `rule` (low→high wick) + `bar` (open→close body) layered, color by up/down close | `candlestick.vl.json` |
| plotly `sunburst` / `ggsunburst` | full Vega `partition` → `arc` marks (angle = a0/a1, radius = r0/r1), leaves at parent-family color + a legend | `sunburst.vg.json` |
| `ggradar` / plotly `scatterpolar(fill)` | hand-authored SVG: concentric grid polygons, labeled spokes, one translucent polygon per series | `svg-examples/radar.svg` |
| ECharts / AntV `rose` / Nightingale coxcomb | hand-authored SVG: equal-angle annular sectors, one per category, radius = value, stacked + coloured by sub-cause, native `<title>` tooltips + CSS `:has()` hover to isolate a cause | `svg-examples/rose.svg` |
| D3 / AntV `pack` / hierarchical circle packing | hand-authored SVG: an offline pack layout (`packSiblings` front-chain + `packEnclose` Welzl, ported from D3), leaves sized by value and shaded by size, each top-level family a hue, outside name pills + a hero call-out, native `<title>` tooltips + CSS `:hover` to isolate a package | `svg-examples/circle-packing.svg` |

The everyday-but-less-obvious cases (waterfall with `bar` y/y2 and a precomputed
running total, calendar heatmap as `rect` on week × weekday, Q-Q plot of sample vs
theoretical quantiles plus a 45° `rule`, ROC curve as `line` plus chance diagonal,
confusion / correlation matrices as `rect` plus contrast-aware `text`) are all
idiomatic Vega-Lite; runnable specs ship in `assets/vega-examples/`.

## Where matplotlib genuinely still wins

The residue is now short and specific:

- **Live-interactive 3D** — rotating / zooming a 3D camera in the browser, and
  volume rendering. *Static* 3D surfaces / wireframes / 3D scatter are doable
  (project offline, draw full-Vega polygons, see "Closing the residue" above),
  but Vega has no camera or z-axis, so live rotation stays in plotly / three.js.
- **Streamplot** — integrated streamlines. Only doable by integrating the
  lines offline and drawing them as `line` / `path` marks; not shipped here.
- **Interpolated `imshow`** — matplotlib's bilinear / bicubic smoothing
  between pixels, or an in-memory pixel array. Vega draws hard `rect` cells (a
  fine grid approximates but is not true interpolation); its `image` mark only
  takes an external URL.
- **> ~50k marks** — in-browser rendering gets heavy; rasterise with
  matplotlib / datashader.
- **Broken / twin-independent secondary axes** — deliberately discouraged
  (the auditor flags dual axes).

Everything else (the everyday 2D statistical and scientific plotting API of
matplotlib, seaborn, and pyplot) is covered above.

## Shipped runnable specs

Auto-derived from `assets/`. Render any with `python scripts/render_diagram.py assets/<dir>/<file> --out /tmp/x.png`. Keep this list current with `.private/data-viz-capabilities.csv` when figures are added or removed.

**Vega / Vega-Lite** (`assets/vega-examples/`, 49):

- `bar-grouped.vl.json`
- `bar.vl.json`
- `beeswarm.vg.json`
- `boxplot.vl.json`
- `bubble.vl.json`
- `calendar-heatmap.vl.json`
- `candlestick.vl.json`
- `choropleth.vl.json`
- `clustermap.vl.json`
- `confusion-matrix.vl.json`
- `corr-matrix.vl.json`
- `donut.vl.json`
- `dotplot.vl.json`
- `ecdf.vl.json`
- `errorbar.vl.json`
- `funnel.vl.json`
- `gantt.vl.json`
- `gaussian-process.vl.json`
- `heatmap.vl.json`
- `hexbin.vl.json`
- `histogram.vl.json`
- `jointplot.vl.json`
- `kde1d.vl.json`
- `kde2d-contour.vg.json`
- `line-multi.vl.json`
- `lollipop.vl.json`
- `mosaic.vg.json`
- `parcoords.vg.json`
- `population-pyramid.vl.json`
- `qqplot.vl.json`
- `quiver.vl.json`
- `regression-ci-band.vl.json`
- `ridgeline.vl.json`
- `roc-curve.vl.json`
- `rug.vl.json`
- `scatter.vl.json`
- `slope.vl.json`
- `stacked-area.vl.json`
- `stacked-bar.vl.json`
- `step.vl.json`
- `strip.vl.json`
- `sunburst.vg.json`
- `surface-3d.vg.json`
- `survival-km.vl.json`
- `treemap.vg.json`
- `violin.vl.json`
- `volcano.vl.json`
- `waffle.vl.json`
- `waterfall.vl.json`

**SVG escape-hatch — statistics, networks, 3D, animation, maps + the library sweep** (`assets/svg-examples/`, 91):

- `alluvial.svg`
- `andrews.svg`
- `arcdiagram.svg`
- `bar3d.svg`
- `binned-grid-map.svg`
- `blandaltman.svg`
- `bollinger.svg`
- `boxen.svg`
- `bullet.svg`
- `calibration.svg`
- `chord.svg`
- `circle-packing.svg`
- `connected-scatter.svg`
- `convex-hull.svg`
- `dendrogram.svg`
- `dependency-wheel.svg`
- `difference-chart.svg`
- `dotdensity.svg`
- `dotplot.svg`
- `dumbbell.svg`
- `edge-bundling.svg`
- `embedding-projector.svg`
- `forest.svg`
- `fr-presidentielles-small-multiples-fr.svg`
- `fr-presidentielles-small-multiples.svg`
- `gapminder-animated.fr.svg`
- `gapminder-animated.svg`
- `gapminder-fertility.fr.svg`
- `gapminder-fertility.svg`
- `gapminder-income-survival.fr.svg`
- `gapminder-income-survival.svg`
- `gauge.svg`
- `globe3d.svg`
- `hexbin-map.svg`
- `hexmap.svg`
- `horizon.svg`
- `icicle.svg`
- `imshow-interpolated.svg`
- `interactive-bar.svg`
- `jointplot.svg`
- `liftgain.svg`
- `liquid-gauge.svg`
- `manhattan.svg`
- `map-bars.svg`
- `map-bivariate.svg`
- `map-bubble.svg`
- `map-diverging.svg`
- `map-flow.svg`
- `map-pie.svg`
- `map-small-multiples.svg`
- `map-tilegrid.svg`
- `mosaic.svg`
- `network.svg`
- `org-chart.svg`
- `packed-bubble.svg`
- `pairplot.svg`
- `parallel-sets.svg`
- `pareto.svg`
- `parliament.svg`
- `pictorial.svg`
- `polar.svg`
- `ppplot.svg`
- `prcurve.svg`
- `radar.svg`
- `radial-bar.svg`
- `radial-tree.svg`
- `radviz.svg`
- `residual.svg`
- `ridgeline.svg`
- `rose.svg`
- `rug.svg`
- `sankey.svg`
- `scatter3d.svg`
- `sfdp-largegraph.svg`
- `speaking_time.svg`
- `spectrogram.svg`
- `spike-map.svg`
- `streamgraph.svg`
- `streamplot.svg`
- `ternary.svg`
- `timeline.svg`
- `tree.svg`
- `upset.svg`
- `variwide.svg`
- `venn.svg`
- `voronoi.svg`
- `waffle.svg`
- `windbarb.svg`
- `windrose.svg`
- `wireframe3d.svg`
- `wordcloud.svg`

Situation maps (areas-of-control) live under `assets/situation-maps/` and are generated by `scripts/make_situation_map.py`; the French presidential-runoff small-multiples and their per-year data are under `assets/data/elections/`.

