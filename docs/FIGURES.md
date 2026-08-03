# FIGURES.md — everything the engines can draw

A catalog of the figures this skill's engines produce, from **fake data**, each
one **rendered** so you can see it rather than take it on faith. It is the
public, positive twin of the gitignored `../.private/vega-failures/FAILURES.md`
(what genuinely did not work).

Together the two engines cover the everyday plotting application programming interface (API) of **matplotlib**,
**seaborn**, and **plotly**, including the plots people assume need one of
those libraries.

## The policy: Vega first, Scalable Vector Graphics (SVG) as the escape hatch

For any figure, the [Ralph Eyeball Loop](../sprezzature-figures/references/ralph-eyeball-loop.md) drives
the choice:

1. **Try Vega**: render the spec, look at it, refine. Vega is preferred (the
   spec carries its own data, themes to the house style, is natively
   interactive in a page).
2. **If the Vega loop can't get there**, drop to a **hand-authored SVG**, and
   run the same loop (render → look → refine). SVG covers what Vega's grammar
   can't express: smoothing filters, arrowhead markers, gradients.

Every figure below is rendered with `../sprezzature-figures/scripts/render_diagram.py <source> --out
<png>`; the kind (vega / svg) is auto-detected.

---

## Vega engine — everyday charts

| | |
|---|---|
| ![bar](../sprezzature-figures/assets/figures-gallery/bar.png) **Bar** — `plt.bar` / `sns.barplot` · `bar.vl.json` | ![line](../sprezzature-figures/assets/figures-gallery/line-multi.png) **Multi-line** — `sns.lineplot(hue=…)` · `line-multi.vl.json` |
| ![scatter](../sprezzature-figures/assets/figures-gallery/scatter.png) **Scatter** — `sns.scatterplot(hue=…)` · `scatter.vl.json` | ![histogram](../sprezzature-figures/assets/figures-gallery/histogram.png) **Histogram** — `sns.histplot` · `histogram.vl.json` |
| ![boxplot](../sprezzature-figures/assets/figures-gallery/boxplot.png) **Box plot** — `plt.boxplot` / `sns.boxplot` · `boxplot.vl.json` | ![stacked bar](../sprezzature-figures/assets/figures-gallery/stacked-bar.png) **100% stacked bar** — `sns.histplot(multiple="fill")` · `stacked-bar.vl.json` |
| ![stacked area](../sprezzature-figures/assets/figures-gallery/stacked-area.png) **Stacked area** — `plt.stackplot` · `stacked-area.vl.json` | ![donut](../sprezzature-figures/assets/figures-gallery/donut.png) **Donut** — `plt.pie(wedgeprops)` · `donut.vl.json` |
| ![heatmap](../sprezzature-figures/assets/figures-gallery/heatmap.png) **Annotated heatmap** — `sns.heatmap(annot=True)` · `heatmap.vl.json` | ![ecdf](../sprezzature-figures/assets/figures-gallery/ecdf.png) **empirical cumulative distribution function (ECDF)** — `sns.ecdfplot` · `ecdf.vl.json` |
| ![grouped bar](../sprezzature-figures/assets/figures-gallery/bar-grouped.png) **Grouped bar** — `sns.barplot(hue=…)` (`xOffset` encoding) · `bar-grouped.vl.json` | ![step](../sprezzature-figures/assets/figures-gallery/step.png) **Step / stairs** — `plt.step` (`interpolate: step-after`) · `step.vl.json` |
| ![lollipop](../sprezzature-figures/assets/figures-gallery/lollipop.png) **Lollipop** — `plt.stem` (`rule` + `point` layers) · `lollipop.vl.json` | ![error bars](../sprezzature-figures/assets/figures-gallery/errorbar.png) **Error bars** — `plt.errorbar` / `sns.pointplot` (mean + 95% interval) · `errorbar.vl.json` |
| ![density](../sprezzature-figures/assets/figures-gallery/kde1d.png) **Density (KDE)** — `sns.kdeplot` (Vega `density` transform) · `kde1d.vl.json` | |

## Vega engine — advanced cases

The plots people assume need matplotlib / plotly. All Vega (or full Vega),
rendered and eyeballed.

| | |
|---|---|
| ![hexbin](../sprezzature-figures/assets/figures-gallery/hexbin.png) **Hexbin** — `plt.hexbin` (offline hex + hexagon shape) · `hexbin.vl.json` | ![contour](../sprezzature-figures/assets/figures-gallery/kde2d-contour.png) **2D kernel density estimate (KDE) contour** — `sns.kdeplot` 2D (full-Vega `kde2d`+`isocontour`) · `kde2d-contour.vg.json` |
| ![beeswarm](../sprezzature-figures/assets/figures-gallery/beeswarm.png) **Beeswarm** — `sns.swarmplot` (full-Vega `force`+`collide`) · `beeswarm.vg.json` | ![clustermap](../sprezzature-figures/assets/figures-gallery/clustermap.png) **Clustermap** — `sns.clustermap` (scipy linkage + reordered heatmap) · `clustermap.vl.json` |
| ![quiver](../sprezzature-figures/assets/figures-gallery/quiver.png) **Quiver** — `plt.quiver` (`angle` on a triangle mark) · `quiver.vl.json` | ![regression](../sprezzature-figures/assets/figures-gallery/regression-ci-band.png) **Regression + confidence-interval (CI) band** — `sns.regplot` (offline fit + CI) · `regression-ci-band.vl.json` |
| ![surface](../sprezzature-figures/assets/figures-gallery/surface-3d.png) **Static 3D surface** — `plot_surface` / plotly `Surface` (offline projection + shaded polygons) · `surface-3d.vg.json` | ![violin](../sprezzature-figures/assets/figures-gallery/violin.png) **Violin** — `sns.violinplot` (offline KDE + mirrored `area`) · `violin.vl.json` |
| ![gaussian process](../sprezzature-figures/assets/figures-gallery/gaussian-process.png) **Gaussian process** — GP regression posterior: mean + 95% band + sampled functions (offline RBF kernel) · `gaussian-process.vl.json` | ![treemap](../sprezzature-figures/assets/figures-gallery/treemap.png) **Treemap** — hierarchical part-to-whole (full-Vega `stratify`+`treemap` squarify) · `treemap.vg.json` |
| ![parallel coordinates](../sprezzature-figures/assets/figures-gallery/parcoords.png) **Parallel coordinates** — multivariate profiles across shared axes (full-Vega per-field scales) · `parcoords.vg.json` | ![candlestick](../sprezzature-figures/assets/figures-gallery/candlestick.png) **Candlestick** — financial open-high-low-close (OHLC) (`rule` wick + `bar` body, up/down color) · `candlestick.vl.json` |
| ![sunburst](../sprezzature-figures/assets/figures-gallery/sunburst.png) **Sunburst** — radial hierarchical part-to-whole (full-Vega `partition` + `arc`) · `sunburst.vg.json` | ![waterfall](../sprezzature-figures/assets/figures-gallery/waterfall.png) **Waterfall** — running-total bridge, increase/decrease/total color (`bar` y/y2) · `waterfall.vl.json` |
| ![calendar heatmap](../sprezzature-figures/assets/figures-gallery/calendar-heatmap.png) **Calendar heatmap** — value per weekday × week (`rect` grid, Apple-blue ramp) · `calendar-heatmap.vl.json` | ![Q-Q plot](../sprezzature-figures/assets/figures-gallery/qqplot.png) **Q-Q plot** — sample vs theoretical normal quantiles + 45° reference · `qqplot.vl.json` |
| ![ROC curve](../sprezzature-figures/assets/figures-gallery/roc-curve.png) **ROC curve** — true vs false positive rate + chance diagonal, AUC in the title · `roc-curve.vl.json` | ![confusion matrix](../sprezzature-figures/assets/figures-gallery/confusion-matrix.png) **Confusion matrix** — actual × predicted counts (`rect` + `text`, contrast-aware labels) · `confusion-matrix.vl.json` |
| ![correlation matrix](../sprezzature-figures/assets/figures-gallery/corr-matrix.png) **Correlation matrix** — diverging red–white–blue with coefficient labels · `corr-matrix.vl.json` | ![funnel](../sprezzature-figures/assets/figures-gallery/funnel.png) **Funnel** — stage-to-stage drop-off, centered bars · `funnel.vl.json` |
| ![population pyramid](../sprezzature-figures/assets/figures-gallery/population-pyramid.png) **Population pyramid** — back-to-back bars by sex, absolute-value axis · `population-pyramid.vl.json` | ![bubble](../sprezzature-figures/assets/figures-gallery/bubble.png) **Bubble chart** — x, y, size, and color (four encodings) · `bubble.vl.json` |
| ![strip plot](../sprezzature-figures/assets/figures-gallery/strip.png) **Strip plot** — jittered points per category · `strip.vl.json` | ![volcano](../sprezzature-figures/assets/figures-gallery/volcano.png) **Volcano plot** — effect size vs significance, up/down/n.s. · `volcano.vl.json` |
| ![Kaplan-Meier](../sprezzature-figures/assets/figures-gallery/survival-km.png) **Kaplan–Meier survival** — step curves + confidence bands per arm · `survival-km.vl.json` | ![gantt](../sprezzature-figures/assets/figures-gallery/gantt.png) **Gantt** — task bars from start to end (`x`/`x2`) · `gantt.vl.json` |
| ![slope chart](../sprezzature-figures/assets/figures-gallery/slope.png) **Slope chart** — before/after across two points, crossings visible · `slope.vl.json` | |

## SVG engine — the escape hatch

When the Vega loop can't get there, hand-authored SVG does, rasterised with
`rsvg-convert`.

| | |
|---|---|
| ![streamplot](../sprezzature-figures/assets/figures-gallery/streamplot.png) **Streamplot** — RK4 streamlines of a wind field + arrowhead markers (Vega has no marker-end) · `svg-examples/streamplot.svg` | ![radar](../sprezzature-figures/assets/figures-gallery/radar.png) **Radar / spider** — multivariate profiles on radial axes, concentric grid + translucent polygons · `svg-examples/radar.svg` |

## Coverage sweep — statistics, networks & 3D

Eleven more hand-authored SVG figures from the capability sweep, each a
pure-Python generator (`scripts/make_<id>.py`) rasterised for this catalog.

| | |
|---|---|
| ![manhattan](../sprezzature-figures/assets/figures-gallery/manhattan.png) **Manhattan plot** — genome-wide −log10 p per position, peaks above the significance line, lead genes labelled · `svg-examples/manhattan.svg` | ![forest](../sprezzature-figures/assets/figures-gallery/forest.png) **Forest plot** — per-study odds ratios + confidence intervals, weight-sized boxes, pooled diamond · `svg-examples/forest.svg` |
| ![lift/gain](../sprezzature-figures/assets/figures-gallery/liftgain.png) **Cumulative gain / lift** — positives captured vs population contacted, baseline + perfect envelope · `svg-examples/liftgain.svg` | ![precision-recall](../sprezzature-figures/assets/figures-gallery/prcurve.png) **Precision-recall curve** — precision vs recall with the no-skill baseline and average precision · `svg-examples/prcurve.svg` |
| ![calibration](../sprezzature-figures/assets/figures-gallery/calibration.png) **Calibration / reliability** — predicted vs observed frequency over a confidence histogram · `svg-examples/calibration.svg` | ![UpSet](../sprezzature-figures/assets/figures-gallery/upset.png) **UpSet plot** — set-intersection bars over a membership matrix, scaling past a Venn · `svg-examples/upset.svg` |
| ![Venn](../sprezzature-figures/assets/figures-gallery/venn.png) **Venn / Euler** — overlapping sets, each region sized and counted · `svg-examples/venn.svg` | ![force-directed graph](../sprezzature-figures/assets/figures-gallery/sfdp-largegraph.png) **Force-directed graph** — a 318-node co-authorship network in six spatially-separated communities · `svg-examples/sfdp-largegraph.svg` |
| ![edge bundling](../sprezzature-figures/assets/figures-gallery/edge-bundling.png) **Hierarchical edge bundling** — relations bundled into smooth cables on a radial hierarchy · `svg-examples/edge-bundling.svg` | ![radial tree](../sprezzature-figures/assets/figures-gallery/radial-tree.png) **Radial tree** — a hierarchy drawn outward onto concentric rings · `svg-examples/radial-tree.svg` |
| ![rotating globe](../sprezzature-figures/assets/figures-gallery/globe3d.png) **Rotating globe** — orthographic Earth, animated in pure SMIL, spinning through a full day · `svg-examples/globe3d.svg` | |

## Charts from the library sweep — Highcharts / ECharts / Observable Plot

Ten more hand-authored SVG figures covering chart types the big JavaScript
libraries ship by default, each a pure-Python generator rasterised for this
catalog. Several carry hover interactions in the live SVG.

| | |
|---|---|
| ![word cloud](../sprezzature-figures/assets/figures-gallery/wordcloud.png) **Word cloud** — spiral-packed review terms sized by mention count, coloured by theme with a plus or minus sign so praise and gripe read without colour, hover a legend swatch to lift a theme · `svg-examples/wordcloud.svg` | ![streamgraph](../sprezzature-figures/assets/figures-gallery/streamgraph.png) **Streamgraph** — music-streaming volume by genre 2000–2024 on a wiggle baseline, Hip-Hop and R&B overtaking a thinning Rock · `svg-examples/streamgraph.svg` |
| ![packed bubbles](../sprezzature-figures/assets/figures-gallery/packed-bubble.png) **Packed bubbles** — programming languages as circles sized by developer usage, coloured by language family, hover a family to lift it · `svg-examples/packed-bubble.svg` | ![circle packing](../sprezzature-figures/assets/figures-gallery/circle-packing.png) **Circle packing** — a source tree as nested circles, packages enclosing modules sized by lines of code, hover a package to isolate it · `svg-examples/circle-packing.svg` |
| ![icicle](../sprezzature-figures/assets/figures-gallery/icicle.png) **Icicle** — a hierarchy partitioned into stacked rectangles, a rectangular sunburst · `svg-examples/icicle.svg` | ![bullet graph](../sprezzature-figures/assets/figures-gallery/bullet.png) **Bullet graph** — KPIs as a measure bar against a target tick and qualitative bands · `svg-examples/bullet.svg` |
| ![radial gauge](../sprezzature-figures/assets/figures-gallery/gauge.png) **Radial gauge** — server load, a needle over green / amber / red zones with a big percentage readout · `svg-examples/gauge.svg` | ![radial bar](../sprezzature-figures/assets/figures-gallery/radial-bar.png) **Radial bar** — a circular bar chart, bars wrapped around a polar axis · `svg-examples/radial-bar.svg` |
| ![Nightingale rose](../sprezzature-figures/assets/figures-gallery/rose.png) **Nightingale rose** — a coxcomb / polar-area chart of causes of mortality, radius by count · `svg-examples/rose.svg` | ![parliament](../sprezzature-figures/assets/figures-gallery/parliament.png) **Parliament hemicycle** — one dot per seat coloured by party, a majority line and a seat-count legend · `svg-examples/parliament.svg` |

## Charts from the library sweep — batch two

Ten more hand-authored SVG figures rounding out the same sweep, each a
pure-Python generator rasterised for this catalog. Several carry hover
interactions in the live SVG.

| | |
|---|---|
| ![dependency wheel](../sprezzature-figures/assets/figures-gallery/dependency-wheel.png) **Dependency wheel** — a directed circular sankey of internal migration between six regions, arcs sized by throughput and ribbons coloured by origin, hover a region to isolate its flows · `svg-examples/dependency-wheel.svg` | ![org chart](../sprezzature-figures/assets/figures-gallery/org-chart.png) **Org chart** — a top-down boxed org chart, a CEO over four hue-owned VP divisions and their teams, each box with role and headcount · `svg-examples/org-chart.svg` |
| ![variable-width columns](../sprezzature-figures/assets/figures-gallery/variwide.png) **Variable-width columns** — the eight largest economies, height as GDP per capita and width as population, so area reads as total GDP · `svg-examples/variwide.svg` | ![Pareto chart](../sprezzature-figures/assets/figures-gallery/pareto.png) **Pareto chart** — sorted support-ticket causes, a cumulative-share line and an 80% reference line on one shared axis, the vital few · `svg-examples/pareto.svg` |
| ![dumbbell chart](../sprezzature-figures/assets/figures-gallery/dumbbell.png) **Dumbbell chart** — two points per category joined by a segment, showing the change between two states · `svg-examples/dumbbell.svg` | ![spike map](../sprezzature-figures/assets/figures-gallery/spike-map.png) **Spike map** — vertical spikes at geographic locations, height encoding a value, over a faint basemap · `svg-examples/spike-map.svg` |
| ![difference chart](../sprezzature-figures/assets/figures-gallery/difference-chart.png) **Difference chart** — two time series with the gap between them shaded bicolour, above in one hue and below in another · `svg-examples/difference-chart.svg` | ![Voronoi tessellation](../sprezzature-figures/assets/figures-gallery/voronoi.png) **Voronoi tessellation** — catchment areas coloured by group, with seed points · `svg-examples/voronoi.svg` |
| ![convex hull](../sprezzature-figures/assets/figures-gallery/convex-hull.png) **Convex hull** — a grouped scatter with a translucent convex hull around each cluster · `svg-examples/convex-hull.svg` | ![timeline](../sprezzature-figures/assets/figures-gallery/timeline.png) **Timeline** — dated milestones on a horizontal spine with alternating above and below callouts · `svg-examples/timeline.svg` |

## Charts from the library sweep — batch three

Eight more hand-authored SVG figures from the same sweep, each a pure-Python
generator rasterised for this catalog. Several carry hover interactions in the
live SVG.

| | |
|---|---|
| ![wind-barb station plot](../sprezzature-figures/assets/figures-gallery/windbarb.png) **Wind-barb station plot** — a synoptic surface wind field, staffs point from the wind with a pennant for 50kt, a full barb for 10kt and a half barb for 5kt, a cold front dividing warm air ahead from a cold gale behind · `svg-examples/windbarb.svg` | ![Bollinger bands](../sprezzature-figures/assets/figures-gallery/bollinger.png) **Bollinger bands** — a daily price series with a 20-day moving average and shaded ±2σ bands, a volatility squeeze then an upside breakout · `svg-examples/bollinger.svg` |
| ![hexbin map](../sprezzature-figures/assets/figures-gallery/hexbin-map.png) **Hexbin map** — a world hexbin map of earthquakes, hexagons coloured by count, the densest bins tracing the Pacific Ring of Fire · `svg-examples/hexbin-map.svg` | ![connected scatter](../sprezzature-figures/assets/figures-gallery/connected-scatter.png) **Connected scatter** — a path through (x, y) points ordered by time to trace a trajectory, with year labels and start and end markers · `svg-examples/connected-scatter.svg` |
| ![liquid gauge](../sprezzature-figures/assets/figures-gallery/liquid-gauge.png) **Liquid gauge** — a disc filled with wavy liquid to a percentage, a reservoir at 63% of capacity, with a big percentage readout · `svg-examples/liquid-gauge.svg` | ![pictorial unit chart](../sprezzature-figures/assets/figures-gallery/pictorial.png) **Pictorial unit chart** — an ISOTYPE icon array where each repeated icon encodes a fixed count, one icon per N units · `svg-examples/pictorial.svg` |
| ![parallel sets](../sprezzature-figures/assets/figures-gallery/parallel-sets.png) **Parallel sets** — a categorical alluvial across class, sex, age and survival for the Titanic, ribbon width by count · `svg-examples/parallel-sets.svg` | ![binned grid map](../sprezzature-figures/assets/figures-gallery/binned-grid-map.png) **Binned grid map** — square-bin aggregation over geography, cells coloured by count · `svg-examples/binned-grid-map.svg` |

## Maps — thematic cartography

Thematic maps from a vendored, offline **Natural Earth** basemap
([`assets/geo/`](../sprezzature-figures/assets/geo/PROVENANCE.md), public domain, 110m + 50m). Built to
the conventions the best data desks use: **Equal-Earth** (equal-area, so a
country's ink matches its real size; never Mercator for a choropleth),
**classed** color (quintiles with rounded breaks, not a raw ramp), a
**conclusion title + source line**, hairline borders, and area-true symbols
(radius ∝ √value). Choropleths render in Vega; the overlay and hand-projected
maps take the SVG path (Vega's layered `geoshape` + `lon/lat` does not render
reliably under vl-convert, and Equal-Earth polygons need antimeridian cutting +
Antarctica handling that we do offline).

| | |
|---|---|
| ![choropleth](../sprezzature-figures/assets/figures-gallery/choropleth.png) **Choropleth** — Equal-Earth, quintile classes, headline + source (Vega `geoshape` + TopoJSON lookup) · `choropleth.vl.json` | ![bivariate](../sprezzature-figures/assets/figures-gallery/map-bivariate.png) **Bivariate choropleth** — two variables on a 3×3 color key · `svg-examples/map-bivariate.svg` |
| ![bubble map](../sprezzature-figures/assets/figures-gallery/map-bubble.png) **Proportional-symbol map** — area-true √ scale · `svg-examples/map-bubble.svg` | ![flow map](../sprezzature-figures/assets/figures-gallery/map-flow.png) **Connection / flow map** — great-circle arcs, width by volume (label synthetic flows as illustrative) · `svg-examples/map-flow.svg` |
| ![pie map](../sprezzature-figures/assets/figures-gallery/map-pie.png) **Pie-glyph map** — a pie per region · `svg-examples/map-pie.svg` | ![bar map](../sprezzature-figures/assets/figures-gallery/map-bars.png) **Bar-glyph map** — mini bars per region · `svg-examples/map-bars.svg` |

The editorial end: every unit equal weight, signed change, and change over time:

| | |
|---|---|
| ![tile grid](../sprezzature-figures/assets/figures-gallery/map-tilegrid.png) **Tile-grid cartogram** — one equal tile per country in a geographic layout, quintile classes · `svg-examples/map-tilegrid.svg` | ![diverging](../sprezzature-figures/assets/figures-gallery/map-diverging.png) **Diverging + annotated** — red–white–blue centered at 0, no-data gray, key countries labeled directly · `svg-examples/map-diverging.svg` |
| ![small multiples](../sprezzature-figures/assets/figures-gallery/map-small-multiples.png) **Small multiples** — one panel per year, class breaks frozen so the panels compare · `svg-examples/map-small-multiples.svg` | |

Honest scope: this is thematic map **visualization**, not a geographic information system (GIS). Spatial
analysis (joins, buffers, coordinate reference system (CRS) transforms, raster) is out of scope; use
geopandas / Quantum GIS (QGIS) for that (also how you'd curate more basemap geometry, see
`assets/geo/PROVENANCE.md`).

### Situation maps — layered areas-of-control plates, any region

Where the choropleths above summarise one variable per unit, a **situation map**
shows *who controls what*. `scripts/make_situation_map.py` reverse-engineers the
plate a geopolitics data desk draws (a stack of named layers: sea, bathymetry,
land, **real international frontiers** with neighbour labels, **areas of control**
with white boundary casing, infrastructure, **named rivers** in water-blue
italics, forces, events, letter-spaced labels, dual-unit scale bar, floated on a
shadowed panel) into a **parameterized generator**: one YAML config projects
*any* region (an auto-centred Lambert conformal conic) and emits the SVG.
`load_country("<name>")` lifts a real national outline from the vendored basemap
so you can partition it into zones rather than tracing borders; frontiers and
rivers come from the same offline Natural Earth library. Runtime geometry needs
`shapely` + `pyproj` (in `requirements-dataviz.txt`). Schema and layer table:
[`assets/situation-maps/ABOUT.md`](../sprezzature-figures/assets/situation-maps/ABOUT.md).

| | |
|---|---|
| ![Ukraine areas of control](../sprezzature-figures/assets/figures-gallery/situation-ukraine.png) **Ukraine** — government / occupied / contested along an approximate 2024 contact line (Wikipedia / ISW / DeepStateMap) · `ukraine.yaml` | |

Sprezzature lines are only as good as the geometry you feed it. Every plate is
**schematic, illustrative, and says so on its face**: approximate open-source
geography, not operational intelligence. All regenerate from one open, sourced
builder
([`scripts/build_situation_examples.py`](../sprezzature-figures/scripts/build_situation_examples.py)).

### Real data — the last five French presidential runoffs

The same SVG engine on **real** data (not synthetic): the winner's second-round
vote share **by département** for 2002–2022, from the Ministère de l'Intérieur, on
one frozen blue scale so the panels compare. Vendored geometry
([`assets/geo/fr/`](../sprezzature-figures/assets/geo/fr/PROVENANCE.md), metropolitan
départements) is projected offline with a **Lambert conformal conic**; results
live in [`assets/data/elections/`](../sprezzature-figures/assets/data/elections/PROVENANCE.md).

![French presidential runoffs 2002–2022 by département](../sprezzature-figures/assets/figures-gallery/fr-presidentielles-small-multiples.png)

2002 (the republican sprezzature) is near-uniformly dark; 2012 (the closest race) is the
palest; 2017 and 2022 show the lighter départements where the far right ran
strongest. Rendered on the website's figures gallery with a results table.

## Animated — the Hans Rosling tribute

Animation *is* ours, in pure SVG. `scripts/make_gapminder.py` rebuilds Hans
Rosling's famous "health vs wealth" bubble chart as a single **self-contained
animated SVG**: GDP per capita on a log x-axis, life expectancy on y, one bubble
per country sized by population and coloured by region, sweeping year by year
from 1950 to 2025. The motion is pure **SMIL** (`<animate>`), with no JavaScript
charting library, and the figure ships with the same **play / pause / scrub**
player we built for the website, so a reader can drive the years by hand.

[![Gapminder: GDP per capita vs life expectancy, animated](../sprezzature-figures/assets/figures-gallery/gapminder-animated.png)](../sprezzature-figures/assets/svg-examples/gapminder-animated.svg)

`scripts/make_gapminder_variants.py` reuses the same engine and player for two
sibling charts on the same country set: **fertility rate vs life expectancy** and
**GDP per capita vs child survival**. So the site's
[`web/hans-rosling.html`](../web/hans-rosling.html) carries three independently
playable charts, each in a bilingual English and French edition. Every mark
starts fully drawn (the still frame is complete on its own); the animation only
*adds* the year-over-year motion, so the base figure never animates in from
nothing. The data is real, from Our World in Data and the UN (see the sibling
`.PROVENANCE.md` files).

## Plotly, specifically

Most of plotly maps onto Vega directly, and one of plotly's headline features is
a **Vega native strength**, not a gap:

- **Interactivity** (hover, zoom, pan, linked brushing) — first-class in
  Vega-Lite (`params` / `selection`); a static export drops it, but the shipped
  spec is interactive in a page.
- **Maps** (`choropleth`, `scattergeo`) — Vega-Lite `geoshape` + projections.
- **Statistical** (violin, box, density-contour, distplot) — covered above.
- **`sunburst` / `treemap` / `icicle` / `sankey` / `parallel coordinates`** —
  full-Vega layouts (`partition`, `treemap`, custom Sankey, the parallel-coords
  example).
- **`candlestick` (open-high-low-close) / `waterfall` / `funnel`** — Vega-Lite `rule` + `bar`
  composites.
- **3D** — static surfaces / scatter as above.

## Accessibility — levels, live simulation, and OS-adaptive figures

Every generator takes an `--accessibility` level (`universal` default, plus
`high-contrast`, `monochrome`, `deuteranopia`, `protanopia`, `tritanopia`);
`universal` is the identity, so default figures are byte-for-byte unchanged.
The colour science lives in `sprezzature-colors` (`accessibility_levels.py`), wired
through `sprezzature-figures/scripts/_style.py`. Continuous or perceptual colour maps
(viridis, single-hue ramps) keep their colours as a documented no-op.

Beyond the static levels, most hand-authored SVG figures are now **OS-adaptive**:
one file that retunes itself when the reader's operating system signals a
preference, with no page scripting and no separate file per level. Inside each
SVG, additive `@media` blocks respond to three signals:

- `prefers-contrast: more` — each series deepens to its high-contrast hue and
  outlines strengthen; where a straight deepen would swallow overlaid labels
  (a Venn's region counts, say) the fills lighten instead so the core mark stays
  readable. Perceptual maps and ramps (viridis, single-hue, the bivariate
  matrix) keep their colours and only firm up ink, axes and frame.
- `forced-colors: active` (Windows High Contrast and kin) — figures whose
  category identity survives with no colour (position, shape, a numbered badge,
  a text label: Venn, parliament, waffle, network, org-chart...) drop to
  system-palette line art. Colour-**encoded** figures (streamgraph, sankey,
  chord, voronoi, the region choropleths...) instead give each series a distinct
  SVG **pattern** (hatch, dots, cross; open-stroke series get a dash key), so the
  encoding survives where a roughly four-colour system palette would merge it.
- `prefers-color-scheme: dark` — the paper inverts to a near-black surface, the
  house inks lighten, `mix-blend-mode: multiply` flips to `screen` so overlaps
  lighten instead of muddying, and light panels, gridlines and white pills are
  darkened per figure. Data hues and perceptual ramps are left alone (they read
  on dark); white keylines stay. The maps and `interactive-bar`, which ship as
  hand-authored SVGs with no generator, carry the same blocks injected directly.

Because every override lives inside a media query, the default render (no
preference active) is unchanged — verified additive-only across the whole
catalogue (every changed SVG differs from the previous release only by added
class hooks, media-gated style, and forced-colors pattern defs). The gallery
also carries a
"See it for… / Voir pour…" viewer that *simulates* colour-vision deficiencies
over the default figures for review; it simulates, it does not replace. Model
and sources: `sprezzature-colors/references/accessibility-levels.md`.


## Coverage sweep — the complete generator set

The remaining generators, each rendered from fake data in the house style so
the catalog matches every `make_*.py` one-to-one.

| | |
|---|---|
| ![andrews](../sprezzature-figures/assets/figures-gallery/andrews.png) **Andrews curves** — High-dimensional data as sinusoidal curves, one per observation · `svg-examples/andrews.svg` | ![arcdiagram](../sprezzature-figures/assets/figures-gallery/arcdiagram.png) **Arc diagram** — Network connections curved above a linear node axis · `svg-examples/arcdiagram.svg` |
| ![bar3d](../sprezzature-figures/assets/figures-gallery/bar3d.png) **Bar 3D** — Three-axis bar chart for two categorical dimensions and one metric · `svg-examples/bar3d.svg` | ![bellcurve](../sprezzature-figures/assets/figures-gallery/bellcurve.png) **Bell curve** — Normal distribution with a configurable mean and standard deviation · `svg-examples/bellcurve.svg` |
| ![blandaltman](../sprezzature-figures/assets/figures-gallery/blandaltman.png) **Bland-Altman** — Agreement between two measurement methods, with limits of agreement · `svg-examples/blandaltman.svg` | ![boxen](../sprezzature-figures/assets/figures-gallery/boxen.png) **Boxen plot** — Nested quantile boxes for large samples where a box plot loses detail · `svg-examples/boxen.svg` |
| ![columnrange](../sprezzature-figures/assets/figures-gallery/columnrange.png) **Column range** — High-low intervals per category (temperature ranges, confidence intervals) · `make_columnrange.py` | ![dendrogram](../sprezzature-figures/assets/figures-gallery/dendrogram.png) **Dendrogram** — Hierarchical clustering tree showing merge order and distances · `svg-examples/dendrogram.svg` |
| ![dotdensity](../sprezzature-figures/assets/figures-gallery/dotdensity.png) **Dot density** — One dot per unit of a quantity, placed within a geographic region · `svg-examples/dotdensity.svg` | ![dotplot](../sprezzature-figures/assets/figures-gallery/dotplot.png) **Dot plot** — One dot per observation, stacked into bins (Wilkinson dot plot) · `svg-examples/dotplot.svg` |
| ![hexmap](../sprezzature-figures/assets/figures-gallery/hexmap.png) **Hex map** — Cartogram where each geographic unit becomes a uniform hexagon · `svg-examples/hexmap.svg` | ![imshow-interpolated](../sprezzature-figures/assets/figures-gallery/imshow-interpolated.png) **Interpolated heatmap** — A matrix rendered with smooth bilinear interpolation (imshow) · `svg-examples/imshow-interpolated.svg` |
| ![jointplot](../sprezzature-figures/assets/figures-gallery/jointplot.png) **Joint plot** — Scatter of two variables with marginal histograms or densities · `svg-examples/jointplot.svg` | ![mosaic](../sprezzature-figures/assets/figures-gallery/mosaic.png) **Mosaic plot** — Two categoricals as a grid of rectangles sized by joint frequency · `svg-examples/mosaic.svg` |
| ![pairplot](../sprezzature-figures/assets/figures-gallery/pairplot.png) **Pair plot** — All pairwise scatter plots for a multivariate dataset · `svg-examples/pairplot.svg` | ![ppplot](../sprezzature-figures/assets/figures-gallery/ppplot.png) **P-P plot** — Probability-probability plot comparing two distributions · `svg-examples/ppplot.svg` |
| ![radviz](../sprezzature-figures/assets/figures-gallery/radviz.png) **RadViz** — Multivariate point placed by attraction to anchors on a unit circle · `svg-examples/radviz.svg` | ![residual](../sprezzature-figures/assets/figures-gallery/residual.png) **Residual plot** — Regression residuals vs. fitted values, for diagnostics · `svg-examples/residual.svg` |
| ![ridgeline](../sprezzature-figures/assets/figures-gallery/ridgeline.png) **Ridgeline** — Stacked, overlapping densities, one per group, shifted vertically · `svg-examples/ridgeline.svg` | ![rug](../sprezzature-figures/assets/figures-gallery/rug.png) **Rug plot** — Marginal tick marks for raw values beneath a density estimate · `svg-examples/rug.svg` |
| ![scatter3d](../sprezzature-figures/assets/figures-gallery/scatter3d.png) **Scatter 3D** — Three-variable scatter rendered as a projected 3D cloud · `svg-examples/scatter3d.svg` | ![speaking_time](../sprezzature-figures/assets/figures-gallery/speaking_time.png) **Speaking time** — A bar per speaker showing who spoke when in a recording · `svg-examples/speaking_time.svg` |
| ![spectrogram](../sprezzature-figures/assets/figures-gallery/spectrogram.png) **Spectrogram** — Time-frequency energy map of an audio signal · `svg-examples/spectrogram.svg` | ![ternary](../sprezzature-figures/assets/figures-gallery/ternary.png) **Ternary** — Three-component compositions inside an equilateral triangle · `svg-examples/ternary.svg` |
| ![windrose](../sprezzature-figures/assets/figures-gallery/windrose.png) **Wind rose** — Wind direction frequency and speed on a polar histogram · `svg-examples/windrose.svg` | ![wireframe3d](../sprezzature-figures/assets/figures-gallery/wireframe3d.png) **Wireframe 3D** — A mathematical surface as a projected mesh of grid lines · `svg-examples/wireframe3d.svg` |
| ![interruption-matrix](../sprezzature-figures/assets/figures-gallery/interruption-matrix.png) **Interruption matrix** — Directed "who cuts whom" heatmap: who interrupts whom in a conversation, tinted by the interrupter, with row/column totals and a crosshair hover · `svg-examples/interruption-matrix.svg` | |

## What still isn't ours

Honestly out of reach (see `../.private/vega-failures/FAILURES.md`):

- **Live-interactive 3D** — rotating a 3D camera in the browser (plotly's
  `Surface`/`Scatter3d` interactivity). Static 3D is fine; live rotation is
  three.js / plotly.
- **> ~50k marks** — rasterise with matplotlib / datashader.
