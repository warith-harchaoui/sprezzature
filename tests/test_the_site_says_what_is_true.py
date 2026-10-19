"""
The website is a claim about the suite, and claims go stale silently.

Every number on it was hand-typed and every one of them drifted. On
2026-10-19 the site was, simultaneously: advertising `sprezzature-vision` as a
tenth skill eight weeks after it was folded into `sprezzature-accessibility`;
saying "ten skills" in a `<title>`, a meta description and two schema blocks
above nine cards; telling a reader the accessibility linter had fifteen rules
when it had twenty; and claiming on one line of `packages.html` that eight
packages were on PyPI and on another that nine were.

None of that was visible from inside any package. Each brick guards its own
numbers — `sprezzature-accessibility` has a test that compares every rule
count in its own documents against `len(ALL_RULES)` — and the website is in
this repository, outside all of them. So the guard goes here, where the site
and the nine packages are both in reach.

What is deliberately *not* checked: prose. A claim this cannot see is a claim
somebody has to keep true by hand, which is the situation that produced all of
the above; the answer to that is to derive the number, as
`web/tools/site_indexes.py` now does for its tagline, rather than to write a
regex that pretends to read English.

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

#: Written-out numbers the site actually uses for counts.
_WORDS = {
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
    "onze": 11,
}

_PAGES = sorted(
    [p for p in WEB.glob("*.html") if p.name != "head.html"]
    + list((WEB / "fr").glob("*.html"))
)


def _skill_cards(page: Path) -> int:
    """How many skill cards the home page's own array declares."""
    return len(
        re.findall(r"^      \['sprezzature", page.read_text(encoding="utf-8"), re.M)
    )


def test_there_are_pages_to_check() -> None:
    """A glob that stops matching would make everything below vacuous."""
    assert len(_PAGES) >= 30, [p.name for p in _PAGES]


@pytest.mark.parametrize("home", ["index.html", "fr/index.html"])
def test_the_home_page_counts_its_own_cards(home: str) -> None:
    """`ten skills` above nine cards is the exact defect this catches.

    The count is written in a <title>, a meta description, an og: and a
    twitter: pair, and two schema.org blocks — six places, one array.
    """
    page = WEB / home
    cards = _skill_cards(page)
    assert cards >= 8, f"{home} declares only {cards} skill cards"

    text = page.read_text(encoding="utf-8")
    claims = {
        _WORDS[word.lower()]
        for word in re.findall(
            r"\b(eight|nine|ten|eleven|huit|neuf|dix|onze)\b(?=\s+(?:Claude|skills|compétences))",
            text,
            re.I,
        )
    }
    wrong = sorted(c for c in claims if c != cards)
    assert not wrong, (
        f"{home} tells the reader there are {wrong} skills, and lists {cards} "
        f"cards. The card array is what decides."
    )


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_no_page_still_advertises_a_merged_away_brick(page: Path) -> None:
    """`sprezzature-vision` became part of `sprezzature-accessibility`.

    Its own page survives as a noindexed notice pointing readers at the new
    home — that is the point of it — so the rule is about every *other* page.
    """
    if page.stem == "vision":
        pytest.skip("vision.html is the merge notice itself")
    text = page.read_text(encoding="utf-8")
    assert "sprezzature-vision" not in text, (
        f"{page.name} names sprezzature-vision, which has not existed as a "
        f"package since it was folded into sprezzature-accessibility"
    )


def test_the_sitemap_does_not_offer_a_noindexed_page() -> None:
    """Listing a page that asks not to be indexed is a contradiction.

    `web/tools/site_indexes.py` filters these out; this holds the generated
    file to it, because the generator is only run by hand.
    """
    sitemap = (WEB / "sitemap.xml").read_text(encoding="utf-8")
    noindexed = [
        p
        for p in _PAGES
        if "noindex" in p.read_text(encoding="utf-8", errors="replace")[:4000]
    ]
    assert noindexed, "no noindexed page found — has the convention changed?"
    for page in noindexed:
        rel = page.relative_to(WEB).as_posix()
        assert rel not in sitemap, (
            f"sitemap.xml lists {rel}, whose own <head> tells robots not to "
            f"index it. Re-run web/tools/site_indexes.py."
        )


def test_every_package_the_site_names_is_one_the_suite_ships() -> None:
    """A package page for something that does not exist is worse than none."""
    shipped = {
        p.name for p in REPO_ROOT.glob("sprezzature-*") if (p / "SKILL.md").is_file()
    }
    assert shipped, "no skill folders found — has the layout changed?"

    named: set[str] = set()
    for page in _PAGES:
        if page.stem == "vision":
            continue
        named |= set(
            re.findall(
                r"\bsprezzature-[a-z][a-z-]+\b", page.read_text(encoding="utf-8")
            )
        )

    # Names that are CSS/JS identifiers rather than packages, and the console
    # scripts the packages install — both legitimately appear in prose.
    not_packages = {
        n
        for n in named
        if n not in shipped
        and (
            n.startswith(tuple(f"{s}-" for s in shipped))
            or n
            in {"sprezzature-color-mode", "sprezzature-theme", "sprezzature-skills"}
        )
    }
    unknown = sorted(named - shipped - not_packages)
    assert not unknown, (
        f"the site names {unknown}, which the suite does not ship as a brick"
    )
