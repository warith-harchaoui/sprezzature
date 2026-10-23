"""
A class in the markup has a rule somewhere the page loads.

``web/css/app.css`` is a **content-scanned** Tailwind build, committed so the
site needs no build step to serve. The consequence nobody feels until it bites:
a class written into a page after the last build has no rule, the page renders
exactly as if the class were not there, and nothing says so. It is the quietest
failure on the site — no error, no missing file, no console warning, just a box
that is not tinted.

Two ways in, both found the same afternoon:

* **A colour the theme never declared.** Four pages — ``audio.html`` and
  ``maps.html`` in both languages — carried a "work in progress" callout styled
  ``border-brand-orange/40 bg-brand-orange/10``. ``brand-orange`` was in no
  palette and no config, Tailwind emits no rule for a colour it does not know,
  and the callout rendered with no background and no border on all four.
* **A utility added without rebuilding.** Adding ``object-left`` to a card did
  nothing at all until ``npx tailwindcss`` ran again. ``css/BUILD.md`` says
  "rebuild after changing any page's classes" and nothing enforced it.

The question asked here is the general one — is this class defined anywhere the
page loads — rather than "is this a Tailwind class", which would need a list of
every utility prefix and would rot. Stylesheets, inline ``<style>`` blocks and
the compiled build all count as a definition.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

#: Names a generator writes as markers, with nothing styling them. Each one is
#: traced to the line that emits it, because "it is probably a hook" is the
#: sentence that would turn this guard into a list of unexplained exceptions.
MARKERS: dict[str, str] = {
    "fm-card": "case-studies/financial-markets/build.py:331 writes it on each <figure>",
    "panel-svg": "case-studies/financial-markets/market_style.py:382 writes it on each <svg>",
}

_PAGES = sorted(
    [p for p in WEB.glob("*.html") if p.name != "head.html"]
    + list((WEB / "fr").glob("*.html"))
)

_CLASS_ATTR = re.compile(r'\bclass="([^"]*)"')
_STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
#: A class selector, with CSS escapes kept so ``.sm\:flex`` is read as
#: ``sm:flex`` rather than as ``sm``.
_CLASS_SELECTOR = re.compile(r"\.((?:[\w-]|\\.)+)")


def _unescape(selector: str) -> str:
    return re.sub(r"\\(.)", r"\1", selector)


def _defined() -> set[str]:
    """Every class name any stylesheet or inline style block defines."""
    names: set[str] = set()
    for sheet in WEB.rglob("*.css"):
        for match in _CLASS_SELECTOR.finditer(sheet.read_text(encoding="utf-8", errors="replace")):
            names.add(_unescape(match.group(1)))
    for page in _PAGES:
        body = page.read_text(encoding="utf-8", errors="replace")
        for block in _STYLE_BLOCK.findall(body):
            for match in _CLASS_SELECTOR.finditer(block):
                names.add(_unescape(match.group(1)))
    return names


@pytest.fixture(scope="module")
def defined() -> set[str]:
    return _defined()


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_uses_no_class_that_styles_nothing(page: Path, defined: set[str]) -> None:
    """Every class on the page resolves to a rule, or is a declared marker."""
    used = {
        token
        for attr in _CLASS_ATTR.findall(page.read_text(encoding="utf-8", errors="replace"))
        for token in attr.split()
    }
    orphans = sorted(used - defined - set(MARKERS))
    assert not orphans, (
        f"{page.relative_to(WEB)} uses {orphans}, which no stylesheet defines. "
        f"Either the Tailwind build is stale — `npx tailwindcss@3 -c "
        f"tailwind.config.js -i css/tailwind-input.css -o css/app.css --minify` "
        f"from web/ — or the class names something the theme does not have."
    )


def test_the_markers_are_still_markers(defined: set[str]) -> None:
    """A marker that acquires a rule should leave this list.

    Otherwise the exception outlives its reason and the next reader cannot
    tell a deliberate hook from a forgotten one.
    """
    styled = sorted(name for name in MARKERS if name in defined)
    assert not styled, (
        f"{styled} now have CSS rules, so they are no longer unstyled markers. "
        f"Remove them from MARKERS — the guard covers them on its own."
    )


def test_the_stylesheets_were_read(defined: set[str]) -> None:
    """A regex that stopped matching would declare every class undefined.

    The failure mode is the opposite of vacuous here — an empty set makes
    every page above fail — but the message would blame the pages instead of
    the parser, so it is worth saying which it is.
    """
    assert len(defined) > 200, (
        f"read {len(defined)} class names from web/**/*.css; the compiled "
        f"Tailwind build alone defines several hundred"
    )
    assert "object-cover" in defined, "the compiled Tailwind build was not read"
