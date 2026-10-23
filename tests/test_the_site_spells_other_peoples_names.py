"""
The site spells other projects' names the way their owners spell them.

``GitHub`` was written ``Github`` seventy-two times and ``GitHub`` twenty, and
the two forms met on the home page's first screen: the nav said
``⭐️ on Github`` and the hero button right under it said ``Give a ⭐ on
GitHub``. Nobody is misled by it, which is exactly why it survived thirty-six
pages and two languages -- and it is the one class of error a project arguing
that a name quoted to a reader must come from the thing it names cannot
afford on its own front page.

Three exclusions, each for a reason, and each with teeth of its own below:

* **URLs and attributes.** ``github.com`` is lowercase because the host is.
* **``<code>``.** ``markdown to website`` and ``lint markdown`` are trigger
  phrases quoted verbatim from a skill. A quotation is not prose, and
  correcting its capitalisation would make the page quote something the skill
  does not say.
* **``<script>`` / ``<style>``.** Identifiers, not writing.

The table is deliberately short. Every entry is a name this suite actually
uses; inventing rules for names the site never writes would make the guard
look thorough and check nothing.

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

#: ``wrong spelling -> the owner's spelling``. Only names the site writes.
HOUSE_STYLE: dict[str, str] = {
    "Github": "GitHub",
    "GITHUB": "GitHub",
    "Pypi": "PyPI",
    "PyPi": "PyPI",
    "Javascript": "JavaScript",
    "Typescript": "TypeScript",
    "MacOS": "macOS",
    "TailwindCSS": "Tailwind CSS",
    "Open AI": "OpenAI",
    "Latex": "LaTeX",
    "Numpy": "NumPy",
}

_PAGES = sorted(
    [p for p in WEB.glob("*.html") if p.name != "head.html"]
    + list((WEB / "fr").glob("*.html"))
)

_CODE = re.compile(r"<code\b[^>]*>.*?</code>", re.S | re.I)
_SCRIPTISH = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_ATTRIBUTE = re.compile(r'\b(?:href|src|srcset|content|id|class|data-[\w-]+)="[^"]*"')


def _prose(markup: str) -> str:
    """What the page says in its own voice: no code, no URLs, no identifiers."""
    markup = _SCRIPTISH.sub(" ", markup)
    markup = _CODE.sub(" ", markup)
    return _ATTRIBUTE.sub(" ", markup)


@pytest.mark.parametrize("page", _PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_a_page_spells_other_projects_the_way_they_do(page: Path) -> None:
    """No misspelled proper name in a page's own prose."""
    prose = _prose(page.read_text(encoding="utf-8", errors="replace"))
    wrong = {
        bad: right
        for bad, right in HOUSE_STYLE.items()
        if re.search(r"(?<![\w.-])" + re.escape(bad) + r"(?![\w.-])", prose)
    }
    assert not wrong, (
        f"{page.relative_to(WEB)} writes {wrong}. The owner's spelling is the "
        f"right-hand side."
    )


def test_the_code_exclusion_is_doing_work() -> None:
    """The ``<code>`` carve-out protects something real, not nothing.

    Without this, a carve-out that stopped matching would read as a guard
    that got stricter. ``publish.html`` quotes two trigger phrases that are
    lowercase on purpose -- they are what the skill answers to -- and they are
    the reason the exclusion exists.
    """
    page = WEB / "publish.html"
    markup = page.read_text(encoding="utf-8")
    quoted = [
        block for block in _CODE.findall(markup) if "markdown" in block
    ]
    assert quoted, (
        "publish.html no longer quotes a lowercase trigger phrase inside "
        "<code>. Either the page changed or the pattern stopped matching; "
        "check which before trusting the exclusion above."
    )


def test_there_are_pages_to_check() -> None:
    """A glob that stops matching would make everything above vacuous."""
    assert len(_PAGES) >= 30, [p.name for p in _PAGES]
