#!/usr/bin/env python3
"""
audit_laws_of_ux
================

Static auditor for the canonical *Laws of UX* (Jon Yablonski,
https://lawsofux.com/) against vanilla-JS + Tailwind HTML emitted by
the ``sprezzature-ui`` skill.

The script does **not** render the page. It parses HTML with the
standard library and flags violations that are mechanically detectable
from the source — the same way ``sprezzature-accessibility``'s static lint flags
accessibility issues without spinning up a browser. Browser-time
behaviour (real measured response time, real layout sizes, focus
trapping under mouse) is out of scope by design.

The checks are deliberately conservative. Findings come in two
severities:

* ``error``   — a confident violation; the build should fail.
* ``warning`` — heuristic; the maintainer should look but may rule it
  out as a false positive.

Implemented checks
------------------

==================================  =========  =================================================================
Law                                  Severity   Trigger
==================================  =========  =================================================================
Hick's Law                           error      ``<nav>`` with more than seven top-level ``<a>`` or ``<button>``
Choice Overload                      warning    Pricing-grid pattern with more than four columns
Miller's Law                         warning    Visible run ≥ 8 chars that contains at least one digit
                                                (codes / IDs / phone numbers; pure-alphabetic words
                                                are skipped to suppress false positives on ordinary
                                                English such as "collaborators" or "implementation")
Jakob's Law                          error      Clickable ``<div>`` / ``<span>`` (``role="button"`` or
                                                ``onclick=`` / ``cursor-pointer`` without a ``<button>`` parent)
Fitts's Law                          warning    Interactive element with neither a ``min-h-`` nor an ``h-`` class
                                                of at least ``11`` (44 px) on the Tailwind scale
Aesthetic-Usability                  warning    Interactive element missing ``focus-visible:ring-*`` /
                                                ``focus:ring-*``
Selective Attention                  warning    Status ``<span>`` whose only signal is ``text-red-*`` /
                                                ``text-green-*`` (no icon, no text label like "error"/"ok")
Tesler's Law                         warning    Plain ``HH:MM`` time string with no neighbouring timezone
                                                token (``UTC``, ``GMT``, ``+0X``, ``Z``, named TZ)
==================================  =========  =================================================================

Usage
-----
::

    # Audit a single file, human-readable output, exit non-zero on any error
    python scripts/audit_laws_of_ux.py path/to/page.html

    # Audit a directory recursively, JSON output for CI
    python scripts/audit_laws_of_ux.py --json src/

    # Promote warnings to errors (strict mode)
    python scripts/audit_laws_of_ux.py --strict src/

    # Restrict to a subset of laws
    python scripts/audit_laws_of_ux.py --only hick,miller,jakob src/

    # AUTO-FIX MODE — apply mechanical fixes in place
    python scripts/audit_laws_of_ux.py --fix path/to/page.html
    #   Fitts                → adds ``min-h-11`` to the element's class list
    #   Aesthetic-Usability  → adds ``focus-visible:ring-2 …`` tokens
    #   Miller               → chunks long digit runs with non-breaking spaces
    #   Jakob                → rewrites <div role="button"> / <span> to <button>
    # Idempotent: re-running on a fixed file applies zero edits.
    # Hick / Choice-Overload / Tesler / Selective-Attention have no
    # fixer because they need a design decision, not a text edit.

    # PREVIEW MODE — show what --fix would change without writing
    python scripts/audit_laws_of_ux.py --fix --dry-run path/to/page.html

Notes
-----
* Python 3.10+, stdlib only. No ``beautifulsoup`` / no ``lxml``.
* Pairs with ``references/laws-of-ux.md`` (the rules) and
  ``references/checklist.md`` (the broader gate).
* For runtime checks (real layout, focus trap, dynamic
  ``aria-live`` regions) reach for ``axe-core`` / ``Pa11y`` /
  ``Lighthouse`` — this script is intentionally a static pre-commit
  filter.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable

from _argparse import make_parser


# ── Domain types ───────────────────────────────────────────────────────────


#: Set of HTML tags considered interactive for Fitts / focus / Jakob checks.
INTERACTIVE_TAGS: frozenset[str] = frozenset(
    {"button", "a", "input", "select", "textarea", "summary"}
)

#: Set of Tailwind size tokens (last component of ``h-`` / ``min-h-`` /
#: ``size-`` classes) that satisfy the Fitts 44 px minimum. ``11`` is
#: 44 px on the default Tailwind scale; ``12``+ is larger; ``full`` /
#: ``screen`` / ``auto`` are accepted as "explicit choice by the author".
FITTS_OK_SIZES: frozenset[str] = frozenset(
    {str(n) for n in range(11, 97)} | {"full", "screen", "auto"}
)

#: Regex that finds a Tailwind size class. Matches ``h-11``, ``min-h-12``,
#: ``size-11`` and their responsive / state-prefixed cousins
#: (``sm:h-11``, ``hover:min-h-12``, …).
RE_TW_SIZE: re.Pattern[str] = re.compile(
    r"(?:[a-z-]+:)*(?:min-)?(?:h|size)-(\w+)"
)

#: Regex finding a ``focus-visible:ring-*`` / ``focus:ring-*`` class.
RE_TW_FOCUS_RING: re.Pattern[str] = re.compile(
    r"(?:[a-z-]+:)*focus(?:-visible)?:ring(?:-\w+)?"
)

#: Regex finding a Tailwind status colour utility (``text-red-700``,
#: ``text-green-500``, …).
RE_TW_STATUS_COLOUR: re.Pattern[str] = re.compile(
    r"(?:[a-z-]+:)*text-(red|green|amber|yellow|orange)-\d{3}"
)

#: Regex catching a contiguous run of ≥ 8 alphanumeric characters with no
#: space, dash, slash, or non-breaking space. Used by the Miller check.
RE_LONG_RUN: re.Pattern[str] = re.compile(r"[A-Za-z0-9]{8,}")

#: Regex catching ``HH:MM`` or ``HH:MM:SS`` time strings. The Tesler check
#: then looks for a timezone token within ~20 chars on either side.
RE_TIME_STAMP: re.Pattern[str] = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

#: Regex of timezone tokens that suppress a Tesler warning when found near
#: a ``HH:MM`` match.
RE_TZ_TOKEN: re.Pattern[str] = re.compile(
    r"\b(?:UTC|GMT|CET|CEST|EST|EDT|PST|PDT|JST|Z)\b|[+-]\d{1,2}:?\d{0,2}|"
    r"[A-Z][a-z]+/[A-Z][a-z_]+"
)

#: Labels that count as a "second channel" for the Selective-Attention
#: check (a status colour plus one of these words is fine).
STATUS_WORDS: frozenset[str] = frozenset(
    {
        "error", "errors", "failed", "failure", "fail",
        "ok", "okay", "success", "succeeded", "saved",
        "warning", "warn", "caution",
        "info", "notice",
        "pending", "loading", "running",
    }
)


# ── Finding container ──────────────────────────────────────────────────────


@dataclass
class Finding:
    """
    One violation row.

    Attributes
    ----------
    law : str
        Short slug of the law (e.g. ``"hick"``).
    severity : str
        ``"error"`` or ``"warning"``.
    path : str
        File the finding was produced from, relative to CWD if possible.
    line : int
        1-based line number of the offending source.
    message : str
        Human-readable summary suitable for stdout / CI logs.
    snippet : str
        ≤ 120-char excerpt of the offending source. Whitespace
        collapsed for readability.
    """

    law: str
    severity: str
    path: str
    line: int
    message: str
    snippet: str = ""


# ── HTML walker ────────────────────────────────────────────────────────────


@dataclass
class Element:
    """
    Lightweight HTML element record collected by :class:`Walker`.

    Only the bits the auditor actually consults are kept. Nesting is
    tracked via a parent index so we can ask "is this <a> inside a
    <nav>?".

    Attributes
    ----------
    tag : str
        Lowercased tag name.
    attrs : dict of str → str
        Attribute map. Multi-valued attributes are joined with spaces.
    line : int
        1-based source line.
    parent : int
        Index into the parent walker's ``elements`` list, or ``-1`` for
        the document root.
    text_chunks : list of str
        Visible text directly inside this element (does not include
        text in descendants).
    """

    tag: str
    attrs: dict[str, str]
    line: int
    parent: int
    text_chunks: list[str] = field(default_factory=list)


class Walker(HTMLParser):
    """
    Minimal DOM-shape collector built on :class:`html.parser.HTMLParser`.

    Drives the law checks below. We keep a flat ``elements`` list plus a
    stack of indices so we can pop on end tags and reach for ancestors
    cheaply.
    """

    def __init__(self) -> None:
        """Initialise the audit parser's element and text accumulators."""
        super().__init__(convert_charrefs=True)
        self.elements: list[Element] = []
        self._stack: list[int] = []

    # ── HTMLParser hooks ──────────────────────────────────────────────────

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """Record an opening tag and its attributes for later rule checks."""
        parent: int = self._stack[-1] if self._stack else -1
        line, _ = self.getpos()
        elem: Element = Element(
            tag=tag,
            attrs={k: (v or "") for k, v in attrs},
            line=line,
            parent=parent,
        )
        self.elements.append(elem)
        # Void tags do not push onto the stack — they have no children.
        if tag not in {
            "img", "br", "hr", "input", "meta", "link", "source", "area",
        }:
            self._stack.append(len(self.elements) - 1)

    def handle_endtag(self, tag: str) -> None:
        # HTML in the wild is messy; only pop if the top matches.
        """Record a closing tag for structural (nesting / heading) checks."""
        while self._stack:
            top: int = self._stack[-1]
            if self.elements[top].tag == tag:
                self._stack.pop()
                return
            self._stack.pop()

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        # Self-closing form (``<input … />``) — same as start but no push.
        """Record a self-closing tag (e.g. ``<img/>``, ``<input/>``)."""
        parent: int = self._stack[-1] if self._stack else -1
        line, _ = self.getpos()
        self.elements.append(
            Element(
                tag=tag,
                attrs={k: (v or "") for k, v in attrs},
                line=line,
                parent=parent,
            )
        )

    def handle_data(self, data: str) -> None:
        """Accumulate visible text for rules that inspect element content."""
        if not self._stack:
            return
        # Attach the raw text run to the element currently open.
        self.elements[self._stack[-1]].text_chunks.append(data)


# ── Helpers used by multiple checks ────────────────────────────────────────


def _classes(elem: Element) -> list[str]:
    """
    Return the element's space-split ``class`` list, or an empty list.

    Parameters
    ----------
    elem : Element
        Element to inspect.

    Returns
    -------
    list of str
        Class tokens in source order.
    """
    return elem.attrs.get("class", "").split()


def _ancestors(walker: Walker, idx: int) -> Iterable[Element]:
    """
    Yield ancestors of ``walker.elements[idx]`` from nearest to root.

    Parameters
    ----------
    walker : Walker
        Walker the indices belong to.
    idx : int
        Index of the starting element.

    Yields
    ------
    Element
        Each ancestor up the tree (root excluded — the document has no
        parent element).
    """
    cur: int = walker.elements[idx].parent
    while cur != -1:
        yield walker.elements[cur]
        cur = walker.elements[cur].parent


def _has_ancestor(walker: Walker, idx: int, tag: str) -> bool:
    """Return ``True`` iff one of ``idx``'s ancestors has tag ``tag``."""
    return any(a.tag == tag for a in _ancestors(walker, idx))


def _short(snippet: str, max_chars: int = 120) -> str:
    """Collapse whitespace and truncate a snippet for log lines."""
    flat: str = " ".join(snippet.split())
    return flat if len(flat) <= max_chars else flat[: max_chars - 1] + "…"


def _file_lines(path: Path) -> list[str]:
    """Read the file and return one entry per line (no trailing newline)."""
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


# ── The law checks ─────────────────────────────────────────────────────────


def _ancestor_indices(walker: Walker, idx: int) -> list[int]:
    """
    Return the index list of ancestors of ``idx``, nearest first.

    Parameters
    ----------
    walker : Walker
        Walker the indices belong to.
    idx : int
        Index of the starting element.

    Returns
    -------
    list of int
        Ancestor indices in walk order, root excluded.
    """
    chain: list[int] = []
    cur: int = walker.elements[idx].parent
    while cur != -1:
        chain.append(cur)
        cur = walker.elements[cur].parent
    return chain


def check_hick(walker: Walker, path: str) -> list[Finding]:
    """
    Hick's Law — no single ``<nav>`` should expose > 7 top-level choices.

    "Top-level" means a direct ``<a>`` or ``<button>`` whose nearest
    ``<nav>`` ancestor is *this* nav (so the two navs in a page are
    counted independently), and which is **not** wrapped by a closer
    grouping container that already collapses several controls into
    one logical choice — ``<details>``, ``<dialog>``, ``<menu>``,
    or an element with ``role`` in
    {``radiogroup``, ``tablist``, ``menubar``, ``listbox``,
    ``combobox``}.

    Parameters
    ----------
    walker : Walker
        Parsed document.
    path : str
        Source path, for the finding row.

    Returns
    -------
    list of Finding
        Zero or one finding per ``<nav>``.
    """
    grouping_roles: frozenset[str] = frozenset(
        {"radiogroup", "tablist", "menubar", "listbox", "combobox"}
    )
    grouping_tags: frozenset[str] = frozenset(
        {"details", "dialog", "menu"}
    )
    out: list[Finding] = []
    for idx, elem in enumerate(walker.elements):
        if elem.tag != "nav":
            continue
        # Count distinct logical choices: each grouping container (one
        # radiogroup, one details, …) counts as a single choice; any
        # remaining direct interactive descendants count one each.
        counted_groups: set[int] = set()
        top_level: int = 0
        for j, child in enumerate(walker.elements):
            if j == idx:
                continue
            if child.tag not in {"a", "button"}:
                continue
            chain: list[int] = _ancestor_indices(walker, j)
            # Must descend from THIS nav (the nearest nav ancestor must
            # be ``idx``).
            nav_idx: int | None = next(
                (k for k in chain if walker.elements[k].tag == "nav"), None
            )
            if nav_idx != idx:
                continue
            # Walk up from child to this nav; stop at the first grouping
            # container we find — that container is the unit of choice.
            grouped_under: int | None = None
            for k in chain:
                if k == idx:
                    break
                anc: Element = walker.elements[k]
                role: str = anc.attrs.get("role", "").lower()
                if anc.tag in grouping_tags or role in grouping_roles:
                    grouped_under = k
                    break
            if grouped_under is not None:
                if grouped_under in counted_groups:
                    continue
                counted_groups.add(grouped_under)
                top_level += 1
                continue
            top_level += 1
        if top_level > 7:
            out.append(
                Finding(
                    law="hick",
                    severity="error",
                    path=path,
                    line=elem.line,
                    message=(
                        f"<nav> exposes {top_level} top-level choices "
                        f"(> 7). Group, hide behind 'More', or split."
                    ),
                )
            )
    return out


def check_choice_overload(walker: Walker, path: str) -> list[Finding]:
    """
    Choice Overload — pricing-grid heuristic: > 4 column-like children.

    Triggers on a ``<section>`` or ``<div>`` whose class list contains
    one of ``pricing`` / ``plans`` **and** ``grid`` / ``flex``, and
    which has more than four direct ``<article>`` / ``<div>``
    column children.
    """
    out: list[Finding] = []
    for idx, elem in enumerate(walker.elements):
        if elem.tag not in {"section", "div"}:
            continue
        cls: list[str] = _classes(elem)
        flat: str = " ".join(cls).lower()
        if not (("pricing" in flat or "plans" in flat) and ("grid" in flat or "flex" in flat)):
            continue
        columns: int = sum(
            1
            for j, child in enumerate(walker.elements)
            if child.parent == idx and child.tag in {"article", "div"}
        )
        if columns > 4:
            out.append(
                Finding(
                    law="choice-overload",
                    severity="warning",
                    path=path,
                    line=elem.line,
                    message=(
                        f"Pricing/plans grid with {columns} columns. "
                        f"Trim to 3 + 'Contact us' and recommend one."
                    ),
                )
            )
    return out


def check_miller(path: str, lines: list[str]) -> list[Finding]:
    """
    Miller's Law — flag visible alphanumeric runs of ≥ 8 characters.

    Scans only the visible text of the file (lines outside ``<script>``
    / ``<style>`` blocks). False positives on hashed CSS class names
    are filtered by also requiring the run to *not* sit inside a
    ``class="…"`` or ``id="…"`` attribute on the same line.
    """
    out: list[Finding] = []
    in_script: bool = False
    in_style: bool = False
    for n, raw in enumerate(lines, start=1):
        low: str = raw.lower()
        if "<script" in low:
            in_script = True
        if "<style" in low:
            in_style = True
        if in_script or in_style:
            if "</script" in low:
                in_script = False
            if "</style" in low:
                in_style = False
            continue
        # Strip attribute values so class hashes don't trigger.
        stripped: str = re.sub(r'(?:class|id|href|src)="[^"]*"', "", raw)
        # Strip HTML tags themselves; leave only visible text.
        visible: str = re.sub(r"<[^>]+>", " ", stripped)
        for m in RE_LONG_RUN.finditer(visible):
            run: str = m.group(0)
            # Miller's chunking advice targets codes / IDs / phone
            # numbers — all of which contain at least one digit. Pure
            # alphabetic runs are either ordinary English
            # (collaborators, implementation, configuration) or
            # technical jargon that does not benefit from 3–4-char
            # chunking, so skip them.
            if not any(c.isdigit() for c in run):
                continue
            out.append(
                Finding(
                    law="miller",
                    severity="warning",
                    path=path,
                    line=n,
                    message=(
                        f"Long unbroken run '{run}' "
                        f"({len(run)} chars). Chunk into groups of 3–4."
                    ),
                    snippet=_short(raw),
                )
            )
    return out


def check_jakob(walker: Walker, path: str) -> list[Finding]:
    """
    Jakob's Law — refuse clickable ``<div>`` / ``<span>``.

    Triggers when a ``<div>`` or ``<span>`` has ``onclick=``,
    ``role="button"``, or ``cursor-pointer`` in its class list and is
    **not** wrapping a real ``<button>`` / ``<a>`` child.
    """
    out: list[Finding] = []
    for idx, elem in enumerate(walker.elements):
        if elem.tag not in {"div", "span"}:
            continue
        cls: list[str] = _classes(elem)
        has_onclick: bool = "onclick" in elem.attrs
        has_role_button: bool = elem.attrs.get("role", "").lower() == "button"
        has_cursor_ptr: bool = "cursor-pointer" in cls
        if not (has_onclick or has_role_button or has_cursor_ptr):
            continue
        # Allow wrappers that contain a real interactive child.
        has_real_child: bool = any(
            child.tag in {"button", "a", "input", "select", "summary"}
            for j, child in enumerate(walker.elements)
            if child.parent == idx
        )
        if has_real_child:
            continue
        # Allow the visual skin of a real control: a styled <span>/<div> inside
        # a <label> that holds an <input>/<select>/<textarea> (the accessible
        # segmented-control / custom-checkbox pattern — the form control carries
        # the semantics and keyboard behaviour; the span is only its paint).
        anc: int = elem.parent
        in_labelled_control = False
        while anc != -1:
            node = walker.elements[anc]
            if node.tag == "label":
                in_labelled_control = any(
                    c.tag in {"input", "select", "textarea"}
                    for c in walker.elements if c.parent == anc
                )
                break
            anc = node.parent
        if in_labelled_control:
            continue
        out.append(
            Finding(
                law="jakob",
                severity="error",
                path=path,
                line=elem.line,
                message=(
                    f"<{elem.tag}> acts as a button. Use a real <button> "
                    f"or <a href> — native focus, Enter/Space, screen-reader role."
                ),
            )
        )
    return out


def check_fitts(walker: Walker, path: str) -> list[Finding]:
    """
    Fitts's Law — interactive controls need ≥ 44 px hit area.

    The skill's Tailwind size scale uses ``h-11`` / ``min-h-11`` for
    44 px. The check warns when an interactive element has no
    height-setting class at all (so the browser falls back to
    line-height + padding, which routinely lands < 44 px).
    """
    out: list[Finding] = []
    for elem in walker.elements:
        if elem.tag not in INTERACTIVE_TAGS:
            continue
        # ``<input type="hidden">`` is not interactive.
        if elem.tag == "input" and elem.attrs.get("type", "").lower() == "hidden":
            continue
        # Skip ``<a>`` inside ``<p>`` / ``<li>`` — they're text links, not buttons.
        cls: list[str] = _classes(elem)
        if elem.tag == "a" and not any(
            c in cls
            for c in ("inline-flex", "flex", "block", "btn", "button")
        ) and not any(c.startswith(("bg-", "border-")) for c in cls):
            continue
        sizes: list[str] = [
            m.group(1) for c in cls for m in (RE_TW_SIZE.fullmatch(c),) if m
        ]
        if any(s in FITTS_OK_SIZES for s in sizes):
            continue
        out.append(
            Finding(
                law="fitts",
                severity="warning",
                path=path,
                line=elem.line,
                message=(
                    f"<{elem.tag}> has no min-h-11 / h-11 (44 px). "
                    f"Confirm the hit area is at least 44×44."
                ),
            )
        )
    return out


def check_aesthetic_usability(walker: Walker, path: str) -> list[Finding]:
    """
    Aesthetic-Usability — every interactive control needs a focus ring.

    The skill's house token is ``focus-visible:ring-2``. The check
    warns when an interactive element has neither
    ``focus-visible:ring-*`` nor ``focus:ring-*`` in its class list.
    Elements that explicitly opt out via ``focus:outline-none`` *and*
    have no ring still fail — the ring is the replacement.
    """
    out: list[Finding] = []
    for elem in walker.elements:
        if elem.tag not in INTERACTIVE_TAGS:
            continue
        if elem.tag == "input" and elem.attrs.get("type", "").lower() in {"hidden", "submit"}:
            # ``<input type=submit>`` typically renders as the form's
            # default; we accept it. Real submit buttons should be ``<button>``.
            if elem.attrs.get("type", "").lower() == "hidden":
                continue
        cls_join: str = " ".join(_classes(elem))
        if RE_TW_FOCUS_RING.search(cls_join):
            continue
        out.append(
            Finding(
                law="aesthetic-usability",
                severity="warning",
                path=path,
                line=elem.line,
                message=(
                    f"<{elem.tag}> has no focus-visible:ring-* class. "
                    f"Add the house focus token."
                ),
            )
        )
    return out


def check_selective_attention(walker: Walker, path: str) -> list[Finding]:
    """
    Selective Attention — colour alone is not a status channel.

    Flags a ``<span>`` whose only class signal is a Tailwind status
    colour (``text-red-*``, ``text-green-*``, …) and whose visible
    text is **not** one of the canonical status words.
    """
    out: list[Finding] = []
    for idx, elem in enumerate(walker.elements):
        if elem.tag != "span":
            continue
        cls: list[str] = _classes(elem)
        flat: str = " ".join(cls)
        if not RE_TW_STATUS_COLOUR.search(flat):
            continue
        text: str = "".join(elem.text_chunks).strip().lower()
        if any(w in text for w in STATUS_WORDS):
            continue
        # Has an icon child? Then there is a second channel.
        has_icon: bool = any(
            child.tag in {"svg", "img"}
            for j, child in enumerate(walker.elements)
            if child.parent == idx
        )
        if has_icon:
            continue
        out.append(
            Finding(
                law="selective-attention",
                severity="warning",
                path=path,
                line=elem.line,
                message=(
                    "Status colour without a second channel "
                    "(icon, status word, aria-label)."
                ),
                snippet=_short(text),
            )
        )
    return out


def check_tesler(path: str, lines: list[str]) -> list[Finding]:
    """
    Tesler's Law — time strings should carry a timezone.

    For every ``HH:MM`` match, look at a ~40-char window on each side
    for a timezone token (``UTC``, ``+02:00``, ``Europe/Paris``, …).
    Misses warn — the user might be displaying a duration, in which
    case the warning is a false positive and can be silenced with
    ``--ignore tesler``.
    """
    out: list[Finding] = []
    for n, raw in enumerate(lines, start=1):
        for m in RE_TIME_STAMP.finditer(raw):
            start: int = max(0, m.start() - 40)
            end: int = min(len(raw), m.end() + 40)
            window: str = raw[start:end]
            if RE_TZ_TOKEN.search(window):
                continue
            out.append(
                Finding(
                    law="tesler",
                    severity="warning",
                    path=path,
                    line=n,
                    message=(
                        f"Time '{m.group(0)}' shown without a timezone "
                        f"in a 40-char window. State the TZ explicitly."
                    ),
                    snippet=_short(raw),
                )
            )
    return out


# ── Driver ─────────────────────────────────────────────────────────────────


#: Map of CLI law names to (walker-check, text-check) entries. ``None``
#: means the check does not need that input shape.
LAW_REGISTRY: dict[str, tuple[
    "Callable[..., Any] | None", "Callable[..., Any] | None"
]] = {
    "hick": (check_hick, None),
    "choice-overload": (check_choice_overload, None),
    "miller": (None, check_miller),
    "jakob": (check_jakob, None),
    "fitts": (check_fitts, None),
    "aesthetic-usability": (check_aesthetic_usability, None),
    "selective-attention": (check_selective_attention, None),
    "tesler": (None, check_tesler),
}


# ── Auto-fix machinery ─────────────────────────────────────────────────────


#: Token strings the Fitts fixer inserts. ``min-h-11`` is 44 px on the
#: default Tailwind scale (the skill's house hit-area minimum).
FITTS_FIX_TOKEN: str = "min-h-11"

#: Token strings the Aesthetic-Usability fixer inserts. Mirrors the
#: focus-ring snippet used in ``sprezzature-ui/assets/components/button.html``.
AU_FIX_TOKENS: tuple[str, ...] = (
    "focus:outline-none",
    "focus-visible:ring-2",
    "focus-visible:ring-brand-blue",
)

#: Non-breaking-space character used by the Miller fixer to chunk a
#: long digit run without breaking copy-paste round-trip in most
#: browsers / form parsers (which treat NBSP as whitespace).
NBSP: str = " "


def _insert_class_tokens(line: str, tokens: list[str]) -> tuple[str, bool]:
    """
    Insert one or more class tokens into the first ``class="…"`` on a line.

    Idempotent: tokens already present are not duplicated. Returns the
    new line and ``True`` iff anything actually changed.

    Parameters
    ----------
    line : str
        Source line containing a ``class="…"`` attribute.
    tokens : list of str
        Tokens to ensure are present, in declaration order.

    Returns
    -------
    (str, bool)
        ``(new_line, mutated)``. When no ``class="…"`` is found, the
        line is returned unchanged and ``mutated`` is ``False`` — the
        caller is expected to surface this as a fix-not-applied warning.
    """
    # Match either single- or double-quoted attribute values. Capture
    # the quote so the rewrite can reuse it (single-quoted ``class``
    # attributes are valid HTML and appear in sprezzature-ui examples).
    m = re.search(r'''class=(["'])((?:(?!\1).)*)\1''', line)
    if not m:
        return line, False
    existing: list[str] = m.group(2).split()
    missing: list[str] = [t for t in tokens if t not in existing]
    if not missing:
        return line, False
    new_classes: str = " ".join(existing + missing)
    return (
        line[: m.start(2)] + new_classes + line[m.end(2) :],
        True,
    )


def _fix_fitts(lines: list[str], finding: "Finding") -> bool:
    """Add ``min-h-11`` to the offending element's class list."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    new_line, mutated = _insert_class_tokens(lines[idx], [FITTS_FIX_TOKEN])
    if mutated:
        lines[idx] = new_line
    return mutated


def _fix_aesthetic_usability(lines: list[str], finding: "Finding") -> bool:
    """Add ``focus-visible:ring-*`` tokens to the offending element's class list."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    new_line, mutated = _insert_class_tokens(lines[idx], list(AU_FIX_TOKENS))
    if mutated:
        lines[idx] = new_line
    return mutated


def _chunk_digits(run: str, size: int = 4) -> str:
    """Insert a non-breaking space every ``size`` chars (right-aligned chunks)."""
    n: int = len(run)
    # Right-align: e.g. a 13-char run with size=4 -> 1 / 4 / 4 / 4.
    first: int = n % size
    parts: list[str] = []
    if first:
        parts.append(run[:first])
    for i in range(first, n, size):
        parts.append(run[i : i + size])
    return NBSP.join(parts)


def _fix_miller(lines: list[str], finding: "Finding") -> bool:
    """Replace the long digit-bearing run with an NBSP-chunked version."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    # Extract the run from the finding message: ``Long unbroken run '<RUN>'``.
    m = re.search(r"'([A-Za-z0-9]+)'", finding.message)
    if not m:
        return False
    run: str = m.group(1)
    if run not in lines[idx]:
        return False
    chunked: str = _chunk_digits(run)
    # ``replace`` is idempotent for our case: once the run has been
    # replaced by ``chunked``, the raw run string no longer appears
    # on the line, so a second pass is a no-op.
    new_line: str = lines[idx].replace(run, chunked, 1)
    if new_line == lines[idx]:
        return False
    lines[idx] = new_line
    return True


def _fix_jakob(lines: list[str], finding: "Finding") -> bool:
    """
    Rewrite a clickable ``<div>`` / ``<span>`` to a real ``<button>``.

    Conservative — only handles the single-line case. Multi-line
    elements are left for the maintainer; running the auditor again
    after the fix will still flag them, which is the right behaviour.
    """
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    line: str = lines[idx]
    for src_tag in ("div", "span"):
        # Track whether either path opened a tag rewrite — if so we
        # need to rewrite the matching close tag on the same line.
        opened: bool = False
        # Path A: strip ``role="button"`` and rename the tag in one
        # pass (handles ``<div role="button" class="…">``).
        role_pat = re.compile(
            rf'<{src_tag}\b([^>]*?)\s+role="button"([^>]*?)>'
        )
        new_line = role_pat.sub(r"<button\1\2>", line, count=1)
        if new_line != line:
            line = new_line
            opened = True
        # Path B: rename a bare ``<div onclick=…>`` /
        # ``<div class="cursor-pointer">`` whose opening tag still
        # carries the source tag name. Only run if Path A did not
        # already convert this element (avoid double-rewrite).
        if not opened and re.search(rf"<{src_tag}\b", line):
            line = re.sub(rf"<{src_tag}\b", "<button", line, count=1)
            opened = True
        # Whichever path opened the tag, rewrite the matching close.
        # We only ever rewrite ONE close tag per fixer invocation to
        # keep the surgery local to the flagged element.
        if opened and re.search(rf"</{src_tag}>", line):
            line = re.sub(rf"</{src_tag}>", "</button>", line, count=1)
    if line == lines[idx]:
        return False
    lines[idx] = line
    return True


#: Map of law → fixer. Laws absent from this map are reported but
#: cannot be auto-fixed (Tesler, Selective-Attention, Choice-Overload,
#: Hick — these need design decisions, not text edits).
LAW_FIXERS: dict[str, "Callable[..., Any]"] = {
    "fitts": _fix_fitts,
    "aesthetic-usability": _fix_aesthetic_usability,
    "miller": _fix_miller,
    "jakob": _fix_jakob,
}


#: Maximum number of fix→audit→fix passes per file. Pathological
#: shapes (a fixer that re-introduces another finding) would otherwise
#: loop forever; 5 covers every realistic case (Jakob rewriting <div>
#: → <button> introduces Fitts + AU, which then fix in the next pass,
#: and so on — at most three rounds in practice).
MAX_FIX_ITERATIONS: int = 5


def fix_file(
    path: Path, laws: set[str], *, dry_run: bool = False
) -> tuple[int, int, list[Finding]]:
    """
    Apply mechanical fixes to one HTML file and rewrite it in place.

    Idempotent: a second invocation against a fixed file applies zero
    edits. Laws not present in :data:`LAW_FIXERS` are passed through
    untouched (they need design decisions, not text edits).

    The function runs the audit→fix loop until either no fixer
    matches a remaining finding or :data:`MAX_FIX_ITERATIONS` is
    reached. Looping matters because some fixers (Jakob's
    ``<div>``→``<button>`` rewrite) *introduce* new fixable findings
    (the freshly-minted ``<button>`` will trigger Fitts + AU until
    they too are patched).

    Parameters
    ----------
    path : Path
        File to repair.
    laws : set of str
        Subset of :data:`LAW_REGISTRY` keys to operate on. Laws not
        present in :data:`LAW_FIXERS` are skipped silently.
    dry_run : bool, default False
        If ``True``, never write to disk — just report what *would*
        be applied based on a single audit pass against the original
        content.

    Returns
    -------
    (int, int, list of Finding)
        ``(applied, skipped, remaining)`` — total edits across all
        iterations, count of findings for which no fixer exists
        (counted once on the first pass), and the residual findings
        observed after the final write.
    """
    raw: str = path.read_text(encoding="utf-8", errors="replace")
    bare_lines: list[str] = raw.splitlines()
    applied: int = 0
    skipped: int = 0
    # Dry-run: report what the FIRST pass would apply, without
    # mutating disk and without running a second iteration.
    if dry_run:
        findings: list[Finding] = audit_file(path, laws)
        for f in findings:
            fixer = LAW_FIXERS.get(f.law)
            if fixer is None:
                skipped += 1
                continue
            # Apply against an in-memory copy to count, then discard.
            shadow: list[str] = bare_lines[:]
            if fixer(shadow, f):
                applied += 1
        return applied, skipped, findings

    # Live fix loop. Re-audit after each round so fixers that create
    # new findings (Jakob) reach a fixed point.
    skipped_seen: bool = False
    for _ in range(MAX_FIX_ITERATIONS):
        # Write current state so the re-audit sees the latest text.
        new_text: str = "\n".join(bare_lines)
        if raw.endswith("\n"):
            new_text += "\n"
        path.write_text(new_text, encoding="utf-8")
        findings = audit_file(path, laws)
        round_applied: int = 0
        round_skipped: int = 0
        for f in findings:
            fixer = LAW_FIXERS.get(f.law)
            if fixer is None:
                round_skipped += 1
                continue
            if fixer(bare_lines, f):
                round_applied += 1
        applied += round_applied
        # Only count "unfixable" findings once (the first time round)
        # — subsequent iterations re-see the same Hick/Tesler/etc.
        if not skipped_seen:
            skipped = round_skipped
            skipped_seen = True
        if round_applied == 0:
            break
    # Final write + final re-audit for the truthful remaining list.
    new_text = "\n".join(bare_lines)
    if raw.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text, encoding="utf-8")
    remaining: list[Finding] = audit_file(path, laws)
    return applied, skipped, remaining


def audit_file(path: Path, laws: set[str]) -> list[Finding]:
    """
    Run every requested law check against one HTML file.

    Parameters
    ----------
    path : Path
        File to audit.
    laws : set of str
        Subset of :data:`LAW_REGISTRY` keys to run.

    Returns
    -------
    list of Finding
        All findings, in registry order.
    """
    raw: str = path.read_text(encoding="utf-8", errors="replace")
    walker: Walker = Walker()
    walker.feed(raw)
    walker.close()
    lines: list[str] = raw.splitlines()
    findings: list[Finding] = []
    rel: str = str(path)
    for law, (walker_fn, text_fn) in LAW_REGISTRY.items():
        if law not in laws:
            continue
        if walker_fn is not None:
            findings.extend(walker_fn(walker, rel))
        if text_fn is not None:
            findings.extend(text_fn(rel, lines))
    return findings


def discover(targets: list[Path]) -> list[Path]:
    """
    Expand CLI targets into a list of ``.html`` files.

    Parameters
    ----------
    targets : list of Path
        Files and directories from the command line.

    Returns
    -------
    list of Path
        HTML files, deduplicated, in stable order.
    """
    seen: set[Path] = set()
    out: list[Path] = []
    for t in targets:
        if t.is_dir():
            for p in sorted(t.rglob("*.html")):
                if p not in seen:
                    seen.add(p)
                    out.append(p)
        elif t.is_file() and t.suffix.lower() in {".html", ".htm"}:
            if t not in seen:
                seen.add(t)
                out.append(t)
        else:
            print(f"warning: skipping non-HTML target {t}", file=sys.stderr)
    return out


def format_text(findings: list[Finding]) -> str:
    """Render findings as a grep-friendly text report."""
    if not findings:
        return "audit_laws_of_ux: 0 findings.\n"
    rows: list[str] = []
    for f in findings:
        rows.append(
            f"{f.path}:{f.line}: [{f.severity}] {f.law}: {f.message}"
        )
        if f.snippet:
            rows.append(f"    {f.snippet}")
    rows.append("")
    rows.append(f"audit_laws_of_ux: {len(findings)} finding(s).")
    return "\n".join(rows) + "\n"


def format_json(findings: list[Finding]) -> str:
    """Render findings as a JSON array — one object per finding."""
    payload: list[dict[str, str | int]] = [
        {
            "law": f.law,
            "severity": f.severity,
            "path": f.path,
            "line": f.line,
            "message": f.message,
            "snippet": f.snippet,
        }
        for f in findings
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns
    -------
    int
        ``0`` when no findings of severity ``error`` (or any severity in
        ``--strict``). ``1`` otherwise.
    """
    parser: argparse.ArgumentParser = make_parser(
        prog="sprezzature-ux-laws-audit",
        description=(
            "Static auditor for the canonical Laws of UX "
            "(Jon Yablonski, lawsofux.com) against sprezzature-ui output."
        ),
    )
    parser.add_argument(
        "targets",
        nargs="+",
        type=Path,
        help="HTML files or directories to audit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a text report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote warnings to errors (any finding fails the run).",
    )
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help=(
            "Comma-separated subset of laws to run. Defaults to all. "
            f"Available: {','.join(sorted(LAW_REGISTRY))}."
        ),
    )
    parser.add_argument(
        "--ignore",
        type=str,
        default="",
        help="Comma-separated laws to skip.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Apply mechanical fixes in place for the laws that have "
            "a fixer (Fitts adds min-h-11; Aesthetic-Usability adds "
            "focus-visible:ring-2; Miller chunks long digit runs with "
            "NBSP; Jakob rewrites a clickable <div>/<span> to a real "
            "<button>). Idempotent — running again on a fixed file "
            "performs zero edits. Combine with --dry-run to preview."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "With --fix, print what would change without touching the "
            "files. Implies --fix when used alone."
        ),
    )
    args: argparse.Namespace = parser.parse_args(argv)

    requested: set[str] = (
        {s.strip() for s in args.only.split(",") if s.strip()}
        if args.only
        else set(LAW_REGISTRY)
    )
    ignored: set[str] = {s.strip() for s in args.ignore.split(",") if s.strip()}
    laws: set[str] = requested - ignored
    unknown: set[str] = laws - set(LAW_REGISTRY)
    if unknown:
        print(
            f"audit_laws_of_ux: unknown law(s): {','.join(sorted(unknown))}",
            file=sys.stderr,
        )
        return 2

    files: list[Path] = discover(args.targets)
    if not files:
        print("audit_laws_of_ux: no HTML files found.", file=sys.stderr)
        return 0

    # ── Fix mode ───────────────────────────────────────────────────────
    # ``--dry-run`` alone implies ``--fix`` (preview only). Plain
    # invocation (neither flag) falls through to the auditor below.
    if args.fix or args.dry_run:
        total_applied: int = 0
        total_skipped: int = 0
        total_remaining: list[Finding] = []
        for p in files:
            applied, skipped, remaining = fix_file(
                p, laws, dry_run=args.dry_run
            )
            total_applied += applied
            total_skipped += skipped
            total_remaining.extend(remaining)
            verb: str = "would apply" if args.dry_run else "applied"
            print(
                f"{p}: {verb} {applied} fix(es); {skipped} unfixable "
                f"finding(s); {len(remaining)} remaining.",
                file=sys.stderr,
            )
        # After the fix pass, emit the remaining findings on stdout in
        # the requested format so a CI pipeline can still gate on them.
        out: str = (
            format_json(total_remaining)
            if args.json
            else format_text(total_remaining)
        )
        sys.stdout.write(out)
        # Dry-run is a preview, not a verdict — always exit 0 so the
        # user can pipe it without failing their pre-commit hook.
        # Live --fix follows the same exit-code policy as audit mode.
        if args.dry_run:
            return 0
        if total_remaining:
            return 1 if (args.strict or any(f.severity == "error" for f in total_remaining)) else 0
        return 0

    # ── Audit-only mode ────────────────────────────────────────────────
    findings: list[Finding] = []
    for p in files:
        findings.extend(audit_file(p, laws))

    out = format_json(findings) if args.json else format_text(findings)
    sys.stdout.write(out)

    if not findings:
        return 0
    if args.strict:
        return 1
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
