# Vector basemap library

Vendored world geometry so maps render **offline** and reproducibly: no fetch
at figure time. Used by the map figures in [`../../../docs/FIGURES.md`](../../../docs/FIGURES.md).

## Files

| File | What | Size |
|---|---|---|
| `countries-110m.json` | World countries, TopoJSON, 1:110m (overview scale) | ~108 KB |
| `countries-50m.json` | World countries, TopoJSON, 1:50m (detail scale) | ~740 KB |
| `rivers-50m.geojson` | Named river + lake centerlines, GeoJSON, 1:50m (situation-map named rivers) | ~460 KB |
| `svg/world-equal-earth.svg` | Drop-in **Equal-Earth** SVG basemap (equal-area, Antarctica omitted) | ~150 KB |
| `svg/world-110m.svg` | Drop-in SVG basemap, equirectangular | ~144 KB |

## Provenance

All geometry is **Natural Earth** (public domain, free for any use) via the
[topojson/world-atlas](https://github.com/topojson/world-atlas) pre-built
TopoJSON (itself derived from Natural Earth admin-0 countries). Natural Earth
ships at 1:110m / 1:50m / 1:10m; we vendor 110m (overview) and 50m (detail).
10m (~5 MB) and per-country splits are available from the same source when a
zoomed view needs them.

`rivers-50m.geojson` is Natural Earth's **50m rivers + lake centerlines** (same
public-domain source, via the [nvkelso/natural-earth-vector](https://github.com/nvkelso/natural-earth-vector)
GeoJSON), trimmed to named features with coordinates rounded to ~100 m and a few
transboundary names normalised to English (Al Furat / Fırat → Euphrates, Dicle →
Tigris). The situation-map generator reads it for named rivers.

## Curating more (build-time, optional)

Producing or trimming vector geodata is a GIS job, not a runtime one: do it
once, commit the result, and the figures just read it:

- **mapshaper** (`mapshaper in.geojson -simplify 10% -o out.topojson`) —
  simplify / split by field, the lightest tool.
- **QGIS** / **geopandas** — import Natural Earth, reproject, split admin-0 by
  country, dissolve, export GeoJSON/TopoJSON.

Runtime needs none of these, only the vendored files above.

## Using it

- **Vega choropleth** — embed the TopoJSON inline (`data.values` +
  `format: {type: topojson, feature: countries}`) and join a value table with a
  `lookup` transform. A local `data.url` reference does not load reliably under
  vl-convert, so the shipped `choropleth.vl.json` embeds the geometry; it is
  self-contained and renders from anywhere.
- **SVG maps** — the map generator decodes the TopoJSON, projects it offline
  (**Equal Earth**, equal-area), cuts polygons at the antimeridian, omits
  Antarctica, and draws the basemap plus overlays: bubbles (area-true √),
  pie / bar glyphs, a bivariate 3×3 choropleth, and great-circle connection
  arcs. Vega's layered `geoshape` + `lon/lat` points does not render reliably
  under vl-convert, so these take the SVG path, the honest Vega→SVG fallback.
  Synthetic flow (O-D) data must be labeled illustrative; a real connection map
  needs a real origin-destination matrix.
