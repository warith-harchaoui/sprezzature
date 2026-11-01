"""
The deploy list and the installer must agree about which files exist.

``web/video/`` is not in git — 300 MB of 4K MP4 has no business there — so a
clone carries none of it and ``git status`` can never remind anyone that a
film is pending. ``sftp/UPLOAD-films.txt`` is that reminder, and it is written
by hand.

Two lists, and until this guard nothing compared them. The failure is quiet
and lands on a visitor: a twelfth film ships, the page offers its three
canvases, the manifest still describes eleven, and the portrait button 404s
for everyone. That is the same shape as the eleven-films page whose portrait
and square cuts were never uploaded at all — rendered, named correctly,
offered by the page, and absent from the server.

What this can check without the videos
--------------------------------------
Names, which is the part that drifts. The manifest's ``video/`` entries are
compared against what ``install_films.py`` would write, derived from the same
three registries the installer uses: the films, the languages and the
canvases. No file has to exist, so this runs on a runner exactly as it runs
here.

Three MP4s, three posters and **one** WebVTT per film and language: the three
canvases are the same minute laid out differently and share their captions,
because a second copy could only ever be the first one going stale.

Author
------
Project maintainers.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "brag-output"))

MANIFEST = ROOT / "sftp" / "UPLOAD-films.txt"


def _listed() -> set[str]:
    """Every path the manifest names, comments and blank lines dropped."""
    return {
        line.strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def _installed() -> set[str]:
    """Every path ``install_films.py`` writes, from the same registries it uses."""
    import build_films
    import install_films

    films = sorted({f for f, _ in build_films.cuts()
                    if build_films.FILMS[f]["duration"] >= 30})
    out = set()
    for film in films:
        for lang in install_films.LANGS:
            out.add(f"video/{film}.{lang}.vtt")
            for suffix in install_films.FORMATS.values():
                out.add(f"video/{film}.{lang}{suffix}.mp4")
                out.add(f"video/{film}.{lang}{suffix}.jpg")
    return out


def test_the_manifest_is_here_and_says_something() -> None:
    """Without it there is no list, and a deploy is from memory."""
    assert MANIFEST.is_file(), f"{MANIFEST.relative_to(ROOT)} is missing"
    assert len(_listed()) > 100, f"only {len(_listed())} paths listed"


def test_the_arithmetic_is_what_it_claims() -> None:
    """Non-vacuity. A registry that answered nothing would make the comparison
    below trivially true, which is exactly how this kind of test rots."""
    installed = _installed()
    assert len(installed) == 154, (
        f"expected 11 films x 2 languages x (3 MP4 + 3 posters + 1 VTT) = 154, "
        f"got {len(installed)}"
    )


def test_every_cut_the_installer_writes_is_on_the_upload_list() -> None:
    """The direction that costs a visitor a 404."""
    missing = sorted(_installed() - _listed())
    assert not missing, (
        f"{len(missing)} file(s) the installer writes are not in "
        f"{MANIFEST.name}, so a deploy from that list leaves them behind:\n  "
        + "\n  ".join(missing)
    )


def test_the_upload_list_promises_no_cut_that_is_never_written() -> None:
    """The other direction, which costs an upload that fails on a missing file."""
    extra = sorted({p for p in _listed() if p.startswith("video/")} - _installed())
    assert not extra, (
        f"{MANIFEST.name} names {len(extra)} video file(s) the installer never "
        "writes:\n  " + "\n  ".join(extra)
    )


def test_one_caption_track_per_language_not_per_canvas() -> None:
    """A second copy could only ever be the first one going stale."""
    vtts = {p for p in _installed() if p.endswith(".vtt")}
    assert len(vtts) == 22, f"{len(vtts)} caption tracks for 11 films x 2 languages"
    for suffix in (".portrait.", ".square."):
        assert not [v for v in vtts if suffix in v], (
            f"a canvas has its own caption track ({suffix}); the three share one"
        )
