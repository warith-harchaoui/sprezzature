"""
A render older than the page it was made from is the wrong film.

``render_films.sh`` compares two mtimes to decide what to re-render: a
project's newest MP4 against its ``index.html``. ``install_films.py`` copies
the newest MP4 into ``web/video/`` and, until this guard, compared nothing —
the same check existing on one side of a handoff and not the other.

Found the hard way on 2026-11-01. ``build_films.py`` had just regenerated all
sixty-six ``index.html`` with new line-breaking, the re-render was still
running, and the installer cheerfully copied a cut from the previous day: 42 MB
of a film whose text had since changed, reported as success. Nothing downstream
could have noticed — the file plays, it is the right shape, and the only wrong
thing about it is the sentence on screen.

Why this is tested here and not by running the installer
--------------------------------------------------------
``install`` shells out to ``sprezzature-video poster`` and writes into
``web/video/``, which is a 300 MB directory outside git. So the comparison is
tested on its own, against a temporary project tree, and the test asserts the
*decision* rather than the copy.

Author
------
Project maintainers.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))


def _installer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The module, with its film tree redirected into *tmp_path*."""
    import install_films

    monkeypatch.setattr(install_films, "FILMS_DIR", tmp_path)
    return install_films


def _project(root: Path, name: str, *, render_age: float, source_age: float) -> None:
    """A project whose render and index.html have the given ages, in seconds."""
    renders = root / name / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    source = root / name / "index.html"
    source.write_text("<html></html>", encoding="utf-8")
    mp4 = renders / f"{name}_2026-11-01_00-00-00.mp4"
    mp4.write_bytes(b"\x00" * 16)
    now = 1_800_000_000.0
    os.utime(mp4, (now - render_age, now - render_age))
    os.utime(source, (now - source_age, now - source_age))


def test_a_render_older_than_its_page_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The case that shipped a stale cut."""
    module = _installer(tmp_path, monkeypatch)
    _project(tmp_path, "accessibility-fr-portrait", render_age=86_400, source_age=60)
    problems = module.install("accessibility", "fr", "portrait")
    assert problems, "a cut older than its page was accepted"
    assert "older than its index.html" in problems[0]
    assert "render_films.sh" in problems[0], "the message does not say how to fix it"


def test_a_render_newer_than_its_page_passes_the_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-vacuity: the check must not refuse everything.

    It stops at the *next* requirement rather than succeeding, because a real
    install needs a poster time, a caption track and ``sprezzature-video``.
    What matters is that the staleness message is not the one that comes back.
    """
    module = _installer(tmp_path, monkeypatch)
    _project(tmp_path, "accessibility-fr-portrait", render_age=60, source_age=86_400)
    problems = module.install("accessibility", "fr", "portrait")
    assert not any("older than its index.html" in p for p in problems), problems


def test_a_missing_render_still_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The older check, which this one must not have displaced."""
    module = _installer(tmp_path, monkeypatch)
    (tmp_path / "accessibility-fr-portrait" / "renders").mkdir(parents=True)
    problems = module.install("accessibility", "fr", "portrait")
    assert problems and "not rendered" in problems[0]


def test_every_canvas_the_page_offers_is_one_the_installer_knows() -> None:
    """The three names have to agree across the generator, the installer and
    the page's own JavaScript, or a button points at a file nobody writes."""
    import build_films
    import install_films

    assert set(install_films.FORMATS) == set(build_films.FORMATS)
    script = (ROOT / "web/js/film-format.js").read_text(encoding="utf-8")
    for canvas, suffix in install_films.FORMATS.items():
        assert canvas in script, f"film-format.js never mentions {canvas!r}"
        if suffix:
            assert f'"{suffix}"' in script, f"film-format.js does not use {suffix!r}"
