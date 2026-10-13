#!/usr/bin/env python3
"""
build_map_kits
==============

One downloadable, runnable kit per card in the map gallery, the way
``build_figure_kits.py`` does it for ``figures.html``.

A reader who likes a plate on ``maps.html`` currently gets a picture. The kit
gives them the thing that made it: the configuration as the generator reads
it, a short script that renders it, and the SVG it produces, in a zip they can
open, change and re-run.

Where this differs from the figure kits, and why
------------------------------------------------

A figure kit bundles its own drawing engine and runs on the standard library.
A map kit cannot and should not. A plate needs a projection (``pyproj``),
geometry (``shapely``), a vendored Natural Earth atlas and a real elevation
pyramid — tens of megabytes of public-domain data that would dwarf the zip and
go stale the moment the atlas is updated. So a map kit declares one dependency
and says so on its first page:

    pip install sprezzature-maps

That is the honest trade, and it is also the better one for this material: the
interesting file in a figure kit is the generator, and the interesting file in
a map kit is the **configuration** — the claim lines, the categories, the
confidence tiers. That is the file a reader wants to argue with, and it is
already published next to every plate.

What a kit holds
----------------

``<slug>.yaml`` / ``data.csv``
    The input, exactly as the published plate was built from. For a situation
    plate that is the full config, polygons and all; for a choropleth it is
    one value per country. **This is the file to edit.**
``make_<slug>.py``
    Twenty lines that read the input and call the library. Short on purpose:
    the generator lives in the installed package, not in the kit, so there is
    nothing here to fall out of date with it.
``<slug>.png``
    The plate as published, so a reader can see what they should get before
    they install anything. A raster and not the SVG on purpose: a shaded
    plate *is* a raster under its vectors, and the published Himalaya SVG is
    2.4 MB of which 2.3 MB is relief. Shipping it would have made a 1.8 MB
    "small kit"; the 256-colour PNG is a tenth of that and shows the same
    picture.
``index.html``
    A page that opens the plate. It asks for ``<slug>.svg`` first and falls
    back to the PNG, so it shows the preview before the script has run and
    the live, interactive document -- tooltips, layer panel -- after.
``README.md``, ``LICENSE``, ``requirements.txt``
    What it is, how to run it, and under what terms.

Usage
-----
::

    python web/tools/build_map_kits.py                   # every gallery card
    python web/tools/build_map_kits.py --only situation-sudan
    python web/tools/build_map_kits.py --check           # verify, write nothing

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

#: ``web/tools/build_map_kits.py`` -> the site checkout.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent

#: The sibling checkout that owns the generators and the published configs.
#: Sibling layout is the documented arrangement in both repositories' READMEs.
MAPS_REPO: Path = Path.home() / "sprezzature-maps"

WEB: Path = REPO_ROOT / "web"
KITS_EN: Path = WEB / "kits"
KITS_FR: Path = WEB / "kits" / "fr"
GALLERY_PAGES: tuple[tuple[Path, bool], ...] = (
    (WEB / "maps.html", False),
    (WEB / "fr" / "maps.html", True),
)

#: The minimum release that carries every generator these kits call.
PACKAGE_PIN: str = "sprezzature-maps>=0.14.0"

#: One gallery card, and the slug it points at. Shared with the figure kits
#: in shape but not in path: these cards point into ``img/maps/``.
_CARD = re.compile(r"<figure\b.*?</figure>", re.DOTALL)
_CARD_SLUG = re.compile(r'data-src="(?:\.\./)?img/maps/([a-z0-9-]+)\.svg"')
_EXISTING_LINK = re.compile(
    r'\s*(?:<div class="mt-2">)?<a href="(?:\.\./)?kits/(?:fr/)?[a-z0-9_-]+\.zip".*?</a>(?:</div>)?',
    re.DOTALL,
)

#: Byte-for-byte the figure kits' chip, so the two galleries do not drift
#: into two different download buttons.
_KIT_LINK: str = (
    '<div class="mt-2"><a href="{prefix}{slug}.zip" download '
    'class="inline-flex items-center min-h-11 rounded-lg border '
    "border-neutral-200 px-3 "
    "text-xs text-neutral-600 hover:border-brand-blue hover:text-brand-linktext "
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue "
    'dark:border-neutral-700 dark:text-neutral-400" '
    'aria-label="{aria}">{label}</a></div>'
)


def card_titles(page: Path) -> dict[str, str]:
    """Return ``slug -> the card's own name``, for the download label."""
    html = page.read_text(encoding="utf-8")
    titles: dict[str, str] = {}
    for block in _CARD.finditer(html):
        slug = _CARD_SLUG.search(block.group(0))
        name = re.search(r'<span class="font-medium">([^<]+)</span>', block.group(0))
        if slug and name:
            titles[slug.group(1)] = name.group(1).strip()
    return titles


def discover_cards(page: Path) -> list[str]:
    """Return the slugs the gallery shows, in page order and without repeats."""
    seen: list[str] = []
    for match in _CARD_SLUG.finditer(page.read_text(encoding="utf-8")):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def situation_region(slug: str) -> str | None:
    """Return the builder key behind ``situation-<region>``, or None."""
    return slug[len("situation-") :] if slug.startswith("situation-") else None


def choropleth_variant(slug: str) -> str | None:
    """Return the variant behind ``choropleth-<variant>``, or None."""
    return slug[len("choropleth-") :] if slug.startswith("choropleth-") else None


def _demo_rows() -> list[dict[str, object]]:
    """The choropleth demo values, read from the package rather than copied."""
    sys.path.insert(0, str(MAPS_REPO / "scripts"))
    from make_choropleth import DEMO_DATA  # noqa: PLC0415

    return list(DEMO_DATA)


def _diverging_rows() -> list[dict[str, object]]:
    """The same values recentred, exactly as the published diverging plate."""
    sys.path.insert(0, str(MAPS_REPO / "scripts"))
    from build_choropleth_examples import _diverging_rows as rows  # noqa: PLC0415

    return list(rows())


def rows_to_csv(rows: Sequence[dict[str, object]]) -> str:
    """Return ``id,value`` CSV. Two columns, because the format is the point."""
    out = ["id,value"]
    out.extend(f"{r['id']},{r['value']}" for r in rows)
    return "\n".join(out) + "\n"


SITUATION_SCRIPT = '''#!/usr/bin/env python3
"""Rebuild the {title} plate from its own configuration.

    pip install sprezzature-maps
    python3 {script}

The interesting file is not this one: it is `{slug}.yaml`, which carries the
region, the categories, every claim polygon and the confidence each one is
asserted at. Edit that, re-run this, and the plate changes.
"""

from pathlib import Path

import yaml

from sprezzature_maps import make_situation_map

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "{slug}.yaml"
OUT = HERE / "{slug}.svg"


def main() -> None:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    # The generator resolves any relative path in the config against this,
    # so a config that points at a local GeoJSON keeps working from the kit.
    cfg["_config_dir"] = str(HERE)
    make_situation_map(config=cfg, out=OUT)
    print(f"wrote {{OUT.name}}  ({{OUT.stat().st_size // 1024}} KB)")


if __name__ == "__main__":
    main()
'''

CHOROPLETH_SCRIPT = '''#!/usr/bin/env python3
"""Rebuild the {title} map from `data.csv`.

    pip install sprezzature-maps
    python3 {script}

`data.csv` is two columns: `id` is an ISO-3166-1 numeric country code, `value`
is the number the colour encodes. Swap in your own and re-run.
"""

import csv
from pathlib import Path

from sprezzature_maps import make_choropleth

HERE = Path(__file__).resolve().parent
DATA = HERE / "data.csv"
OUT = HERE / "{slug}.svg"


def rows() -> list[dict[str, object]]:
    with DATA.open(encoding="utf-8") as fh:
        return [
            {{"id": row["id"], "value": float(row["value"])}}
            for row in csv.DictReader(fh)
            if row.get("value") not in (None, "")
        ]


def main() -> None:
    make_choropleth(
        data=rows(),
        out=OUT,
        title={title!r},
{extra}    )
    print(f"wrote {{OUT.name}}  ({{OUT.stat().st_size // 1024}} KB)")


if __name__ == "__main__":
    main()
'''

#: The calls the three published choropleths really make, so a kit rebuilds
#: the plate on the card rather than a near-miss of it.
CHOROPLETH_EXTRA: dict[str, str] = {
    "sequential": "",
    "diverging": "        diverging=True,\n",
    "large": "        width=2000,\n        height=1128,\n        simplify=0.1,\n",
}

INDEX_HTML = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; padding: 2rem 1rem; font: 16px/1.5 system-ui, sans-serif;
         background: #fafaf8; color: #2b2926; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #0b0b0c; color: #e8e6e3; }}
  }}
  main {{ max-width: 72rem; margin: 0 auto; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .25rem; }}
  p {{ margin: .25rem 0 1.5rem; opacity: .75; }}
  object, img {{ display: block; width: 100%; height: auto; border-radius: 12px;
                 background: #fff; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p>{blurb}</p>
  <object data="{slug}.svg" type="image/svg+xml" aria-label="{title}">
    <img src="{slug}.png" alt="{title}">
  </object>
</main>
</body>
</html>
"""


def readme(slug: str, title: str, kind: str, *, french: bool) -> str:
    """Return the kit's front page, in one language."""
    script = f"make_{slug.replace('-', '_')}.py"
    if kind == "situation":
        input_file, input_role_en, input_role_fr = (
            f"{slug}.yaml",
            "The configuration: region, categories, every claim polygon, and the "
            "confidence each one is asserted at. **This is the file to edit.**",
            "La configuration : région, catégories, chaque polygone de revendication "
            "et la confiance avec laquelle il est affirmé. **C'est le fichier à "
            "modifier.**",
        )
    else:
        input_file, input_role_en, input_role_fr = (
            "data.csv",
            "Two columns: `id` is an ISO-3166-1 numeric country code, `value` is the "
            "number the colour encodes. **This is the file to edit.**",
            "Deux colonnes : `id` est un code pays numérique ISO-3166-1, `value` est "
            "le nombre que la couleur encode. **C'est le fichier à modifier.**",
        )

    if french:
        return f"""# {title} — plateau autonome

Le plateau «&nbsp;{title}&nbsp;» de la galerie Sprezzature, avec de quoi le
reconstruire et le changer.

## Ce qu'il y a dedans

| Fichier | Rôle |
|---|---|
| `{input_file}` | {input_role_fr} |
| `{script}` | Vingt lignes : lire l'entrée, appeler la bibliothèque. |
| `{slug}.png` | Le plateau tel que publié, pour voir ce qu'on doit obtenir avant d'installer quoi que ce soit. |
| `index.html` | Une page qui ouvre le plateau : le SVG une fois le script lancé, l'aperçu PNG avant. |
| `requirements.txt` | La seule dépendance. |
| `LICENSE` | Le texte de licence. À garder en cas de redistribution. |

## Le faire tourner

```sh
pip install sprezzature-maps
python3 {script}
```

Contrairement aux kits de figures du même site, celui-ci **ne contient pas**
son moteur de dessin. Une carte a besoin d'une projection, d'une géométrie et
d'un atlas Natural Earth vendu avec : des dizaines de mégaoctets qui
écraseraient l'archive et vieilliraient dès la mise à jour de l'atlas. Le
paquet les porte ; le kit porte ce qui vous appartient.

## Regarder le résultat

```sh
open {slug}.svg        # macOS
xdg-open {slug}.svg    # Linux
start {slug}.svg       # Windows
```

Le SVG s'ouvre comme une page : les infobulles et le panneau de couches sont
écrits dans le fichier lui-même. Dans une page web, utilisez
`<object data="{slug}.svg"></object>`, pas `<img>` : une balise `img` fige le
document et éteint l'interactivité.

## Ce que le plateau affirme

Un plateau de ce genre est un argument, pas un relevé. Les exemples livrés
sont **schématiques et le disent sur leur propre face**. Si vous publiez une
version modifiée, dites d'où vient l'appréciation : ce n'est pas un avis de
non-responsabilité à coller en bas, cela fait partie du sens de la carte.

Documentation : <https://github.com/warith-harchaoui/sprezzature-maps>
"""

    return f"""# {title} — standalone plate

The “{title}” plate from the Sprezzature gallery, with everything needed to
rebuild and change it.

## What is in here

| File | Role |
|---|---|
| `{input_file}` | {input_role_en} |
| `{script}` | Twenty lines: read the input, call the library. |
| `{slug}.png` | The plate as published, so you can see what you should get before installing anything. |
| `index.html` | A page that opens the plate: the SVG once the script has run, the PNG preview before. |
| `requirements.txt` | The one dependency. |
| `LICENSE` | The licence text. Keep it if you redistribute. |

## Run it

```sh
pip install sprezzature-maps
python3 {script}
```

Unlike the figure kits on the same site, this one **does not bundle** its
drawing engine. A map needs a projection, geometry and a vendored Natural
Earth atlas: tens of megabytes that would dwarf the archive and go stale the
moment the atlas is updated. The package carries those; the kit carries the
part that is yours.

## Look at the result

```sh
open {slug}.svg        # macOS
xdg-open {slug}.svg    # Linux
start {slug}.svg       # Windows
```

The SVG opens like a page: the hover tooltips and the layer panel are written
into the file itself. To put it in a web page use
`<object data="{slug}.svg"></object>`, not `<img>` — an `img` tag freezes the
document and switches the interactivity off.

## What the plate asserts

A plate of this kind is an argument, not a survey. The bundled examples are
**schematic and say so on their own face**. If you publish a changed version,
say where the underlying assessment came from: that is not a disclaimer to
append, it is part of the map's meaning.

Documentation: <https://github.com/warith-harchaoui/sprezzature-maps>
"""


def kit_files(
    slug: str, title: str, *, french: bool
) -> tuple[dict[str, str], dict[str, bytes]]:
    """Return ``(text files, binary files)`` for one kit, or raise if an input is missing."""
    script_name = f"make_{slug.replace('-', '_')}.py"
    png = WEB / "img" / "maps" / f"{slug}.png"
    if not png.is_file():
        raise FileNotFoundError(f"{slug}: no published raster at {png}")

    files: dict[str, str] = {
        "LICENSE": (MAPS_REPO / "LICENSE").read_text(encoding="utf-8"),
        "requirements.txt": f"{PACKAGE_PIN}\n",
    }
    binaries: dict[str, bytes] = {f"{slug}.png": png.read_bytes()}

    region = situation_region(slug)
    variant = choropleth_variant(slug)
    if region is not None:
        config = MAPS_REPO / "assets" / "situation-maps" / f"{region}.yaml"
        if not config.is_file():
            raise FileNotFoundError(
                f"{slug}: no published config at {config}. Run "
                "`python scripts/build_situation_examples.py` in the maps repo first."
            )
        # Round-trip through json so a kit never ships a config the loader
        # would choke on; these are written as JSON, which is valid YAML.
        json.loads(config.read_text(encoding="utf-8"))
        files[f"{slug}.yaml"] = config.read_text(encoding="utf-8")
        files[script_name] = SITUATION_SCRIPT.format(slug=slug, title=title, script=script_name)
        kind = "situation"
    elif variant is not None:
        rows = _diverging_rows() if variant == "diverging" else _demo_rows()
        files["data.csv"] = rows_to_csv(rows)
        files[script_name] = CHOROPLETH_SCRIPT.format(
            slug=slug, title=title, script=script_name,
            extra=CHOROPLETH_EXTRA.get(variant, ""),
        )
        kind = "choropleth"
    else:
        raise ValueError(f"{slug}: not a situation or choropleth card")

    blurb = (
        f"Rebuilt by <code>{script_name}</code>. Edit the input next to it and run again."
        if not french
        else f"Reconstruit par <code>{script_name}</code>. Modifiez l'entrée à côté et relancez."
    )
    files["index.html"] = INDEX_HTML.format(
        slug=slug, title=title, blurb=blurb, lang="fr" if french else "en"
    )
    files["README.md"] = readme(slug, title, kind, french=french)
    return files, binaries


def write_kit(
    slug: str, files: dict[str, str], binaries: dict[str, bytes], out_dir: Path
) -> int:
    """Write ``<out_dir>/<slug>.zip`` and return its size in bytes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{slug}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / slug
        root.mkdir()
        for name, text in files.items():
            (root / name).write_text(text, encoding="utf-8")
        for name, blob in binaries.items():
            (root / name).write_bytes(blob)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted([*files, *binaries]):
                zf.write(root / name, f"{slug}/{name}")
    return archive.stat().st_size


def link_gallery(page: Path, sizes: dict[str, int], *, french: bool) -> int:
    """Put a kit download link on every map card of one gallery page."""
    prefix = "../kits/fr/" if french else "kits/"
    html = page.read_text(encoding="utf-8")
    linked = 0

    def rewrite(match: re.Match[str]) -> str:
        nonlocal linked
        block = _EXISTING_LINK.sub("", match.group(0))
        slug_match = _CARD_SLUG.search(block)
        if slug_match is None or slug_match.group(1) not in sizes:
            return block
        slug = slug_match.group(1)
        name_match = re.search(r'<span class="font-medium">([^<]+)</span>', block)
        name = name_match.group(1) if name_match else slug
        kb = round(sizes[slug] / 1024)
        config = "YAML" if slug.startswith("situation-") else "CSV"
        if french:
            label = f"↓ Kit {config} + Python + SVG ({kb} Ko)"
            aria = f"Télécharger le kit de la carte {name} : {config}, Python et SVG, {kb} Ko"
        else:
            label = f"↓ {config} + Python + SVG kit ({kb} KB)"
            aria = f"Download the {name} kit: {config}, Python and SVG, {kb} KB"
        chip = _KIT_LINK.format(prefix=prefix, slug=slug, aria=aria, label=label)
        linked += 1
        return block.replace("</figcaption>", f"\n            {chip}</figcaption>", 1)

    page.write_text(_CARD.sub(rewrite, html), encoding="utf-8")
    return linked


def build_all(slugs: Sequence[str], *, check: bool) -> int:
    """Build every kit and link both galleries. Returns a process exit code."""
    problems: list[str] = []
    sizes: dict[str, int] = {}
    titles_en = card_titles(GALLERY_PAGES[0][0])
    titles_fr = card_titles(GALLERY_PAGES[1][0])

    for slug in slugs:
        try:
            en, blobs = kit_files(slug, titles_en.get(slug, slug), french=False)
            fr, _ = kit_files(slug, titles_fr.get(slug, slug), french=True)
        except (FileNotFoundError, ValueError) as exc:
            problems.append(str(exc))
            continue
        if check:
            sizes[slug] = 1
            continue
        sizes[slug] = write_kit(slug, en, blobs, KITS_EN)
        write_kit(slug, fr, blobs, KITS_FR)
        print(f"  {slug:28} {sizes[slug] // 1024:5} KB")

    if problems:
        for p in problems:
            print(f"  !! {p}", file=sys.stderr)
        return 1
    if check:
        print(f"{len(sizes)} kit(s) would build, inputs all present.")
        return 0

    for page, french in GALLERY_PAGES:
        n = link_gallery(page, sizes, french=french)
        print(f"  linked {n} card(s) on {page.relative_to(REPO_ROOT)}")
    print(f"wrote {len(sizes)} kits to {KITS_EN.relative_to(REPO_ROOT)} (+ /fr)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_map_kits", description=__doc__)
    parser.add_argument("--only", help="Comma-separated slugs, while iterating.")
    parser.add_argument("--check", action="store_true", help="Verify inputs, write nothing.")
    args = parser.parse_args(argv)

    if not MAPS_REPO.is_dir():
        print(
            f"the sibling checkout {MAPS_REPO} is missing; these kits ship its "
            "published configs, so clone it beside this repository first.",
            file=sys.stderr,
        )
        return 1
    if shutil.which("python3") is None:  # pragma: no cover - sanity only
        print("no python3 on PATH", file=sys.stderr)
        return 1

    slugs = discover_cards(GALLERY_PAGES[0][0])
    if args.only:
        wanted = [s.strip() for s in args.only.split(",") if s.strip()]
        unknown = [s for s in wanted if s not in slugs]
        if unknown:
            print(f"unknown card(s) {unknown}; the gallery has {slugs}", file=sys.stderr)
            return 1
        slugs = wanted
    return build_all(slugs, check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
