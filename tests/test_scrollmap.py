"""
Tests for the scrollytelling page builder.

What matters is not that it renders, but that it keeps the two promises the
form is usually broken by: it never takes the scroll away from the reader,
and it still works when the JavaScript does not.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _builder():
    spec = importlib.util.spec_from_file_location(
        "_scrollmap", ROOT / "web" / "tools" / "build_scrollmap.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STORY = {
    "title": "A title",
    "steps": [
        {"text": "one", "plate": "a.svg", "caption": "A"},
        {"text": "two", "plate": "b.svg", "caption": "B"},
    ],
}


def test_it_never_takes_the_scroll() -> None:
    """
    No wheel handler, no programmatic scrolling, no trapping.

    Pages that hijack the scroll are the reason many readers distrust this
    form, and the effect is entirely available without doing it. A future
    edit that reached for scrollTo would be caught here.
    """
    page = _builder().build_page(STORY)
    for forbidden in ("scrollTo", "scrollIntoView", "wheel", "preventDefault", "scrollBy"):
        assert forbidden not in page, f"the page reaches for {forbidden!r}"


def test_it_works_without_javascript() -> None:
    """
    With scripts off the page is a list of paragraphs, each with its figure.

    The body ships with the no-js class and the script removes it, rather
    than the other way round: a page that hides its content until a script
    runs shows nothing when the script does not.
    """
    page = _builder().build_page(STORY)
    assert 'class="no-js"' in page
    assert ".no-js .stage object" in page
    assert "classList.remove('no-js')" in page


def test_the_steps_are_a_real_list() -> None:
    """An ordered list, so a screen reader announces position and length."""
    page = _builder().build_page(STORY)
    assert "<ol" in page and page.count("<li") == 2


def test_reduced_motion_is_honoured() -> None:
    """The cross-fade is a preference, not a requirement."""
    assert "prefers-reduced-motion" in _builder().build_page(STORY)


def test_a_step_without_a_plate_is_refused() -> None:
    """
    Worse than an error: the stage would hold the previous map while the
    text talks about something else, and nothing would look wrong.
    """
    module = _builder()
    with pytest.raises(ValueError, match="names no plate"):
        module.build_page({"steps": [{"text": "orphan"}]})


def test_an_empty_story_is_refused() -> None:
    """A page with no steps is a headline and a blank rectangle."""
    module = _builder()
    with pytest.raises(ValueError, match="at least one step"):
        module.build_page({"steps": []})


def test_text_is_escaped() -> None:
    """Captions travel into JSON inside a script tag; escaping is not optional."""
    module = _builder()
    page = module.build_page({
        "title": "<script>x</script>",
        "steps": [{"text": "a & b", "plate": "p.svg", "caption": "c"}],
    })
    assert "<script>x</script>" not in page.split("<script>")[0]
    assert "a &amp; b" in page
