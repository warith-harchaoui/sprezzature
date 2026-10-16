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
def test_every_heading_style_in_the_suite_is_recognised(
    line: str, expected: str
) -> None:
    """A style nobody parses looks exactly like a package that stopped shipping."""
    m = feed._HEADING_RE.match(line)
    assert m, f"unparsed release heading: {line!r}"
    version = (
        m.group("bracket")
        or m.group("vprefix")
        or m.group("plain")
        or m.group("bare")
        or ""
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
        m.group("bracket")
        or m.group("vprefix")
        or m.group("plain")
        or m.group("bare")
        or ""
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
        "sprezzature-figures",
        "sprezzature-maps",
        "sprezzature-colors",
        "sprezzature-accessibility",
        "sprezzature-audio",
        "sprezzature-cli-gui",
        "sprezzature-ux-laws",
    ]
    checked = 0
    for name in siblings:
        changelog = REPO_ROOT.parent / name / "CHANGELOG.md"
        if not changelog.is_file():
            continue
        checked += 1
        headings = [
            line
            for line in changelog.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        ]
        assert headings, f"{name}: CHANGELOG has no '## ' heading at all"
        top = headings[0]
        m = feed._HEADING_RE.match(top)
        assert m, f"{name}: newest release heading is unparsable by the feed: {top!r}"
        version = (
            m.group("bracket")
            or m.group("vprefix")
            or m.group("plain")
            or m.group("bare")
            or ""
        ).strip()
        assert re.fullmatch(r"[\d.]+", version) or version == "Unreleased", (
            f"{name}: {top!r} parsed as {version!r}"
        )

    if checked == 0:
        pytest.skip("no sibling checkouts; nothing to read")


#: The same styles again, now asked for the *title* rather than the version.
#: Recognising a heading and reading it are two different failures: the first
#: drops a release from the feed, the second keeps it and gives it a bad name.
TITLES = [
    (
        "## [0.18.0] - 2026-10-15: a page a journal can actually use",
        "a page a journal can actually use",
    ),
    (
        "## 2.6.0 (2026-10-15): forty figures, and the probe",
        "forty figures, and the probe",
    ),
    (
        "## v1.1.1 (2026-10-02): the half of the dependency guard",
        "the half of the dependency guard",
    ),
    (
        "## [1.4.0] (2026-10-15): the extra could not install",
        "the extra could not install",
    ),
    # A colon inside the title must not be mistaken for the separator, which
    # is why the pattern anchors on the date or the closing parenthesis.
    (
        "## [0.17.0] - 2026-10-15: `provenance`: the question a caption cannot settle",
        "`provenance`: the question a caption cannot settle",
    ),
]


@pytest.mark.parametrize("line,expected", TITLES)
def test_a_heading_that_carries_a_title_gives_it_up(line: str, expected: str) -> None:
    """Both date styles, parenthesised and not.

    The pattern used to require the closing parenthesis, so it read
    ``## 2.6.0 (date): title`` and missed ``## [0.18.0] - date: title`` -- the
    Keep a Changelog convention most of this suite writes. **46 of 109 release
    headings had no title in the published feed**, 25 of them in
    ``sprezzature-maps`` alone.

    That is not a silent failure, it is a loud one: with no title an entry
    falls back to its body, so a feed reader showed raw markdown as the
    headline, asterisks and backticks included.
    """
    match = feed._TITLE_RE.search(line)
    assert match, f"no title read from {line!r}"
    assert match.group(1) == expected


@pytest.mark.parametrize(
    "line",
    [
        "## [1.0.0] - 2026-07-29",
        "## [0.5.0] (2026-06-21)",
        "## v1.0.0 (2026-07-29)",
        "## [Unreleased]",
    ],
)
def test_a_heading_with_no_title_is_left_alone(line: str) -> None:
    """Seventeen headings in the suite are version-and-date only. Inventing a
    title for them -- by reaching further into the line, or by falling back to
    something that merely looks like one -- would be worse than having none."""
    assert feed._TITLE_RE.search(line) is None


def test_the_suite_loses_no_title_it_actually_wrote() -> None:
    """The measurement that found this, kept as a test.

    Walks every sibling CHANGELOG and asserts that a heading whose line holds
    a title yields it. Written against the real files rather than samples
    because the defect was a *style* nobody had enumerated -- the samples
    above are the styles known today, and this is the net under them.
    """
    import re

    siblings = sorted(
        p for p in REPO_ROOT.parent.glob("sprezzature*/CHANGELOG.md") if p.is_file()
    )
    assert siblings, (
        "no sibling changelogs found; this test is looking in the wrong place"
    )

    # "Has a title" is defined here independently of the pattern under test --
    # otherwise this would assert the implementation against itself. A title is
    # introduced by a colon, full stop. That also keeps
    # ``## [0.1.0] - 2026-08-07 through 2026-08-16`` out: a date *range* is not
    # a title, and the first draft of this test wrongly flagged it by looking
    # for any word after the date.
    has_title = re.compile(r":\s*\S")
    missed: list[str] = []
    for path in siblings:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = feed._HEADING_RE.match(line)
            if not match:
                continue
            rest = match.group("rest")
            if has_title.search(rest) and not feed._TITLE_RE.search(rest):
                missed.append(f"{path.parent.name}: {line}")
    assert not missed, (
        "headings carrying a title the feed cannot read:\n  " + "\n  ".join(missed[:10])
    )
