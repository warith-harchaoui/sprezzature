# FIGURES.md — sprezzature-figures

The figures skill generates publication-quality data visualizations from code.
Every chart renders to PNG, SVG, or PDF and passes through the Ralph Eyeball
Loop quality gate before it is considered done.

## How to use

### From the command line

```sh
python sprezzature-figures/scripts/make_bar.py --out output.png
python sprezzature-figures/scripts/make_bar.py --out output.png --title "My title"
```

### As a library

```python
from pathlib import Path
# Each script exposes a make_<name> function and DEMO_DATA.
import importlib, sys
sys.path.insert(0, "sprezzature-figures/scripts")
mod = importlib.import_module("make_bar")
path = mod.make_bar(mod.DEMO_DATA, out=Path("output.png"), title="My chart")
```

### With the Ralph Eyeball Loop

```sh
# Agent mode (Claude reads the PNG):
python sprezzature-figures/scripts/ralph_eyeball_loop.py output.png

# Local mode (qwen3-vl via Ollama, fully offline):
python sprezzature-figures/scripts/ralph_eyeball_loop.py output.png --local
```

## Chart catalogue

91 chart generators, one per row. The script name encodes the chart type:
strip the `make_` prefix and replace hyphens and underscores with spaces.

| Chart | Script | When to use |
|---|---|---|
| Alluvial | make_alluvial.py | Flows of a population across two or more categorical stages |
| Andrews curves | make_andrews.py | High-dimensional data as sinusoidal curves, one per observation |
| Arc diagram | make_arcdiagram.py | Network connections curved above a linear node axis |
| Area chart | make_area.py | Stacked area showing how a whole made of categories evolves over an ordered axis |
| Bar 3D | make_bar3d.py | Three-axis bar chart for two categorical dimensions and one metric |
| Bell curve | make_bellcurve.py | Normal distribution with configurable mean and standard deviation |
| Binned grid map | make_binned-grid-map.py | Geographic aggregates binned into a regular grid of hexagons or squares |
| Bland-Altman | make_blandaltman.py | Agreement between two measurement methods; limits of agreement |
| Bollinger bands | make_bollinger.py | Price with rolling mean and ±2-sigma envelope for volatility |
| Box plot | make_boxplot.py | Five-number summary (median, quartiles, whiskers) per category, with outliers |
| Boxen plot | make_boxen.py | Nested quantile boxes for large samples where box plots lose detail |
| Bullet chart | make_bullet.py | Actual vs. target on a qualitative performance scale |
| Calibration curve | make_calibration.py | Predicted probability vs. observed frequency for classifier reliability |
| Chord diagram | make_chord.py | Pairwise flows between categories as arcs on a circle |
| Circle packing | make_circle-packing.py | Hierarchical proportions as nested circles |
| Column range | make_columnrange.py | High-low intervals per category; temperature ranges, confidence intervals |
| Connected scatter | make_connected-scatter.py | Temporal path through two variables with labelled waypoints |
| Convex hull | make_convex-hull.py | Cluster boundaries as minimal enclosing polygons on a scatter |
| Cycle wheel | make_cycle.py | Directed ring of proportional arcs for a recurring process (rotation, seasons, lifecycle) |
| Dendrogram | make_dendrogram.py | Hierarchical clustering tree showing merge order and distances |
| Dependency wheel | make_dependency-wheel.py | Directed module or package dependencies on a chord wheel |
| Difference chart | make_difference-chart.py | Two lines with the gap filled green (A ahead) or red (B ahead) |
| Dot density | make_dotdensity.py | One dot per unit of a quantity placed randomly within a geographic region |
| Dot plot | make_dotplot.py | One dot per observation stacked into bins (Wilkinson dot plot) |
| Dumbbell | make_dumbbell.py | Before-and-after change for each item as a horizontal segment |
| Edge bundling | make_edge-bundling.py | Large network with edges grouped into smooth bundles to reduce clutter |
| Embedding projector | make_embedding_projector.py | High-dimensional embeddings projected to 2D for cluster inspection |
| Figure (generic) | make_figure.py | Entry point that delegates to the appropriate specialist generator |
| Forest plot | make_forest.py | Effect sizes and confidence intervals from multiple studies |
| Funnel | make_funnel.py | Conversion or attrition across sequential pipeline stages |
| Gapminder | make_gapminder.py | Animated bubble chart of health vs. wealth by country and year |
| Gapminder variants | make_gapminder_variants.py | Animated bubble chart variants for the Hans Rosling world-health demo |
| Gauge | make_gauge.py | Single KPI on a semicircular dial with colour-coded zones |
| Heatmap | make_heatmap.py | Row × column matrix with cell colour encoding a numeric value |
| Hex map | make_hexmap.py | Cartogram where each geographic unit becomes a uniform hexagon |
| Hexbin map | make_hexbin-map.py | Geographic point density aggregated into hexagonal bins on a map |
| Histogram | make_histogram.py | Bins a single numeric variable and counts observations per bin |
| Horizon | make_horizon.py | Area chart folded into colour bands to compress vertical space |
| Icicle | make_icicle.py | Hierarchical data as nested rectangles growing from a root column |
| Imshow interpolated | make_imshow-interpolated.py | Raster image or matrix rendered with smooth bilinear interpolation |
| Interruption matrix | make_interruption-matrix.py | Directed who-cuts-whom heatmap: who interrupts whom in a conversation, with row/column totals and a crosshair hover |
| Joint plot | make_jointplot.py | Scatter of two variables with marginal histograms or densities |
| Lift-gain curve | make_liftgain.py | Model targeting efficiency: lift and cumulative gain vs. population depth |
| Line chart | make_line.py | Multi-series line chart, the default for a value over an ordered axis |
| Liquid gauge | make_liquid-gauge.py | Percentage as a rising liquid fill inside a circular container |
| Manhattan plot | make_manhattan.py | Genome-wide association p-values by chromosomal position |
| Mosaic plot | make_mosaic.py | Two categorical variables as a grid of rectangles sized by joint frequency |
| Network | make_network.py | Force-directed graph for arbitrary node-edge data |
| Org chart | make_org-chart.py | Hierarchical reporting structure as a top-down tree |
| P-P plot | make_ppplot.py | Probability-probability plot for comparing two distributions |
| Packed bubble | make_packed-bubble.py | Proportional circles packed to fill a frame, sized by a single metric |
| Pair plot | make_pairplot.py | All pairwise scatter plots for a multivariate dataset |
| Parallel sets | make_parallel-sets.py | Categorical flows across multiple axes as ribbon widths |
| Pareto | make_pareto.py | Bar chart sorted descending with a cumulative percentage line overlay |
| Parliament | make_parliament.py | Seat distribution in a semicircular legislative chamber layout |
| Pictorial | make_pictorial.py | Icon array or pictogram for proportions intended for a general audience |
| Polar | make_polar.py | Data on a circular axis system; useful for cyclic or directional data |
| PR curve | make_prcurve.py | Precision-recall trade-off for a binary classifier |
| Radar | make_radar.py | Multi-attribute comparison on spoke axes radiating from a centre |
| Radial bar | make_radial-bar.py | Bar chart bent into concentric arcs on a polar axis |
| Radial tree | make_radial-tree.py | Hierarchical tree laid out on radial spokes |
| RadViz | make_radviz.py | Multivariate point placed by attraction to anchors on a unit circle |
| Residual plot | make_residual.py | Regression residuals vs. fitted values for diagnostic inspection |
| Ridgeline | make_ridgeline.py | Stacked, overlapping densities one per group, shifted vertically |
| Rose diagram | make_rose.py | Angular frequency histogram on a polar axis |
| Rug plot | make_rug.py | Marginal tick marks for raw values beneath a density estimate |
| Sankey | make_sankey.py | Flow diagram where ribbon widths encode quantities between nodes |
| Scatter 3D | make_scatter3d.py | Three-variable scatter rendered as a projected 3D cloud |
| Scatter plot | make_scatter.py | Two numeric variables as points, optionally coloured by group |
| SFDP large graph | make_sfdp-largegraph.py | Force-directed layout scaled to thousands of nodes via SFDP |
| Situation map | make_situation_map.py | Geographic map with overlaid areas of control and military symbols |
| Speaking time | make_speaking_time.py | Gantt-style bar per speaker showing who spoke when in a recording |
| Spectrogram | make_spectrogram.py | Time-frequency energy map of an audio signal |
| Spike map | make_spike-map.py | Geographic quantities as vertical spikes rising from each location |
| Stream plot | make_streamplot.py | Vector field as smooth flow lines with arrowheads |
| Streamgraph | make_streamgraph.py | Stacked area chart centred on the baseline for flowing time series |
| Sunburst | make_sunburst.py | Hierarchical part-to-whole as nested arcs radiating from a centre |
| Ternary | make_ternary.py | Three-component compositions inside an equilateral triangle |
| Timeline | make_timeline.py | Events or durations placed along a horizontal time axis |
| Tree | make_tree.py | Rooted hierarchical tree with labelled nodes and edges |
| Treemap | make_treemap.py | Hierarchical proportions as nested rectangles sized by value |
| UpSet plot | make_upset.py | Set intersections as a matrix of dots with bar charts for counts |
| Variwide | make_variwide.py | Bar chart where column width encodes a second variable |
| Venn diagram | make_venn.py | Overlap between two or three sets shown as intersecting circles |
| Voronoi | make_voronoi.py | Space partitioned into regions of nearest-neighbour influence |
| Waffle | make_waffle.py | Proportion as a grid of filled squares, one square per unit |
| Waterfall | make_waterfall.py | Cumulative change from a baseline as positive and negative segments |
| Wind rose | make_windrose.py | Wind direction frequency and speed on a polar histogram |
| Windbarb | make_windbarb.py | Meteorological wind speed and direction as barbed staffs on a map |
| Wireframe 3D | make_wireframe3d.py | Mathematical surface as a projected mesh of grid lines |
| Word cloud | make_wordcloud.py | Term frequency encoded as font size in a fitted text layout |

## Adding a new chart type

1. Copy the structure of any existing `make_*.py`.
2. Populate `DEMO_DATA` with realistic, domain-specific numbers. No placeholder names.
3. Run the script to confirm it renders: `python sprezzature-figures/scripts/make_<name>.py`.
4. Place the output in `web/img/figures/<name>.png` (or `.svg`).
5. Add a row to the catalogue table above.
6. Add trigger phrases to `TRIGGERS.md`.
7. Add a card to `web/figures.html` and `web/fr/figures.html`.

## Ralph Eyeball Loop integration

Every generator is a valid input to the loop. Pass the output file directly:

```sh
# Render, critique with Ollama vision, apply fixes, repeat until verdict.
python sprezzature-figures/scripts/ralph_eyeball_loop.py web/img/figures/waterfall.png --local
```

The loop reads the PNG, asks the vision model to critique layout, contrast,
hierarchy, spacing, accessibility, and color, then edits the source and
re-renders. It stops when the verdict clears or the iteration budget runs out.
