"""
Unit tests for lint_a11y.py.

Each test feeds a tiny HTML snippet to the parser and asserts that the
expected rule fires (and only that rule). Each rule has a positive and
a negative case where it matters.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path


from lint_a11y import (
    accessible_name,
    lint_file,
    TreeBuilder,
)


def parse(html: str) -> TreeBuilder:
    """Parse a snippet and return the populated TreeBuilder."""
    p = TreeBuilder()
    p.feed(html)
    p.close()
    return p


def lint_str(html: str, tmp_path: Path, ignored: set[str] | None = None) -> list[str]:
    """Lint an in-memory HTML string by writing to a temp file."""
    (tmp_path / "in.html").write_text(html, encoding="utf-8")
    findings = lint_file(tmp_path / "in.html", ignored or set())
    return [f.rule for f in findings]


class TestAccessibleName:
    """The accessible name walks descendants, not just direct text."""

    def test_aria_label_wins(self) -> None:
        p = parse('<button aria-label="Close">×</button>')
        button = p.root.children[0]
        assert accessible_name(button) == "Close"

    def test_descendant_text_counts(self) -> None:
        p = parse("<a href='/'><span>Home</span></a>")
        link = p.root.children[0]
        assert "Home" in accessible_name(link)

    def test_empty_when_no_content(self) -> None:
        p = parse("<button></button>")
        button = p.root.children[0]
        assert accessible_name(button) == ""


class TestImageRules:
    def test_img_missing_alt(self, tmp_path: Path) -> None:
        rules = lint_str("<html lang='en'><body><img src='/x.png'></body></html>", tmp_path)
        assert "img-missing-alt" in rules

    def test_img_with_alt_passes(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><img src='/x.png' alt='A dog'></body></html>",
            tmp_path,
        )
        assert "img-missing-alt" not in rules
        assert "img-redundant-aria" not in rules

    def test_redundant_aria(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body>"
            "<img src='/x.png' alt='' role='presentation'>"
            "</body></html>",
            tmp_path,
        )
        assert "img-redundant-aria" in rules

    def test_empty_alt_alone_passes(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><img src='/x.png' alt=''></body></html>",
            tmp_path,
        )
        assert "img-redundant-aria" not in rules


class TestLinkRules:
    def test_a_missing_href(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><a>Click</a></body></html>",
            tmp_path,
        )
        assert "a-missing-href" in rules

    def test_empty_link(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><a href='/'></a></body></html>",
            tmp_path,
        )
        assert "a-empty" in rules

    def test_link_with_text_passes(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><a href='/'>Home</a></body></html>",
            tmp_path,
        )
        assert "a-empty" not in rules


class TestButtonRule:
    def test_empty_button(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><button></button></body></html>",
            tmp_path,
        )
        assert "button-empty" in rules

    def test_aria_label_button_passes(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><button aria-label='Close'></button></body></html>",
            tmp_path,
        )
        assert "button-empty" not in rules


class TestStructuralRules:
    def test_html_missing_lang(self, tmp_path: Path) -> None:
        rules = lint_str("<html><body>Hi</body></html>", tmp_path)
        assert "html-missing-lang" in rules

    def test_html_with_lang_passes(self, tmp_path: Path) -> None:
        rules = lint_str("<html lang='en'><body>Hi</body></html>", tmp_path)
        assert "html-missing-lang" not in rules

    def test_tabindex_positive(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><div tabindex='3'>x</div></body></html>",
            tmp_path,
        )
        assert "tabindex-positive" in rules

    def test_tabindex_zero_is_fine(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><div tabindex='0'>x</div></body></html>",
            tmp_path,
        )
        assert "tabindex-positive" not in rules

    def test_heading_skip(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><h2>A</h2><h4>B</h4></body></html>",
            tmp_path,
        )
        assert "heading-skip" in rules

    def test_orderly_headings_pass(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><h1>A</h1><h2>B</h2><h3>C</h3></body></html>",
            tmp_path,
        )
        assert "heading-skip" not in rules


class TestDivOnclickAndAriaHidden:
    def test_div_onclick_caught(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body><div onclick='x()'>x</div></body></html>",
            tmp_path,
        )
        assert "div-onclick" in rules

    def test_div_onclick_with_role_button_passes(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body>"
            "<div onclick='x()' role='button' tabindex='0'>x</div>"
            "</body></html>",
            tmp_path,
        )
        assert "div-onclick" not in rules

    def test_aria_hidden_on_button(self, tmp_path: Path) -> None:
        rules = lint_str(
            "<html lang='en'><body>"
            "<button aria-hidden='true' aria-label='x'>X</button>"
            "</body></html>",
            tmp_path,
        )
        assert "aria-hidden-interactive" in rules


class TestFixturesFreeOfFindings:
    """Whole-file negative tests against the skill's own assets."""

    def test_starter_page_passes(self, repo_root: Path) -> None:
        starter = repo_root / "sprezzature-ui" / "assets" / "starter-page.html"
        findings = lint_file(starter, set())
        assert findings == []

    def test_demo_index_passes(self, repo_root: Path) -> None:
        demo = repo_root / "sprezzature-cli-gui" / "assets" / "examples" / "cli-gui-demo" / "public" / "index.html"
        findings = lint_file(demo, set())
        assert findings == []
