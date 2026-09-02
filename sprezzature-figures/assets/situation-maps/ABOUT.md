# Situation maps — layered areas-of-control plates for any region

`scripts/make_situation_map.py` reverse-engineers the plate structure that
geopolitics data desks use into a **parameterized generator**: from one YAML
config it projects *any* region of the world and emits a single SVG built as a
stack of named layers, the same decomposition an analyst reads a situation map
in (bottom → top paint order):

| # | Layer id | Carries |
|---|----------|---------|
| 1 | `basemap-sea` | sea fill |
| 2 | `basemap-bathymetry` | depth-contour halo radiating from the coast |
| 3 | `basemap-land` | land fill |
| 4 | `frontiers` | real international borders (dashed hairline) + neighbour-country labels |
| 5 | `areas-of-control` | territory zones — pastel fill under a **white casing**; contested = hatch |
| 6 | `infrastructure` | roads / highways / airports as hairlines |
| 7 | `rivers` | river centerlines (water blue) with italic names for the major ones |
| 8 | `forces` | unit / actor positions (point markers) |
| 9 | `events` | incidents (ceasefire points, clashes, strikes) |
| 10 | `annotation-labels` | letter-spaced place + water labels, white-haloed |
| 11 | `annotation-furniture` | title block, north arrow, **dual-unit (km + mi) scale bar** |
| 12 | `legend` | floating legend panel with swatches |
| 13 | `frame` | rounded-rectangle panel mask, floated on a light page with a soft shadow |

Craft signatures reproduced: an equal-angle **local projection** (Lambert
Conformal Conic auto-centred on the region), a **classed pastel palette**,
**white boundary casing** between adjacent zones, **real international frontiers**
with neighbour labels, **named rivers** in water-blue italics, **bathymetry** in
the sea, **drop-shadowed** panel + markers, **letter-spaced haloed** labels, and
a **dual-unit scale bar**, reachable for any part of the world, not one example.

Basemap geometry is the vendored, offline Natural Earth land polygon
(`assets/geo/countries-50m.json`); `load_country("<name>")` extracts a real
national outline you can partition into zones. The caller supplies the thematic
layers (zones, forces, events, labels).

## Run

```bash
pip install -r sprezzature-figures/scripts/requirements-dataviz.txt   # shapely + pyproj
python sprezzature-figures/scripts/make_situation_map.py \
    --config sprezzature-figures/assets/situation-maps/ukraine.yaml \
    --out /tmp/ukraine.svg --render
```

### Bundled examples

Each example ships as three artifacts: `<name>.yaml` (the config), `<name>.svg`
(the plate), and `<name>.png` (a raster export), plus a gallery copy at
`../figures-gallery/situation-<name>.png`.

| Example | What it shows |
|---------|---------------|
| `ukraine` | **Schematic** government / occupied / contested split of the real outline along an approximate 2024 contact line, per open-source reporting (Wikipedia / ISW / DeepStateMap). |

Every example is **coarse, illustrative, and labelled as such on the plate**:
approximate open-source geography, not operational intelligence. They exist to
prove the generator reaches professional quality on real, well-documented
geography for any region and any period.

### Regenerate

All examples (config + SVG + PNG + gallery raster, plus the a-posteriori layer
exports below) come from one tracked builder; the schematic front lines and
control polygons live in the open there, sourced in the comments, so anyone can
read how each map was drawn and refine it:

```bash
python sprezzature-figures/scripts/build_situation_examples.py           # all
python sprezzature-figures/scripts/build_situation_examples.py ukraine    # just one
```

### A-posteriori layer exports

As a final stage the builder decomposes each finished plate into the strata a
geopolitics analyst toggles between, in `layers/`, one SVG **and** PNG per view,
the basemap kept as a constant backdrop under each:

| File (`layers/<name>.a-posteriori.<view>.{svg,png}`) | Shows |
|------|-------|
| `…basemap` | coastline, bathymetry, scale bar, north arrow — geographic context only |
| `…areas-of-control` | the control zones + contested band + legend |
| `…markers` | the point markers (forces / flashpoints) + legend |
| `…labels` | the place-name gazetteer (city dots + names) |

## Config schema (abridged)

```yaml
title: "…"
subtitle: "…"                      # keep illustrative maps honest on their face
region: {bbox: [west, south, east, north]}   # degrees
projection: auto                   # or a European Petroleum Survey Group (EPSG) code, e.g. EPSG:3857
canvas_width: 1000
basemap:
  sea_color: "#9fb2c0"
  land_color: "#f7f3e3"
  bathymetry: {rings: 7, color: "#ffffff", opacity: 0.5}   # step_km optional
areas_of_control:
  category_field: actor
  palette: {ActorA: "#f2c4c4", …}
  contested: [ContestedZone]       # rendered with a diagonal hatch
  source: {type: FeatureCollection, features: [ … ]}   # inline, or a path to a .geojson
forces:  [{lon, lat, color, r}]    # point markers
events:  [{lon, lat, color, r}]
infrastructure: {roads: <geojson path/inline>, airports: [{lon, lat}]}
labels:
  water:  {lon, lat, text, size}
  places: [{lon, lat, text, size, tracking}]
frame: {margin: 22, page_color: "#eef1f3", radius: 8}
```

## Honest scope

This is thematic **visualization**, not a geographic information system (GIS) and
not an intelligence product. Front lines / control boundaries are only as good as
the geometry you feed it; label approximate or synthetic maps as such. Spatial
analysis (spatial joins, buffers you intend to be metrically exact, coordinate
reference system transforms beyond the built-in projection) belongs in
geopandas / Quantum GIS (QGIS).
