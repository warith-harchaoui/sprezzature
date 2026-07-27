#!/usr/bin/env python3
"""
build_triggers
==============

Read every shipped SKILL.md, extract its trigger phrases from the
``description`` field, and emit ``TRIGGERS.md`` at repo root —
a single table mapping each user-facing prompt phrase to the skill
it activates and that skill's status.

Why this file exists
--------------------

Trigger phrases already live in each SKILL.md's frontmatter — that
is the Anthropic-spec location and what Claude / OpenCode actually
read at conversation time. ``TRIGGERS.md`` is a **generated**
quick-reference for humans who want to know which prompt invokes
which behaviour without grep'ing eight SKILL.mds.

Hand-maintaining the same list in two places risks drift; this
script makes ``TRIGGERS.md`` a deterministic projection of the
SKILL.md descriptions. A companion test
(``tests/test_triggers_md.py``) asserts that the committed
``TRIGGERS.md`` equals the generated output — so a CHANGELOG-worthy
trigger-phrase change in any SKILL.md fails CI until the generated
file is refreshed.

Run
---
::

    python scripts/build_triggers.py            # writes TRIGGERS.md
    python scripts/build_triggers.py --check    # exit 1 if drift

Status source
-------------

The status column is a small static map (``STATUS``) inside this
module. The test asserts every shipped skill in ``SKILLS.txt``
appears in the map — so adding skill #9 forces a status decision
rather than silently shipping it as "unknown".

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from skills_manifest import SHIPPED_SKILLS


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
OUTPUT: Path = REPO_ROOT / "TRIGGERS.md"


#: Status of each shipped skill, in the same shape as the README's
#: Status section. Update this when a skill's maturity changes; the
#: test asserts every entry in :data:`SHIPPED_SKILLS` has an entry
#: here so adding skill #9 forces a status decision at PR time.
STATUS: dict[str, str] = {
    "sprezzature-ui": "Stable",
    "sprezzature-cli-gui": "Stable",
    "sprezzature-publish": "Stable",
    "sprezzature-accessibility": "Stable",
    "sprezzature-colors": "Stable",
    "sprezzature-vision": "Stable",
    "sprezzature-audio": "Stable — WiP: caption WER baselines",
    "sprezzature-ux-laws": "Stable",
    "sprezzature-figures": "Stable",
}


#: One-sentence summary per skill — what the agent does when the
#: trigger fires. Static to keep the projection from this script
#: deterministic; the matching SKILL.md description is the canonical
#: long-form prose.
WHAT_IT_DOES: dict[str, str] = {
    "sprezzature-ui": "Generates vanilla JS + Tailwind UI (components, pages, dataviz, audit).",
    "sprezzature-cli-gui": "Wraps an argparse / Click / any-CLI in a single-page HTML GUI (three adapters).",
    "sprezzature-publish": "Markdown → static site + meta tags + favicons + site indexes + plain-language rewrite.",
    "sprezzature-accessibility": "Static HTML a11y lint (14 rules) with `--fix` for the five safe mechanical repairs.",
    "sprezzature-colors": "WCAG contrast audit + CVD simulation + curated palette + Tailwind config emitter.",
    "sprezzature-vision": "Drafts W3C-compliant alt text via local Ollama vision (qwen3-vl:8b).",
    "sprezzature-audio": "Drafts WebVTT / SRT captions via whisper.cpp, adds speaker diarization (NeMo Sortformer), speaker ID (TitaNet or transcript-based rule + local Ollama), and speaker-labelled VTT.",
    "sprezzature-ux-laws": "Applies / audits the canonical Laws of UX (30 laws) with `--fix` for four mechanical fixers.",
    "sprezzature-figures": "Emits data-viz / SHAP / Shapash / TimeSHAP / LIME / DoWhy figures + audits Vega specs and matplotlib SVGs.",
}


def _description(skill: str) -> str:
    """
    Read the ``description`` field from a skill's SKILL.md frontmatter.

    Raises
    ------
    FileNotFoundError
        If the skill folder or its SKILL.md is missing.
    KeyError
        If the frontmatter lacks a description field.
    """
    path: Path = REPO_ROOT / skill / "SKILL.md"
    text: str = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter block")
    sprezzature = yaml.safe_load(m.group(1))
    return sprezzature["description"]


def _extract_triggers(description: str) -> list[str]:
    """
    Extract trigger-phrase string literals from a SKILL.md description.

    Looks for the canonical ``Trigger phrases:`` marker and pulls
    every double- or single-quoted string after it. When the marker
    is absent, returns an empty list — the caller may choose to use
    the description as-is.

    Parameters
    ----------
    description : str
        The SKILL.md frontmatter description, raw.

    Returns
    -------
    list of str
        Trigger phrases in declaration order, deduplicated.
    """
    # Some skills use "Trigger phrases:", others embed quotes directly
    # in prose ("Use it for ..."). We accept both — anything quoted in
    # the description is a trigger candidate.
    parts: list[tuple[str, str]] = re.findall(r'"([^"]+)"|“([^”]+)”', description)
    flat: list[str] = [a or b for a, b in parts]
    # Deduplicate while preserving first-seen order.
    seen: set[str] = set()
    out: list[str] = []
    for phrase in flat:
        if phrase not in seen:
            seen.add(phrase)
            out.append(phrase)
    return out


def build() -> str:
    """
    Render the full TRIGGERS.md file from every shipped SKILL.md.

    Returns
    -------
    str
        Markdown body, ending with a newline.
    """
    rows: list[str] = []
    rows.append("# Trigger phrases — what to say to invoke each sprezzature-* skill")
    rows.append("")
    rows.append(
        "**Generated by `scripts/build_triggers.py`** from every shipped "
        "skill's `SKILL.md` description. **Do not hand-edit** — a test "
        "in `tests/test_triggers_md.py` asserts this file equals the "
        "generated output on every commit. To change a phrase, edit the "
        "relevant `SKILL.md` and re-run the generator."
    )
    rows.append("")
    rows.append(
        "The trigger phrases below are what each skill's frontmatter "
        "description claims will activate it in Claude Code / OpenCode. "
        "They are not the only phrases that work — the agent matches "
        "prompts to the description holistically — but they are the "
        "ones the maintainer guarantees."
    )
    rows.append("")
    rows.append("| Trigger phrase | Activates | Status |")
    rows.append("|---|---|---|")

    for skill in SHIPPED_SKILLS:
        triggers: list[str] = _extract_triggers(_description(skill))
        what: str = WHAT_IT_DOES[skill]
        status: str = STATUS[skill]
        for phrase in triggers:
            # Escape pipe characters in the phrase so the table parses
            # cleanly. Markdown tables use ``|`` as the delimiter.
            safe: str = phrase.replace("|", "\\|")
            rows.append(
                f"| `{safe}` | **{skill}** — {what} | {status} |"
            )

    rows.append("")
    rows.append("## How discovery works")
    rows.append("")
    rows.append(
        "Claude Code / OpenCode read every installed skill's "
        "`SKILL.md` frontmatter at conversation start. When the user's "
        "prompt matches a description, that skill is loaded and its "
        "instructions become available. The agent matches "
        "semantically — phrases above are illustrative, not "
        "exhaustive. Say what you mean; the right skill should fire."
    )
    rows.append("")
    rows.append("## Adding a new trigger")
    rows.append("")
    rows.append(
        "1. Edit the relevant `<skill>/SKILL.md` `description` field; "
        "add the new quoted phrase to the existing Trigger-phrase "
        "list.\n"
        "2. Re-run `python scripts/build_triggers.py`.\n"
        "3. Commit both files together — the test will refuse a "
        "commit where they drift."
    )
    rows.append("")
    return "\n".join(rows) + "\n"


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns
    -------
    int
        ``0`` on success; ``1`` when ``--check`` finds drift.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="sprezzature-build-triggers",
        description=(
            "Generate TRIGGERS.md from every shipped SKILL.md. "
            "Use --check in CI to fail on drift."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Compare the generated output to the committed "
            "TRIGGERS.md and exit 1 on any difference. Do not write."
        ),
    )
    args: argparse.Namespace = parser.parse_args(argv)

    generated: str = build()
    if args.check:
        if not OUTPUT.is_file():
            print(
                f"TRIGGERS.md does not exist at {OUTPUT}. Run without "
                f"--check to generate it.",
                file=sys.stderr,
            )
            return 1
        current: str = OUTPUT.read_text(encoding="utf-8")
        if current != generated:
            print(
                "TRIGGERS.md is out of sync with the SKILL.md "
                "descriptions. Re-run scripts/build_triggers.py and "
                "commit both files together.",
                file=sys.stderr,
            )
            return 1
        print("TRIGGERS.md is in sync.")
        return 0

    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(generated)} chars).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
