"""
Every animated figure must stop when the reader has asked motion to stop.

Fifty-seven SVGs in this repository move. They move in three different ways,
and each way needs a different guard — which is why this had gone wrong
quietly in twenty-two of them:

- **SMIL** (``<animate>``, ``<animateTransform>``) is a timeline the document
  owns. CSS cannot touch it. The only things that stop it are
  ``pauseAnimations()`` on the SVG element, or removing the animated element
  from rendering with ``display: none``.
- **CSS animations** are stopped by ``animation: none`` under a ``reduce``
  query, or better, by only declaring them under ``no-preference`` at all.
- **The trap**: a ``@media (prefers-reduced-motion: reduce)`` block holding
  ``animation: none`` in front of a figure whose motion is SMIL. It reads
  exactly like a guard, it passes any check that greps for the media query,
  and it does nothing. ``pictorial.svg`` and ``radial-bar.svg`` shipped that
  in four copies each.

And the rule the second half of this file is about: **a frozen animation must
be seeked to its end, never to zero.** ``gauge.svg``'s needle animates from
289.2 degrees to its real reading of 322.8 and freezes there. Pausing at
``setCurrentTime(0)`` — the obvious guard, and the one the looping figures
correctly use — would leave an accessible reader looking at a gauge showing a
number the chart does not mean. The guard would have made the figure lie.

Nothing here needs a browser: SMIL timing and the CSS are both decidable from
the source.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SVG_NS = "{http://www.w3.org/2000/svg}"
SMIL_TAGS = {
    SVG_NS + tag
    for tag in ("animate", "animateTransform", "animateMotion", "set")
}

#: Directories that hold shipped figures. Every figure exists in up to four
#: copies — the gallery, its French twin, the academic theme and the skill's
#: bundled examples — and a fix applied to one of them is a fix the other
#: three readers never get. The glob is deliberately repo-wide for that
#: reason: it is the only version of this check that cannot miss a copy.
FIGURE_GLOBS = ("web/img/figures/**/*.svg", "sprezzature-figures/assets/**/*.svg")


def _strip_fonts(text: str) -> str:
    """Drop base64 font payloads so the regexes below stay cheap.

    ``wireframe3d.svg`` is 1.9 MB, nearly all of it two embedded variable
    fonts. Nothing in this file cares about them.
    """
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "b64", text)


def _animated_svgs() -> list[Path]:
    """Every shipped SVG that moves."""
    found: list[Path] = []
    for pattern in FIGURE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            text = _strip_fonts(path.read_text(encoding="utf-8", errors="replace"))
            if re.search(r"<animate[A-Za-z]*\b|<set\b", text) or re.search(
                r"[^-]animation\s*:\s*(?!none)", text
            ):
                found.append(path)
    return found


ANIMATED = _animated_svgs()


def _reduce_blocks(text: str) -> list[str]:
    return re.findall(
        r"@media\s*\(prefers-reduced-motion:\s*reduce\)[^{]*\{(?:[^{}]|\{[^{}]*\})*\}",
        text,
    )


def _classes_hidden_under_reduce(text: str) -> set[str]:
    """Classes a reduce block removes from rendering with ``display: none``.

    Only ``display: none`` is collected. ``animation: none`` is deliberately
    *not*: against SMIL it is the trap described at the top of this file.
    """
    hidden: set[str] = set()
    for block in _reduce_blocks(text):
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", block):
            if "display" in body and "none" in body:
                hidden.update(re.findall(r"\.([A-Za-z0-9_-]+)", selectors))
    return hidden


def _every_animation_is_hidden(path: Path, classes: set[str]) -> bool:
    """Does every SMIL element sit inside an element carrying one of these?"""
    if not classes:
        return False
    tree = ET.parse(path)
    parents = {child: parent for parent in tree.iter() for child in parent}
    animations = [node for node in tree.iter() if node.tag in SMIL_TAGS]
    for node in animations:
        current, covered = node, False
        while current is not None:
            if set((current.get("class") or "").split()) & classes:
                covered = True
                break
            current = parents.get(current)
        if not covered:
            return False
    return True


def _smil(text: str) -> list[str]:
    return re.findall(r"<animate[A-Za-z]*\b[^>]*>|<set\b[^>]*>", text)


def _last_moment(tags: list[str]) -> float:
    """When the last non-looping animation finishes, in seconds."""
    end = 0.0
    for tag in tags:
        if 'repeatCount="indefinite"' in tag:
            continue
        begin = re.search(r'begin="([-0-9.]+)s?"', tag)
        duration = re.search(r'dur="([0-9.]+)s"', tag)
        end = max(
            end,
            (float(begin.group(1)) if begin else 0.0)
            + (float(duration.group(1)) if duration else 0.0),
        )
    return end


def _seek(text: str) -> float | None:
    """The time the reduced-motion guard seeks to, if there is one."""
    match = re.search(
        r"prefers-reduced-motion[^}]*?setCurrentTime\(([0-9.]+)\)", text, re.S
    )
    return float(match.group(1)) if match else None


def test_there_are_animated_figures_to_check() -> None:
    """
    A guard over an empty list is a guard over nothing.

    If a refactor moves the figures and the globs above stop matching, every
    other test in this file would pass by vacuum. This is the canary.
    """
    assert len(ANIMATED) >= 50, (
        f"only {len(ANIMATED)} animated figures found; the globs have "
        f"probably stopped matching"
    )


@pytest.mark.parametrize(
    "path", ANIMATED, ids=lambda p: str(p.relative_to(ROOT))
)
def test_the_motion_can_be_stopped(path: Path) -> None:
    """
    Each figure carries a guard that works against the kind of motion it has.

    Three mechanisms are accepted, and each is only accepted for the motion
    it can actually stop.
    """
    text = _strip_fonts(path.read_text(encoding="utf-8", errors="replace"))
    tags = _smil(text)

    if tags:
        script_guard = "pauseAnimations" in text and "prefers-reduced-motion" in text
        hidden = _every_animation_is_hidden(
            path, _classes_hidden_under_reduce(text)
        )
        assert script_guard or hidden, (
            f"{path.relative_to(ROOT)} animates with SMIL "
            f"({len(tags)} elements) and nothing stops it. CSS cannot: only "
            f"pauseAnimations() under a reduced-motion query, or display:none "
            f"on an ancestor, will. A reduce block holding `animation: none` "
            f"is the trap -- it reads as a guard and does nothing."
        )
        return

    # CSS-only motion.
    opt_in = re.search(r"@media\s*\(prefers-reduced-motion:\s*no-preference\)", text)
    killed = any(
        "animation" in block and "none" in block for block in _reduce_blocks(text)
    )
    assert opt_in or killed, (
        f"{path.relative_to(ROOT)} has a CSS animation that runs whatever the "
        f"reader has asked for"
    )


@pytest.mark.parametrize(
    "path", ANIMATED, ids=lambda p: str(p.relative_to(ROOT))
)
def test_a_frozen_animation_rests_on_its_end_not_its_start(path: Path) -> None:
    """
    The rule that keeps an accessible rendering from showing a false value.

    ``fill="freeze"`` means the animation holds its last value forever: the
    figure's real state is the END of the timeline, and the markup's static
    attributes are written to match it. Seek such a figure to 0 and it rests
    on the *pre-animation* state instead — a gauge needle at 289.2 degrees
    rather than the 322.8 it is reporting, bars at the width they grew from
    rather than the width they mean.

    Looping figures are the opposite case and are exempt: a closed loop's
    first frame is a real frame of the figure, so seeking to 0 is right
    there, and that is what they do.
    """
    text = _strip_fonts(path.read_text(encoding="utf-8", errors="replace"))
    tags = _smil(text)
    frozen = [tag for tag in tags if 'fill="freeze"' in tag]
    if not frozen:
        pytest.skip("no freeze animation; nothing to rest on")

    seek = _seek(text)
    if seek is None:
        # Guarded by display:none instead — the element is not rendered at
        # all, so there is no resting frame to get wrong.
        assert _every_animation_is_hidden(
            path, _classes_hidden_under_reduce(text)
        ), f"{path.relative_to(ROOT)} freezes animations and has no guard"
        return

    end = _last_moment(tags)
    assert seek >= end, (
        f"{path.relative_to(ROOT)} seeks to {seek}s but its last freeze "
        f"animation ends at {end}s: readers who asked for reduced motion "
        f"would see the state the figure animates AWAY from, not the one it "
        f"reports"
    )


@pytest.mark.parametrize(
    "path", ANIMATED, ids=lambda p: str(p.relative_to(ROOT))
)
def test_the_guard_does_not_break_the_document(path: Path) -> None:
    """The guards are injected into shipped files; they must still parse."""
    ET.parse(path)


def test_every_copy_of_a_figure_is_guarded_the_same_way(path=None) -> None:
    """
    A figure fixed in the gallery and not in its French twin is a figure
    fixed for half its readers.

    Each name exists in up to four places. They are separate files on disk,
    which is exactly why they drift: this is the check that notices.
    """
    by_name: dict[str, list[Path]] = {}
    for figure in ANIMATED:
        by_name.setdefault(figure.name, []).append(figure)

    drifted: list[str] = []
    for name, copies in sorted(by_name.items()):
        if len(copies) < 2:
            continue
        seeks = set()
        for copy in copies:
            text = _strip_fonts(copy.read_text(encoding="utf-8", errors="replace"))
            seeks.add(
                (
                    "pauseAnimations" in text,
                    _seek(text),
                    bool(
                        re.search(
                            r"@media\s*\(prefers-reduced-motion:\s*no-preference\)",
                            text,
                        )
                    ),
                )
            )
        if len(seeks) > 1:
            drifted.append(f"{name} ({len(copies)} copies): {sorted(map(str, seeks))}")

    assert not drifted, "copies of the same figure guard motion differently:\n" + "\n".join(
        drifted
    )
