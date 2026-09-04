#!/usr/bin/env python3
"""
changelog_feed
==============

Build the sprezzature.ai Atom/RSS feed from CHANGELOG.md release notes.

The site has no blog, so ``site_indexes.py``'s ``--feed-from posts/`` blog
auto-detection doesn't apply. What the site *does* have is eight
``sprezzature-*`` packages (plus the main ``sprezzature`` repo), each with
a Keep-a-Changelog-style ``CHANGELOG.md`` at its root. This script treats
that as the content stream: it parses every repo's CHANGELOG.md, turns
each dated release heading into a feed entry, and writes a combined,
date-sorted ``feed.atom`` / ``feed.xml`` into the site's ``web/`` output.

It does **not** reimplement Atom/RSS XML rendering — it imports and calls
:func:`site_indexes.render_atom` / :func:`site_indexes.render_rss`
directly, passing two small overrides (``entry_ids``, ``entry_links``)
that ``site_indexes`` already exposes for exactly this case: entries that
are not on-site pages and need their own stable id + external link.

Headings recognized
--------------------
Three heading styles are in live use across the sprezzature-* repos
(confirmed by inspection, not assumed):

* ``## [1.0.0] - 2026-07-29`` — plain Keep-a-Changelog, no title.
* ``## [1.0.1] (2026-07-29): Three-layer architecture, ...`` — the main
  ``sprezzature`` repo's style, with a heading-line title.
* ``## v1.0.0 (2026-07-29)`` — the style used by sprezzature-audio and
  sprezzature-cli-gui.

A heading is only turned into a feed entry when a full ``YYYY-MM-DD``
date can be extracted from it. This is what quietly and correctly drops
dateless ``## Unreleased`` sections (audio, cli-gui, the main repo) while
still keeping ``## [Unreleased] - 2026-08-20``-style headings (maps,
ux-laws) that *do* carry a real date, and a lone ``## [0.1.0] (2025)``
in the main repo's CHANGELOG (year only, no day — not a stable date).
A ``... through ...`` date range keeps the later date.

Usage
-----
::

    python scripts/changelog_feed.py
    python scripts/changelog_feed.py --repos-root .. --out ../web
    python scripts/changelog_feed.py --base-url https://sprezzature.ai --rss-only

Notes
-----
* Python 3.10+, stdlib only.
* Entry ``id``/``guid`` is a stable ``tag:`` URI:
  ``tag:sprezzature.ai,<year>:<package>-<version>``.
* Entry ``link`` points at the package's CHANGELOG.md on GitHub (the
  standalone repo for the eight packages; the monorepo for the main
  ``sprezzature`` entries), matching how other reference links on the
  site point at GitHub-hosted files rather than site pages.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from site_indexes import _today_iso, render_atom, render_rss  # noqa: E402


# ── Package registry ─────────────────────────────────────────────────────

#: Directory names (siblings of the monorepo root, one level up) that
#: carry a release-worthy CHANGELOG.md. ``sprezzature`` itself (the
#: monorepo / skills repo) is included; ``sprezzature-local`` is skipped
#: because it is archived/deprecated.
PACKAGE_REPOS: tuple[str, ...] = (
    "sprezzature-accessibility",
    "sprezzature-audio",
    "sprezzature-cli-gui",
    "sprezzature-colors",
    "sprezzature-figures",
    "sprezzature-maps",
    "sprezzature-ux-laws",
    "sprezzature",
)

#: Matches a full ISO-8601 date. Deliberately does not match a bare year
#: (``(2025)``) — a year alone isn't a stable enough date to sort or feed.
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

#: Matches a release heading in any of the three styles documented above:
#: ``[version]`` or ``vX.Y.Z`` or the bare word ``Unreleased``, followed
#: by whatever the rest of the line holds (date, title).
_HEADING_RE = re.compile(
    r"^##\s+(?:\[(?P<bracket>[^\]]+)\]|v(?P<vprefix>\d[\w.\-]*)\b|(?P<bare>Unreleased)\b)"
    r"(?P<rest>.*)$"
)

#: A heading-line title follows the date, set off by "): " — e.g.
#: ``(2026-07-29): Renamed `front` -> `sprezzature```.
_TITLE_RE = re.compile(r"\):\s*(.+)$")

#: Any subsequent ``## `` line ends the current entry's body.
_NEXT_HEADING_RE = re.compile(r"^##\s")

#: Cap on how much of a release's body becomes the feed summary. Long
#: enough to carry the real content, short enough not to make a single
#: entry (sprezzature-figures' 1.1.0, the main repo's bigger releases)
#: dominate the feed.
SUMMARY_MAX_CHARS: int = 900


@dataclass(frozen=True)
class ChangelogEntry:
    """
    One feed-ready release, parsed from a single CHANGELOG.md heading.

    Attributes
    ----------
    package : str
        Repo / package directory name, e.g. ``sprezzature-colors``.
    version : str
        Version token as it appears in the heading, e.g. ``1.2.0`` or
        ``Unreleased``.
    date_iso : str
        ``YYYY-MM-DD`` release date (the later date, for a range).
    title : str
        Heading-line title, or a short synopsis derived from the first
        line of the entry's body when the heading carries none.
    summary : str
        Body excerpt used as the feed entry's summary/description.
    """

    package: str
    version: str
    date_iso: str
    title: str
    summary: str


def _clean_line(line: str) -> str:
    """Strip a Markdown bullet marker and surrounding whitespace from one line."""
    line = line.strip()
    for marker in ("- ", "* "):
        if line.startswith(marker):
            line = line[len(marker):].strip()
            break
    return line


def _unwrap_lines(body_lines: list[str]) -> list[str]:
    """
    Collapse soft-wrapped Markdown source lines into logical lines.

    These CHANGELOG.md bodies wrap prose at roughly 80 columns, so a
    single bullet item or paragraph sentence spans several physical
    source lines. Reading the first *physical* line only (the naive
    approach) cuts summaries off mid-sentence. This joins continuation
    lines — anything that is not blank, not a ``#`` sub-heading, and
    does not start a new bullet — onto the line above with a single
    space, so each bullet/paragraph becomes one logical line again.

    Parameters
    ----------
    body_lines : list of str
        Raw lines between a release heading and the next one.

    Returns
    -------
    list of str
        Logical lines: sub-heading lines (``### Added``) kept verbatim,
        each bullet or paragraph collapsed to a single line, blank
        lines dropped.
    """
    logical: list[str] = []
    buf: str = ""
    for raw in body_lines:
        stripped = raw.strip()
        is_heading = stripped.startswith("#")
        is_bullet = stripped.startswith("- ") or stripped.startswith("* ")
        if not stripped or is_heading or is_bullet:
            if buf:
                logical.append(buf)
                buf = ""
            if is_heading:
                logical.append(stripped)
            elif is_bullet:
                buf = stripped
            # A blank line is just a paragraph/bullet separator.
        else:
            buf = f"{buf} {stripped}" if buf else stripped
    if buf:
        logical.append(buf)
    return logical


def _synopsis(logical_lines: list[str], limit: int = 80) -> str:
    """
    Derive a short title-like synopsis from a release's (unwrapped) body.

    Skips bare ``###`` sub-headings (``### Added`` carries no information
    on its own); returns the first logical line that does, bullet marker
    stripped, truncated to ``limit`` characters on a word boundary so a
    feed reader's single-line entry list never shows a mid-word cut.

    Parameters
    ----------
    logical_lines : list of str
        Output of :func:`_unwrap_lines`.
    limit : int, optional
        Maximum length before truncating with an ellipsis. Kept short
        (default 80) because this fills the Atom/RSS *title*, which
        readers render as one line in a list — the full text is already
        available in the entry's summary.

    Returns
    -------
    str
        Synopsis, or ``""`` when the body has no usable line.
    """
    for line in logical_lines:
        if line.startswith("#"):
            continue
        line = _clean_line(line)
        if len(line) > limit:
            head = line[:limit]
            cut = head.rfind(" ")
            head = head[:cut] if cut > 0 else head
            line = head.rstrip(" .,;:") + "…"
        return line
    return ""


def _summary_text(logical_lines: list[str], limit: int = SUMMARY_MAX_CHARS) -> str:
    """
    Render a release's (unwrapped) body as a compact plain-text summary.

    ``###`` sub-headings are kept (they carry real structure: Added /
    Changed / Fixed) but demoted to plain text since Atom/RSS summaries
    are not Markdown-aware. Truncated to ``limit`` characters at a line
    boundary where possible.

    Parameters
    ----------
    logical_lines : list of str
        Output of :func:`_unwrap_lines`.
    limit : int, optional
        Maximum length before truncating with an ellipsis.

    Returns
    -------
    str
        Plain-text summary, or ``""`` when the body is empty.
    """
    cleaned = [
        line.lstrip("#").strip() if line.startswith("#") else _clean_line(line)
        for line in logical_lines
    ]
    text = "\n".join(cleaned)
    if len(text) <= limit:
        return text
    truncated = text[:limit].rsplit("\n", 1)[0]
    return truncated.rstrip() + "\n…"


def parse_changelog(path: Path, package: str) -> list[ChangelogEntry]:
    """
    Parse one CHANGELOG.md into a list of dated release entries.

    Parameters
    ----------
    path : Path
        Path to the package's CHANGELOG.md.
    package : str
        Repo / package directory name, used to tag each entry.

    Returns
    -------
    list of ChangelogEntry
        One per heading that carries a full ``YYYY-MM-DD`` date.
        Headings with no date (bare ``## Unreleased``, a year-only
        ``(2025)``) are skipped — there is nothing stable to sort or
        feed on.
    """
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    # Locate every heading line, then slice the body between consecutive
    # headings so each entry gets exactly the text under it.
    heading_idx: list[int] = [i for i, line in enumerate(lines) if _NEXT_HEADING_RE.match(line)]

    entries: list[ChangelogEntry] = []
    for pos, idx in enumerate(heading_idx):
        m = _HEADING_RE.match(lines[idx])
        if not m:
            continue
        version = (m.group("bracket") or m.group("vprefix") or m.group("bare") or "").strip()
        rest = m.group("rest") or ""
        dates = _DATE_RE.findall(rest)
        if not dates:
            continue  # No stable date on the heading line — skip (Unreleased, year-only, ...).
        date_iso = dates[-1]  # A "through" range: the later date is the release date.

        title_m = _TITLE_RE.search(rest)
        heading_title = title_m.group(1).strip() if title_m else ""

        body_end = heading_idx[pos + 1] if pos + 1 < len(heading_idx) else len(lines)
        logical_lines = _unwrap_lines(lines[idx + 1 : body_end])

        title = heading_title or _synopsis(logical_lines)
        summary = _summary_text(logical_lines)
        entries.append(
            ChangelogEntry(
                package=package, version=version, date_iso=date_iso,
                title=title, summary=summary,
            )
        )
    return entries


# ── Feed assembly ─────────────────────────────────────────────────────────

def github_changelog_url(package: str) -> str:
    """
    Return the CHANGELOG.md's GitHub URL for one package.

    Every ``sprezzature-*`` package (and the main ``sprezzature`` repo
    itself) is a standalone GitHub repo — see the JSON-LD
    ``codeRepository`` fields on the site's package pages, e.g.
    ``colors.html`` points ``https://github.com/warith-harchaoui/
    sprezzature-colors`` — so the CHANGELOG lives at that repo's root,
    not under the monorepo path some older reference links use.

    Parameters
    ----------
    package : str
        Repo / package directory name, e.g. ``sprezzature-colors``.

    Returns
    -------
    str
        Absolute GitHub URL to ``CHANGELOG.md`` on the default branch.
    """
    return f"https://github.com/warith-harchaoui/{package}/blob/main/CHANGELOG.md"


def build_posts(
    entries: list[ChangelogEntry],
) -> tuple[list[tuple[Path, str, str, str]], dict[str, str], dict[str, str]]:
    """
    Turn parsed CHANGELOG entries into ``render_atom``/``render_rss`` inputs.

    Parameters
    ----------
    entries : list of ChangelogEntry
        Already sorted newest-first.

    Returns
    -------
    (list of (Path, str, str, str), dict, dict)
        ``posts`` in the ``(relative_path, title, updated_iso, summary)``
        shape the renderers expect, plus the ``entry_ids`` and
        ``entry_links`` dicts keyed by ``relative_path.as_posix()``.
        ``relative_path`` here is a synthetic, non-file key
        (``changelog/<package>/<version>``) — there is no on-site page
        per release, only the id/link overrides matter.
    """
    posts: list[tuple[Path, str, str, str]] = []
    entry_ids: dict[str, str] = {}
    entry_links: dict[str, str] = {}

    for e in entries:
        rel = Path("changelog") / e.package / e.version
        key = rel.as_posix()
        feed_title = f"{e.package} {e.version}: {e.title}" if e.title else f"{e.package} {e.version}"
        updated_iso = f"{e.date_iso}T00:00:00Z"
        posts.append((rel, feed_title, updated_iso, e.summary))
        year = e.date_iso[:4]
        entry_ids[key] = f"tag:sprezzature.ai,{year}:{e.package}-{e.version}"
        entry_links[key] = github_changelog_url(e.package)

    return posts, entry_ids, entry_links


def main() -> int:
    """CLI entry point. Parses every package CHANGELOG.md and writes feed.atom / feed.xml."""
    p = make_parser(
        prog="sprezzature-publish-changelog-feed",
        description="Build the sprezzature.ai Atom + RSS feed from every "
                    "sprezzature-* package's CHANGELOG.md release notes.",
        epilog="Examples:\n"
               "  changelog_feed.py\n"
               "  changelog_feed.py --repos-root .. --out ../web\n"
               "  changelog_feed.py --rss-only\n",
    )
    default_root: Path = Path(__file__).resolve().parents[2]  # .../sprezzature (monorepo root)
    p.add_argument(
        "--repos-root", type=Path, default=default_root.parent,
        help="Directory containing the sprezzature-* sibling repos "
             f"(and, as one of them, sprezzature/). Default: {default_root.parent}",
    )
    p.add_argument(
        "--out", type=Path, default=default_root / "web",
        help=f"Output directory for feed.atom / feed.xml. Default: {default_root / 'web'}",
    )
    p.add_argument(
        "--base-url", default="https://sprezzature.ai",
        help="Absolute origin of the published site. Default: https://sprezzature.ai",
    )
    p.add_argument(
        "--rss-only", action="store_true",
        help="Only write feed.xml (RSS 2.0); skip feed.atom.",
    )
    p.add_argument(
        "--atom-only", action="store_true",
        help="Only write feed.atom (Atom 1.0); skip feed.xml.",
    )
    args = p.parse_args()

    base_url: str = args.base_url.rstrip("/")
    repos_root: Path = args.repos_root.resolve()
    out_dir: Path = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_entries: list[ChangelogEntry] = []
    per_package_counts: dict[str, int] = {}
    for package in PACKAGE_REPOS:
        changelog_path = repos_root / package / "CHANGELOG.md"
        found = parse_changelog(changelog_path, package)
        per_package_counts[package] = len(found)
        if not found:
            print(f"  ⚠ {changelog_path}: no dated release headings found")
        all_entries.extend(found)

    # Newest first; tie-break on package name for a stable, reproducible order.
    all_entries.sort(key=lambda e: (e.date_iso, e.package, e.version), reverse=True)

    posts, entry_ids, entry_links = build_posts(all_entries)

    feed_title = "Sprezzature — Release notes"
    feed_summary = (
        "Combined, date-sorted release notes from the sprezzature-* packages "
        "(accessibility, audio, CLI-to-GUI, colors, figures, maps, UX laws) "
        "and the main sprezzature skills repository."
    )

    if not args.rss_only:
        today = _today_iso()
        feed_id = f"tag:{re.sub(r'^https?://', '', base_url)},{today}:changelog-feed"
        atom_body = render_atom(
            base_url,
            feed_id=feed_id,
            feed_title=feed_title,
            posts=posts,
            entry_ids=entry_ids,
            entry_links=entry_links,
        )
        atom_path = out_dir / "feed.atom"
        atom_path.write_text(atom_body, encoding="utf-8")
        print(f"→ Wrote {atom_path} ({len(posts)} entries)")

    if not args.atom_only:
        rss_body = render_rss(
            base_url,
            feed_title=feed_title,
            feed_description=feed_summary,
            posts=posts,
            entry_ids=entry_ids,
            entry_links=entry_links,
        )
        rss_path = out_dir / "feed.xml"
        rss_path.write_text(rss_body, encoding="utf-8")
        print(f"→ Wrote {rss_path} ({len(posts)} entries)")

    print(f"→ {len(all_entries)} entries from {sum(1 for c in per_package_counts.values() if c)} "
          f"of {len(PACKAGE_REPOS)} packages")
    for package, count in per_package_counts.items():
        print(f"    {package}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
