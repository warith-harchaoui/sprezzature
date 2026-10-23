"""
A downloadable kit that reads a data file ships that file, and runs.

Each gallery card offers a zip: the generator, its data, the drawing engine in
one vendored file, and a page that opens the result. ``build_figure_kits.py``
has a ``--check`` mode that builds every one into a temp dir and reports — and
nothing ran it, so the gallery went on linking two zips that could not work.

``hexbin-map`` and ``spike-map`` draw on a real projection. They reach it
through ``_worldmap``, which was not in the bundle at all, so the kit died on
``cannot import name 'equal_earth'`` — inside a zip somebody had just
downloaded. Adding the helper moved the failure one step along: the projection
loads ``assets/geo/countries-110m.json`` by a path built *in the helper*, and
the builder scanned only the generator for asset reads, and re-rooted paths
only in the generator. So the kit shipped without the file and looked for it
one directory above itself.

Both halves are the same shape — the bundle was treated as code that cannot
touch the disk — and neither is visible from the repository, where every path
resolves and every import is on ``sys.path``.

Two halves, because they cost different things.

The **static** half asks whether the bundle re-roots the asset paths it
vendors. It is free, it runs everywhere, and it is the half that was wrong:
``Path(__file__).parent.parent / "assets"`` is right in the repository, where
the helpers live one level down in ``scripts/``, and wrong in a kit, where the
bundle is the root.

The **build** half runs the generator inside the staged kit, which is the only
way to see an ImportError or a missing file before a reader does. It needs
``sprezzature_figures`` importable: all 167 generators import
``sprezzature_figures.fonts`` at module level, so no kit can be built without
it. The hub's test lane does not install it — it is a large dependency for one
check — so this half skips there and names what to run instead. It is the step
that rebuilds the kits before they are uploaded, which is the moment it
matters.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER = REPO_ROOT / "web" / "tools" / "build_figure_kits.py"
FIGURES = REPO_ROOT.parent / "sprezzature-figures"


def _builder():
    """The kit builder, imported for its own asset-detection helpers."""
    if not FIGURES.is_dir():
        pytest.skip("no sprezzature-figures checkout; run scripts/fetch_siblings.sh")
    name = "_kit_builder"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BUILDER)
    assert spec is not None and spec.loader is not None, BUILDER
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _figures_that_read_an_asset() -> list[str]:
    """Slugs whose kit has a file to ship, asked of the builder itself.

    Computed rather than listed: a generator that starts reading an outline
    joins this set without anybody remembering to add it here, which is the
    only way a guard like this keeps up with a catalogue of 160.
    """
    builder = _builder()
    slugs: list[str] = []
    for generator in sorted((FIGURES / "scripts").glob("make_*.py")):
        source = generator.read_text(encoding="utf-8", errors="replace")
        # Its own reads, or a projection that reads for it. Not conditioned on
        # what the bundle currently carries: the first version asked "does the
        # bundle read an asset" first, so deleting the projection from the
        # bundle emptied that question, dropped both map figures out of the
        # checked set, and the guard passed on the exact breakage it was
        # written for. A guard must never narrow itself out of a defect.
        if builder.kit_assets(source) or _draws_a_map(source):
            slugs.append(generator.stem[len("make_") :])
    return slugs


def _draws_a_map(source: str) -> bool:
    """Whether a generator reaches the projection, and so the bundle's asset."""
    return "_worldmap" in source or "equal_earth" in source


def test_every_kit_that_needs_an_asset_builds_and_runs() -> None:
    """``--check`` stages each kit and runs its generator inside it."""
    if importlib.util.find_spec("sprezzature_figures") is None:
        pytest.skip(
            "sprezzature_figures is not installed, and every generator imports "
            "its fonts module, so no kit can be staged. Run "
            "`python3 web/tools/build_figure_kits.py --check` where the kits "
            "are rebuilt."
        )
    slugs = _figures_that_read_an_asset()
    assert slugs, (
        "no generator reads an asset, which cannot be right: the map figures "
        "load a country outline. Either the detection broke or they moved."
    )
    done = subprocess.run(
        [sys.executable, str(BUILDER), "--check", "--only", ",".join(slugs)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=900,
    )
    failures = [
        line.strip()
        for line in (done.stdout + done.stderr).splitlines()
        if line.strip().startswith("FAIL")
    ]
    assert done.returncode == 0 and not failures, (
        "kits that ship a data file do not build:\n" + "\n".join(failures[:6])
    )


def test_the_bundle_re_roots_the_paths_it_vendors() -> None:
    """No vendored helper looks for an asset above the kit it sits in.

    ``Path(__file__).parent.parent / "assets"`` is right in the repository,
    where the helpers live one level down in ``scripts/``, and wrong in a kit,
    where the bundle is the root. The rewrite exists; this says it reached the
    bundle and not only the generator.
    """
    bundle = _builder().bundle_source(FIGURES)
    assert 'parent.parent\n    / "assets"' not in bundle, (
        "the bundled engine still builds an assets path from its parent's "
        "parent, which in a kit is the directory above the kit"
    )
    assert "resolve().parent.parent" not in bundle.replace(
        "resolve().parent.parent.parent", ""
    ) or '"assets"' not in bundle, (
        "an un-rewritten assets path survives in the bundle"
    )
