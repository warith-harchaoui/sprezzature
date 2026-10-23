"""
The contrast ratios written in the stylesheet's comment, re-derived.

``css/tailwind-input.css`` carries a paragraph of reasoning and four numbers:
that ``text-brand-blue`` sits directly on the page background rather than
inside a button, that academic's base blue is "only 3.79:1 on the dark theme's
#0B0B0C background", that it was lightened to ``#1F81C2`` "(4.66:1)", and that
corporate's "already clears 4.9:1". Every one of those is hand-typed, and the
reason ``test_the_site_says_what_is_true.py`` exists is that every hand-typed
number on this site drifted.

Nothing checked them. ``sprezzature-colors`` ships the contrast engine, and
its own CLI takes a JSON palette rather than a page, so pointing it at this
stylesheet was never one command. This file closes that: four theme-and-scheme
combinations, two page backgrounds, one floor.

The parser matches a selector **whole**. A first pass asked whether the block's
selector *contained* ``[data-color-mode="academic"]`` -- which
``[data-color-mode="academic"][data-color-scheme="dark"]`` does -- and so read
the dark value while believing it was measuring the light one. It reported two
failures on a stylesheet that has none. A measurement is checked by looking at
which side it puts the case you already know is good.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STYLESHEET = REPO_ROOT / "web" / "css" / "tailwind-input.css"

#: WCAG 2.2 AA for body text. Links are body text here: they sit in running
#: prose, not in a button, which is the whole reason this token exists.
AA_BODY: float = 4.5

#: The page backgrounds, as the markup sets them: white, and the near-black
#: the dark theme paints. Read from the pages rather than invented -- the
#: stylesheet comment names ``#0B0B0C`` and so does every page's theme-color.
SURFACES: dict[str, str] = {"light": "#FFFFFF", "dark": "#0B0B0C"}

#: ``(name, selector, surface)`` for every combination a reader can be in.
COMBINATIONS: tuple[tuple[str, str, str], ...] = (
    ("academic light", '[data-color-mode="academic"]', "light"),
    ("academic dark", '[data-color-mode="academic"][data-color-scheme="dark"]', "dark"),
    ("corporate light", '[data-color-mode="corporate"]', "light"),
    ("corporate dark", '[data-color-mode="corporate"][data-color-scheme="dark"]', "dark"),
)

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
_LINKTEXT = re.compile(r"--brand-linktext-rgb:\s*([\d\s]+);")


def _declared_link_colours() -> dict[str, str]:
    """``selector -> #RRGGBB`` for every block declaring the link token.

    Comments are stripped first: a ``/* … */`` holding a hex code would
    otherwise be read as a selector, which is how the first version of this
    produced a dozen nonsense rows alongside the real four.
    """
    css = _COMMENT.sub(" ", STYLESHEET.read_text(encoding="utf-8"))
    declared: dict[str, str] = {}
    for rule in _RULE.finditer(css):
        value = _LINKTEXT.search(rule.group(2))
        if value is None:
            continue
        triplet = tuple(int(part) for part in value.group(1).split())
        for selector in (s.strip() for s in rule.group(1).split(",")):
            declared[selector] = "#%02X%02X%02X" % triplet
    return declared


def _relative_luminance(colour: str) -> float:
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(one: str, other: str) -> float:
    high, low = sorted((_relative_luminance(one), _relative_luminance(other)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize(
    ("name", "selector", "surface"), COMBINATIONS, ids=[c[0] for c in COMBINATIONS]
)
def test_link_text_clears_aa_in_every_theme(name: str, selector: str, surface: str) -> None:
    """Every mode-and-scheme a reader can land in clears 4.5:1."""
    declared = _declared_link_colours()
    colour = declared.get(selector)
    assert colour is not None, (
        f"{selector} declares no --brand-linktext-rgb. Either the token was "
        f"renamed or the selector changed; the ratio below is unmeasurable "
        f"either way. Declared: {sorted(declared)}"
    )
    ratio = _contrast(colour, SURFACES[surface])
    assert ratio >= AA_BODY, (
        f"{name}: link text {colour} on {SURFACES[surface]} is {ratio:.2f}:1, "
        f"under WCAG AA's {AA_BODY}:1 for body text"
    )


def test_the_stylesheet_was_actually_read() -> None:
    """Four combinations, four colours: a parser that found none would pass.

    Every assertion above is "this ratio is high enough", and a parser that
    stopped matching makes all four unmeasurable rather than false. This is
    the one that notices.
    """
    declared = _declared_link_colours()
    assert len(declared) >= 4, (
        f"read {len(declared)} link-colour declarations from "
        f"{STYLESHEET.name}; the stylesheet carries at least four"
    )
    wanted = {selector for _, selector, _ in COMBINATIONS}
    assert wanted <= set(declared), f"missing {sorted(wanted - set(declared))}"
