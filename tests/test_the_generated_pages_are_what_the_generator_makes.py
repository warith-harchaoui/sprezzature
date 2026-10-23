"""
A generated page equals what its generator produces, right now.

``scripts/build_films_page.py`` writes ``web/films.html`` and
``web/fr/films.html``. Somebody corrected the output by hand and not the
source, and the two drifted in both directions at once:

* the page said "the nine skills" and the generator still said "the ten",
  eight weeks after ``sprezzature-vision`` was folded into
  ``sprezzature-accessibility``;
* the page carried an ``og:image:alt`` describing the title card, and the
  generator emitted no such tag at all.

So running the repository's own documented way to build that page put a stale
count back onto the public site **and** turned two tests in
``test_the_site_holds_together.py`` red. A generated file that cannot be
regenerated is a hand-written file with a misleading header, and the only
moment anyone would find out is the moment they ran the generator -- which is
to say, in the middle of doing something else.

This compares text to text. It is not a style check and it has no tolerance:
the question is whether the two are the same file, and any answer but yes
means one of them is about to be lost.

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_films_page  # noqa: E402


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_films_page_on_disk_is_what_the_generator_writes(lang: str) -> None:
    """Regenerating changes nothing, so nobody loses an edit by running it."""
    page = build_films_page.page_path(lang)
    assert page.is_file(), f"{page} does not exist"
    on_disk = page.read_text(encoding="utf-8")
    fresh = build_films_page.render(lang)
    if on_disk == fresh:
        return
    disk_lines = on_disk.splitlines()
    fresh_lines = fresh.splitlines()
    first = next(
        (
            i
            for i in range(max(len(disk_lines), len(fresh_lines)))
            if disk_lines[i : i + 1] != fresh_lines[i : i + 1]
        ),
        0,
    )
    pytest.fail(
        f"{page.relative_to(REPO_ROOT)} and build_films_page.render({lang!r}) "
        f"differ from line {first + 1}.\n"
        f"  on disk  : {(disk_lines[first:first + 1] or ['<end of file>'])[0][:160]}\n"
        f"  generator: {(fresh_lines[first:first + 1] or ['<end of file>'])[0][:160]}\n"
        f"Fix the generator, then run it -- editing the page alone is how the "
        f"two came apart."
    )


def test_the_generator_actually_produced_something() -> None:
    """A render that returned an empty string would make the test above pass.

    Both sides would be compared and both could be wrong together only if the
    page were empty too, which this rules out from one end.
    """
    for lang in ("en", "fr"):
        html = build_films_page.render(lang)
        assert html.lstrip().startswith("<!doctype html"), lang
        assert len(html) > 10_000, f"{lang}: render() produced {len(html)} characters"
