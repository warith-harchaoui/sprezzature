"""
The structural claims ``web/`` makes about itself, checked.

Everything here was verified by hand during the 2026-10-15 release pass and
then written down in a note -- which is exactly how a site rots. A link that
stops resolving, an ``hreflang`` pair that stops being reciprocal, a page that
joins the tree and never joins the sitemap: none of these break a build, none
raise, and all of them are invisible until a reader or a crawler finds them.
A note saying "verified on the 15th" is not a guard; it is an expiry date.

So these are the one-off checks turned into a suite. They are deliberately
structural -- they ask whether the site is internally consistent, not whether
it is beautiful or correct in its prose. Accessibility rules live in
``sprezzature-accessibility``'s own linter; contrast lives in
``sprezzature-colors``; this file owns the plumbing those two assume.

Every check runs off the files on disk, with no network and no browser, so it
costs milliseconds and can sit in the default run.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"
BASE_URL = "https://sprezzature.ai"

#: ``head.html`` is a ``<head>``-only include fragment, not a page. It has no
#: ``<html>`` element, no canonical and no place in the sitemap, and treating
#: it as a page is the mistake every one of these checks would otherwise make.
NOT_A_PAGE = {"head.html"}


def _pages(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.html") if p.name not in NOT_A_PAGE)


EN_PAGES = _pages(WEB)
FR_PAGES = _pages(WEB / "fr")
ALL_PAGES = EN_PAGES + FR_PAGES


def _url_for(page: Path) -> str:
    """The canonical URL a page should claim, matching the published form.

    ``index.html`` is served at its directory, so the site writes
    ``https://sprezzature.ai/`` and ``https://sprezzature.ai/fr/`` rather than
    spelling the filename out; anything else keeps its name.
    """
    relative = page.relative_to(WEB).as_posix()
    if relative == "index.html":
        return f"{BASE_URL}/"
    if relative == "fr/index.html":
        return f"{BASE_URL}/fr/"
    return f"{BASE_URL}/{relative}"


def test_there_are_pages_to_check_at_all() -> None:
    """The guard on every other test in this file.

    A glob that matches nothing turns an entire suite green, and a site-wide
    check that silently examines zero pages is worse than no check: it reads
    as proof. If ``web/`` moves, this fails first and by name.
    """
    assert len(EN_PAGES) >= 15, f"only {len(EN_PAGES)} English pages found in {WEB}"
    assert len(FR_PAGES) >= 15, (
        f"only {len(FR_PAGES)} French pages found in {WEB / 'fr'}"
    )


# --------------------------------------------------------------------------
# The sitemap and the page tree must be the same set
# --------------------------------------------------------------------------


def _sitemap_urls() -> set[str]:
    root = ET.parse(WEB / "sitemap.xml").getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {element.text or "" for element in root.findall(".//sm:loc", namespace)}


def test_the_sitemap_lists_every_page_and_only_pages() -> None:
    """Both directions, because they fail differently.

    A page missing from the sitemap is invisible to crawlers. A sitemap entry
    with no page behind it is a 404 served to every crawler that trusts the
    file -- and the sitemap is precisely the document that asks to be trusted.
    """
    listed = _sitemap_urls()
    expected = {_url_for(page) for page in ALL_PAGES}
    assert listed - expected == set(), (
        f"sitemap lists URLs with no page: {sorted(listed - expected)}"
    )
    assert expected - listed == set(), (
        f"pages missing from the sitemap: {sorted(expected - listed)}"
    )


# --------------------------------------------------------------------------
# Every local reference resolves to a file that exists
# --------------------------------------------------------------------------

_REFERENCE_RE = re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']+)["']""")

#: ``?v=`` cache-busting suffixes and JS template literals (``${...}``) are
#: not paths and must be stripped or skipped before anything is resolved --
#: the 2026-10-15 pass found both and they are why this is not a one-liner.
_TEMPLATE_RE = re.compile(r"\$\{[^}]*\}")


def _local_references(page: Path) -> list[str]:
    out = []
    for raw in _REFERENCE_RE.findall(page.read_text(encoding="utf-8")):
        if _TEMPLATE_RE.search(raw):
            continue
        parsed = urlparse(raw)
        if parsed.scheme or parsed.netloc:  # external, or mailto:, or tel:
            continue
        if not parsed.path or raw.startswith("#"):  # same-page anchor
            continue
        out.append(unquote(parsed.path))
    return out


#: Reference prefixes the repository deliberately does not track: the 177
#: downloadable figure kits and the films, both built by tools in
#: ``web/tools/`` and uploaded with the rest of the site. They exist on the
#: machine that deploys and never in a fresh checkout, so a check that
#: demanded them would pass locally and fail on CI -- which is exactly what
#: the first version of this file did.
#:
#: Listed here rather than inferred, and held to what git actually tracks by
#: the test below, so the exemption cannot quietly grow to cover a link that
#: is simply broken.
BUILT_NOT_COMMITTED = ("kits/", "video/")


def test_the_untracked_prefixes_really_are_untracked() -> None:
    """The exemption above is only legitimate while git agrees with it.

    If one of these directories starts being committed, its files are in a
    checkout and their references should be checked like any other. And if a
    new prefix is ever added to the tuple to silence a failure, this is where
    that shows up.
    """
    import subprocess

    for prefix in BUILT_NOT_COMMITTED:
        tracked = subprocess.run(
            ["git", "ls-files", "--", str(WEB / prefix)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert not tracked.stdout.strip(), (
            f"web/{prefix} is tracked by git now; remove it from "
            "BUILT_NOT_COMMITTED so its references are checked again"
        )


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: p.relative_to(WEB).as_posix())
def test_every_local_reference_resolves(page: Path) -> None:
    """A broken local link or a missing asset is a 404 the build never sees.

    References into :data:`BUILT_NOT_COMMITTED` are exempt because those
    files are generated and uploaded rather than committed; everything else
    must be on disk here and now.
    """
    missing = []
    for path in _local_references(page):
        target = (
            (WEB / path.lstrip("/")) if path.startswith("/") else (page.parent / path)
        )
        # Matched on the *resolved* path, not the written one: a French page
        # reaches the films as `../video/...`, which no prefix on the raw
        # string would catch.
        resolved = target.resolve()
        if any(
            resolved.is_relative_to((WEB / prefix).resolve())
            for prefix in BUILT_NOT_COMMITTED
        ):
            continue
        # A directory reference is served by its index.html.
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            missing.append(path)
    assert not missing, f"{page.relative_to(WEB)}: unresolved → {sorted(set(missing))}"


# --------------------------------------------------------------------------
# Canonical and hreflang
# --------------------------------------------------------------------------

_CANONICAL_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"')
_ALTERNATE_RE = re.compile(
    r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"'
)


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: p.relative_to(WEB).as_posix())
def test_each_page_declares_the_canonical_url_it_is_served_at(page: Path) -> None:
    """A canonical pointing anywhere but at the page itself asks search
    engines to drop it in favour of another document."""
    found = _CANONICAL_RE.findall(page.read_text(encoding="utf-8"))
    assert len(found) == 1, (
        f"{page.relative_to(WEB)}: {len(found)} canonical links, expected 1"
    )
    assert found[0] == _url_for(page)


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: p.relative_to(WEB).as_posix())
def test_the_translation_pair_points_both_ways(page: Path) -> None:
    """``hreflang`` is only honoured when it is reciprocal.

    A page naming its translation while the translation does not name it back
    is ignored outright by search engines -- so a one-way declaration is not
    half-working, it is not working.
    """
    text = page.read_text(encoding="utf-8")
    alternates = dict(_ALTERNATE_RE.findall(text))
    assert {"en", "fr"} <= set(alternates), (
        f"{page.relative_to(WEB)}: hreflang has {sorted(alternates)}, needs en and fr"
    )

    relative = page.relative_to(WEB).as_posix()
    is_french = relative.startswith("fr/")
    twin_relative = relative[3:] if is_french else f"fr/{relative}"
    twin = WEB / twin_relative
    assert twin.is_file(), f"{relative}: no translation at {twin_relative}"

    assert alternates["fr" if is_french else "en"] == _url_for(page)
    assert alternates["en" if is_french else "fr"] == _url_for(twin)

    # The twin points back at this page under *this page's* language, which is
    # the opposite of the key used just above. Getting that inverted is an easy
    # mistake and a quiet one: it fails on every page at once, which reads like
    # a broken site rather than a broken check.
    back = dict(_ALTERNATE_RE.findall(twin.read_text(encoding="utf-8")))
    own_language = "fr" if is_french else "en"
    assert back.get(own_language) == _url_for(page), (
        f"{twin_relative} does not point back at {relative} under hreflang={own_language}"
    )


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: p.relative_to(WEB).as_posix())
def test_each_page_declares_the_language_of_its_tree(page: Path) -> None:
    """A French page declaring ``lang="en"`` is read aloud in the wrong accent
    by every screen reader, and indexed as the wrong language."""
    expected = "fr" if page.relative_to(WEB).as_posix().startswith("fr/") else "en"
    match = re.search(
        r"<html[^>]*\blang=\"([^\"]+)\"", page.read_text(encoding="utf-8")
    )
    assert match, f"{page.relative_to(WEB)}: <html> has no lang attribute"
    assert match.group(1) == expected


# --------------------------------------------------------------------------
# The gallery's figures
# --------------------------------------------------------------------------

_IMG_RE = re.compile(r"<img\b[^>]*>")


@pytest.mark.parametrize(
    "gallery", ["figures.html", "fr/figures.html", "maps.html", "fr/maps.html"]
)
def test_every_gallery_image_carries_an_alt_text(gallery: str) -> None:
    """``alt`` is the whole accessible content of an image, and a chart with
    none is simply absent for anyone not looking at it."""
    page = WEB / gallery
    images = _IMG_RE.findall(page.read_text(encoding="utf-8"))
    assert images, f"{gallery}: no <img> found at all -- has the gallery moved?"
    silent = [img for img in images if 'alt="' not in img]
    assert not silent, (
        f"{gallery}: {len(silent)} image(s) with no alt, first: {silent[0][:120]}"
    )


def test_both_galleries_show_the_same_number_of_figures() -> None:
    """The French gallery is a translation, not a subset. A figure added to one
    and not the other is the drift this catches, and nothing else would."""
    counts = {
        name: len(_IMG_RE.findall((WEB / name).read_text(encoding="utf-8")))
        for name in ("figures.html", "fr/figures.html")
    }
    assert counts["figures.html"] == counts["fr/figures.html"], counts


# --------------------------------------------------------------------------
# The SVGs the pages embed
# --------------------------------------------------------------------------


def _referenced_svgs() -> list[Path]:
    seen: set[Path] = set()
    for page in ALL_PAGES:
        for path in _local_references(page):
            if not path.endswith(".svg"):
                continue
            target = (
                (WEB / path.lstrip("/"))
                if path.startswith("/")
                else (page.parent / path)
            )
            if target.is_file():
                seen.add(target.resolve())
    return sorted(seen)


SVGS = _referenced_svgs()


def test_the_pages_reference_svgs_at_all() -> None:
    """Again the empty-glob guard: this site is built out of hand-authored
    SVG, so finding none means the discovery above is broken, not that the
    site is clean."""
    assert len(SVGS) > 50, f"only {len(SVGS)} SVGs discovered"


@pytest.mark.parametrize("svg", SVGS, ids=lambda p: p.name)
def test_every_referenced_svg_parses_and_scales(svg: Path) -> None:
    """Two failures in one check, both silent in a browser.

    Malformed XML renders as nothing at all. A missing ``viewBox`` renders at
    its intrinsic size and refuses to scale, so the figure is the wrong size
    on every screen that is not the author's.
    """
    try:
        root = ET.parse(svg).getroot()
    except ET.ParseError as exc:
        pytest.fail(f"{svg.name} is not well-formed XML: {exc}")
    assert root.tag.endswith("svg"), (
        f"{svg.name}: root element is {root.tag}, not <svg>"
    )
    assert root.get("viewBox"), f"{svg.name}: no viewBox, so it cannot scale"


# --------------------------------------------------------------------------
# The card a page presents when it is shared
# --------------------------------------------------------------------------

_META_RE = re.compile(r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"')


def _meta(page: Path) -> dict[str, str]:
    return dict(_META_RE.findall(page.read_text(encoding="utf-8")))


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: p.relative_to(WEB).as_posix())
def test_each_page_presents_a_complete_card_when_shared(page: Path) -> None:
    """A shared link is a page's first impression, and it is assembled from
    tags no reader ever sees, so nothing on the page itself looks wrong when
    one is missing."""
    meta = _meta(page)
    for key in (
        "description",
        "og:title",
        "og:description",
        "og:url",
        "og:image",
        "og:type",
    ):
        assert meta.get(key), f"{page.relative_to(WEB)}: {key} missing or empty"
    assert meta["og:url"] == _url_for(page)


@pytest.mark.parametrize("page", ALL_PAGES, ids=lambda p: p.relative_to(WEB).as_posix())
def test_the_shared_card_image_describes_itself(page: Path) -> None:
    """``og:image:alt`` is the card image's only accessible name.

    Unlike the rest of the Twitter block -- where ``twitter:title`` and
    friends fall back to their ``og:`` equivalents -- this one has no
    fallback. Without it, someone reading a shared post with a screen reader
    gets a picture announced as nothing at all. It was missing on 34 of these
    36 pages.

    The minimum length is there because the easy way to satisfy a check like
    this is to paste the page title in, and a title is not a description of a
    picture.
    """
    alt = _meta(page).get("og:image:alt")
    assert alt, f"{page.relative_to(WEB)}: og:image:alt missing"
    assert len(alt) >= 25, (
        f"{page.relative_to(WEB)}: og:image:alt is too short to describe anything"
    )


def test_the_card_descriptions_are_written_in_the_page_language() -> None:
    """A French page sharing an English card is the drift this catches.

    Checked by looking for accented characters rather than by guessing at
    vocabulary: every French description here carries at least one, and a copy
    of the English text would carry none. Crude, and it fails in exactly the
    direction that matters -- an English string pasted into a French page.
    """
    accented = re.compile(r"[àâçéèêëîïôûùüÿœæ]", re.IGNORECASE)
    flat = []
    for page in FR_PAGES:
        meta = _meta(page)
        for key in ("description", "og:description", "og:image:alt"):
            value = meta.get(key, "")
            # The logo's description is legitimately accent-free in French.
            if value and "logo" not in value.lower() and not accented.search(value):
                flat.append(f"{page.relative_to(WEB)}:{key}")
    assert not flat, (
        f"French pages with un-accented prose (English left in place?): {flat}"
    )
