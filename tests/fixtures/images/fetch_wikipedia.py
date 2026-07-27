#!/usr/bin/env python3
"""
fetch_wikipedia.py — populate ``tests/fixtures/images/wiki/`` with real
Wikipedia images that carry human-written alt text and captions.

The synthetic 64x64 Pillow patterns in ``tests/fixtures/images/*.png`` are
fine for structural checks (file exists, is a valid PNG, the decorative
short-circuit returns ``""``) but they have nothing to *describe*. The
eval suite for :mod:`alt_from_ollama` needs images with real semantic
content and a ground-truth reference written by a human reviewer.

This script downloads ~5 such images directly from ``upload.wikimedia.org``
(the content-addressed CDN — these URLs are persistent) and writes a
``truth.json`` manifest mapping each filename to its category, language,
alt text, caption, source article URL, and license.

Design rules (per the bundle's stdlib-only fetcher convention):

- Standard library only (``urllib``, ``json``, ``hashlib``, ``pathlib``).
  No ``requests``, no ``Pillow``, no third-party HTTP client.
- Idempotent: re-running with files already on disk and matching the
  expected SHA-256 is a no-op (skipped with an ``OK`` line).
- Hash-pinned: every entry carries an ``expected_sha256``. Mismatches
  abort that entry with a clear error; the rest of the batch continues.
- License-aware: each entry records the Commons licence (CC-BY-SA, PD)
  and the original author, copied verbatim into ``truth.json`` so
  downstream tooling can attribute correctly.

Run
---
``python3 tests/fixtures/images/fetch_wikipedia.py``

The exit code is ``0`` on full success and ``1`` when at least one entry
failed to download / verify. Either way, the script prints a one-line
summary of successes and failures.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ── Fixture catalogue ───────────────────────────────────────────────────────

# Each entry: ``(image_url, expected_sha256, slug, ext, kind, lang,
# alt_text, caption, article_url, author, license_note)``.
#
# - ``image_url`` is the direct upload.wikimedia.org CDN URL. These URLs
#   are content-addressed (the path includes the file's hash prefix) and
#   remain valid for years — Commons has never broken them in production.
# - ``expected_sha256`` is the hash of *the exact bytes* served by the CDN
#   at the time of authorship. If Commons re-encodes a derivative (rare),
#   re-run this script, inspect the new hash, and update the entry.
# - ``alt_text`` and ``caption`` are copied verbatim from the Wikipedia
#   *article* that uses the image (not from the Commons file page) — that
#   is the version a human reviewer wrote for the actual reading context.
# - ``article_url`` is the article the alt/caption was lifted from. It is
#   not used at runtime; it documents the provenance for future curators.

ENTRIES: list[dict] = [
    {
        # informative + en: portrait photo from a featured article. PD by
        # virtue of age (Marie Curie, c. 1920, photographer's life + 70 y
        # elapsed). Article source: https://en.wikipedia.org/wiki/Marie_Curie
        "image_url": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "c/c8/Marie_Curie_c._1920s.jpg/250px-Marie_Curie_c._1920s.jpg"
        ),
        "expected_sha256": (
            "f9dc314762fd4c5613361424934285eebdc064ab27dfd6c169b48dbc59214681"
        ),
        "slug": "marie-curie-portrait",
        "ext": "jpg",
        "kind": "informative",
        "lang": "en",
        "alt_text": "Black-and-white head shot of Curie",
        "caption": "Marie Sklodowska Curie, c. 1920",
        "article_url": "https://en.wikipedia.org/wiki/Marie_Curie",
        "author": "Unknown photographer (Henri Manuel studio attributed)",
        "license_note": "Public domain (author's life + 70 years elapsed)",
    },
    {
        # complex + en: a temperature-anomaly chart from the Climate
        # change featured article. CC-BY 4.0, NASA-derived rendition.
        # Article source: https://en.wikipedia.org/wiki/Climate_change
        "image_url": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "0/08/Global_Temperature_And_Forces_With_Fahrenheit.svg/"
            "330px-Global_Temperature_And_Forces_With_Fahrenheit.svg.png"
        ),
        "expected_sha256": (
            "bc3e4d824061b84cfedcaa14559617676cd7c5b934fabb4110d3cfb56d8c33a3"
        ),
        "slug": "climate-temperature-chart",
        "ext": "png",
        "kind": "complex",
        "lang": "en",
        "alt_text": (
            "Timeseries of global warming from 1880 to 2020 compared to "
            "simulated temperatures given only natural forcing. The first "
            "shows a positive trend since around 1950 and the second stays "
            "relatively flat."
        ),
        "caption": (
            "Earth's average surface air temperature has increased about "
            "1.5 C (2.7 F) since the Industrial Revolution. Natural forces "
            "cause some variability, but the persistent temperature "
            "increase shows the progressive influence of human activity."
        ),
        "article_url": "https://en.wikipedia.org/wiki/Climate_change",
        "author": "Efbrazil (Wikimedia Commons), data from NASA GISS",
        "license_note": "CC-BY-SA 4.0",
    },
    {
        # functional + en: the Wikipedia globe logo, used as a brand /
        # navigation element. Wikimedia trademark, but free to use for
        # the encyclopedia's own purposes; here we use it strictly to
        # exercise the ``--kind functional`` code path in tests.
        # Article source: https://en.wikipedia.org/wiki/Wikipedia
        "image_url": (
            "https://upload.wikimedia.org/wikipedia/en/thumb/"
            "8/80/Wikipedia-logo-v2.svg/250px-Wikipedia-logo-v2.svg.png"
        ),
        "expected_sha256": (
            "3fb41becf3b8f779cef08c3f3d01846b876643537055d5ec0c57a8fe37fbbea4"
        ),
        "slug": "wikipedia-logo",
        "ext": "png",
        "kind": "functional",
        "lang": "en",
        "alt_text": (
            "An incomplete sphere made of large, white jigsaw puzzle "
            "pieces. Each puzzle piece contains one glyph from a different "
            "writing system, with each glyph written in black."
        ),
        "caption": (
            "The logo of Wikipedia, a globe made out of puzzle pieces "
            "featuring glyphs from various writing systems"
        ),
        "article_url": "https://en.wikipedia.org/wiki/Wikipedia",
        "author": "Nohat (concept by Paullusmagnus); Wikimedia Foundation",
        "license_note": (
            "CC-BY-SA 3.0 / Wikimedia trademark — used under fair-use "
            "for accessibility test fixtures only"
        ),
    },
    {
        # informative + fr: same purpose as Marie Curie but in French,
        # so the eval suite can exercise the ``--lang fr`` path against
        # an image with French ground-truth alt text.
        # Article source: https://fr.wikipedia.org/wiki/Tour_Eiffel
        "image_url": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "a/a8/Tour_Eiffel_Wikimedia_Commons.jpg/"
            "330px-Tour_Eiffel_Wikimedia_Commons.jpg"
        ),
        "expected_sha256": (
            "f9635eb74597b0cf1b3ad8e3dc80008df780f4f6219f5ce2d834b9f7a1807366"
        ),
        "slug": "tour-eiffel",
        "ext": "jpg",
        "kind": "informative",
        "lang": "fr",
        "alt_text": (
            "Le Champ-de-Mars au premier plan, la tour Eiffel au "
            "deuxieme, puis le palais de Chaillot au troisieme plan."
        ),
        "caption": (
            "Le Champ-de-Mars au premier plan, la tour Eiffel au "
            "deuxieme, puis le palais de Chaillot au troisieme plan."
        ),
        "article_url": "https://fr.wikipedia.org/wiki/Tour_Eiffel",
        "author": "Benh LIEU SONG (Wikimedia Commons)",
        "license_note": "CC-BY-SA 3.0",
    },
    # decorative + en: we *intentionally* reuse the Pillow-synthetic
    # ``decorative-pattern.png`` from the parent directory. Decorative
    # images by W3C definition convey no information, so there is no
    # caption or alt-text to ground-truth against — and the test for
    # this case only asserts the empty-string short-circuit, which does
    # not need real content. The entry below lives in the manifest so
    # the eval test can iterate uniformly over all five categories.
    {
        "image_url": "",  # not downloaded — see comment above
        "expected_sha256": "",
        "slug": "decorative-pattern",
        "ext": "png",
        "kind": "decorative",
        "lang": "en",
        "alt_text": "",  # W3C decorative => empty alt by definition
        "caption": "Synthetic diagonal-stripe pattern (no semantic content).",
        "article_url": "",
        "author": "sprezzature-accessibility test fixtures (Pillow-generated)",
        "license_note": "Public domain (synthetic fixture)",
        "source_path": "tests/fixtures/images/decorative-pattern.png",
    },
]


# ── Download helpers ────────────────────────────────────────────────────────


# A polite-but-identifiable UA: Wikimedia's CDN rejects bare ``urllib``
# requests on some edge nodes. The contact URL lets ops reach the
# project if our traffic ever becomes a problem.
_USER_AGENT = (
    "sprezzature-accessibility-test-fixtures/1.0 "
    "(+https://github.com/warithharchaoui/sprezzature; stdlib urllib)"
)


def _sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def _download(url: str, dest: Path, expected_hash: str) -> tuple[bool, str]:
    """
    Download ``url`` to ``dest`` and verify its SHA-256.

    Returns ``(ok, message)`` where ``ok`` is ``True`` when the file on
    disk matches ``expected_hash`` (either because it already did or
    because the download succeeded). On failure, ``message`` describes
    the problem in human terms.
    """
    # Fast path: file already exists and matches → no network call.
    if dest.exists():
        actual = _sha256(dest.read_bytes())
        if actual == expected_hash:
            return True, f"OK (cached) {dest.name}"
        # Stale or corrupt cache — fall through and re-download.

    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"FAIL {dest.name}: download failed ({exc})"

    actual = _sha256(data)
    if actual != expected_hash:
        return False, (
            f"FAIL {dest.name}: SHA-256 mismatch — "
            f"expected {expected_hash[:12]}... got {actual[:12]}..."
        )

    dest.write_bytes(data)
    return True, f"OK (downloaded {len(data):,} bytes) {dest.name}"


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    """Download every entry, write the manifest, return shell exit code."""
    wiki_dir = Path(__file__).resolve().parent / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, dict] = {}
    successes = 0
    failures: list[str] = []

    for entry in ENTRIES:
        filename = f"{entry['slug']}.{entry['ext']}"
        dest = wiki_dir / filename

        # Decorative entry: nothing to download, just record in the manifest.
        if not entry["image_url"]:
            successes += 1
            print(f"OK (synthetic, no download) {filename}")
            manifest[filename] = {
                "kind": entry["kind"],
                "lang": entry["lang"],
                "alt_text": entry["alt_text"],
                "caption": entry["caption"],
                "article_url": entry["article_url"],
                "image_url": entry["image_url"],
                "sha256": entry["expected_sha256"],
                "author": entry["author"],
                "license_note": entry["license_note"],
                "source_path": entry.get("source_path", ""),
            }
            continue

        ok, msg = _download(entry["image_url"], dest, entry["expected_sha256"])
        print(msg)
        if ok:
            successes += 1
            manifest[filename] = {
                "kind": entry["kind"],
                "lang": entry["lang"],
                "alt_text": entry["alt_text"],
                "caption": entry["caption"],
                "article_url": entry["article_url"],
                "image_url": entry["image_url"],
                "sha256": entry["expected_sha256"],
                "author": entry["author"],
                "license_note": entry["license_note"],
            }
        else:
            failures.append(msg)

    # Always write whatever we have — partial manifests are useful for
    # debugging and the test module skips missing entries gracefully.
    manifest_path = wiki_dir / "truth.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nManifest: {manifest_path} ({len(manifest)} entries)")
    print(f"Summary: {successes} succeeded, {len(failures)} failed")
    for f in failures:
        print(f"  - {f}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
