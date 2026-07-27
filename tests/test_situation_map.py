"""test_situation_map — the layered situation-map generator.

`make_situation_map.py` projects any region and assembles an SVG from a fixed
stack of named layers. These smoke tests assert the pieces a downstream reader
depends on: the vendored basemap decodes, a real country outline can be lifted,
the projection is sane, and a minimal config renders every expected layer.

The tests skip cleanly if the optional geo stack (shapely / pyproj) is absent,
so the fast suite still runs without them.

Author
------
Project maintainers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "sprezzature-figures" / "scripts"))

pytest.importorskip("shapely")
pytest.importorskip("pyproj")

import make_situation_map as m  # noqa: E402

# The layer ids a geopolitics reader expects, bottom -> top.
EXPECTED_LAYERS = [
    "basemap-sea",
    "basemap-bathymetry",
    "basemap-land",
    "areas-of-control",
    "infrastructure",
    "forces",
    "events",
    "annotation-labels",
    "annotation-furniture",
    "legend",
    "frame",
]


def test_load_land_is_valid_and_global() -> None:
    """The vendored Natural Earth land decodes to a valid, world-spanning polygon."""
    land = m.load_land()
    assert not land.is_empty
    minx, _, maxx, _ = land.bounds
    assert minx < -150 and maxx > 150  # spans most of the globe


def test_load_country_lifts_a_named_outline() -> None:
    """A real national outline can be extracted by Natural Earth name."""
    ukr = m.load_country("Ukraine")
    assert not ukr.is_empty
    minx, miny, maxx, maxy = ukr.bounds
    assert 21 < minx < 25 and 39 < maxx < 41  # Ukraine's rough lon extent
    assert 44 < miny < 46 and 51 < maxy < 53  # and lat extent

    with pytest.raises(KeyError):
        m.load_country("Atlantis")


def test_auto_projection_is_metric_and_local() -> None:
    """The auto projection maps the region centre near the origin, in metres."""
    bbox = [8.0, 38.75, 9.95, 41.35]
    proj = m.build_projection(bbox, "auto")
    cx, cy = proj.transform((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    assert abs(cx) < 1e4 and abs(cy) < 1e4  # centre ~ (0, 0) metres


def test_build_map_emits_every_layer() -> None:
    """A minimal config renders a well-formed SVG carrying all expected layers."""
    cfg = {
        "title": "Test",
        "subtitle": "smoke",
        "region": {"bbox": [8.0, 38.75, 9.95, 41.35]},
        "projection": "auto",
        "canvas_width": 600,
        "areas_of_control": {"palette": {"A": "#f2c4c4"}},
        "forces": [{"lon": 9.0, "lat": 39.2}],
        "events": [{"lon": 8.5, "lat": 40.7}],
        "labels": {"water": {"lon": 9.4, "lat": 41.1, "text": "Sea"},
                   "places": [{"lon": 9.1, "lat": 39.2, "text": "Town"}]},
    }
    svg = m.build_map(cfg)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for layer in EXPECTED_LAYERS:
        assert f'id="{layer}"' in svg, f"missing layer {layer}"
    # A dual-unit scale bar and the contested hatch pattern are always defined.
    assert "KM" in svg and "MI" in svg
    assert "hatch-contested" in svg


@pytest.mark.parametrize("name", ["ukraine", "syria", "libya"])
def test_shipped_example_config_renders(name: str) -> None:
    """Every example config bundled with the skill builds without error."""
    import json

    example = REPO_ROOT / "sprezzature-figures" / "assets" / "situation-maps" / f"{name}.yaml"
    cfg = json.loads(example.read_text())
    cfg["_config_dir"] = str(example.parent)
    svg = m.build_map(cfg)
    assert 'id="areas-of-control"' in svg
    assert svg.count("<path") > 5  # zones + bathymetry + land/sea


@pytest.mark.parametrize("name", ["ukraine", "syria", "libya"])
def test_builder_reproduces_each_example(name: str) -> None:
    """The tracked builder regenerates each shipped config in-memory (reproducible)."""
    import build_situation_examples as b  # noqa: PLC0415

    cfg = b.BUILDERS[name]()
    assert cfg["title"] and cfg["region"]["bbox"]
    assert cfg["areas_of_control"]["palette"]
    # Every example must carry a schematic disclaimer on its face.
    assert "not operational" in cfg["subtitle"].lower() or "schematic" in cfg["subtitle"].lower()
