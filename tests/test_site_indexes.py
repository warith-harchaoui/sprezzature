"""
test_site_indexes — coverage for ``sprezzature-publish/scripts/site_indexes.py``.

Covers URL formatting, title/description extraction, page discovery,
blog-folder resolution, every renderer (robots, sitemap, atom, rss,
humans, llms.txt), and an end-to-end run over a temp project tree.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import site_indexes as si


# ── _format_url ─────────────────────────────────────────────────────────────

class TestFormatUrl:
    def test_collapses_index_html(self):
        # ``section/index.html`` is served at ``section/``.
        assert si._format_url("https://example.com", Path("section/index.html")) == "https://example.com/section/"

    def test_collapses_root_index(self):
        assert si._format_url("https://example.com/", Path("index.html")) == "https://example.com/"

    def test_handles_base_url_without_trailing_slash(self):
        assert si._format_url("https://example.com", Path("about.html")) == "https://example.com/about.html"


# ── _read_title ─────────────────────────────────────────────────────────────

class TestReadTitle:
    def test_html_title_tag(self, tmp_path: Path):
        p = tmp_path / "page.html"
        p.write_text("<html><head><title>Hello</title></head></html>", encoding="utf-8")
        assert si._read_title(p) == "Hello"

    def test_html_h1_fallback(self, tmp_path: Path):
        p = tmp_path / "page.html"
        p.write_text("<h1>From H1</h1>", encoding="utf-8")
        assert si._read_title(p) == "From H1"

    def test_markdown_first_heading(self, tmp_path: Path):
        p = tmp_path / "post.md"
        p.write_text("Front matter junk\n\n# Markdown Title\n\nBody.", encoding="utf-8")
        assert si._read_title(p) == "Markdown Title"

    def test_stem_fallback(self, tmp_path: Path):
        p = tmp_path / "my-page.html"
        p.write_text("<p>Body only.</p>", encoding="utf-8")
        assert si._read_title(p) == "My Page"


# ── _read_description ──────────────────────────────────────────────────────

class TestReadDescription:
    def test_html_meta_description(self, tmp_path: Path):
        p = tmp_path / "page.html"
        p.write_text(
            '<meta name="description" content="A short description">',
            encoding="utf-8",
        )
        assert si._read_description(p) == "A short description"

    def test_markdown_first_paragraph(self, tmp_path: Path):
        p = tmp_path / "post.md"
        p.write_text("# Title\n\nFirst paragraph wins.\n\nSecond.", encoding="utf-8")
        assert si._read_description(p) == "First paragraph wins."

    def test_empty_when_no_description(self, tmp_path: Path):
        p = tmp_path / "page.html"
        p.write_text("<p>No meta tag.</p>", encoding="utf-8")
        assert si._read_description(p) == ""


# ── discover_pages ──────────────────────────────────────────────────────────

class TestDiscoverPages:
    def test_walks_root_and_output_dirs(self, tmp_path: Path):
        (tmp_path / "index.html").write_text("<title>Root</title>", encoding="utf-8")
        (tmp_path / "about.md").write_text("# About", encoding="utf-8")
        (tmp_path / "public").mkdir()
        (tmp_path / "public" / "deep.html").write_text("<title>Deep</title>", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide", encoding="utf-8")

        pages = si.discover_pages(tmp_path)
        names = {p.as_posix() for p in pages}
        assert "index.html" in names
        assert "about.md" in names
        assert "public/deep.html" in names
        assert "docs/guide.md" in names

    def test_skips_unknown_dirs(self, tmp_path: Path):
        (tmp_path / "logs").mkdir()
        (tmp_path / "logs" / "leak.html").write_text("<title>x</title>", encoding="utf-8")
        pages = si.discover_pages(tmp_path)
        assert not any("logs/" in p.as_posix() for p in pages)


# ── find_blog_dir ──────────────────────────────────────────────────────────

class TestFindBlogDir:
    def test_explicit_wins(self, tmp_path: Path):
        (tmp_path / "writings").mkdir()
        result = si.find_blog_dir(tmp_path, Path("writings"))
        assert result == tmp_path / "writings"

    def test_default_posts(self, tmp_path: Path):
        (tmp_path / "posts").mkdir()
        assert si.find_blog_dir(tmp_path, None) == tmp_path / "posts"

    def test_default_blog(self, tmp_path: Path):
        (tmp_path / "blog").mkdir()
        assert si.find_blog_dir(tmp_path, None) == tmp_path / "blog"

    def test_none_when_no_match(self, tmp_path: Path):
        assert si.find_blog_dir(tmp_path, None) is None


# ── render_robots ───────────────────────────────────────────────────────────

class TestRenderRobots:
    def test_has_required_lines(self):
        body = si.render_robots("https://example.com", "https://example.com/sitemap.xml")
        assert "User-agent: *" in body
        assert "Sitemap: https://example.com/sitemap.xml" in body


# ── render_sitemap ──────────────────────────────────────────────────────────

class TestRenderSitemap:
    def test_well_formed_xml(self):
        body = si.render_sitemap("https://example.com", [(Path("about.html"), "2026-06-19")])
        # Parses without error and contains a urlset root.
        root = ET.fromstring(body)
        assert root.tag.endswith("urlset")

    def test_url_count_cap(self, monkeypatch):
        # Drop the cap so the test stays fast, then check it stops at the cap.
        monkeypatch.setattr(si, "SITEMAP_MAX_URLS", 3)
        pages = [(Path(f"p{i}.html"), "2026-06-19") for i in range(10)]
        body = si.render_sitemap("https://example.com", pages)
        root = ET.fromstring(body)
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        assert len(root.findall(f"{ns}url")) == 3


# ── render_atom ─────────────────────────────────────────────────────────────

class TestRenderAtom:
    def test_atom_required_elements(self):
        posts = [(Path("posts/hello.md"), "Hello", "2026-06-19T12:00:00Z", "Short summary.")]
        body = si.render_atom(
            "https://example.com",
            feed_id="tag:example.com,2026:feed",
            feed_title="Test feed",
            posts=posts,
        )
        root = ET.fromstring(body)
        ns = "{http://www.w3.org/2005/Atom}"
        assert root.find(f"{ns}title") is not None
        assert root.find(f"{ns}id") is not None
        assert root.find(f"{ns}updated") is not None
        # rel="self" link present.
        self_link = [l for l in root.findall(f"{ns}link") if l.get("rel") == "self"]
        assert len(self_link) == 1

        entries = root.findall(f"{ns}entry")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.find(f"{ns}title").text == "Hello"
        assert entry.find(f"{ns}id") is not None
        assert entry.find(f"{ns}updated").text == "2026-06-19T12:00:00Z"


# ── render_rss ──────────────────────────────────────────────────────────────

class TestRenderRss:
    def test_rss_structure(self):
        posts = [(Path("posts/hello.md"), "Hello", "2026-06-19T12:00:00Z", "Short summary.")]
        body = si.render_rss(
            "https://example.com",
            feed_title="Channel",
            feed_description="Desc",
            posts=posts,
        )
        root = ET.fromstring(body)
        assert root.tag == "rss"
        assert root.get("version") == "2.0"
        channel = root.find("channel")
        assert channel is not None
        assert channel.find("title").text == "Channel"
        # lastBuildDate present and roughly RFC-822 looking.
        last = channel.find("lastBuildDate")
        assert last is not None and "2026" in last.text
        # One item with the expected title.
        items = channel.findall("item")
        assert len(items) == 1
        assert items[0].find("title").text == "Hello"


# ── render_humans ───────────────────────────────────────────────────────────

class TestRenderHumans:
    def test_has_team_and_site_sections(self):
        body = si.render_humans(
            ["Warith Harchaoui - Author"],
            {"Language": "English", "Doctype": "HTML5"},
        )
        assert "/* TEAM */" in body
        assert "Warith Harchaoui - Author" in body
        assert "/* SITE */" in body
        assert "Language: English" in body

    def test_handles_empty_authors(self):
        body = si.render_humans([], {})
        # Falls back to a placeholder so the file is never empty.
        assert "/* TEAM */" in body
        assert "Author" in body


# ── End-to-end main() ───────────────────────────────────────────────────────

class TestMain:
    def test_full_project_tree(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
        # Build a tiny project: a README, a public/index.html, a docs/ page,
        # and a posts/ directory with one post.
        (tmp_path / "README.md").write_text("# My Project\n\nA test project.", encoding="utf-8")
        (tmp_path / "index.html").write_text("<title>Home</title>", encoding="utf-8")
        (tmp_path / "public").mkdir()
        (tmp_path / "public" / "about.html").write_text("<title>About</title>", encoding="utf-8")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide\n\nDescription.", encoding="utf-8")
        (tmp_path / "posts").mkdir()
        (tmp_path / "posts" / "hello.md").write_text("# Hello\n\nFirst post.", encoding="utf-8")

        out = tmp_path / "_out"
        argv = [
            "site_indexes",
            "--root", str(tmp_path),
            "--out", str(out),
            "--base-url", "https://example.com",
        ]
        monkeypatch.setattr(sys, "argv", argv)
        rc = si.main()
        assert rc == 0

        # Always-on outputs.
        assert (out / "robots.txt").is_file()
        assert (out / "sitemap.xml").is_file()
        assert (out / "llms.txt").is_file()

        # Sitemap mentions discovered pages.
        sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
        assert "about.html" in sitemap
        assert "guide.md" in sitemap

        # Feed file is the Atom variant (default) and lists the post.
        atom = (out / "feed.atom").read_text(encoding="utf-8")
        assert "Hello" in atom
        # Auto-detected project name comes from the README's H1.
        llms = (out / "llms.txt").read_text(encoding="utf-8")
        assert llms.startswith("# My Project")
