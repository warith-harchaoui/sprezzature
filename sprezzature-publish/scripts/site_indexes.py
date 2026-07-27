#!/usr/bin/env python3
"""
site_indexes
============

Generate the standard set of site-index files for a project's web output.

Always emitted
--------------

* **``robots.txt``** — controls crawler access; references the sitemap.
* **``sitemap.xml``** — per the sitemaps.org spec (XML 0.9 namespace).
* **``llms.txt``** — per https://llmstxt.org/. Title, summary, and a
  bullet list of important pages.
* **``llms-full.txt``** — the companion "full-text" variant: the
  complete Markdown of every page concatenated into a single file so
  an agent can ingest the whole site in one request instead of
  crawling ``llms.txt``'s links page by page. Only **Markdown**
  sources are concatenated (never generated HTML), which keeps the
  file free of raw tags / image attributes and avoids duplicating
  pages that exist as both ``.md`` and rendered ``.html``. Opt out
  with ``--no-llms-full``.

Conditional
-----------

* **``feed.atom``** — Atom 1.0 (RFC 4287). Emitted when a blog directory
  (``posts/`` or ``blog/``) is detected at the project root, or when
  ``--feed-from DIR`` is supplied. RSS 2.0 is available with ``--rss``
  for clients that haven't moved past 2002.
* **``humans.txt``** — per https://humanstxt.org/. Emitted only when
  ``--humans`` is passed or an ``AUTHORS`` / ``CREDITS`` file exists at
  the project root.

Specs honored
-------------
* robots.txt — Google Search Central:
  https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
* Sitemap — https://www.sitemaps.org/protocol.html
* llms.txt — https://llmstxt.org/
* Atom 1.0 — RFC 4287 (https://datatracker.ietf.org/doc/html/rfc4287)
* RSS 2.0 — https://www.rssboard.org/rss-specification
* humans.txt — https://humanstxt.org/Standard.html

Usage
-----
::

    # Most common: emit the three always-on files
    python site_indexes.py --root . --base-url https://example.com

    # Project with a blog
    python site_indexes.py --root . --base-url https://example.com --feed-from posts

    # Force RSS 2.0 instead of Atom
    python site_indexes.py --root . --base-url https://example.com --feed-from posts --rss

    # Ship a humans.txt (will read AUTHORS / CREDITS if present)
    python site_indexes.py --root . --base-url https://example.com --humans

    # Choose a non-default output directory
    python site_indexes.py --root . --base-url https://example.com --out public

Notes
-----
* Python 3.10+, stdlib only.
* The script reads ``.html`` files at the project root and inside common
  output folders (``public/``, ``dist/``, ``site/``, ``_site/``,
  ``build/``) to populate sitemap and llms.txt. ``.md`` files at the
  root and under ``docs/`` are also included.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path as _PathHelper

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import format_datetime
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin


# ── Module-level configuration ────────────────────────────────────────────────

#: Directories at the project root that may contain static HTML output.
WEB_OUTPUT_DIRS: tuple[str, ...] = ("public", "dist", "site", "_site", "build", "out")


# ── Audio enclosure plumbing ──────────────────────────────────────────────


@dataclass(frozen=True)
class AudioEntry:
    """
    One ``<enclosure>`` row's worth of information about a narration.

    Attributes
    ----------
    path : str
        Relative path of the audio file (from site root), e.g.
        ``audio/2026-06-21-hello.wav``.
    mime_type : str
        Media type, e.g. ``audio/wav`` or ``audio/mpeg``. RSS
        readers use this to pick a player.
    length_bytes : int
        File size in bytes. The RSS 2.0 spec requires ``length`` on
        every enclosure; we fall back to 0 when the file isn't
        reachable.
    """

    path: str
    mime_type: str
    length_bytes: int


#: Map audio file extensions to RFC 2046 media types. Narration
#: typically lands as WAV (lossless, what the engines produce) or
#: MP3 (after the user re-encodes for distribution).
_AUDIO_MIME: dict[str, str] = {
    ".wav":  "audio/wav",
    ".mp3":  "audio/mpeg",
    ".m4a":  "audio/mp4",
    ".aac":  "audio/aac",
    ".ogg":  "audio/ogg",
    ".opus": "audio/ogg",
    ".flac": "audio/flac",
}


def load_audio_manifest(
    manifest_path: Path,
    audio_root: Path | None = None,
) -> dict[str, AudioEntry]:
    """
    Read ``out/audio/manifest.json`` and return a feed-ready mapping.

    The narration manifest is keyed by the **source Markdown path**;
    the feed renderers look up by **post HTML stem** (the relative
    URL without ``.html``). This helper normalises the key by
    stripping the source extension so the renderer's lookup works
    on both ``posts/foo.md → posts/foo``.

    Parameters
    ----------
    manifest_path : Path
        Path to the JSON manifest written by ``narrate_post.py``.
        Missing / unreadable files yield an empty mapping; this is
        a soft feature and should never crash feed generation.
    audio_root : Path or None, optional
        Directory the audio paths in the manifest are relative to.
        When set, the renderer stats each audio file to populate
        ``length_bytes``; when None, lengths default to 0.

    Returns
    -------
    dict
        ``{post_stem: AudioEntry}`` ready to pass to
        :func:`render_rss` / :func:`render_atom`.
    """
    if not manifest_path.is_file():
        return {}
    try:
        rows = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(rows, list):
        return {}

    out: dict[str, AudioEntry] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source: str = str(row.get("source", "")).strip()
        audio: str = str(row.get("audio", "")).strip()
        if not source or not audio:
            continue
        # Strip the source extension to get the stem used by feeds.
        stem: str = Path(source).with_suffix("").as_posix()
        # Detect media type from extension; fall back to a generic
        # value rather than skipping the row.
        ext: str = Path(audio).suffix.lower()
        mime: str = _AUDIO_MIME.get(ext, "application/octet-stream")
        # File size is only known when we can resolve the audio path.
        length_bytes: int = 0
        if audio_root is not None:
            candidate: Path = (audio_root / audio).resolve()
            if candidate.is_file():
                length_bytes = candidate.stat().st_size
        out[stem] = AudioEntry(
            path=audio, mime_type=mime, length_bytes=length_bytes,
        )
    return out

#: Names recognized as a default blog folder when ``--feed-from`` is absent.
DEFAULT_BLOG_DIRS: tuple[str, ...] = ("posts", "blog", "articles")

#: Per-spec maximum number of URLs in a single sitemap. The sitemaps.org
#: protocol caps a single ``sitemap.xml`` at 50000 URLs / 50 MB; this
#: script does not split sitemaps because real-world projects emitting
#: more than 50000 pages need a dedicated tool.
SITEMAP_MAX_URLS: int = 50_000


# ── Utility helpers ────────────────────────────────────────────────────────

def _today_iso() -> str:
    """Return today's date as ISO-8601 (YYYY-MM-DD) in UTC."""
    return datetime.date.today().isoformat()


def _format_url(base_url: str, rel_path: Path) -> str:
    """
    Combine the base URL with a relative project path.

    Parameters
    ----------
    base_url : str
        Origin of the published site, with or without a trailing slash.
    rel_path : Path
        Path relative to the project root (or the output directory).

    Returns
    -------
    str
        Fully-qualified URL. ``index.html`` is collapsed to a directory URL.
    """
    posix: str = rel_path.as_posix()
    # Strip ``index.html`` suffix so the URL looks like ``/section/`` rather
    # than ``/section/index.html`` — what most servers serve and what
    # crawlers prefer.
    if posix.endswith("/index.html"):
        posix = posix[: -len("index.html")]
    elif posix == "index.html":
        posix = ""
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    return urljoin(base_url, posix)


def _read_title(path: Path) -> str:
    """
    Extract a human-readable title from an HTML or Markdown page.

    Falls back to the file's stem when no title is found.

    Parameters
    ----------
    path : Path
        File to read.

    Returns
    -------
    str
        Title string.
    """
    text: str = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() in {".html", ".htm"}:
        m = re.search(r"<title>([^<]+)</title>", text, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r"<h1[^>]*>([^<]+)</h1>", text, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    else:
        # Markdown: first ATX-style heading.
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def _read_description(path: Path) -> str:
    """
    Extract a one-sentence description from an HTML or Markdown page.

    Returns an empty string when no description is found. Used for
    llms.txt entries.
    """
    text: str = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() in {".html", ".htm"}:
        m = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            text, re.I,
        )
        if m:
            return m.group(1).strip()
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                      text, re.I)
        if m:
            return m.group(1).strip()
        return ""
    # Markdown: first blockquote or first paragraph after the title.
    in_post_title: bool = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            in_post_title = True
            continue
        if in_post_title:
            return line.lstrip("> ").strip()
    return ""


# ── Page discovery ────────────────────────────────────────────────────────

def discover_pages(root: Path) -> list[Path]:
    """
    Discover web-facing pages in the project tree.

    Walks the project root looking for ``.html`` files at the root and in
    the conventional output directories (:data:`WEB_OUTPUT_DIRS`), plus
    ``.md`` files at the root and under ``docs/``.

    Parameters
    ----------
    root : Path
        Project root.

    Returns
    -------
    list of Path
        Discovered files, in stable sorted order, paths relative to ``root``.
    """
    found: set[Path] = set()
    for pattern in ("*.html", "*.md"):
        for p in root.glob(pattern):
            if p.is_file():
                found.add(p.relative_to(root))
    for sub in WEB_OUTPUT_DIRS:
        d = root / sub
        if d.is_dir():
            for p in d.rglob("*.html"):
                found.add(p.relative_to(root))
    docs = root / "docs"
    if docs.is_dir():
        for p in docs.rglob("*.md"):
            found.add(p.relative_to(root))
    return sorted(found)


# ── robots.txt ────────────────────────────────────────────────────────────

def render_robots(base_url: str, sitemap_url: str) -> str:
    """
    Render a minimal robots.txt allowing all crawlers.

    Parameters
    ----------
    base_url : str
        Site origin (for context only — not embedded).
    sitemap_url : str
        Absolute URL of the sitemap to advertise.

    Returns
    -------
    str
        File body.
    """
    # A conservative default: allow everything, point crawlers at the sitemap.
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {sitemap_url}\n"
    )


# ── sitemap.xml ───────────────────────────────────────────────────────────

def render_sitemap(base_url: str, pages: Iterable[tuple[Path, str]]) -> str:
    """
    Render a sitemap.xml document per sitemaps.org 0.9.

    Parameters
    ----------
    base_url : str
        Site origin.
    pages : iterable of (Path, str)
        ``(relative_path, lastmod_iso)`` tuples to include.

    Returns
    -------
    str
        XML document body.
    """
    SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    count: int = 0
    for rel, lastmod in pages:
        if count >= SITEMAP_MAX_URLS:
            break
        url = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = _format_url(base_url, rel)
        if lastmod:
            ET.SubElement(url, f"{{{SITEMAP_NS}}}lastmod").text = lastmod
        count += 1
    # ``ET.tostring`` with ``xml_declaration=True`` emits the canonical
    # ``<?xml version="1.0" encoding="UTF-8"?>`` prologue.
    return ET.tostring(urlset, encoding="unicode", xml_declaration=True).rstrip() + "\n"


# ── llms.txt ──────────────────────────────────────────────────────────────

def render_llms_txt(
    base_url: str,
    project_name: str,
    summary: str,
    sections: dict[str, list[tuple[str, str, str]]],
) -> str:
    """
    Render an llms.txt file per https://llmstxt.org/.

    Parameters
    ----------
    base_url : str
        Site origin, used to fully qualify the links.
    project_name : str
        H1 title.
    summary : str
        Single-paragraph blockquote summary.
    sections : dict
        Map from H2 heading to a list of ``(name, url, description)``
        link entries. ``description`` may be empty.

    Returns
    -------
    str
        Markdown document body.
    """
    lines: list[str] = [f"# {project_name}", ""]
    if summary:
        lines.append(f"> {summary}")
        lines.append("")
    for heading, entries in sections.items():
        lines.append(f"## {heading}")
        lines.append("")
        for name, url, desc in entries:
            full = url if url.startswith(("http://", "https://")) else _format_url(base_url, Path(url))
            if desc:
                lines.append(f"- [{name}]({full}): {desc}")
            else:
                lines.append(f"- [{name}]({full})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ── llms-full.txt ──────────────────────────────────────────────────────────

#: Soft size threshold (bytes) above which we nudge the user toward
#: curation even when no hard ``--llms-full-max-kb`` cap is set. Chosen
#: as a round ~200 KB — comfortably inside every current model context,
#: past which a "linked index + on-demand fetch" usually beats one blob.
LLMS_FULL_SOFT_LIMIT: int = 200 * 1024


def _strip_frontmatter(text: str) -> str:
    """
    Drop a leading YAML front-matter block from Markdown source.

    Front matter is page *metadata* (title, date, tags) — boilerplate
    for a full-text corpus, and we emit our own ``Source:`` line per
    page instead. A block is only stripped when the very first line is
    ``---`` and a closing ``---`` follows.

    Parameters
    ----------
    text : str
        Raw Markdown file contents.

    Returns
    -------
    str
        Body with any leading front-matter block removed.
    """
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    # First line must be exactly the fence (allow trailing whitespace).
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :]).lstrip("\n")
    return text


def render_llms_full_txt(
    base_url: str,
    project_name: str,
    summary: str,
    docs: list[tuple[str, str, str]],
    max_bytes: int = 0,
) -> tuple[str, list[str]]:
    """
    Render an ``llms-full.txt`` corpus — the full text of every page.

    The companion to :func:`render_llms_txt`: where ``llms.txt`` links
    to pages, this concatenates their **Markdown** bodies into one file
    an agent can ingest in a single request. Only Markdown is passed in
    (see :func:`main`), so the output carries no HTML tags, image
    attributes, nav, or footer boilerplate, and never duplicates a page
    that ships as both ``.md`` and rendered ``.html``.

    Parameters
    ----------
    base_url : str
        Site origin, used to fully qualify each ``Source:`` URL.
    project_name : str
        H1 title.
    summary : str
        Single-paragraph blockquote summary (may be empty).
    docs : list of (str, str, str)
        ``(title, url, body)`` per page, already in priority order
        (most important first) so any budget truncation keeps the
        pages that matter.
    max_bytes : int, optional
        Hard size budget. When > 0, pages are appended in order until
        the next page would exceed the budget; the rest are dropped and
        returned as ``dropped`` rather than silently truncated. ``0``
        (default) means no cap.

    Returns
    -------
    (str, list of str)
        The document body, and the list of page titles that were
        dropped to honor ``max_bytes`` (empty when nothing was cut).
    """
    header: list[str] = [f"# {project_name}", ""]
    if summary:
        header.append(f"> {summary}")
        header.append("")
    header.append(
        "> Full text of the pages linked from llms.txt, concatenated for "
        "single-request ingestion by AI agents. Markdown sources only."
    )
    header.append("")
    head_text: str = "\n".join(header)

    # ── Assemble page blocks, respecting the optional byte budget. ──
    budget: int = max_bytes if max_bytes > 0 else 0
    running: int = len(head_text.encode("utf-8"))
    blocks: list[str] = []
    dropped: list[str] = []
    for title, url, body in docs:
        full = url if url.startswith(("http://", "https://")) else _format_url(base_url, Path(url))
        block: str = f"## {title}\n\nSource: {full}\n\n{body.strip()}\n"
        block_bytes: int = len(("\n---\n\n" + block).encode("utf-8"))
        if budget and running + block_bytes > budget and blocks:
            # Budget reached — drop this and every remaining page.
            dropped.append(title)
            continue
        blocks.append(block)
        running += block_bytes

    body_text: str = head_text + "\n---\n\n" + "\n---\n\n".join(blocks)
    return body_text.rstrip() + "\n", dropped


# ── Atom feed ─────────────────────────────────────────────────────────────

def render_atom(
    base_url: str,
    feed_id: str,
    feed_title: str,
    posts: list[tuple[Path, str, str, str]],
    audio_entries: dict[str, "AudioEntry"] | None = None,
) -> str:
    """
    Render an Atom 1.0 feed per RFC 4287.

    Parameters
    ----------
    base_url : str
        Site origin.
    feed_id : str
        Permanent feed URI (e.g. ``tag:example.com,2026:feed``).
    feed_title : str
        Human-readable feed title.
    posts : list of (Path, str, str, str)
        ``(relative_path, title, updated_iso, summary)`` per post, in
        reverse-chronological order.
    audio_entries : dict or None, optional
        Mapping of *post stem* (the relative HTML path without
        ``.html``) → :class:`AudioEntry`. When present, each matching
        post gets a ``<link rel="enclosure">`` so podcast apps see
        the narration as an audio item.

    Returns
    -------
    str
        Atom XML document body.
    """
    ATOM_NS = "http://www.w3.org/2005/Atom"
    ET.register_namespace("", ATOM_NS)
    feed = ET.Element(f"{{{ATOM_NS}}}feed")
    ET.SubElement(feed, f"{{{ATOM_NS}}}title").text = feed_title
    ET.SubElement(feed, f"{{{ATOM_NS}}}id").text = feed_id

    link_self = ET.SubElement(feed, f"{{{ATOM_NS}}}link")
    link_self.set("rel", "self")
    link_self.set("href", _format_url(base_url, Path("feed.atom")))
    link_html = ET.SubElement(feed, f"{{{ATOM_NS}}}link")
    link_html.set("rel", "alternate")
    link_html.set("type", "text/html")
    link_html.set("href", base_url)

    # The feed-level ``<updated>`` mirrors the newest entry.
    feed_updated: str = posts[0][2] if posts else _today_iso() + "T00:00:00Z"
    ET.SubElement(feed, f"{{{ATOM_NS}}}updated").text = feed_updated

    for rel, title, updated, summary in posts:
        entry = ET.SubElement(feed, f"{{{ATOM_NS}}}entry")
        ET.SubElement(entry, f"{{{ATOM_NS}}}title").text = title
        post_url: str = _format_url(base_url, rel)
        ET.SubElement(entry, f"{{{ATOM_NS}}}id").text = post_url
        link = ET.SubElement(entry, f"{{{ATOM_NS}}}link")
        link.set("rel", "alternate")
        link.set("type", "text/html")
        link.set("href", post_url)
        ET.SubElement(entry, f"{{{ATOM_NS}}}updated").text = updated
        if summary:
            ET.SubElement(entry, f"{{{ATOM_NS}}}summary").text = summary
        # Optional audio enclosure for podcast-app consumption.
        audio = (audio_entries or {}).get(rel.with_suffix("").as_posix())
        if audio is not None:
            audio_link = ET.SubElement(entry, f"{{{ATOM_NS}}}link")
            audio_link.set("rel", "enclosure")
            audio_link.set("type", audio.mime_type)
            audio_link.set("href", _format_url(base_url, Path(audio.path)))
            if audio.length_bytes > 0:
                audio_link.set("length", str(audio.length_bytes))

    return ET.tostring(feed, encoding="unicode", xml_declaration=True).rstrip() + "\n"


# ── RSS 2.0 feed (alternative output) ─────────────────────────────────────

def render_rss(
    base_url: str,
    feed_title: str,
    feed_description: str,
    posts: list[tuple[Path, str, str, str]],
    audio_entries: dict[str, "AudioEntry"] | None = None,
) -> str:
    """
    Render an RSS 2.0 feed.

    Parameters
    ----------
    base_url : str
        Site origin.
    feed_title : str
        Channel title.
    feed_description : str
        Channel description.
    posts : list of (Path, str, str, str)
        ``(relative_path, title, updated_iso, summary)`` per post.
    audio_entries : dict or None, optional
        Mapping of *post stem* (the relative HTML path without
        ``.html``) → :class:`AudioEntry`. When present, each matching
        post gets an ``<enclosure>`` row — the feed becomes a valid
        podcast feed automatically consumable in any podcast app.

    Returns
    -------
    str
        RSS XML document body.
    """
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = feed_title
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = feed_description
    if posts:
        # ``email.utils.format_datetime`` produces RFC 822 dates, which RSS
        # requires (not ISO-8601 like Atom).
        try:
            dt = datetime.datetime.fromisoformat(posts[0][2].replace("Z", "+00:00"))
            ET.SubElement(channel, "lastBuildDate").text = format_datetime(dt)
        except ValueError:
            pass

    for rel, title, updated, summary in posts:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        link_url: str = _format_url(base_url, rel)
        ET.SubElement(item, "link").text = link_url
        ET.SubElement(item, "guid").text = link_url
        if summary:
            ET.SubElement(item, "description").text = summary
        try:
            dt = datetime.datetime.fromisoformat(updated.replace("Z", "+00:00"))
            ET.SubElement(item, "pubDate").text = format_datetime(dt)
        except ValueError:
            pass
        # Optional audio enclosure for podcast-app consumption. The
        # ``length`` attribute is required by the RSS spec; we use 0
        # when the audio file isn't reachable so the feed still parses.
        audio = (audio_entries or {}).get(rel.with_suffix("").as_posix())
        if audio is not None:
            ET.SubElement(item, "enclosure", {
                "url": _format_url(base_url, Path(audio.path)),
                "length": str(audio.length_bytes),
                "type": audio.mime_type,
            })

    return ET.tostring(rss, encoding="unicode", xml_declaration=True).rstrip() + "\n"


# ── humans.txt ────────────────────────────────────────────────────────────

def render_humans(authors: list[str], site_meta: dict[str, str]) -> str:
    """
    Render a humans.txt file per humanstxt.org.

    Parameters
    ----------
    authors : list of str
        Author / contributor lines, e.g. ``"Warith Harchaoui - Author -
        warith@example.com - linkedin.com/in/warith-harchaoui"``.
    site_meta : dict
        Free-form key/value pairs for the ``/* SITE */`` section
        (``Last update``, ``Standards``, ``Components``, ``Software``).

    Returns
    -------
    str
        File body.
    """
    lines: list[str] = ["/* TEAM */", ""]
    if not authors:
        authors = ["Author -- see repository metadata."]
    lines.extend(authors)
    lines.append("")
    lines.append("/* SITE */")
    lines.append("")
    lines.append(f"Last update: {_today_iso()}")
    for key, value in site_meta.items():
        lines.append(f"{key}: {value}")
    lines.append("")
    return "\n".join(lines) + "\n"


def read_authors(root: Path) -> list[str]:
    """
    Read author lines from ``AUTHORS``, ``CREDITS``, or ``HUMANS`` files at
    the project root.

    Parameters
    ----------
    root : Path
        Project root.

    Returns
    -------
    list of str
        One non-empty line per author. Empty list when none of the files exist.
    """
    for name in ("AUTHORS", "AUTHORS.txt", "AUTHORS.md", "CREDITS", "CREDITS.txt", "HUMANS"):
        p = root / name
        if p.is_file():
            return [
                line.strip()
                for line in p.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
    return []


# ── Blog-post discovery ────────────────────────────────────────────────────

def discover_posts(feed_dir: Path) -> list[tuple[Path, str, str, str]]:
    """
    Walk ``feed_dir`` and discover Markdown / HTML posts.

    Each post becomes a tuple ``(relative_path, title, updated_iso,
    summary)``. ``updated_iso`` is the file's mtime as an ISO-8601 UTC
    string.

    Parameters
    ----------
    feed_dir : Path
        Directory containing the blog posts.

    Returns
    -------
    list of tuple
        Posts in reverse-chronological order by mtime.
    """
    posts: list[tuple[Path, str, str, str]] = []
    for pattern in ("*.html", "*.md"):
        for p in feed_dir.rglob(pattern):
            if not p.is_file():
                continue
            # ``index.{html,md}`` at the feed root is the listing page; skip it.
            if p.name.lower() in {"index.html", "index.md"} and p.parent == feed_dir:
                continue
            stat = p.stat()
            updated = (
                datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            title = _read_title(p)
            summary = _read_description(p)
            posts.append((p, title, updated, summary))
    # Reverse chronological order — newest first.
    posts.sort(key=lambda x: x[2], reverse=True)
    # Convert paths to feed-relative for the renderer.
    rel_posts: list[tuple[Path, str, str, str]] = [
        (p[0].relative_to(feed_dir.parent), p[1], p[2], p[3]) for p in posts
    ]
    return rel_posts


# ── Orchestration ─────────────────────────────────────────────────────────

def find_blog_dir(root: Path, explicit: Optional[Path]) -> Optional[Path]:
    """
    Resolve the blog-posts directory.

    Parameters
    ----------
    root : Path
        Project root.
    explicit : Path or None
        Value of ``--feed-from`` (may be absolute or relative to ``root``).

    Returns
    -------
    Path or None
        Resolved directory, or ``None`` when no blog is detected.
    """
    if explicit is not None:
        candidate = explicit if explicit.is_absolute() else root / explicit
        return candidate if candidate.is_dir() else None
    for name in DEFAULT_BLOG_DIRS:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    return None


def main() -> int:
    """CLI entry point. Writes the requested files into ``--out`` (default ``root``)."""
    p = make_parser(
        prog="sprezzature-publish-indexes",
        description="Generate robots.txt, sitemap.xml, llms.txt, an Atom or RSS "
                    "feed and humans.txt for a static site. Stdlib only.",
        epilog="Examples:\n"
               "  sprezzature-publish-indexes --root . --base-url https://example.com\n"
               "  sprezzature-publish-indexes --root . --base-url https://example.com --feed-from posts\n"
               "  sprezzature-publish-indexes --root . --base-url https://example.com --rss --humans\n",
    )
    p.add_argument(
        "--root", type=Path, default=Path("."),
        help="Project root. Default: current directory.",
    )
    p.add_argument(
        "--base-url", required=True,
        help="Absolute origin of the published site (e.g. https://example.com).",
    )
    p.add_argument(
        "--out", type=Path,
        help="Output directory. Default: same as --root.",
    )
    p.add_argument(
        "--feed-from", type=Path, dest="feed_from",
        help="Directory containing blog posts. When omitted, posts/ or blog/ is auto-detected.",
    )
    p.add_argument(
        "--rss", action="store_true",
        help="Emit RSS 2.0 instead of Atom 1.0.",
    )
    p.add_argument(
        "--humans", action="store_true",
        help="Emit humans.txt (always reads AUTHORS / CREDITS when present).",
    )
    p.add_argument(
        "--name", default="",
        help="Project name. Falls back to the H1 / <title> of the root README / index.",
    )
    p.add_argument(
        "--summary", default="",
        help="Site summary used in llms.txt blockquote.",
    )
    p.add_argument(
        "--no-llms-full", action="store_true", dest="no_llms_full",
        help="Skip llms-full.txt (the concatenated full-text corpus). "
             "By default it is emitted from the Markdown sources.",
    )
    p.add_argument(
        "--llms-full-max-kb", type=int, default=0, dest="llms_full_max_kb",
        help="Hard size budget (KB) for llms-full.txt. Pages are kept in "
             "priority order (README / index first) until the budget is "
             "reached; the rest are dropped and named in a warning. "
             "0 (default) means no cap.",
    )
    p.add_argument(
        "--audio-manifest", type=Path, default=None, dest="audio_manifest",
        help="Path to out/audio/manifest.json (from narrate_post.py). "
             "When passed, feed entries gain <enclosure> rows so the "
             "blog feed doubles as a podcast feed.",
    )
    p.add_argument(
        "--audio-root", type=Path, default=None, dest="audio_root",
        help="Directory the audio paths in --audio-manifest are relative "
             "to. When set, the renderer stats each file to populate the "
             "enclosure 'length' attribute. Defaults to --root.",
    )
    args = p.parse_args()

    root: Path = args.root.resolve()
    out_dir: Path = (args.out or root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base_url: str = args.base_url.rstrip("/")

    # Project metadata: prefer the README's title; fall back to the folder name.
    project_name: str = args.name
    if not project_name:
        for candidate in ("README.md", "index.html", "index.md"):
            path = root / candidate
            if path.is_file():
                project_name = _read_title(path)
                break
    if not project_name:
        project_name = root.name

    # 1. robots.txt
    sitemap_url: str = _format_url(base_url + "/", Path("sitemap.xml"))
    (out_dir / "robots.txt").write_text(
        render_robots(base_url, sitemap_url),
        encoding="utf-8",
    )
    print(f"→ Wrote {out_dir / 'robots.txt'}")

    # 2. sitemap.xml
    pages: list[Path] = discover_pages(root)
    today: str = _today_iso()
    sitemap_pages: list[tuple[Path, str]] = [(p, today) for p in pages]
    (out_dir / "sitemap.xml").write_text(
        render_sitemap(base_url, sitemap_pages),
        encoding="utf-8",
    )
    print(f"→ Wrote {out_dir / 'sitemap.xml'} ({len(pages)} URL(s))")

    # 3. llms.txt
    sections: dict[str, list[tuple[str, str, str]]] = {"Pages": []}
    for page in pages:
        title = _read_title(root / page)
        desc = _read_description(root / page)
        sections["Pages"].append((title, page.as_posix(), desc))
    (out_dir / "llms.txt").write_text(
        render_llms_txt(base_url, project_name, args.summary, sections),
        encoding="utf-8",
    )
    print(f"→ Wrote {out_dir / 'llms.txt'}")

    # 3b. llms-full.txt — full-text corpus (Markdown sources only).
    if not args.no_llms_full:
        # Markdown only: rendered HTML is generated *from* these pages,
        # so including it would duplicate content and drag in tag / nav
        # boilerplate — the classic llms-full.txt bloat. Priority order
        # (README / index first, then the rest) so any budget truncation
        # keeps the pages that matter.
        def _priority(rel: Path) -> tuple[int, str]:
            name = rel.name.lower()
            if name in {"readme.md", "index.md"} and rel.parent == Path("."):
                return (0, rel.as_posix())
            if rel.parent == Path("."):
                return (1, rel.as_posix())
            return (2, rel.as_posix())

        md_pages: list[Path] = sorted(
            (p for p in pages if p.suffix.lower() == ".md"), key=_priority
        )
        docs: list[tuple[str, str, str]] = []
        for page in md_pages:
            raw = (root / page).read_text(encoding="utf-8", errors="ignore")
            docs.append((_read_title(root / page), page.as_posix(), _strip_frontmatter(raw)))
        if docs:
            max_bytes: int = max(0, args.llms_full_max_kb) * 1024
            body, dropped = render_llms_full_txt(
                base_url, project_name, args.summary, docs, max_bytes=max_bytes,
            )
            (out_dir / "llms-full.txt").write_text(body, encoding="utf-8")
            size_kb: float = len(body.encode("utf-8")) / 1024
            kept: int = len(docs) - len(dropped)
            print(f"→ Wrote {out_dir / 'llms-full.txt'} ({kept} page(s), {size_kb:.0f} KB)")
            if dropped:
                print(
                    f"  ⚠ {len(dropped)} page(s) dropped to honor "
                    f"--llms-full-max-kb {args.llms_full_max_kb}: "
                    + ", ".join(dropped)
                )
            elif not max_bytes and len(body.encode("utf-8")) > LLMS_FULL_SOFT_LIMIT:
                print(
                    f"  ⚠ llms-full.txt is {size_kb:.0f} KB — large enough to "
                    "crowd a model's context. Consider --llms-full-max-kb, or "
                    "let llms.txt's linked index carry the long tail."
                )
        else:
            print("→ No Markdown pages found; skipping llms-full.txt.")

    # 4. Feed (conditional)
    feed_dir: Optional[Path] = find_blog_dir(root, args.feed_from)
    if feed_dir is not None:
        posts = discover_posts(feed_dir)
        if posts:
            # Optional audio manifest → podcast enclosures in the feed.
            audio_entries: dict[str, AudioEntry] = (
                load_audio_manifest(
                    args.audio_manifest,
                    audio_root=(args.audio_root or root),
                )
                if args.audio_manifest else {}
            )
            if args.rss:
                body = render_rss(
                    base_url,
                    feed_title=project_name,
                    feed_description=args.summary or f"{project_name} feed",
                    posts=posts,
                    audio_entries=audio_entries,
                )
                feed_path = out_dir / "rss.xml"
            else:
                feed_id = f"tag:{re.sub(r'^https?://', '', base_url)},{today}:feed"
                body = render_atom(
                    base_url,
                    feed_id=feed_id,
                    feed_title=project_name,
                    posts=posts,
                    audio_entries=audio_entries,
                )
                feed_path = out_dir / "feed.atom"
            feed_path.write_text(body, encoding="utf-8")
            n_audio: int = sum(
                1 for p, _, _, _ in posts
                if p.with_suffix("").as_posix() in audio_entries
            )
            audio_note: str = (
                f", {n_audio} with audio enclosure" if audio_entries else ""
            )
            print(f"→ Wrote {feed_path} ({len(posts)} post(s){audio_note})")
        else:
            print(f"→ No posts found in {feed_dir}; skipping feed.")

    # 5. humans.txt (opt-in or AUTHORS-driven)
    authors = read_authors(root)
    if args.humans or authors:
        site_meta: dict[str, str] = {
            "Language": "English",
            "Doctype": "HTML5",
            "Components": "vanilla JavaScript, Tailwind CSS, Roboto / Roboto Serif / Roboto Mono",
        }
        (out_dir / "humans.txt").write_text(
            render_humans(authors, site_meta),
            encoding="utf-8",
        )
        print(f"→ Wrote {out_dir / 'humans.txt'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
