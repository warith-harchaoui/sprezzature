"""
The release feed has to read every CHANGELOG in the suite, not most of them.

``sprezzature-publish/scripts/changelog_feed.py`` builds sprezzature.ai's Atom
and RSS feeds by parsing each sibling package's ``CHANGELOG.md``. The eight
repositories do not write release headings the same way, and never agreed to:

* ``## [0.18.0] - 2026-10-15: …``  — maps, colors, accessibility, ux-laws
* ``## v1.1.1 (2026-10-02): …``    — audio, cli-gui
* ``## 2.6.0 (2026-10-15): …``     — figures, since 2.0.0
* ``## [1.4.0] (2026-10-15): …``   — this repository

The parser knew the first, second and fourth. It did not know the third, so
``sprezzature-figures`` published 1.0.0, 1.0.1 and 1.1.0 to the feed and then
appeared to stop releasing — for seven versions and several months, while the
generator printed a success line naming it as one of the packages it had read.

That is the failure mode worth a test: a heading style the parser does not
recognise is indistinguishable, in the output and in the logs, from a package
that has nothing to announce. Counting entries per package is how the
difference becomes visible.

Author
------
Project maintainers.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FEED_SCRIPT = REPO_ROOT / "sprezzature-publish" / "scripts" / "changelog_feed.py"


def _module():
    spec = importlib.util.spec_from_file_location("changelog_feed", FEED_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["changelog_feed"] = mod
    spec.loader.exec_module(mod)
    return mod


feed = _module()


#: One heading per style actually in use, with the version it must yield.
HEADINGS = [
    ("## [0.18.0] - 2026-10-15: a page a journal can actually use", "0.18.0"),
    ("## v1.1.1 (2026-10-02): the half of the dependency guard", "1.1.1"),
    ("## 2.6.0 (2026-10-15): forty figures, and the probe", "2.6.0"),
    ("## [1.4.0] (2026-10-15): the extra could not install", "1.4.0"),
    ("## [Unreleased]", "Unreleased"),
    ("## Unreleased", "Unreleased"),
]


@pytest.mark.parametrize("line,expected", HEADINGS)
def test_every_heading_style_in_the_suite_is_recognised(line: str, expected: str) -> None:
    """A style nobody parses looks exactly like a package that stopped shipping."""
    m = feed._HEADING_RE.match(line)
    assert m, f"unparsed release heading: {line!r}"
    version = (
        m.group("bracket") or m.group("vprefix") or m.group("plain") or m.group("bare") or ""
    ).strip()
    assert version == expected, f"{line!r} parsed as {version!r}, expected {expected!r}"


@pytest.mark.parametrize(
    "line",
    [
        "## Releases",
        "## 3 things that changed",
        "## Installing",
    ],
)
def test_prose_headings_are_not_read_as_releases(line: str) -> None:
    """The bare-dotted branch needs ``major.minor``, or prose becomes a release."""
    m = feed._HEADING_RE.match(line)
    if m is None:
        return
    version = (
        m.group("bracket") or m.group("vprefix") or m.group("plain") or m.group("bare") or ""
    ).strip()
    assert not re.fullmatch(r"\d+\.\d[\w.\-]*", version), (
        f"prose heading {line!r} was read as release {version!r}"
    )


def test_each_sibling_changelog_yields_its_newest_release() -> None:
    """
    Every repository present on disk must contribute its top release heading.

    Reads the first ``## `` heading of each sibling ``CHANGELOG.md`` and asks
    the parser for it. Skips a repository that is not checked out; this is a
    check for the machine that cuts the release, like the floors check next to
    it. The main repo's first heading is prose (``## Releases``), so it is
    matched against its first *release* heading instead.
    """
    siblings = [
        "sprezzature-figures", "sprezzature-maps", "sprezzature-colors",
        "sprezzature-accessibility", "sprezzature-audio", "sprezzature-cli-gui",
        "sprezzature-ux-laws",
    ]
    checked = 0
    for name in siblings:
        changelog = REPO_ROOT.parent / name / "CHANGELOG.md"
        if not changelog.is_file():
            continue
        checked += 1
        headings = [
            line for line in changelog.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        ]
        assert headings, f"{name}: CHANGELOG has no '## ' heading at all"
        top = headings[0]
        m = feed._HEADING_RE.match(top)
        assert m, f"{name}: newest release heading is unparsable by the feed: {top!r}"
        version = (
            m.group("bracket") or m.group("vprefix") or m.group("plain") or m.group("bare") or ""
        ).strip()
        assert re.fullmatch(r"[\d.]+", version) or version == "Unreleased", (
            f"{name}: {top!r} parsed as {version!r}"
        )

    if checked == 0:
        pytest.skip("no sibling checkouts; nothing to read")
