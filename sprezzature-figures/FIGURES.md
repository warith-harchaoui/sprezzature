# FIGURES.md — sprezzature-figures

The figures skill generates publication-quality data visualizations from code.
Every chart is written directly as SVG; the extension of `--out` picks the
format you get (SVG, PNG, PDF, JPG or HTML). The Ralph Eyeball Loop, and
`sprezzature-figures check` when no vision model is at hand, are the quality
gates before a figure is considered done.

## How to use

### From the command line

```sh
make-figure render bar --out output.png
make-figure render bar --out output.png --title "My title"
make-figure render bar                    # no --out: writes bar.svg in the current directory
make-figure describe bar                  # the data roles and options of one kind
```

`make-figure` and `sprezzature-figures` are the same Click group.

### As a library

```python
from sprezzature_figures import make_figure
path = make_figure("bar", data, out="output.png", title="My chart")
```

### With the Ralph Eyeball Loop

The loop takes the *source* of a visual (`.svg`, `.html`, `.tex`, `.mmd`),
renders it to PNG itself, and writes the critique to
`.private/ralph-loop/assessment-<hash>.md`.

```sh
# Agent mode (Claude reads the PNG):
python -m sprezzature_figures_scripts.ralph_eyeball_loop output.svg

# Local mode (qwen3-vl via Ollama, fully offline):
python -m sprezzature_figures_scripts.ralph_eyeball_loop output.svg --local
```

## Chart catalogue

168 chart generators, one per row — every `make_*.py` in `scripts/`, and
nothing else. The script name encodes the chart type: strip the `make_`
prefix and replace hyphens and underscores with spaces.

Situation maps (areas of control, military symbols) are not here, and neither
are choropleths on a real basemap; they live in the companion
`sprezzature-maps` package and its own skill, `sprezzature-maps`.

| Chart | Script | When to use |
|---|---|---|
| 100% stacked bar | make_stacked-bar.py | The mix within each category, normalised so only the shares compare |
| 2-D density contours | make_kde2d-contour.py | Where a bivariate sample concentrates, as isocontour rings over the scatter |
| 2-D histogram | make_hist2d.py | Overplotted scatter binned into a rectangular grid, cell colour the count |
| 3-D surface | make_surface3d.py | A function sampled on a grid, projected isometrically and shaded by height |
| Ablation matrix | make_ablation_matrix.py | Which components of a model earn their place; one row per variant with its metrics and intervals |
| ACF / PACF | make_acf.py | Autocorrelation and partial autocorrelation by lag, with the noise band; how far back a series remembers |
| Alluvial | make_alluvial.py | Flows of a population across two or more categorical stages |
| Andrews curves | make_andrews.py | High-dimensional data as sinusoidal curves, one per observation |
| Arc diagram | make_arcdiagram.py | Network connections curved above a linear node axis |
| Area chart | make_area.py | Stacked area showing how a whole made of categories evolves over an ordered axis |
| Bar 3D | make_bar3d.py | Three-axis bar chart for two categorical dimensions and one metric |
| Bar chart | make_bar.py | Ranked categories against one measure; revenue by region, headcount by department |
| Beeswarm | make_beeswarm.py | Every observation shown, nudged apart so the swarm's width reads as density |
| Bell curve | make_bellcurve.py | Normal distribution with configurable mean and standard deviation |
| Binned grid map | make_binned-grid-map.py | Geographic aggregates binned into a regular grid of hexagons or squares |
| Bland-Altman | make_blandaltman.py | Agreement between two measurement methods; limits of agreement |
| Bollinger bands | make_bollinger.py | Price with rolling mean and ±2-sigma envelope for volatility |
| Box plot | make_boxplot.py | Five-number summary (median, quartiles, whiskers) per category, with outliers |
| Boxen plot | make_boxen.py | Nested quantile boxes for large samples where box plots lose detail |
| Bubble chart | make_bubble.py | Two axes plus a third measure as bubble area and a fourth as colour |
| Bullet chart | make_bullet.py | Actual vs. target on a qualitative performance scale |
| Bump chart | make_bump.py | Rank over time, one line per competitor, crossing when one overtakes another |
| Calendar heatmap | make_calendar-heatmap.py | A daily count across months at a glance; commit activity, active users, habit tracking |
| Calibration curve | make_calibration.py | Predicted probability vs. observed frequency for classifier reliability |
| Candlestick (OHLC) | make_candlestick.py | Open, high, low and close per period, the body coloured by direction |
| Causal DAG | make_causal-dag.py | An assumed causal structure, each node's role (confounder, mediator, collider) worked out from the arrows |
| Chord diagram | make_chord.py | Pairwise flows between categories as arcs on a circle |
| Circle packing | make_circle-packing.py | Hierarchical proportions as nested circles |
| Clustermap | make_clustermap.py | A heatmap with rows and columns reordered by hierarchical clustering, dendrograms attached |
| Cohort retention | make_cohort-retention.py | Retention triangle: one row per cohort, one column per period of age |
| Column range | make_columnrange.py | High-low intervals per category; temperature ranges, confidence intervals |
| Confusion matrix | make_confusion-matrix.py | Actual against predicted class; the diagonal is right, each off-diagonal cell one specific mistake |
| Connected scatter | make_connected-scatter.py | Temporal path through two variables with labelled waypoints |
| Contour | make_contour.py | Iso-lines and filled bands over a gridded scalar field z = f(x, y) |
| Control chart | make_control-chart.py | Individuals chart with centre line, control limits and named run rules |
| Convex hull | make_convex-hull.py | Cluster boundaries as minimal enclosing polygons on a scatter |
| Correlation matrix | make_corr-matrix.py | Pairwise correlation across features; multicollinearity before modelling |
| Cycle wheel | make_cycle.py | Directed ring of proportional arcs for a recurring process (rotation, seasons, lifecycle) |
| Dendrogram | make_dendrogram.py | Hierarchical clustering tree showing merge order and distances |
| Density (KDE) | make_kde1d.py | The shape of one numeric sample, without a histogram's bin edges in the way |
| Dependency wheel | make_dependency-wheel.py | Directed module or package dependencies on a chord wheel |
| Difference chart | make_difference-chart.py | Two lines with the gap filled green (A ahead) or red (B ahead) |
| Diffusion trajectory | make_diffusion_trajectory.py | An animated walk of a diffusion process across a point cloud |
| Donut | make_donut.py | A small part-of-whole breakdown, two to six categories |
| Dot density | make_dotdensity.py | One dot per unit of a quantity placed randomly within a geographic region |
| Dot plot | make_dotplot.py | One dot per observation stacked into bins (Wilkinson dot plot) |
| Dual axis | make_dual-axis.py | Bars on one axis, a line on the other, for two series whose units share no scale |
| Dumbbell | make_dumbbell.py | Before-and-after change for each item as a horizontal segment |
| ECDF | make_ecdf.py | The share of a sample at or below each value; percentile thresholds and service levels |
| Edge bundling | make_edge-bundling.py | Large network with edges grouped into smooth bundles to reduce clutter |
| Elbow / knee | make_elbow.py | Choosing how many — clusters, components — by the knee of a diminishing-returns curve |
| Embedding projector | make_embedding_projector.py | High-dimensional embeddings projected to 2D for cluster inspection |
| Error bars | make_errorbar.py | A point estimate per category with the interval around it |
| Event plot | make_eventplot.py | Raster of events: one tick per event, one row per thing it happened to |
| Facet (small multiples) | make_facet.py | The same chart once per group, every panel on one shared scale |
| Fishbone | make_fishbone.py | Ishikawa cause-and-effect diagram, causes ranked by weight |
| Flowchart | make_flowchart.py | Labelled boxes and arrows in layers, for a pipeline or a method diagram; every word comes from the rows |
| Forecast fan | make_forecast-fan.py | History solid, forecast dashed inside nested intervals that widen with the horizon |
| Forest plot | make_forest.py | Effect sizes and confidence intervals from multiple studies |
| Funnel | make_funnel.py | Conversion or attrition across sequential pipeline stages |
| Funnel area | make_funnel-area.py | A funnel whose bands are sized by area, the quantity the eye measures |
| Gantt | make_gantt.py | A schedule as one bar per task, spanning start to end, coloured by owning team |
| Gapminder | make_gapminder.py | Animated bubble chart of health vs. wealth by country and year |
| Gapminder variants | make_gapminder_variants.py | Animated bubble chart variants for the Hans ROSLING world-health demo |
| Gauge | make_gauge.py | Single KPI on a semicircular dial with colour-coded zones |
| Gaussian process | make_gaussian-process.py | A GP posterior over a handful of observations: mean, credible band, sample functions |
| Grouped bar | make_bar-grouped.py | Categories split by a second dimension; sales by region and quarter |
| Heatmap | make_heatmap.py | Row × column matrix with cell colour encoding a numeric value |
| Hex map | make_hexmap.py | Cartogram where each geographic unit becomes a uniform hexagon |
| Hexbin density | make_hexbin.py | Overplotted scatter binned into hexagons, cell colour the point count |
| Hexbin map | make_hexbin-map.py | Geographic point density aggregated into hexagonal bins on a map |
| Histogram | make_histogram.py | Bins a single numeric variable and counts observations per bin |
| Horizon | make_horizon.py | Area chart folded into colour bands to compress vertical space |
| Icicle | make_icicle.py | Hierarchical data as nested rectangles growing from a root column |
| Imshow interpolated | make_imshow-interpolated.py | Raster image or matrix rendered with smooth bilinear interpolation |
| Interruption matrix | make_interruption-matrix.py | Directed who-cuts-whom heatmap: who interrupts whom in a conversation, with row/column totals and a crosshair hover |
| Joint plot | make_jointplot.py | Scatter of two variables with marginal histograms or densities |
| Kaplan-Meier | make_survival-km.py | Probability of surviving past each time, from possibly-censored durations |
| Learning curve | make_learning-curve.py | Score against training-set size; whether more data is worth collecting |
| Lift-gain curve | make_liftgain.py | Model targeting efficiency: lift and cumulative gain vs. population depth |
| Line 3D | make_line3d.py | A trajectory through three dimensions, where the order of the points is data |
| Line chart | make_line.py | Multi-series line chart, the default for a value over an ordered axis |
| Liquid gauge | make_liquid-gauge.py | Percentage as a rising liquid fill inside a circular container |
| Lollipop | make_lollipop.py | A lighter bar chart: a stem from zero capped with a dot, sorted |
| Loss curve | make_loss-curve.py | Training and validation loss by epoch, the best epoch marked |
| Manhattan plot | make_manhattan.py | Genome-wide association p-values by chromosomal position |
| Manifold path | make_manifold_path.py | An animated traversal across a landscape or a learned manifold |
| Map bars | make_map-bars.py | A small grouped bar chart planted at each place |
| Map bubbles | make_map-bubble.py | One quantity per place as circle area |
| Map flows | make_map-flow.py | Origin-destination flows as lines between places, width proportional to the flow |
| Map pies | make_map-pie.py | A composition planted at each place, every disc the same size |
| Map tile grid | make_map-tilegrid.py | Every country as an equal square on a roughly geographic grid |
| Missing-value matrix | make_missing-matrix.py | Where values are absent, field by field and record by record |
| Mosaic plot | make_mosaic.py | Two categorical variables as a grid of rectangles sized by joint frequency |
| Multi-line | make_line-multi.py | A few series sampled densely along one continuous axis |
| Network | make_network.py | Force-directed graph for arbitrary node-edge data |
| OHLC bars | make_ohlc.py | Open, high, low, close per session as ticked bars; survives a monochrome print |
| Org chart | make_org-chart.py | Hierarchical reporting structure as a top-down tree |
| P-P plot | make_ppplot.py | Probability-probability plot for comparing two distributions |
| Packed bubble | make_packed-bubble.py | Proportional circles packed to fill a frame, sized by a single metric |
| Pair plot | make_pairplot.py | All pairwise scatter plots for a multivariate dataset |
| Parallel coordinates | make_parcoords.py | Many numeric dimensions at once, each record a polyline across one axis per metric |
| Parallel sets | make_parallel-sets.py | Categorical flows across multiple axes as ribbon widths |
| Pareto | make_pareto.py | Bar chart sorted descending with a cumulative percentage line overlay |
| Parliament | make_parliament.py | Seat distribution in a semicircular legislative chamber layout |
| PDP / ICE | make_pdp-ice.py | Partial dependence with one individual-conditional-expectation line per row |
| Permutation importance | make_permutation-importance.py | How much worse the model scores when each column is shuffled, with the spread |
| Pictorial | make_pictorial.py | Icon array or pictogram for proportions intended for a general audience |
| Pie | make_pie.py | A plain part-of-whole disc, few parts, sorted largest-first |
| Point plot | make_pointplot.py | A point estimate per group with its interval, joined across categories |
| Polar | make_polar.py | Data on a circular axis system; useful for cyclic or directional data |
| Population pyramid | make_population-pyramid.py | Two groups mirrored around a shared zero, one row per age band |
| PR curve | make_prcurve.py | Precision-recall trade-off for a binary classifier |
| Progress bars | make_progress.py | One bar per goal, with a rule where it should stand at this point of the period |
| Q-Q plot | make_qqplot.py | Sample quantiles against a theoretical distribution's; normality at a glance |
| Quiver (vector field) | make_quiver.py | Direction and magnitude at every point of a plane; flow and gradient fields |
| Quiver 3D | make_quiver3d.py | Arrows sampling a three-dimensional vector field |
| Radar | make_radar.py | Multi-attribute comparison on spoke axes radiating from a centre |
| Radial bar | make_radial-bar.py | Bar chart bent into concentric arcs on a polar axis |
| Radial tree | make_radial-tree.py | Hierarchical tree laid out on radial spokes |
| RadViz | make_radviz.py | Multivariate point placed by attraction to anchors on a unit circle |
| Regression with CI band | make_regression-ci-band.py | An ordinary-least-squares fit with the 95% confidence band around the fitted mean |
| Residual plot | make_residual.py | Regression residuals vs. fitted values for diagnostic inspection |
| Ridgeline | make_ridgeline.py | Stacked, overlapping densities one per group, shifted vertically |
| ROC curve | make_roc-curve.py | True-positive against false-positive rate as the decision threshold sweeps |
| Rose diagram | make_rose.py | Angular frequency histogram on a polar axis |
| Rug plot | make_rug.py | Marginal tick marks for raw values beneath a density estimate |
| Sankey | make_sankey.py | Flow diagram where ribbon widths encode quantities between nodes |
| Scatter 3D | make_scatter3d.py | Three-variable scatter rendered as a projected 3D cloud |
| Scatter plot | make_scatter.py | Two numeric variables as points, optionally coloured by group |
| Seasonal decomposition | make_seasonal-decomposition.py | A series split into trend, seasonal cycle and remainder |
| SFDP large graph | make_sfdp-largegraph.py | Force-directed layout scaled to thousands of nodes via SFDP |
| SHAP beeswarm | make_shap-beeswarm.py | One swarm per feature: each row's contribution, coloured by the feature's value |
| SHAP waterfall | make_shap-waterfall.py | One prediction taken apart, from the model's average output, one step per feature |
| Silhouette | make_silhouette.py | One blade per sample, sorted within its cluster; judging a clustering |
| Slope chart | make_slope.py | Each item's value at two periods, joined by a line between two axes |
| Sparklines | make_sparkline.py | Word-sized lines, one metric per row, no axes |
| Speaking time | make_speaking_time.py | Gantt-style bar per speaker showing who spoke when in a recording |
| Spectrogram | make_spectrogram.py | Time-frequency energy map of an audio signal |
| Spike map | make_spike-map.py | Geographic quantities as vertical spikes rising from each location |
| Stacked area | make_stacked-area.py | A composition over a continuous axis, read both as a whole and as its parts |
| Stem plot | make_stem.py | One stalk per sample, for genuinely discrete data |
| Step / stairs | make_step.py | A piecewise-constant series; stock after each transaction, a price that only moves on trade |
| Stream plot | make_streamplot.py | Vector field as smooth flow lines with arrowheads |
| Streamgraph | make_streamgraph.py | Stacked area chart centred on the baseline for flowing time series |
| Strip plot | make_strip.py | Raw measurements per category, jittered so points do not hide each other |
| Sunburst | make_sunburst.py | Hierarchical part-to-whole as nested arcs radiating from a centre |
| Table | make_table.py | A table typeset as a chart: right-aligned tabular digits, comparisons made easy |
| Ternary | make_ternary.py | Three-component compositions inside an equilateral triangle |
| Timeline | make_timeline.py | Events or durations placed along a horizontal time axis |
| Tree | make_tree.py | Rooted hierarchical tree with labelled nodes and edges |
| Treemap | make_treemap.py | Hierarchical proportions as nested rectangles sized by value |
| Tricontour | make_tricontour.py | Iso-lines over scattered samples, triangulated |
| Trisurface | make_trisurface.py | A surface over scattered measurements, joined by a Delaunay triangulation |
| UpSet plot | make_upset.py | Set intersections as a matrix of dots with bar charts for counts |
| Validation curve | make_validation-curve.py | Score against one hyper-parameter, training and validation |
| Variwide | make_variwide.py | Bar chart where column width encodes a second variable |
| Venn diagram | make_venn.py | Overlap between two or three sets shown as intersecting circles |
| Violin plot | make_violin.py | Distribution shape across a few groups, where the shape itself carries the message |
| Volcano plot | make_volcano.py | Effect size against significance; which changes are both large and reliable |
| Voronoi | make_voronoi.py | Space partitioned into regions of nearest-neighbour influence |
| Voxels | make_voxels.py | Cells of a three-dimensional grid drawn as solid blocks |
| Waffle | make_waffle.py | Proportion as a grid of filled squares, one square per unit |
| Waterfall | make_waterfall.py | Cumulative change from a baseline as positive and negative segments |
| Wind rose | make_windrose.py | Wind direction frequency and speed on a polar histogram |
| Windbarb | make_windbarb.py | Meteorological wind speed and direction as barbed staffs on a map |
| Wireframe 3D | make_wireframe3d.py | Mathematical surface as a projected mesh of grid lines |
| Word cloud | make_wordcloud.py | Term frequency encoded as font size in a fitted text layout |

## Adding a new chart type

The generators live in the standalone
[`sprezzature-figures`](https://github.com/warith-harchaoui/sprezzature-figures)
repository, not in this one.

1. There, copy the structure of any existing `scripts/make_*.py`.
2. Populate `DEMO_DATA` with realistic, domain-specific numbers. No placeholder names.
3. Confirm it renders: `sprezzature-figures render <kind> --out /tmp/<kind>.svg`.
4. Add a row to that repository's `FIGURES.md`, and to the table above.
5. Here, `python3 scripts/bump_catalogue_count.py` rewrites every quoted count
   from the brick's `catalog/figures.json`; add
   trigger phrases to `scripts/build_triggers.py` and regenerate `TRIGGERS.md`.
6. Add a card to `web/figures.html` and `web/fr/figures.html`.

## Ralph Eyeball Loop integration

Every generator's SVG is a valid input to the loop. Pass the source file, not
a PNG:

```sh
# Render, critique with a local vision model, write the assessment.
python -m sprezzature_figures_scripts.ralph_eyeball_loop web/img/figures/waterfall.svg --local
```

Each run renders the PNG, asks for a critique of layout, contrast, hierarchy,
spacing, accessibility and colour, and appends an iteration section to the
assessment file. Editing the source is your step, or the agent's; re-run the
loop after each edit, and stop when the Verdict box is checked.
