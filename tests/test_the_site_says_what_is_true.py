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

import html
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB = REPO_ROOT / "web"

#: Written-out numbers the site actually uses for counts.
_WORDS = {
    "five": 5,
    "six": 6,
    "seven": 7,
    "cinq": 5,
    "sept": 7,
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


def _head_of(title: str) -> str:
    """A page title without its brand suffix, folded for comparison.

    Every title on this site ends in an em dash and the project name. What
    comes before it is what the page is about, and that is the half two tags
    have to agree on.
    """
    return html.unescape(title).split("\u2014")[0].strip().lower()


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_social_card_names_the_page(page: Path) -> None:
    """The card a shared link unfurls names the same thing as the <title>.

    `vision.html` is the defect this is shaped around, and it is the reason
    this check has no exemption while the one above has one. The page was
    rewritten into a merge notice -- new title, new body, `noindex`, canonical
    in place -- and its `og:` pair kept the product copy: "Vision - alt text"
    over a paragraph of prose about a local vision model drafting alt text in
    any detected language, as a thing a reader could go and use. Anyone
    sharing the URL shared a card advertising a package that had not existed
    for six days. The page-wide skip above is exactly why nothing saw it: a
    page exempted as "the notice itself" stops being read at all.

    Titles only. An `og:description` is written to sell and a meta description
    to inform, and holding them to the same words would be a check nobody
    could keep green -- which is the kind that gets deleted.
    """
    text = page.read_text(encoding="utf-8", errors="replace")
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    if title is None:
        pytest.skip(f"{page.name} has no <title>")
    for prop, pattern in (
        ("og:title", r'<meta property="og:title" content="([^"]*)"'),
        ("twitter:title", r'<meta name="twitter:title" content="([^"]*)"'),
    ):
        found = re.search(pattern, text)
        if found is None:
            continue
        page_head, card_head = _head_of(title.group(1)), _head_of(found.group(1))
        # Equality, not containment. The first version of this asked whether
        # one head contained the other, and the stale card it was written for
        # passed: "vision" is a substring of "vision is part of accessibility
        # now". A rule that admits the defect it was shaped around is worse
        # than no rule, because it is now also an argument that the defect is
        # gone. All thirty-six pages agree exactly, so exactly is the rule.
        assert page_head == card_head, (
            f"{page.relative_to(WEB)}: <title> says {page_head!r} and {prop} "
            f"says {card_head!r}. A shared link unfurls the second one."
        )


#: The surface cards on ``packages.html``, in the order the page shows them.
#: ``zip`` is a way of delivering a surface rather than one of the five the
#: contract names, which is the distinction the section's own prose makes and
#: the reason the two numbers on that page differ by one.
_SURFACE_CARD = re.compile(
    r'<p class="font-mono text-xs text-brand-linktext">'
    r"(zip|library|biblioth\u00e8que|cli|api|mcp|skills)</p>"
)


@pytest.mark.parametrize("page", ["packages.html", "fr/packages.html"])
def test_the_packages_page_counts_its_own_doors(page: str) -> None:
    """Three statements of one fact: the lede, the heading, and the cards.

    The lede said "reached five different ways" and listed four of them; the
    heading two lines below said "Six ways in"; the section held six cards. A
    reader who counts gets three answers in four lines, on the page whose
    whole argument is that a surface and a re-implementation are different
    things.

    The cards decide, the way the home page's array decides there. Only the
    two numbers that are *about the doors* are read: a count of anything else
    on the page is somebody else's sentence.
    """
    text = (WEB / page).read_text(encoding="utf-8")
    cards = len(_SURFACE_CARD.findall(text))
    assert cards >= 5, f"{page} shows only {cards} surface cards"

    # The lede's "reached N different ways" and the section heading's
    # "N ways in" — not every number on the page. "Five surfaces is the
    # contract", further down, is about the five the contract names, which is
    # deliberately one fewer: the zip is a way of delivering a surface, not a
    # surface. A regex that swept up both would demand the page contradict
    # the distinction it is there to draw.
    spoken = [
        group
        for found in re.findall(
            r"reached (\w+) different ways|atteint de (\w+) fa\u00e7ons"
            r'|<h2[^>]*>(\w+) ways in</h2>|<h2[^>]*>(\w+) portes',
            text,
            re.I,
        )
        for group in found
        if group
    ]
    claims = {_WORDS[word.lower()] for word in spoken if word.lower() in _WORDS}
    assert spoken, f"{page} states no number of ways in; the pattern stopped matching"
    wrong = sorted(c for c in claims if c != cards)
    assert not wrong, (
        f"{page} tells the reader there are {wrong} ways in, and shows "
        f"{cards} cards. The cards are what decide."
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
