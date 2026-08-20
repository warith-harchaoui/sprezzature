# Which catalogue kind for which question

`sprezzature-ui/references/dataviz-chart-selection.md` teaches the general
method for picking a chart shape: name the question in one of four
families (comparison, composition, relationship, distribution), then pick
the chart built for that family. Read that file first if you have not;
this one does not repeat its reasoning. What this file adds is specific
to `sprezzature-figures`: its catalogue is **closed**, `make-figure` only
renders one of 124 registered kinds (`sprezzature-figures list` prints
the current count and names), not an open combination of any x, y, and
mark type. So the real question here is narrower than "what chart shape
fits," it is "which of these 124 already-built kinds fits, and where does
the catalogue simply not have what you need yet."

## The catalogue's own category groupings

Every entry in `sprezzature_figures/catalog/figures.json` carries a
`category` field. Grouped and counted, the seven largest categories are:

| Category | Count | Kinds |
|---|---|---|
| Distribution | 17 | beeswarm, bellcurve, boxen, boxplot, clustermap, corr-matrix, dotplot, ecdf, errorbar, hexbin, histogram, kde1d, population-pyramid, ridgeline, rug, strip, violin |
| Comparison | 9 | bar, bar-grouped, bar3d, bubble, difference-chart, lollipop, packed-bubble, radial-bar, variwide |
| Model evaluation | 6 | calibration, confusion-matrix, gaussian-process, liftgain, prcurve, roc-curve |
| Hierarchy | 6 | circle-packing, icicle, org-chart, radial-tree, sunburst, tree |
| Network | 5 | arcdiagram, dependency-wheel, edge-bundling, network, sfdp-largegraph |
| Composition | 5 | area, donut, stacked-area, stacked-bar, waffle |
| Geospatial | 5 | binned-grid-map, dotdensity, hexbin-map, hexmap, spike-map |
| Time series | 5 | calendar-heatmap, horizon, line, line-multi, step |

The remaining ~40 categories hold one to four kinds each, covering more
specialized questions: model-diagnostic pairs (`qqplot`/`ppplot` for
goodness of fit, `residual` for regression diagnostics), finance
(`candlestick`, `bollinger`), genomics-flavored statistics (`manhattan`,
`volcano`, `survival-km`), vector fields (`quiver`, `streamplot`), and
several 3-D surfaces (`surface3d`, `wireframe3d`, `scatter3d`, `bar3d`).
`sprezzature-figures list` is the authoritative, always-current source for
the full set; the table above is a snapshot, not a promise that these
counts stay fixed as the catalogue grows.

These `category` labels are the catalogue's own bookkeeping, not
identical to the four question-families `dataviz-chart-selection.md`
uses. Composition maps directly. Comparison and Distribution roughly
correspond to that guide's Comparison and Distribution families.
Relationship, in the general guide, is scattered across this catalogue's
Relationship (`parcoords`, `scatter`), Bivariate distribution
(`jointplot`, `kde2d-contour`), Network, and Multivariate categories,
because the catalogue subdivides by structure (is it two variables, a
graph, or many variables at once) rather than by the single question
"how does X relate to Y." Time series in the general guide maps to this
catalogue's Time series category plus a handful of others tagged
elsewhere (`candlestick` under Finance, `streamgraph` under "Time series /
Composition"), since a temporal chart here is filed by what else it is
doing (composition over time, financial data over time) as much as by the
fact that time is on an axis.

## Mapping the general four families onto this catalogue

**Comparison** ("how does A compare to B," "how has A changed over
time"). Few items, no time axis: `bar`, `lollipop`, `dumbbell` (paired
comparison, Change category). Few items over time: `line`, `step`. Many
items, ranked: `pareto`, `radial-bar`. A comparison across a second
dimension too: `bar-grouped`, `variwide` (width itself encodes a second
value), `bubble`.

**Composition** ("what are the parts of a whole"). Static composition:
`donut`, `waffle`, `treemap`, `sunburst`, `icicle` (the last three also
carry hierarchy). Composition changing over time: `stacked-area`,
`stacked-bar`, `streamgraph`. A composition that must reconcile to a
running total: `waterfall` (filed under Accounting / Decomposition, the
catalogue's own name for this).

**Relationship** ("how does X relate to Y"). Two continuous variables:
`scatter`, `connected-scatter` (when order matters), `hexbin` or
`kde2d-contour` (when point overplotting itself is the problem). More
than two variables at once: `parcoords`, `pairplot`, `radviz`,
`andrews`. Explicit graph structure rather than a continuous relationship:
`network`, `arcdiagram`, `chord`, `sankey`, `alluvial` (the last two
answer "how does a population move between categorical states," not a
correlation question at all, filed under Flow).

**Distribution** ("how are values spread"). One variable: `histogram`,
`kde1d`, `boxplot`, `violin`, `ecdf`. One variable across many groups at
once, ranked: `ridgeline`, `beeswarm`, `strip`. Two variables' joint
spread: `jointplot`, `kde2d-contour`. A distribution's tails or extremes
specifically: `bellcurve`, `qqplot` (is this distribution normal),
`survival-km` (time-to-event distribution).

**Geospatial**, not one of the general guide's four families but its own
catalogue category here: `binned-grid-map` and `hexbin-map`/`hexmap` for
point density aggregated over an area, `dotdensity` for individual
points, `spike-map` for a magnitude at a location. See
`sprezzature-ui/references/dataviz-maps.md` for the general geospatial
projection guidance this catalogue's map kinds sit under.

## `sprezzature-figures recommend`: what it can and cannot do for you

`sprezzature-figures recommend --data file.csv` ranks catalogue kinds
your actual data can fill, checked against each kind's declared
`required_roles` (a kind needs, say, one categorical and one numeric
column; your data either has columns that could fill those roles or it
does not). The CLI also accepts `--intent
comparison|trend|distribution|...` to narrow by declared analytical
intent. As shipped, every one of the 124 catalogue entries has an empty
`intents` list, the schema supports it, the field is not yet populated
for any kind, so `--intent` filtering has nothing tagged to filter by
today; treat the ranking as driven by data-shape fit (which roles your
columns can satisfy), not by a curated intent match, until the catalogue
entries are annotated. `sprezzature-figures recommend --render out.svg`
draws the top-ranked pick directly, useful for a first pass, but the
ranking answers "what can render from this data," not "what best answers
your question," that second judgment is still yours.

## When the catalogue does not have what you need

The catalogue is closed-set by design (see `SKILL.md`'s "Honest framing"
table): `make-figure` will not invent a new chart kind from an arbitrary
`--x`/`--y`/mark combination. If `sprezzature-figures list` does not show
a kind that fits your question, the honest options are to compose the
closest available kind and note its limits, or to reach outside this
skill (matplotlib/seaborn directly, for a genuinely novel chart shape;
`sprezzature-ui/references/dataviz-chart-selection.md` and
`dataviz-maps.md` for chart types the general guide covers that this
catalogue does not register at all, such as certain map projections).
