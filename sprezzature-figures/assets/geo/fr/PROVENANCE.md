# French département geometry — vendored, offline

`departements-simplifiee.geojson` — the **96 metropolitan départements** as WGS84
(lon/lat) polygons, **simplified** for light weight (~560 KB). From
[france-geojson](https://github.com/gregoiredavid/france-geojson) by Grégoire
David, itself derived from **IGN Admin Express** (open licence) with
OpenStreetMap. Properties: `code` (INSEE département code) + `nom`.

The French-election small-multiples in
[`../../../../docs/FIGURES.md`](../../../../docs/FIGURES.md) read this file and
project it **offline** with a **Lambert conformal conic** projection (standard
parallels 44° / 49°, centred on 2.5°E / 46.5°N) — the conventional projection for
metropolitan France — so no fetch happens at figure time.

Overseas départements (DOM) are not in this simplified file; a metropolitan-only
map is the usual editorial choice. For DOM insets or higher detail, the same
`france-geojson` repository ships fuller versions.
