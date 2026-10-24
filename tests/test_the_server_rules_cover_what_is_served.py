"""
Every compressible thing the site serves is named in the compression rules.

``web/.htaccess`` lists the MIME types Apache should gzip. The list is
hand-written and the site keeps gaining file types, so the two drift — and
the drift is invisible: an asset that is not compressed still arrives, just
larger, and nothing in a browser says so.

It had already drifted once. ``application/javascript`` was named and
``text/javascript`` was not, and Apache serves ``.js`` as the second — the
type recommended since 2022 — so the rule matched no file on this site and
every script went out uncompressed: 25.9 KB where gzip makes 10.7, on every
page, since all of them load ``theme.js``, ``nav.js`` and ``color-mode.js``.

The same omission had been found on ``deraison.ai`` on 2 October, where it
cost 196 KB a page, and written down there. It was not carried here, which is
this project's most common failure by a distance: a lesson learned in one
place and left there.

Two questions, because one of them is not enough. The first: for every
extension the site serves, is *a* type it may be served as in the list? That
catches a type nobody thought of. It does **not** catch what actually
happened — the first version of this file passed with ``text/javascript``
deleted, because ``application/javascript`` was still there and either
satisfies "a type it may be served as". A guard that admits the defect it was
written for is worse than none.

So the second: where a type has two spellings in live use, **both** have to be
named. From a file on disk there is no way to know which one a host will
choose, and the cost of naming both is nothing.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"
HTACCESS = WEB / ".htaccess"

#: Extension -> the MIME types a server may serve it as. Any one of them in
#: the compression list satisfies the rule; a type nothing is served as does
#: not, which is the whole point.
SERVED_AS: dict[str, tuple[str, ...]] = {
    ".html": ("text/html",),
    ".css": ("text/css",),
    ".js": ("text/javascript", "application/javascript"),
    ".json": ("application/json",),
    ".svg": ("image/svg+xml",),
    ".xml": ("application/xml", "text/xml"),
    ".atom": ("application/atom+xml",),
    ".txt": ("text/plain",),
    ".webmanifest": ("application/manifest+json", "application/json"),
}

#: Extensions whose MIME type is genuinely ambiguous in the wild, with every
#: spelling that must appear. ``.js`` is the one that bit: Apache says
#: ``text/javascript``, a good deal of documentation still says
#: ``application/javascript``, and a file on disk cannot tell you which your
#: host picked.
BOTH_SPELLINGS: dict[str, tuple[str, ...]] = {
    ".js": ("text/javascript", "application/javascript"),
}

#: Not worth compressing: already-compressed bytes, where gzip costs CPU on
#: both ends and gives back nothing.
ALREADY_COMPRESSED = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff2", ".woff",
     ".mp4", ".webm", ".mp3", ".zip", ".gz", ".pdf", ".ttf"}
)


def _declared_types() -> set[str]:
    """Every MIME type named on an ``AddOutputFilterByType DEFLATE`` line."""
    body = HTACCESS.read_text(encoding="utf-8")
    types: set[str] = set()
    for line in re.findall(r"^\s*AddOutputFilterByType\s+DEFLATE\s+(.+)$", body, re.M):
        types |= {token.strip() for token in line.split() if "/" in token}
    return types


def _served_extensions() -> set[str]:
    """Extensions the site actually ships, kits and build artifacts aside."""
    found: set[str] = set()
    for path in WEB.rglob("*"):
        if not path.is_file() or "kits" in path.parts:
            continue
        found.add(path.suffix.lower())
    return found


def test_the_compression_list_covers_every_text_type_served() -> None:
    """A text type the site serves and the rules do not name goes out whole."""
    assert HTACCESS.is_file(), f"{HTACCESS} is gone"
    declared = _declared_types()
    assert declared, "no AddOutputFilterByType DEFLATE line in web/.htaccess"

    uncovered = sorted(
        extension
        for extension in _served_extensions()
        if extension in SERVED_AS and not (set(SERVED_AS[extension]) & declared)
    )
    assert not uncovered, (
        f"web/.htaccess compresses none of the types {uncovered} are served "
        f"as. Declared: {sorted(declared)}"
    )


def test_an_ambiguous_type_is_named_both_ways() -> None:
    """Where two spellings are in use, naming one is naming the wrong one."""
    declared = _declared_types()
    served = _served_extensions()
    missing: dict[str, list[str]] = {}
    for extension, spellings in BOTH_SPELLINGS.items():
        if extension not in served:
            continue
        absent = [spelling for spelling in spellings if spelling not in declared]
        if absent:
            missing[extension] = absent
    assert not missing, (
        f"web/.htaccess names only one spelling for {missing}. Apache serves "
        f".js as text/javascript, so naming application/javascript alone "
        f"matched no file here and every script went out uncompressed."
    )


def test_the_rules_do_not_compress_already_compressed_bytes() -> None:
    """Gzipping a PNG spends CPU at both ends and gives nothing back."""
    wasteful = sorted(
        declared
        for declared in _declared_types()
        if declared.startswith(("image/", "font/", "video/", "audio/"))
        and declared != "image/svg+xml"
    )
    assert not wasteful, (
        f"web/.htaccess asks the server to compress {wasteful}, which is "
        f"already-compressed binary. image/svg+xml is the exception: it is XML."
    )


def test_this_run_read_the_site() -> None:
    """A glob that stopped matching would make the check above vacuous."""
    extensions = _served_extensions()
    assert ".html" in extensions and ".js" in extensions and ".svg" in extensions, (
        f"read {sorted(extensions)[:12]} from web/, which does not look like "
        f"the site"
    )
