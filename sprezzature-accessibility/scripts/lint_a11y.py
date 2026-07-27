#!/usr/bin/env python3
"""
lint_a11y
=========

Accessibility linter for HTML emitted by (or for) the ``sprezzature``
skill. The linter is **static** — no browser, no DOM, no JS execution —
so it fits into a code-emit pipeline or a pre-commit hook.

The rules cover the ~20 violations that account for the bulk of
real-world WCAG / WAI-ARIA failures. None of them require the runtime
DOM; all are decidable from source.

Rule catalogue
--------------
========================  =====================================================
``img-missing-alt``         ``<img>`` with no ``alt`` attribute. Empty
                            ``alt=""`` is correct for decorative images;
                            *omitting* the attribute is not.
``img-redundant-aria``      ``alt=""`` plus ``role="presentation"`` or
                            ``aria-hidden="true"``: redundant.
``a-missing-href``          ``<a>`` without ``href`` (use ``<button>``).
``a-empty``                 ``<a>`` with no text and no accessible name.
``button-empty``            ``<button>`` with no text and no ``aria-label``.
``div-onclick``             ``<div>`` / ``<span>`` with ``onclick`` but no
                            ``role="button"`` and ``tabindex``.
``input-missing-label``     ``<input>`` not wrapped in a ``<label>`` and not
                            referenced by a ``<label for=>``.
``dialog-missing-close``    ``<dialog>`` without a close affordance
                            (``<button>``, ``value="cancel"``, ``[autofocus]``).
``html-missing-lang``       ``<html>`` without ``lang``.
``tabindex-positive``       ``tabindex`` ≥ 1.
``aria-hidden-interactive`` ``aria-hidden="true"`` on a button / link / input.
``heading-skip``            Headings out of order (e.g. ``<h2>`` → ``<h4>``).
``color-only-state``        Tailwind ``*-red-*`` / ``*-green-*`` on a span
                            with no icon, label, or text sibling. Catches the
                            "red is bad / green is good" anti-pattern.
``motion-no-reduce-guard``  ``animate-*`` or ``transition-transform`` without
                            a ``motion-reduce:`` peer.
========================  =====================================================

Output
------
Plain-text report by default; use ``--format json`` for machine consumption.
Exit code ``1`` on any finding (unless ``--ignore`` covers it), ``0``
otherwise. The script can be pointed at a single file or a directory.

Usage
-----
::

    # Lint a single page
    python lint_a11y.py public/index.html

    # Lint a tree
    python lint_a11y.py public/

    # JSON output for CI
    python lint_a11y.py --format json public/index.html

    # Suppress two rules
    python lint_a11y.py --ignore heading-skip,motion-no-reduce-guard public/

Notes
-----
* Python 3.10+, stdlib only (``html.parser``, ``argparse``, ``pathlib``).
* The parser is forgiving — it walks documents that contain mixed-case
  tags, missing closures, and inline scripts without raising.
* This linter is a *first pass*, not a replacement for ``axe-core`` or
  manual screen-reader testing. It catches the violations easiest to fix.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path as _PathHelper

# Shared parser factory: prog name, RawDescriptionHelpFormatter, --version.
sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _lang import detect_text_language, extract_body_text  # noqa: E402
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterator, Optional


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class Element:
    """
    Minimal representation of one HTML element captured during parsing.

    Attributes
    ----------
    tag : str
        Lower-cased tag name (``"img"``, ``"button"``, …).
    attrs : dict
        Attribute map. Boolean attributes resolve to the empty string.
    line : int
        1-based source line of the element's opening tag.
    text : str
        Concatenated text content of the element (children stripped).
    children : list of Element
        Direct element children, in source order.
    parent : Element or None
        Parent element, or ``None`` for the synthetic root.
    """

    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    line: int = 0
    text: str = ""
    children: list["Element"] = field(default_factory=list)
    parent: Optional["Element"] = None


@dataclass
class Finding:
    """
    One reported accessibility violation.

    Attributes
    ----------
    rule : str
        Rule identifier (e.g. ``"img-missing-alt"``).
    line : int
        1-based source line of the offending element.
    message : str
        Human-readable explanation suitable for a console line.
    """

    rule: str
    line: int
    message: str


# ── HTML walker ────────────────────────────────────────────────────────────

# Void elements that never have a closing tag in HTML5; ``html.parser`` does
# not flag them, so the walker maintains an explicit list.
VOID_ELEMENTS: frozenset[str] = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "keygen", "link", "meta", "param", "source", "track", "wbr",
})


class TreeBuilder(HTMLParser):
    """
    Build a lightweight element tree from an HTML string.

    The parser is intentionally forgiving — case-folding tag names, treating
    void elements as self-closing, and collecting source line numbers so
    findings can be reported usefully.
    """

    def __init__(self) -> None:
        # ``convert_charrefs=False`` keeps entities literal so ``<pre>`` blocks
        # in user docs survive the round-trip unchanged.
        """Initialise the audit parser's element and text accumulators."""
        super().__init__(convert_charrefs=False)
        # The root is a synthetic ``html`` element so the tree always has a
        # single entry point; the real ``<html>`` becomes its only child.
        self.root: Element = Element(tag="root", line=0)
        self.stack: list[Element] = [self.root]

    # html.parser hooks --------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        # ``getpos()`` returns (line, column) for the current token; only
        # the line is preserved.
        """Record an opening tag and its attributes for later rule checks."""
        line, _ = self.getpos()
        elem = Element(
            tag=tag.lower(),
            attrs={k.lower(): (v or "") for k, v in attrs},
            line=line,
            parent=self.stack[-1],
        )
        self.stack[-1].children.append(elem)
        # Void elements never push onto the stack — they would otherwise leak
        # if the source forgets a trailing ``/``.
        if tag.lower() not in VOID_ELEMENTS:
            self.stack.append(elem)

    def handle_endtag(self, tag: str) -> None:
        # Pop until we hit a matching open tag (or the root). This handles
        # documents with mismatched closes without raising.
        """Record a closing tag for structural (nesting / heading) checks."""
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag.lower():
                del self.stack[i:]
                return

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        # Self-closing form (``<br />``); treat as a leaf.
        """Record a self-closing tag (e.g. ``<img/>``, ``<input/>``)."""
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_ELEMENTS:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        # Append text to the *currently open* element. Whitespace-only text
        # outside any element is ignored.
        """Accumulate visible text for rules that inspect element content."""
        if self.stack and data.strip():
            self.stack[-1].text += data


def walk(elem: Element) -> Iterator[Element]:
    """
    Depth-first iterator over every descendant of ``elem`` (excluding the root).

    Parameters
    ----------
    elem : Element
        Root of the subtree to traverse.

    Yields
    ------
    Element
        Each descendant in document order.
    """
    for child in elem.children:
        yield child
        yield from walk(child)


def accessible_name(elem: Element) -> str:
    """
    Best-effort accessible name for an element.

    The function picks the first non-empty source from:

    1. ``aria-label`` (explicit override).
    2. ``title`` (tooltip fallback).
    3. Concatenated text content of the element AND every descendant.
       This is what a screen reader announces by default — the simple
       direct-text-only view misses the common ``<a><span>Label</span></a>``
       shape.

    Parameters
    ----------
    elem : Element
        Element under inspection.

    Returns
    -------
    str
        The accessible name, or ``""`` when none is present.
    """
    for attr in ("aria-label", "title"):
        if elem.attrs.get(attr, "").strip():
            return elem.attrs[attr].strip()

    # Aggregate text from this element and every descendant.
    parts: list[str] = [elem.text]
    parts.extend(d.text for d in walk(elem))
    return " ".join(p.strip() for p in parts if p and p.strip()).strip()


def has_descendant(elem: Element, tag: str) -> bool:
    """Return ``True`` when ``elem`` contains any descendant of ``tag``."""
    return any(d.tag == tag for d in walk(elem))


# ── Rule implementations ──────────────────────────────────────────────────

def check_html_lang(root: Element) -> list[Finding]:
    """Rule ``html-missing-lang`` — the ``<html>`` element must declare ``lang``."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag == "html" and not elem.attrs.get("lang", "").strip():
            findings.append(Finding(
                rule="html-missing-lang",
                line=elem.line,
                message="<html> missing required lang attribute.",
            ))
    return findings


def check_img(root: Element) -> list[Finding]:
    """Rules ``img-missing-alt`` and ``img-redundant-aria``."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag != "img":
            continue
        if "alt" not in elem.attrs:
            findings.append(Finding(
                rule="img-missing-alt",
                line=elem.line,
                message='<img> missing alt attribute. Use alt="" for decorative images.',
            ))
            continue
        # ``role="presentation"`` and ``aria-hidden`` are redundant with
        # an explicit empty ``alt`` per W3C / WAI guidance.
        if elem.attrs.get("alt", "") == "" and (
            elem.attrs.get("role", "") == "presentation"
            or elem.attrs.get("aria-hidden", "") == "true"
        ):
            findings.append(Finding(
                rule="img-redundant-aria",
                line=elem.line,
                message='Decorative <img alt="">: drop role="presentation" / aria-hidden="true" (redundant).',
            ))
    return findings


def check_links(root: Element) -> list[Finding]:
    """Rules ``a-missing-href`` and ``a-empty``."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag != "a":
            continue
        # ``<a>`` without ``href`` is not a link — it has no role, no
        # keyboard handling. Use ``<button>``.
        if "href" not in elem.attrs:
            findings.append(Finding(
                rule="a-missing-href",
                line=elem.line,
                message="<a> without href is not a link. Use <button>.",
            ))
        # An empty link has no accessible name and no destination preview.
        if not accessible_name(elem) and not has_descendant(elem, "img"):
            findings.append(Finding(
                rule="a-empty",
                line=elem.line,
                message="<a> has no accessible name.",
            ))
    return findings


def check_buttons(root: Element) -> list[Finding]:
    """Rule ``button-empty``: every ``<button>`` needs an accessible name."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag != "button":
            continue
        if not accessible_name(elem) and not has_descendant(elem, "img") and not has_descendant(elem, "svg"):
            findings.append(Finding(
                rule="button-empty",
                line=elem.line,
                message="<button> has no accessible name. Add text or aria-label.",
            ))
    return findings


def check_divspan_onclick(root: Element) -> list[Finding]:
    """Rule ``div-onclick``: ``<div>`` / ``<span>`` with ``onclick`` must be a button."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag not in {"div", "span"}:
            continue
        if "onclick" not in elem.attrs:
            continue
        # If the author opted into ``role="button"`` and a ``tabindex``,
        # they've at least done the keyboard / AT plumbing. Still suboptimal
        # vs. a real <button> but not a violation worth flagging.
        if elem.attrs.get("role", "") == "button" and "tabindex" in elem.attrs:
            continue
        findings.append(Finding(
            rule="div-onclick",
            line=elem.line,
            message=f"<{elem.tag}> with onclick: prefer <button>, or add role=\"button\" + tabindex.",
        ))
    return findings


def check_input_label(root: Element) -> list[Finding]:
    """Rule ``input-missing-label``: every focusable ``<input>`` needs a label."""
    findings: list[Finding] = []
    # Collect every ``for=...`` so we can answer "is this input referenced?".
    referenced_ids: set[str] = set()
    for elem in walk(root):
        if elem.tag == "label" and elem.attrs.get("for", "").strip():
            referenced_ids.add(elem.attrs["for"].strip())

    for elem in walk(root):
        if elem.tag != "input":
            continue
        # Hidden / submit / button / image inputs don't need a label.
        if elem.attrs.get("type", "text").lower() in {
            "hidden", "submit", "button", "reset", "image",
        }:
            continue
        # A wrapped <label><input/></label> is fine — walk parents.
        wrapped: bool = False
        parent = elem.parent
        while parent is not None and parent.tag != "root":
            if parent.tag == "label":
                wrapped = True
                break
            parent = parent.parent

        if wrapped:
            continue
        if elem.attrs.get("id", "") in referenced_ids:
            continue
        if elem.attrs.get("aria-label", "").strip():
            continue
        findings.append(Finding(
            rule="input-missing-label",
            line=elem.line,
            message="<input> has no associated <label> and no aria-label.",
        ))
    return findings


def check_dialog_close(root: Element) -> list[Finding]:
    """Rule ``dialog-missing-close``: every ``<dialog>`` needs a way out."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag != "dialog":
            continue
        # A close button with ``value="cancel"`` is the conventional pattern;
        # the browser closes the dialog when it's clicked.
        ok: bool = False
        for descendant in walk(elem):
            if descendant.tag == "button" and (
                descendant.attrs.get("value", "") in {"cancel", "close"}
                or "autofocus" in descendant.attrs
                or accessible_name(descendant).lower() in {
                    "close", "cancel", "fermer", "annuler", "schließen",
                }
            ):
                ok = True
                break
        if not ok:
            findings.append(Finding(
                rule="dialog-missing-close",
                line=elem.line,
                message="<dialog> has no obvious close affordance (button value=cancel / autofocus / 'Close' / 'Cancel').",
            ))
    return findings


def check_tabindex_positive(root: Element) -> list[Finding]:
    """Rule ``tabindex-positive``: ``tabindex`` ≥ 1 is an anti-pattern."""
    findings: list[Finding] = []
    for elem in walk(root):
        raw = elem.attrs.get("tabindex", "").strip()
        if not raw:
            continue
        try:
            value = int(raw)
        except ValueError:
            continue
        if value >= 1:
            findings.append(Finding(
                rule="tabindex-positive",
                line=elem.line,
                message=f"<{elem.tag} tabindex=\"{value}\">: positive tabindex breaks DOM order.",
            ))
    return findings


def check_aria_hidden_interactive(root: Element) -> list[Finding]:
    """Rule ``aria-hidden-interactive``: hidden interactive elements are unreachable."""
    findings: list[Finding] = []
    for elem in walk(root):
        if elem.tag not in {"button", "a", "input", "select", "textarea"}:
            continue
        if elem.attrs.get("aria-hidden", "") == "true":
            findings.append(Finding(
                rule="aria-hidden-interactive",
                line=elem.line,
                message=f'<{elem.tag} aria-hidden="true"> removes the control from AT.',
            ))
    return findings


HEADING_TAGS: tuple[str, ...] = ("h1", "h2", "h3", "h4", "h5", "h6")


def check_heading_order(root: Element) -> list[Finding]:
    """Rule ``heading-skip``: heading levels must not skip downward."""
    findings: list[Finding] = []
    previous: int = 0
    for elem in walk(root):
        if elem.tag not in HEADING_TAGS:
            continue
        current: int = HEADING_TAGS.index(elem.tag) + 1
        # Skipping *up* is fine (h3 → h2). Skipping *down* by more than one
        # is the anti-pattern (h2 → h4 skips h3).
        if previous and current > previous + 1:
            findings.append(Finding(
                rule="heading-skip",
                line=elem.line,
                message=f"<{elem.tag}> follows <h{previous}>: heading levels skip downward.",
            ))
        previous = current
    return findings


# Compiled patterns reused across calls.
_COLOR_STATE_PAT: re.Pattern[str] = re.compile(
    r"(?:text|bg|border|ring)-(?:red|green|emerald|rose|crimson)-\d+"
)
_MOTION_PAT: re.Pattern[str] = re.compile(
    r"\b(animate-(?:spin|ping|pulse|bounce)|transition-transform|transition-all)\b"
)
_MOTION_REDUCE_PAT: re.Pattern[str] = re.compile(r"motion-reduce:")


def check_color_only_state(root: Element) -> list[Finding]:
    """Rule ``color-only-state``: a red/green token alone is not a state cue."""
    findings: list[Finding] = []
    for elem in walk(root):
        cls: str = elem.attrs.get("class", "")
        if not _COLOR_STATE_PAT.search(cls):
            continue
        # Skip if the element has accompanying text or icon content; a state
        # banner with an icon + label is fine.
        if elem.text.strip():
            continue
        if has_descendant(elem, "svg") or has_descendant(elem, "img"):
            continue
        findings.append(Finding(
            rule="color-only-state",
            line=elem.line,
            message=f"<{elem.tag}> uses a red/green token but has no icon or text. State must not rely on color alone.",
        ))
    return findings


def check_motion_reduce(root: Element) -> list[Finding]:
    """Rule ``motion-no-reduce-guard``: animations need a reduced-motion peer."""
    findings: list[Finding] = []
    for elem in walk(root):
        cls: str = elem.attrs.get("class", "")
        if not _MOTION_PAT.search(cls):
            continue
        if _MOTION_REDUCE_PAT.search(cls):
            continue
        findings.append(Finding(
            rule="motion-no-reduce-guard",
            line=elem.line,
            message=f"<{elem.tag}> animates without a motion-reduce: peer (prefers-reduced-motion ignored).",
        ))
    return findings


# Registered rules — declaring them in a list makes ``--ignore`` cheap.
ALL_RULES: dict[str, "Callable[..., Any]"] = {
    "html-missing-lang": check_html_lang,
    "img-missing-alt": check_img,
    "img-redundant-aria": check_img,
    "a-missing-href": check_links,
    "a-empty": check_links,
    "button-empty": check_buttons,
    "div-onclick": check_divspan_onclick,
    "input-missing-label": check_input_label,
    "dialog-missing-close": check_dialog_close,
    "tabindex-positive": check_tabindex_positive,
    "aria-hidden-interactive": check_aria_hidden_interactive,
    "heading-skip": check_heading_order,
    "color-only-state": check_color_only_state,
    "motion-no-reduce-guard": check_motion_reduce,
}


# ── Auto-fix machinery ────────────────────────────────────────────────────


def _detect_html_lang(lines: list[str]) -> Optional[str]:
    """Detect the document language from the HTML's own visible body text.

    Uses the shared :func:`_lang.extract_body_text` (HTML → visible text) and
    :func:`_lang.detect_text_language`. Returns a two-letter code, or ``None``
    when the language cannot be determined — ``langdetect`` absent, or too
    little text. **There is no default language**: the caller then leaves the
    finding unfixed rather than guessing.

    Parameters
    ----------
    lines : list of str
        The full HTML source, split into lines.

    Returns
    -------
    str or None
        Lower-case two-letter language code, or ``None`` if undetectable.
    """
    text: str = extract_body_text("\n".join(lines), "html")
    if len("".join(text.split())) < 20:
        return None
    # Empty fallback → ``detect_text_language`` returns "" when it cannot
    # detect (langdetect missing / low signal); map that to None (no default).
    code: str = detect_text_language(text, fallback="")
    return code or None


def _fix_html_missing_lang(lines: list[str], finding: "Finding") -> bool:
    """Insert ``lang="<detected>"`` into the ``<html …>`` opening tag.

    The language is **detected from the document's own visible body text** —
    there is no default language. When it cannot be detected (``langdetect``
    absent, or too little text), the finding is left unfixed for a human
    rather than guessing.
    """
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    line: str = lines[idx]
    # Only patch when the tag has no lang attr at all — re-running against a
    # fixed file is a no-op.
    if re.search(r"<html\b[^>]*\blang=", line, re.IGNORECASE):
        return False
    lang: Optional[str] = _detect_html_lang(lines)
    if not lang:
        return False  # cannot detect the language → do not inject a default
    new_line: str = re.sub(
        r"<html\b", f'<html lang="{lang}"', line, count=1, flags=re.IGNORECASE,
    )
    if new_line == line:
        return False
    lines[idx] = new_line
    return True


def _fix_img_redundant_aria(lines: list[str], finding: "Finding") -> bool:
    """Strip redundant ``role="presentation"`` / ``aria-hidden="true"`` from <img alt="">."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    line: str = lines[idx]
    new_line: str = re.sub(
        r'\s+role=["\']presentation["\']', "", line, count=1
    )
    new_line = re.sub(
        r'\s+aria-hidden=["\']true["\']', "", new_line, count=1
    )
    if new_line == line:
        return False
    lines[idx] = new_line
    return True


def _fix_tabindex_positive(lines: list[str], finding: "Finding") -> bool:
    """Demote ``tabindex="N>0"`` to ``tabindex="0"`` (preserves focusability)."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    line: str = lines[idx]
    new_line: str = re.sub(
        r'tabindex=(["\'])(?:[1-9]\d*)\1', r'tabindex=\g<1>0\1',
        line, count=1,
    )
    if new_line == line:
        return False
    lines[idx] = new_line
    return True


def _fix_aria_hidden_interactive(lines: list[str], finding: "Finding") -> bool:
    """Strip ``aria-hidden="true"`` from an interactive element."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    line: str = lines[idx]
    new_line: str = re.sub(
        r'\s+aria-hidden=["\']true["\']', "", line, count=1
    )
    if new_line == line:
        return False
    lines[idx] = new_line
    return True


def _fix_motion_reduce_guard(lines: list[str], finding: "Finding") -> bool:
    """Append a ``motion-reduce:`` guard to the offending element's class list."""
    idx: int = finding.line - 1
    if not (0 <= idx < len(lines)):
        return False
    line: str = lines[idx]
    m = re.search(r'''class=(["'])((?:(?!\1).)*)\1''', line)
    if not m:
        return False
    existing: list[str] = m.group(2).split()
    # Already has any motion-reduce token? No-op.
    if any(c.startswith("motion-reduce:") for c in existing):
        return False
    new_classes: str = " ".join(existing + ["motion-reduce:transform-none"])
    lines[idx] = line[: m.start(2)] + new_classes + line[m.end(2) :]
    return True


#: Mapping of rule id → fixer. Only rules whose violations have a
#: single safe mechanical repair appear here. Empty links / empty
#: buttons / missing labels / missing headings / color-only state
#: are deliberately absent — those need a content decision the
#: linter cannot make for the user.
RULE_FIXERS: dict[str, "Callable[..., Any]"] = {
    "html-missing-lang": _fix_html_missing_lang,
    "img-redundant-aria": _fix_img_redundant_aria,
    "tabindex-positive": _fix_tabindex_positive,
    "aria-hidden-interactive": _fix_aria_hidden_interactive,
    "motion-no-reduce-guard": _fix_motion_reduce_guard,
}


#: Maximum fix→lint→fix passes per file. None of the current fixers
#: introduces new findings (unlike Jakob in audit_laws_of_ux); a
#: single pass is enough. The cap is here for symmetry and safety.
MAX_FIX_ITERATIONS: int = 3


def fix_file(
    path: Path, ignored: set[str], *, dry_run: bool = False
) -> tuple[int, int, list["Finding"]]:
    """
    Apply mechanical accessibility fixes to one HTML file in place.

    Idempotent: a second invocation against a fixed file applies
    zero edits. Iterates the lint→fix loop up to
    :data:`MAX_FIX_ITERATIONS` times — no current fixer introduces
    new findings, but the cap leaves headroom for future additions.

    Parameters
    ----------
    path : Path
        File to repair.
    ignored : set of str
        Rule ids to suppress (passed through to :func:`lint_file`).
    dry_run : bool, default False
        If ``True``, never write to disk — just compute and return
        the would-be counts.

    Returns
    -------
    (int, int, list of Finding)
        ``(applied, skipped, remaining)`` — number of edits that
        landed, count of findings with no fixer, and the residual
        findings after the final write.
    """
    raw: str = path.read_text(encoding="utf-8", errors="ignore")
    bare_lines: list[str] = raw.splitlines()
    applied: int = 0
    skipped: int = 0
    skipped_seen: bool = False

    if dry_run:
        findings: list["Finding"] = lint_file(path, ignored)
        for f in findings:
            fixer = RULE_FIXERS.get(f.rule)
            if fixer is None:
                skipped += 1
                continue
            shadow: list[str] = bare_lines[:]
            if fixer(shadow, f):
                applied += 1
        return applied, skipped, findings

    for _ in range(MAX_FIX_ITERATIONS):
        new_text: str = "\n".join(bare_lines)
        if raw.endswith("\n"):
            new_text += "\n"
        path.write_text(new_text, encoding="utf-8")
        findings = lint_file(path, ignored)
        round_applied: int = 0
        round_skipped: int = 0
        for f in findings:
            fixer = RULE_FIXERS.get(f.rule)
            if fixer is None:
                round_skipped += 1
                continue
            if fixer(bare_lines, f):
                round_applied += 1
        applied += round_applied
        if not skipped_seen:
            skipped = round_skipped
            skipped_seen = True
        if round_applied == 0:
            break
    new_text = "\n".join(bare_lines)
    if raw.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text, encoding="utf-8")
    remaining: list["Finding"] = lint_file(path, ignored)
    return applied, skipped, remaining


# ── Orchestration ────────────────────────────────────────────────────────

def lint_file(path: Path, ignored: set[str]) -> list[Finding]:
    """
    Run every enabled rule against one HTML file.

    Parameters
    ----------
    path : Path
        HTML file to lint.
    ignored : set of str
        Rule identifiers to suppress.

    Returns
    -------
    list of Finding
        All findings from the enabled rules, deduplicated by (rule, line).
    """
    html = path.read_text(encoding="utf-8", errors="ignore")
    parser = TreeBuilder()
    parser.feed(html)
    parser.close()

    findings: list[Finding] = []
    # Some rule functions emit two rule ids (e.g. ``check_img`` for missing
    # alt and redundant aria). Run each distinct rule function once and
    # then filter findings by the ignored set.
    seen: set[int] = set()
    for fn in {ALL_RULES[r] for r in ALL_RULES if r not in ignored}:
        if id(fn) in seen:
            continue
        seen.add(id(fn))
        for f in fn(parser.root):
            if f.rule in ignored:
                continue
            findings.append(f)

    # Stable order: by line, then by rule.
    findings.sort(key=lambda x: (x.line, x.rule))
    return findings


def collect_targets(target: Path) -> list[Path]:
    """
    Resolve ``target`` to a list of ``.html`` files to lint.

    Parameters
    ----------
    target : Path
        File or directory.

    Returns
    -------
    list of Path
        Every ``.html`` file at or under ``target``.
    """
    if target.is_file():
        return [target]
    return sorted(target.rglob("*.html"))


def main() -> int:
    """
    CLI entry point.

    Returns
    -------
    int
        ``0`` on no findings, ``1`` on any finding.
    """
    p = make_parser(
        prog="sprezzature-accessibility-lint",
        description="W3C/WAI accessibility linter for HTML emitted by the sprezzature skill. "
                    "14 rules, exit 1 on any finding. Pre-commit gate — pair with axe-core "
                    "or Pa11y for runtime DOM audits.",
        epilog="Examples:\n"
               "  sprezzature-accessibility-lint public/index.html\n"
               "  sprezzature-accessibility-lint --format json public/\n"
               "  sprezzature-accessibility-lint --ignore IMG_ALT,A_HREF dist/\n",
    )
    p.add_argument(
        "target", type=Path,
        help="HTML file or directory to lint.",
    )
    p.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format. Default: text.",
    )
    p.add_argument(
        "--ignore", default="",
        help="Comma-separated list of rule ids to skip.",
    )
    p.add_argument(
        "--fix", action="store_true",
        help=(
            "Apply safe mechanical fixes in place: add lang to <html>, "
            "strip redundant role/aria-hidden from decorative <img alt=''>, "
            "demote tabindex>0 to 0, strip aria-hidden from interactive "
            "elements, append motion-reduce:transform-none to animated "
            "elements. Rules without a fixer (empty button, missing "
            "label, heading skip, etc.) are passed through honestly. "
            "Idempotent."
        ),
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help=(
            "With --fix, print what would change without touching the "
            "files. Implies --fix when used alone. Always exits 0."
        ),
    )
    args = p.parse_args()

    ignored: set[str] = {r.strip() for r in args.ignore.split(",") if r.strip()}
    paths = collect_targets(args.target)
    if not paths:
        sys.stderr.write(f"No HTML files found under {args.target}\n")
        return 0

    # ── Fix mode ──────────────────────────────────────────────────────
    # ``--dry-run`` alone implies ``--fix`` (preview only). When the
    # user runs ``--fix``, we apply the safe mechanical fixes in place,
    # then emit the residual findings in the requested format so a CI
    # pipeline can still gate on them.
    if args.fix or args.dry_run:
        total_applied: int = 0
        total_skipped: int = 0
        total_remaining: list[Finding] = []
        for path in paths:
            applied, skipped, remaining = fix_file(
                path, ignored, dry_run=args.dry_run
            )
            total_applied += applied
            total_skipped += skipped
            total_remaining.extend(remaining)
            verb: str = "would apply" if args.dry_run else "applied"
            sys.stderr.write(
                f"{path}: {verb} {applied} fix(es); "
                f"{skipped} unfixable finding(s); "
                f"{len(remaining)} remaining.\n"
            )
        if args.format == "json":
            json.dump(
                {
                    "applied": total_applied,
                    "skipped": total_skipped,
                    "findings_total": len(total_remaining),
                    "findings": [
                        {"rule": f.rule, "line": f.line, "message": f.message}
                        for f in total_remaining
                    ],
                },
                sys.stdout, indent=2, ensure_ascii=False,
            )
            sys.stdout.write("\n")
        else:
            if total_remaining:
                print(
                    f"{len(total_remaining)} remaining finding(s) after "
                    f"{'preview' if args.dry_run else 'fix'} pass."
                )
            else:
                print("0 findings remaining.")
        # Dry-run is a preview, not a verdict — always exit 0.
        if args.dry_run:
            return 0
        return 0 if not total_remaining else 1

    # ── Audit-only mode ───────────────────────────────────────────────
    total: int = 0
    failing_files: int = 0
    report: list[dict] = []
    for path in paths:
        findings = lint_file(path, ignored)
        if not findings:
            continue
        total += len(findings)
        failing_files += 1
        if args.format == "text":
            print(f"{path}:")
            for f in findings:
                print(f"  L{f.line:>4}  [{f.rule}] {f.message}")
        # ``report`` is populated in both formats so the JSON output has the
        # same coverage as the text output.
        report.append({
            "file": str(path),
            "findings": [
                {"rule": f.rule, "line": f.line, "message": f.message}
                for f in findings
            ],
        })

    if args.format == "json":
        json.dump({"findings_total": total, "files": report},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print()
        if total == 0:
            print("0 findings.")
        else:
            print(f"{total} finding(s) across {failing_files} file(s).")

    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
