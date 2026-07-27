#!/usr/bin/env python3
"""Streamlined builder for every shipped situation-map example — one source of truth.

Author: Warith Harchaoui

Generates all example configs for ``make_situation_map.py`` consistently, so the
shipped gallery is uniform and regenerable in one command:

- ``ukraine`` — schematic government / occupied / contested split of the real
  outline, along an approximate contact line per open-source geopolitical
  literature (e.g. ISW), illustrative mid-war snapshot.
- ``syria``   — schematic four-actor split (government / opposition / SDF /
  Turkish-backed) per open-source literature, illustrative ~2018 snapshot.
- ``libya``   — schematic loyalist / rebel / contested split of the First Libyan
  Civil War, per open-source literature, illustrative ~spring 2011 snapshot.

Every non-neutral map is coarse by design and says so on its face. The schematic
sprezzature lines and control polygons live here in the open — sourced in the comments
(Wikipedia / ISW / DeepStateMap) — so an expert can read exactly how each map was
drawn and refine it, rather than trusting an opaque asset. It emits the tracked
``assets/situation-maps/<name>.{yaml,svg,png}`` plus the gallery raster.

    python sprezzature-figures/scripts/build_situation_examples.py            # all three
    python sprezzature-figures/scripts/build_situation_examples.py ukraine    # just one
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sprezzature-figures" / "scripts"))
from make_situation_map import load_country, load_land  # noqa: E402
from shapely.geometry import (  # noqa: E402
    LineString,
    Polygon,
    box,
    mapping,
)
from shapely.ops import unary_union  # noqa: E402

SHIP = REPO / "sprezzature-figures" / "assets" / "situation-maps"


def _feat(name: str, geom: Any) -> dict[str, Any]:
    return {"type": "Feature", "properties": {"actor": name}, "geometry": mapping(geom)}


def _partition_by_claims(country: Any, base_name: str,
                         claims: list[tuple[str, list]]) -> list[dict[str, Any]]:
    """Greedily assign land to the first actor that claims it; remainder -> base.

    Parameters
    ----------
    country : shapely geometry
        The national outline to divide.
    base_name : str
        Actor that holds everything unclaimed (e.g. the government).
    claims : list of (name, polygon-coords)
        Ordered actor claims; earlier claims win overlaps.

    Returns
    -------
    list of GeoJSON features, base actor first.
    """
    assigned = None
    features: list[dict[str, Any]] = []
    zones: list[tuple[str, Any]] = []
    for name, coords in claims:
        poly = Polygon(coords)
        piece = country.intersection(poly)
        if assigned is not None:
            piece = piece.difference(assigned)
        if not piece.is_empty:
            zones.append((name, piece))
            assigned = piece if assigned is None else unary_union([assigned, piece])
    base = country if assigned is None else country.difference(assigned)
    features.append(_feat(base_name, base))
    features.extend(_feat(n, g) for n, g in zones)
    return features


def _contested_band(line_pts: list, country: Any, km: float) -> Any:
    """Return a buffered band along a contact line, clipped to the country."""
    deg = km / 111.0  # crude deg-per-km; fine for a schematic hatch band
    band = LineString(line_pts).buffer(deg)
    return country.intersection(band)


# --------------------------------------------------------------------------- #
# Sardinia — neutral synthetic                                                 #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Ukraine — schematic, per open-source literature                              #
# --------------------------------------------------------------------------- #

# Approximate 2024 contact line north->south, hugging the reported flashpoints
# (Kupiansk, Bakhmut, Avdiivka, Vuhledar, Robotyne) down to the Dnipro / Kherson.
FRONT = [(37.55, 49.75), (38.00, 49.00), (38.05, 48.60), (37.75, 48.15),
         (37.20, 47.90), (36.40, 47.60), (35.85, 47.44), (34.70, 47.05),
         (33.00, 46.72), (32.55, 46.50)]
ENVELOPE = FRONT + [(32.55, 43.8), (41.5, 43.8), (41.5, 50.6), (37.55, 49.75)]
CRIMEA_BBOX = [32.4, 44.28, 36.75, 46.25]
# Shallow NE Kharkiv-oblast salient reached in the May 2024 cross-border push.
VOVCHANSK_BBOX = [36.8, 50.15, 37.7, 50.62]


def build_ukraine() -> dict[str, Any]:
    ukr = load_country("Ukraine")
    occupied = unary_union([
        ukr.intersection(Polygon(ENVELOPE)),
        load_land().intersection(box(*CRIMEA_BBOX)),      # Crimea (occupied 2014)
        ukr.intersection(box(*VOVCHANSK_BBOX)),           # Vovchansk salient (2024)
    ])
    government = ukr.difference(occupied)
    contested = _contested_band(FRONT, ukr, km=22)
    government = government.difference(contested)
    occupied = occupied.difference(contested)
    # Slightly deeper, more saturated pastels so the three classes separate
    # cleanly at fill_opacity ~0.78 (Ukrainian cool blue / occupied warm red /
    # contested ochre) while staying inside the paper-and-ink house palette.
    palette = {
        "Ukrainian government control": "#bcd4ec",
        "Russian-occupied (approx.)": "#e0a89e",
        "Contested (approx. sprezzature)": "#e4cf9c",
    }
    features = [_feat("Ukrainian government control", government),
                _feat("Russian-occupied (approx.)", occupied),
                _feat("Contested (approx. sprezzature)", contested)]
    b = ukr.bounds
    bbox = [b[0] - 0.6, b[1] - 1.2, b[2] + 0.6, b[3] + 0.6]
    return {
        "title": "Ukraine — Areas of Control",
        "subtitle": ("Schematic, approximate open-source positions circa 2024 · "
                     "roughly 18% of the country occupied · illustrative, not operational intelligence"),
        "region": {"bbox": bbox}, "projection": "auto",
        "canvas_width": 1320, "padding": 30,
        "basemap": {"sea_color": "#a8bccb", "land_color": "#f6f1df",
                    "coast_color": "#7993a6",
                    "bathymetry": {"rings": 7, "color": "#ffffff", "opacity": 0.4}},
        "frontiers": {"focus": "Ukraine"},
        "rivers": {"always_label": ["Dnieper"], "color": "#5d86a6",
                   "label_color": "#3f6a8c"},
        # The approximate contact line, drawn as an emphasised sprezzature (north->south).
        "sprezzature": {"line": [[p[0], p[1]] for p in FRONT],
                  "color": "#3a4149",
                  "legend_label": "Approx. contact line"},
        "legend_footer": "As of ~2024 · schematic, open-source geography",
        "areas_of_control": {"category_field": "actor", "palette": palette,
                             "contested": ["Contested (approx. sprezzature)"],
                             "fill_opacity": 0.78, "hatch_color": "#b34a3a",
                             "source": {"type": "FeatureCollection", "features": features}},
        # Reported 2023-24 flashpoints (lon, lat).
        "events": [{"lon": 38.0008, "lat": 48.5947, "color": "#c0392b", "r": 5},  # Bakhmut
                   {"lon": 37.7450, "lat": 48.1453, "color": "#c0392b", "r": 5},  # Avdiivka
                   {"lon": 37.1828, "lat": 48.2828, "color": "#c0392b", "r": 5},  # Pokrovsk
                   {"lon": 37.2483, "lat": 47.7792, "color": "#c0392b", "r": 5},  # Vuhledar
                   {"lon": 35.8261, "lat": 47.4431, "color": "#c0392b", "r": 5},  # Robotyne
                   {"lon": 36.9428, "lat": 50.2878, "color": "#c0392b", "r": 5}],  # Vovchansk
        "marker_legend": [{"color": "#c0392b", "label": "Contested flashpoint (approx.)"}],
        "labels": {
            "waters": [
                {"lon": 31.3, "lat": 43.15, "text": "Black Sea", "size": 19,
                 "tracking": 7},
                {"lon": 37.0, "lat": 46.35, "text": "Sea of Azov", "size": 11,
                 "tracking": 2.4},
            ],
            "places": [
                {"lon": 30.5233, "lat": 50.4500, "text": "Kyiv", "size": 16,
                 "capital": True},
                {"lon": 36.2311, "lat": 49.9925, "text": "Kharkiv"},
                {"lon": 30.7434, "lat": 46.4857, "text": "Odesa", "anchor": "below"},
                {"lon": 35.0400, "lat": 48.4675, "text": "Dnipro"},
                {"lon": 37.98, "lat": 47.88, "text": "Donetsk", "anchor": "end"},  # clear of Avdiivka marker
                {"lon": 39.3031, "lat": 48.5678, "text": "Luhansk"},
                {"lon": 37.5494, "lat": 47.0958, "text": "Mariupol", "anchor": "above"},
                {"lon": 32.6250, "lat": 46.6425, "text": "Kherson", "anchor": "above"},
                {"lon": 35.1175, "lat": 47.8500, "text": "Zaporizhzhia", "anchor": "end"},
                {"lon": 33.5225, "lat": 44.6050, "text": "Sevastopol", "anchor": "above"},
                {"lon": 24.0322, "lat": 49.8425, "text": "Lviv"},
                {"lon": 31.9950, "lat": 46.9750, "text": "Mykolaiv", "size": 11, "anchor": "end"},
                {"lon": 28.4833, "lat": 49.2333, "text": "Vinnytsia", "size": 11},
                {"lon": 34.5514, "lat": 49.5894, "text": "Poltava", "size": 11},
                {"lon": 34.8028, "lat": 50.9119, "text": "Sumy", "size": 11},
                {"lon": 31.2947, "lat": 51.4939, "text": "Chernihiv", "size": 11},
                {"lon": 37.30, "lat": 48.98, "text": "Kramatorsk", "size": 11, "anchor": "above"},
                {"lon": 34.90, "lat": 46.70, "text": "Melitopol", "size": 11, "anchor": "above"},
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Syria — schematic four-actor, per open-source literature (~2018)             #
# --------------------------------------------------------------------------- #

def build_syria() -> dict[str, Any]:
    syr = load_country("Syria")
    # Ordered claims (earlier wins overlaps), per open-source reporting ~2018:
    #  - Turkish-backed: the northern border strip (Afrin + Euphrates Shield),
    #    west of the Euphrates, above Aleppo (which stayed government).
    #  - SDF / AANES: north-east of the Euphrates. Its south-west edge follows the
    #    river so Deir ez-Zor city and al-Bukamal (west/south bank) stay government.
    #  - Opposition / HTS: the Idlib pocket in the north-west.
    claims = [
        ("Turkish-backed", [(36.35, 37.45), (38.15, 37.45), (38.15, 36.35),
                            (36.35, 36.35)]),
        ("SDF / AANES (approx.)", [(38.15, 37.45), (42.5, 37.45), (42.5, 34.35),
                                  (41.15, 34.75), (40.5, 35.1), (40.0, 35.5),
                                  (39.1, 35.75), (38.15, 36.5)]),
        ("Opposition (Idlib)", [(35.6, 36.4), (37.0, 36.4), (37.2, 35.5),
                               (35.9, 35.45)]),
    ]
    features = _partition_by_claims(syr, "Syrian government", claims)
    palette = {
        "Syrian government": "#e3b0aa",
        "Turkish-backed": "#bcd0e6",
        "SDF / AANES (approx.)": "#f2d99a",
        "Opposition (Idlib)": "#cdddb0",
    }
    # Order palette to match legend priority government-first.
    b = syr.bounds
    bbox = [b[0] - 0.6, b[1] - 0.6, b[2] + 0.6, b[3] + 0.6]
    return {
        "title": "Syria — Areas of Control",
        "subtitle": ("Schematic / approximate, per open-source geopolitical literature · "
                     "illustrative ~2018 snapshot, not an operational assessment"),
        "region": {"bbox": bbox}, "projection": "auto", "canvas_width": 1180,
        "basemap": {"sea_color": "#9fb2c0", "land_color": "#f4efdd",
                    "bathymetry": {"rings": 6, "color": "#ffffff", "opacity": 0.45}},
        "frontiers": {"focus": "Syria"},
        "rivers": {"always_label": ["Euphrates", "Tigris"]},
        "areas_of_control": {"category_field": "actor", "palette": palette,
                             "source": {"type": "FeatureCollection", "features": features}},
        "events": [{"lon": 37.13, "lat": 36.20, "color": "#c0392b", "r": 5},   # Aleppo
                   {"lon": 40.14, "lat": 35.34, "color": "#c0392b", "r": 5},   # Deir ez-Zor
                   {"lon": 38.99, "lat": 35.95, "color": "#c0392b", "r": 5}],  # Raqqa
        "marker_legend": [{"color": "#c0392b", "label": "Contested city (approx.)"}],
        "labels": {
            "water": {"lon": 35.55, "lat": 35.95, "text": "Mediterranean Sea", "size": 12,
                      "tracking": 2},
            "places": [
                {"lon": 36.292, "lat": 33.513, "text": "Damascus", "size": 15},
                # Flashpoint cities: the red event dot is the marker (dot:false),
                # name offset with `clear` sized to that dot.
                {"lon": 37.134, "lat": 36.202, "text": "Aleppo", "dot": False,
                 "clear": 5.5, "anchor": "above"},
                {"lon": 36.723, "lat": 34.733, "text": "Homs"},
                {"lon": 36.750, "lat": 35.132, "text": "Hama"},
                {"lon": 35.791, "lat": 35.531, "text": "Latakia"},
                {"lon": 35.886, "lat": 34.889, "text": "Tartus", "size": 11},
                {"lon": 36.634, "lat": 35.931, "text": "Idlib", "anchor": "end"},
                {"lon": 39.017, "lat": 35.950, "text": "Raqqa", "dot": False,
                 "clear": 5.5, "anchor": "below"},
                {"lon": 40.140, "lat": 35.336, "text": "Deir ez-Zor", "dot": False,
                 "clear": 5.5, "anchor": "below"},
                {"lon": 40.750, "lat": 36.500, "text": "Al-Hasakah", "size": 11},
                {"lon": 41.231, "lat": 37.053, "text": "Qamishli", "size": 11, "anchor": "end"},
                {"lon": 38.354, "lat": 36.891, "text": "Kobani", "size": 11, "anchor": "above"},
                {"lon": 36.869, "lat": 36.512, "text": "Afrin", "size": 11, "anchor": "end"},
                {"lon": 37.516, "lat": 36.371, "text": "Al-Bab", "size": 11},
                {"lon": 36.106, "lat": 32.618, "text": "Deraa", "size": 11},
                {"lon": 38.284, "lat": 34.560, "text": "Palmyra", "size": 11},
                {"lon": 40.919, "lat": 34.453, "text": "Al-Bukamal", "size": 11, "anchor": "end"},
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Libya — schematic First Libyan Civil War, ~spring 2011                        #
# --------------------------------------------------------------------------- #

# Oil-crescent sprezzature, Ajdabiya -> Brega -> Ras Lanuf -> Bin Jawad -> toward Sirte.
LIBYA_FRONT = [(20.20, 30.72), (19.58, 30.41), (18.54, 30.50), (17.70, 30.90),
               (16.90, 31.05)]


def build_libya() -> dict[str, Any]:
    lby = load_country("Libya")
    # East/west divide ran around the Gulf of Sidra / Brega (~19 E): rebels (NTC)
    # held Cyrenaica in the east; Gaddafi held Tripolitania (west) + Fezzan (south).
    rebel_east = lby.intersection(Polygon([(18.9, 33.6), (25.8, 33.6),
                                           (25.8, 18.8), (18.9, 18.8)]))
    # Besieged rebel enclaves inside the loyalist west.
    misrata = load_land().intersection(box(14.85, 32.20, 15.40, 32.58))
    nafusa = lby.intersection(box(10.30, 31.45, 12.85, 32.20))  # Berber mountains
    rebel = unary_union([rebel_east, misrata, nafusa])
    gaddafi = lby.difference(rebel)
    contested = _contested_band(LIBYA_FRONT, lby, km=28)
    gaddafi = gaddafi.difference(contested)
    rebel = rebel.difference(contested)
    palette = {
        "Gaddafi loyalists": "#c9d8a6",
        "Rebels / NTC": "#e3b0aa",
        "Contested (oil crescent)": "#e6d5b8",
    }
    features = [_feat("Gaddafi loyalists", gaddafi),
                _feat("Rebels / NTC", rebel),
                _feat("Contested (oil crescent)", contested)]
    b = lby.bounds
    bbox = [b[0] - 0.6, b[1] - 0.6, b[2] + 0.6, b[3] + 1.0]
    return {
        "title": "Libya — Areas of Control",
        "subtitle": ("Schematic · approximate, First Libyan Civil War ~spring 2011 "
                     "(after UNSCR 1973) · open-source reporting, not operational intelligence"),
        "region": {"bbox": bbox}, "projection": "auto", "canvas_width": 1180,
        "basemap": {"sea_color": "#9fb2c0", "land_color": "#f4efdd",
                    "bathymetry": {"rings": 6, "color": "#ffffff", "opacity": 0.45}},
        "frontiers": {"focus": "Libya"},
        "areas_of_control": {"category_field": "actor", "palette": palette,
                             "contested": ["Contested (oil crescent)"],
                             "source": {"type": "FeatureCollection", "features": features}},
        "events": [{"lon": 19.576, "lat": 30.408, "color": "#c0392b", "r": 5},   # Brega
                   {"lon": 18.542, "lat": 30.500, "color": "#c0392b", "r": 5},   # Ras Lanuf
                   {"lon": 15.092, "lat": 32.378, "color": "#c0392b", "r": 5}],  # Misrata siege
        "marker_legend": [{"color": "#c0392b", "label": "Contested / besieged (approx.)"}],
        "labels": {
            "water": {"lon": 18.4, "lat": 33.5, "text": "Mediterranean Sea", "size": 15,
                      "tracking": 4},
            "places": [
                {"lon": 13.191, "lat": 32.887, "text": "Tripoli", "size": 15, "anchor": "above"},
                {"lon": 20.068, "lat": 32.119, "text": "Benghazi", "size": 14},
                {"lon": 15.092, "lat": 32.378, "text": "Misrata", "dot": False,
                 "clear": 5.5, "anchor": "above"},
                {"lon": 16.588, "lat": 31.205, "text": "Sirte"},
                {"lon": 14.429, "lat": 27.038, "text": "Sabha"},
                {"lon": 23.964, "lat": 32.084, "text": "Tobruk", "anchor": "end"},
                {"lon": 20.227, "lat": 30.755, "text": "Ajdabiya", "size": 11},
                {"lon": 21.755, "lat": 32.763, "text": "Al Bayda", "size": 11, "anchor": "end"},
                {"lon": 22.640, "lat": 32.767, "text": "Derna", "size": 11, "anchor": "above"},
                {"lon": 19.576, "lat": 30.408, "text": "Brega", "dot": False,
                 "clear": 5.5, "anchor": "below", "size": 11},
                {"lon": 18.542, "lat": 30.500, "text": "Ras Lanuf", "dot": False,
                 "clear": 5.5, "anchor": "end", "size": 11},
                {"lon": 12.728, "lat": 32.752, "text": "Zawiya", "size": 11, "anchor": "end"},
                {"lon": 12.253, "lat": 31.930, "text": "Zintan", "size": 11, "anchor": "end"},
                {"lon": 10.980, "lat": 31.869, "text": "Nalut", "size": 11, "anchor": "end"},
                {"lon": 23.313, "lat": 24.179, "text": "Al Kufra", "size": 11, "anchor": "end"},
                {"lon": 10.180, "lat": 24.964, "text": "Ghat", "size": 11},
            ],
        },
    }


BUILDERS = {"ukraine": build_ukraine, "syria": build_syria, "libya": build_libya}
GENERATOR = REPO / "sprezzature-figures" / "scripts" / "make_situation_map.py"
GALLERY = REPO / "sprezzature-figures" / "assets" / "figures-gallery"
PNG_WIDTH = 1300  # export raster width, px


def _render_png(svg: Path, png: Path) -> bool:
    """Rasterise ``svg`` to ``png`` with rsvg-convert if available; return success."""
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        print(f"  (skipped PNG for {png.name}: rsvg-convert not found)")
        return False
    subprocess.run([rsvg, "-w", str(PNG_WIDTH), str(svg), "-o", str(png)], check=True)
    return True


# Every named layer the generator emits, bottom -> top.
ALL_LAYERS = (
    "basemap-sea", "basemap-bathymetry", "basemap-land", "frontiers",
    "areas-of-control", "coastline", "infrastructure", "rivers", "front-line",
    "forces", "events", "annotation-labels", "annotation-furniture", "legend",
    "frame",
)
# The physical basemap + furniture kept as a constant backdrop under each view,
# so a single thematic layer is read *in geographic context*, not in a void.
# Frontiers, coastline and rivers are base geography, so they ride the backdrop.
_BACKDROP = {"basemap-sea", "basemap-bathymetry", "basemap-land", "frontiers",
             "coastline", "rivers", "annotation-furniture", "frame"}
# The a-posteriori decompositions a geopolitics analyst actually reads a plate in.
LAYER_VIEWS = {
    "basemap": _BACKDROP,
    "areas-of-control": _BACKDROP | {"areas-of-control", "front-line", "legend"},
    "markers": _BACKDROP | {"forces", "events", "legend"},
    "labels": _BACKDROP | {"annotation-labels"},
}


def _export_layers(name: str, svg_text: str) -> None:
    """Emit a-posteriori per-layer SVG+PNG views by hiding the other layers.

    The generator writes each semantic layer as ``<g id="...">``; a view keeps a
    chosen subset visible and sets ``display:none`` on the rest — a decomposition
    of the finished plate into the strata an analyst toggles between.
    """
    out_dir = SHIP / "layers"
    out_dir.mkdir(parents=True, exist_ok=True)
    for view, keep in LAYER_VIEWS.items():
        text = svg_text
        for layer in ALL_LAYERS:
            if layer not in keep:
                text = text.replace(f'<g id="{layer}">',
                                    f'<g id="{layer}" style="display:none">')
        svg_out = out_dir / f"{name}.a-posteriori.{view}.svg"
        png_out = out_dir / f"{name}.a-posteriori.{view}.png"
        svg_out.write_text(text)
        _render_png(svg_out, png_out)
    print(f"  layers: {name}.a-posteriori.{{{', '.join(LAYER_VIEWS)}}}.svg/.png")


def main(argv: list[str]) -> None:
    names = argv or list(BUILDERS)
    SHIP.mkdir(parents=True, exist_ok=True)
    GALLERY.mkdir(parents=True, exist_ok=True)
    for name in names:
        cfg = BUILDERS[name]()
        yaml_path = SHIP / f"{name}.yaml"
        yaml_path.write_text(json.dumps(cfg, indent=2))
        # SVG next to the config, then a PNG export beside it and in the gallery.
        svg_path = SHIP / f"{name}.svg"
        subprocess.run([sys.executable, str(GENERATOR), "--config", str(yaml_path),
                        "--out", str(svg_path)], check=True, stdout=subprocess.DEVNULL)
        _render_png(svg_path, SHIP / f"{name}.png")
        _render_png(svg_path, GALLERY / f"situation-{name}.png")
        print(f"wrote {name}.yaml / .svg / .png  ({yaml_path.stat().st_size // 1024} KB config)")
        # A-posteriori layer decomposition — the final stage, once the plate is set.
        _export_layers(name, svg_path.read_text())


if __name__ == "__main__":
    main(sys.argv[1:])
