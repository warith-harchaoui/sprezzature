"""
test_figure_kits — the downloadable kit behind every gallery card.

What this checks
----------------
``web/tools/build_figure_kits.py`` turns each card on ``figures.html`` into a
zip a reader can run: two Python files, the data as CSV, and the interactive
SVG. The builder already verifies the interesting part at build time — it runs
every generator in a scratch directory with ``PYTHONPATH`` cleared, so a kit
that quietly depends on the checkout never gets zipped. These tests pin what
survives that: the shape of what shipped, and the two invariants that are easy
to break and expensive to notice.

* Every card on both language pages links a kit, and the zip exists.
* A kit holds exactly the promised files: two ``.py``, the CSV, the SVG, the
  pinned requirements, and both READMEs. No PNG.
* The SVG parses as XML. It is linked, not embedded, fonts, and the
  ampersands in that URL have to be escaped — a raw ``&`` makes the whole
  document unparseable and a browser renders nothing at all.
* ``requirements.txt`` pins with ``==``; "precise versions" was the point.
* The helper modules the bundle concatenates share no top-level name, which
  is the assumption that lets the merge be a plain join.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import ast
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

import sys  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "web" / "tools"))

from build_figure_kits import (  # noqa: E402
    BUNDLED_HELPERS,
    DEFAULT_FIGURES_REPO,
    GALLERY_PAGES,
    KITS_DIR,
    discover_cards,
    rows_to_csv,
    text_columns,
)

KITS: Path = REPO_ROOT / KITS_DIR

#: One kit, read once, for the per-file shape checks. Picked because it is
#: the plainest chart in the catalogue: if its kit is wrong, they all are.
SAMPLE: str = "bar"


def _require_kits() -> None:
    """Skip when the kits have not been built in this checkout."""
    if not KITS.is_dir() or not list(KITS.glob("*.zip")):
        pytest.skip("kits not built; run web/tools/build_figure_kits.py")


@pytest.mark.parametrize("page", GALLERY_PAGES)
def test_every_card_links_an_existing_kit(page: str) -> None:
    """No card advertises a download the site cannot serve."""
    _require_kits()
    html = (REPO_ROOT / page).read_text(encoding="utf-8")
    slugs = discover_cards(REPO_ROOT / page)
    assert slugs, f"{page}: no cards found"

    linked = set(re.findall(r'href="(?:\.\./)?kits/([a-z0-9_-]+)\.zip"', html))
    missing = [s for s in slugs if s not in linked]
    assert not missing, f"{page}: cards with no kit link: {missing[:5]}"

    absent = sorted(s for s in linked if not (KITS / f"{s}.zip").is_file())
    assert not absent, f"{page}: links to kits that do not exist: {absent[:5]}"


@pytest.mark.parametrize("page", GALLERY_PAGES)
def test_kit_links_carry_a_distinct_accessible_name(page: str) -> None:
    """
    Each chip names its own figure.

    A screen-reader user pulling up the link list gets 122 entries. "Download"
    repeated 122 times is a list of nothing.
    """
    _require_kits()
    html = (REPO_ROOT / page).read_text(encoding="utf-8")
    labels = re.findall(r'href="(?:\.\./)?kits/[a-z0-9_-]+\.zip"[^>]*aria-label="([^"]+)"', html)
    assert len(labels) == len(discover_cards(REPO_ROOT / page))
    assert len(set(labels)) == len(labels), "two kit links share an aria-label"


def test_kit_holds_exactly_what_it_promises() -> None:
    """The zip is the seven documented files, and no PNG."""
    _require_kits()
    archive = KITS / f"{SAMPLE}.zip"
    if not archive.is_file():
        pytest.skip(f"{SAMPLE} kit not built")
    with zipfile.ZipFile(archive) as zf:
        names = {Path(n).name for n in zf.namelist()}

    assert names == {
        f"make_{SAMPLE}.py",
        "sprezzature_svg.py",
        "data.csv",
        f"{SAMPLE}.svg",
        "requirements.txt",
        "README.md",
        "LISEZMOI.md",
    }
    assert not any(n.endswith(".png") for n in names), "kits ship vector only"
    assert sum(n.endswith(".py") for n in names) == 2, "a kit is two Python files"


def test_kit_svg_is_well_formed_and_links_its_fonts() -> None:
    """
    The figure parses, and its font URL is XML-escaped.

    An SVG is XML: one raw ``&`` in the Google Fonts query string and the
    browser abandons the document instead of degrading. This is the check that
    would have caught it before 122 blank figures shipped.
    """
    _require_kits()
    archive = KITS / f"{SAMPLE}.zip"
    if not archive.is_file():
        pytest.skip(f"{SAMPLE} kit not built")
    with zipfile.ZipFile(archive) as zf:
        svg = zf.read(f"{SAMPLE}/{SAMPLE}.svg").decode("utf-8")

    ElementTree.fromstring(svg)  # raises on malformed XML
    assert "fonts.googleapis.com" in svg, "fonts should be linked, not embedded"
    assert "@font-face" not in svg, "embedding is what made the repo's SVGs 430 KB"
    query = svg[svg.index("fonts.googleapis.com") : svg.index("');", svg.index("fonts.googleapis.com"))]
    assert "&amp;" in query and re.search(r"&(?!amp;)", query) is None, "unescaped & in the font URL"


def test_requirements_are_pinned_exactly() -> None:
    """Every requirement line pins a version; none floats."""
    _require_kits()
    for archive in sorted(KITS.glob("*.zip"))[:20]:
        with zipfile.ZipFile(archive) as zf:
            name = next(n for n in zf.namelist() if n.endswith("requirements.txt"))
            lines = [
                line.strip()
                for line in zf.read(name).decode("utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
        for line in lines:
            assert "==" in line, f"{archive.name}: '{line}' is not pinned"


def test_bundled_helpers_share_no_top_level_name() -> None:
    """
    The bundle concatenates helper modules, which only works while they
    define disjoint names. A future helper that reuses one would shadow it
    silently, so the invariant is asserted rather than assumed.
    """
    scripts = DEFAULT_FIGURES_REPO / "scripts"
    if not scripts.is_dir():
        pytest.skip("standalone sprezzature-figures repo not checked out")

    seen: dict[str, str] = {}
    clashes: list[str] = []
    for helper in BUNDLED_HELPERS:
        tree = ast.parse((scripts / f"{helper}.py").read_text(encoding="utf-8"))
        for node in tree.body:
            names: list[str] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            for name in names:
                if name in seen:
                    clashes.append(f"{name}: {seen[name]} and {helper}")
                seen[name] = helper
    assert not clashes, f"bundled helpers collide: {clashes}"


def test_csv_round_trips_nested_and_numeric_looking_values() -> None:
    """
    The CSV keeps what a chart needs back.

    Two shapes that plain CSV loses: a cell holding a list (a bullet chart's
    qualitative bands), and a label that looks like a number (a slope chart's
    "2023", which the generator calls ``.replace()`` on).
    """
    rows = [
        {"name": "New revenue", "bands": [150.0, 220.0], "period": "2023", "value": 268.0},
        {"name": "Trial signups", "bands": [900.0, 1350.0], "period": "2024", "value": 1180.0},
    ]
    assert text_columns(rows) == ("period",)

    csv_text = rows_to_csv(rows)
    assert csv_text.splitlines()[0] == "name,bands,period,value"
    assert '"[150.0, 220.0]"' in csv_text
