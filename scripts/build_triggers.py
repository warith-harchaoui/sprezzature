#!/usr/bin/env python3
"""
build_triggers
==============

Read every shipped SKILL.md, extract its trigger phrases from the
``description`` field, and emit ``TRIGGERS.md`` at repo root: a single
table mapping each user-facing prompt phrase to the skill it activates
and that skill's status.

Why this file exists
--------------------

Trigger phrases already live in each SKILL.md's frontmatter; that
is the Anthropic-spec location and what Claude / OpenCode actually
read at conversation time. ``TRIGGERS.md`` is a **generated**
quick-reference for humans who want to know which prompt invokes
which behaviour without grep'ing eight SKILL.mds.

Hand-maintaining the same list in two places risks drift; this
script makes ``TRIGGERS.md`` a deterministic projection of the
SKILL.md descriptions. A companion test
(``tests/test_triggers_md.py``) asserts that the committed
``TRIGGERS.md`` equals the generated output, so a CHANGELOG-worthy
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
appears in the map, so adding skill #9 forces a status decision
rather than silently shipping it as "unknown".

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
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
    "sprezzature-accessibility": 'Stable',
    "sprezzature-colors": "Stable",
    "sprezzature-audio": "Stable (WiP: caption WER baselines)",
    "sprezzature-ux-laws": "Stable",
    "sprezzature-figures": "Stable",
    "sprezzature-maps": "Stable",
    "sprezzature-video": "Beta (the renderer seam is still out of band)",
}


#: One-sentence summary per skill: what the agent does when the
#: trigger fires. Static to keep the projection from this script
#: deterministic; the matching SKILL.md description is the canonical
#: long-form prose.
WHAT_IT_DOES: dict[str, str] = {
    "sprezzature-ui": "Generates vanilla JS + Tailwind UI (components, pages, dataviz, audit).",
    "sprezzature-cli-gui": "Wraps an argparse / Click / any-CLI in a single-page HTML GUI (three adapters).",
    "sprezzature-publish": "Markdown → static site + meta tags + favicons + site indexes + plain-language rewrite.",
    "sprezzature-accessibility": 'Static HTML a11y lint (20 rules, time-based media included) with `--fix` for the six safe mechanical repairs. Drafts W3C-compliant alt text via local Ollama vision (qwen3-vl:8b).',
    "sprezzature-colors": "WCAG contrast audit + CVD simulation + curated palette + Tailwind config emitter.",
    "sprezzature-audio": "Drafts WebVTT / SRT captions via whisper.cpp, adds speaker diarization (NeMo Sortformer), speaker ID (TitaNet or transcript-based rule + local Ollama), and speaker-labelled VTT — and reads written text aloud through Kokoro, OpenVoice or Chatterbox, timed track included.",
    "sprezzature-ux-laws": "Applies / audits the canonical Laws of UX (30 laws) with `--fix` for four mechanical fixers.",
    "sprezzature-figures": "Emits data-viz / SHAP / Shapash / TimeSHAP / LIME / DoWhy figures as hand-authored SVG + audits rendered SVG and HTML figures.",
    "sprezzature-maps": "Draws a choropleth or an areas-of-control situation map on real geography — real coastlines, a real projection, a bundled basemap.",
    "sprezzature-video": "Checks what a project video SAYS against the project: declared claims against the code, numbers on screen against the declared claims, and whether the film can be rendered again from a clone. Captions from the narration script and the measured audio.",
}


#: What the user is holding when each skill is the right answer, and the
#: phrases that say so without naming a tool. This is the half of discovery
#: a phrase list cannot do: the phrases below the routing table are matched
#: one at a time, but a reader choosing between nine skills needs to know
#: what KIND of thing each one takes. The test asserts every entry in
#: :data:`SHIPPED_SKILLS` appears here, so skill #10 forces the decision at
#: PR time rather than quietly missing from the table.
ROUTES: dict[str, tuple[str, str]] = {
    "sprezzature-figures": (
        "Numbers you want somebody to SEE — or a picture of a chart that is hard to read",
        '"show me this data", "which region is biggest", "what does this look like", '
        '"a colleague sent me this graph", « fais-moi voir », « un visuel de ça »',
    ),
    "sprezzature-ui": (
        "A screen to build: a page, a component, a form, a dashboard",
        '"build me a settings page", "I need a modal", "scaffold a landing page", '
        '"audit this UI", « une page pour… »',
    ),
    "sprezzature-cli-gui": (
        "A command-line tool somebody who will not type it needs to run",
        '"my colleague keeps getting the flags wrong", "can non-technical people use '
        'this", « une interface pour l\'équipe »',
    ),
    "sprezzature-publish": (
        "Markdown that has to become a site somebody else can find",
        '"put this online", "why does this look bad when shared", "SEO", "favicons", '
        '"make it readable for a wider audience"',
    ),
    "sprezzature-accessibility": (
        'HTML — usually HTML YOU JUST WROTE, before anyone asks; An image that needs words: alt text, a description, a caption',
        '"is this accessible", "missing alt", "unlabelled input", « vérifie l\'accessibilité »; "describe this image", "draft alt text", "this img has no alt"',
    ),
    "sprezzature-video": (
        "A video that states a fact about a project — or a project that changed under a film already shipped",
        '"make a launch video", "the demo video is out of date", "is this number still right", "re-cut the film", « refais la vidéo »',
    ),
    "sprezzature-ux-laws": (
        "An interface somebody is complaining about the FEEL of",
        '"this page is overwhelming", "too many options", "I can never find the '
        'button", « c\'est confus »',
    ),
    "sprezzature-colors": (
        "A colour being chosen or judged — any colour, in any context",
        '"what colour should this be", "does this pass contrast", "is this '
        'colour-blind safe", « quelle couleur pour ce fond »',
    ),
    "sprezzature-audio": (
        "Recorded speech somebody needs as text, a question about that "
        "text — or written text somebody needs as speech",
        '"what did they say in this meeting", "who spoke when", "subtitles", '
        '"read this aloud", « de quoi ils parlent dans cet enregistrement »',
    ),
    "sprezzature-maps": (
        "Numbers attached to PLACES — a column of countries, regions, states, "
        "départements",
        '"which countries are worst affected", "break this down by region", '
        '"where is this happening", "who holds the east", « par département »',
    ),
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
    is absent, returns an empty list; the caller may choose to use
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
    # in prose ("Use it for ..."). Both forms are accepted: anything
    # quoted in the description is a trigger candidate.
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


#: Marker that opens a description's skip clause. Written in every shipped
#: SKILL.md so the half that says "not this one" lives where an agent will
#: actually read it -- the frontmatter description -- rather than only here.
SKIP_MARKER: str = "Not this one when:"


def _extract_skip(description: str) -> str:
    """
    The clause naming the cases a skill should *not* answer.

    Ten siblings compete for every prompt, and the phrase list only ever
    argues for firing. The clause that argues against it is what keeps a
    contrast question away from the a11y linter and a hex map away from the
    cartographer. Returns an empty string when the marker is absent, which
    the test treats as a failure rather than a default.
    """
    _, _, tail = description.partition(SKIP_MARKER)
    return " ".join(tail.split()).strip()


#: Every phrase that names a skill, exhaustively -- including the ones the
#: 1024-char description cannot afford to carry. The description is what an
#: agent reads to *choose*; this is what it reads once it has chosen, via
#: each skill's ``references/triggers.md``. One source, two renderings, so
#: the two cannot drift.
CATALOGUE: dict[str, list[str]] = {
    "sprezzature-ui": [
        "build a UI",
        "create a component",
        "design a page",
        "make a form / modal / button / nav",
        "scaffold a landing",
        "build a web app",
        "audit this UI",
        "dashboard / data table",
        "settings page",
        "i18n to YAML",
        "audit i18n",
    ],
    "sprezzature-cli-gui": [
        "wrap this CLI in a GUI",
        "build a UI for my CLI",
        "argparse to GUI",
        "click to web UI",
        "GUI for my Python script",
        "wrap my command-line tool",
        "web form for my script",
        "Typer / clap / cobra to GUI",
        "GUI for my Go or Rust CLI",
        "frontend for a CLI",
        "streaming log panel for a CLI",
    ],
    "sprezzature-publish": [
        "markdown to website",
        "meta tags",
        "OG card",
        "SEO",
        "AI Overview",
        "GEO",
        "favicons",
        "app icons",
        "robots.txt",
        "sitemap",
        "llms.txt",
        "llms-full.txt",
        "Atom feed",
        "RSS",
        "plain language",
        "rewrite at grade N",
        "simplify this copy",
        "narrate this post",
        "podcast my blog",
        "text to speech",
        "schema.org JSON-LD",
        "humans.txt",
        "lint markdown",
        "OpenVoice / Chatterbox TTS",
        "read-along",
    ],
    "sprezzature-accessibility": [
        'a11y lint',
        'check this HTML for accessibility',
        'static a11y check',
        'WCAG-friendly lint',
        'a11y pre-commit',
        'missing alt',
        'unlabelled input',
        'WCAG compliance',
        'ARIA / keyboard check',
        'letter-spacing',
        'fix accessibility',
        'alt text',
        'alt text for this image',
        'describe this image',
        'draft alt',
        'write alt text',
        'image description',
        'img has no alt',
        'decorative image',
        'functional image',
        'figure / chart description',
        'accessible images',
        'batch alt text',
    ],
    "sprezzature-colors": [
        "WCAG check",
        "contrast audit",
        "is my palette accessible",
        "colorblind preview",
        "deuteranope",
        "CVD",
        "lighten this color",
        "OKLCH",
        "Apple palette",
        "emotion color",
        "palette to tailwind",
        "regenerate brand tokens",
        "tailwind config from palette",
        "brand colors",
        "accessible color pair",
        "color-blind safe",
        "protanopia / tritanopia",
        "generate palette",
    ],
    "sprezzature-audio": [
        "captions",
        "transcribe video",
        "transcribe audio",
        "WebVTT",
        "SRT",
        "subtitle file",
        "VTT",
        "diarization",
        "who spoke when",
        "Sortformer",
        "TitaNet",
        "identify speakers",
        "name the speakers",
        "translate captions",
        "translated subtitles",
        "subtitles",
        "who is who",
        "I'm Alice",
        "Hey Mary, ...",
        "text to speech",
        "TTS",
        "narrate",
        "read this aloud",
        "synthesise a voice",
        "which voice",
        "Kokoro",
    ],
    "sprezzature-video": [
        "make a launch video",
        "the demo video is out of date",
        "verify the claims in this video",
        "re-cut the film",
        "is this number still right",
        "can we rebuild this video",
        "captions for the film",
        "poster frame",
    ],
    "sprezzature-ux-laws": [
        "design this screen using Hick / Fitts / Miller",
        "what does Peak-End say here",
        "is this onboarding fighting the Paradox of the Active User",
        "audit for Laws of UX",
        "is my nav too Hick-heavy",
        "check my form for Postel / Tesler",
        "too many choices / options",
        "cognitive load",
        "Doherty threshold",
        "reduce clutter",
        "this page is overwhelming",
    ],
    "sprezzature-figures": [
        "make a figure",
        "chart this",
        "plot this",
        "draw a chart",
        "heatmap",
        "treemap",
        "candlestick",
        "choropleth",
        "GPS map",
        "situation map",
        "sankey",
        "mermaid diagram",
        "no ascii art",
        "ralph eyeball loop",
        "SHAP plot",
        "DAG",
        "audit this figure",
        "bell curve",
        "funnel chart",
        "sunburst",
        "waterfall chart",
        "P&L bridge",
        "redraw this chart",
        "make this ugly chart better",
        "rends ce graphique plus lisible",
    ],
    "sprezzature-maps": [
        "situation",
        "map",
        "map this by country",
        "colour the regions by score",
        "which country is worst affected",
        "break this down by region",
        "where is this happening",
        "show me the spread across Europe",
        "world map",
        "choropleth",
        "thematic map",
        "areas of control",
        "front line",
        "contested zones",
        "who controls what",
        "situation map",
        "where did these incidents fall",
        "une carte par departement",
        "carte de situation",
    ],
}

def build_skill_reference(skill: str) -> str:
    """
    Render one skill's ``references/triggers.md``.

    The description an agent reads to choose between ten siblings is capped
    at 1024 characters by the Anthropic spec, which buys routing, a skip
    clause and a handful of phrases -- not an exhaustive list. This file is
    where the rest lives, and it is generated from the same source so the two
    cannot say different things.
    """
    holding, phrasing = ROUTES[skill]
    rows: list[str] = [
        f"# Trigger catalogue — {skill}",
        "",
        "**Generated by `scripts/build_triggers.py`. Do not hand-edit.** A test "
        "asserts this file equals the generated output, so a phrase added here "
        "and nowhere else fails CI.",
        "",
        f"{WHAT_IT_DOES[skill]}",
        "",
        "## When this skill is the answer",
        "",
        f"**You are holding:** {holding}.",
        "",
        "A phrase list cannot generalise — the ways to ask are unbounded, and a "
        "user almost never names the tool. What is bounded is the kind of thing "
        "in front of them. Match that first; the phrases below confirm a match, "
        "they do not make one.",
        "",
        f"Said without naming a tool: {phrasing}",
        "",
        "## When it is not",
        "",
        f"Not this one when: {_extract_skip(_description(skill))}",
        "",
        "## Every phrase that names this skill",
        "",
    ]
    rows += [f"- `{phrase}`" for phrase in CATALOGUE[skill]]
    rows.append("")
    return "\n".join(rows) + "\n"


def build() -> str:
    """
    Render the full TRIGGERS.md file from every shipped SKILL.md.

    Returns
    -------
    str
        Markdown body, ending with a newline.
    """
    rows: list[str] = []
    rows.append("# Trigger phrases: what to say to invoke each sprezzature-* skill")
    rows.append("")
    rows.append(
        "**Generated by `scripts/build_triggers.py`** from every shipped "
        "skill's `SKILL.md` description. **Do not hand-edit.** A test "
        "in `tests/test_triggers_md.py` asserts this file equals the "
        "generated output on every commit. To change a phrase, edit the "
        "relevant `SKILL.md` and re-run the generator."
    )
    rows.append("")
    rows.append(
        "The trigger phrases below are what each skill's frontmatter "
        "description claims will activate it in Claude Code / OpenCode. "
        "They are not the only phrases that work (the agent matches "
        "prompts to the description holistically), but they are the "
        "ones the maintainer guarantees."
    )
    rows.append("")
    rows.append("## Route on what the user is holding")
    rows.append("")
    rows.append(
        "A phrase list cannot generalise: the ways to ask for a chart, a "
        "colour or a caption are unbounded, and a user almost never names "
        "the tool. What IS bounded is the kind of thing they have in front "
        "of them. Match that first; the phrase table below is confirmation, "
        "not the mechanism."
    )
    rows.append("")
    rows.append("| What the user is holding | Skill | Said without naming a tool |")
    rows.append("|---|---|---|")
    for skill in SHIPPED_SKILLS:
        holding, phrasing = ROUTES[skill]
        rows.append(f"| {holding} | **{skill}** | {phrasing} |")
    rows.append("")
    rows.append(
        "Two of these fire on work you just did rather than on a request: "
        "**sprezzature-accessibility** on any HTML you authored, and "
        "**sprezzature-ux-laws** on any interface you authored. Waiting to "
        "be asked means the markup nobody checked is the markup you wrote."
    )
    rows.append("")
    rows.append("Several can be right at once. A page you just built is a "
                "**ui** job, then an **accessibility** lint, a **ux-laws** "
                "audit and a **colors** contrast check — three different "
                "questions about one artefact, and passing one says nothing "
                "about the others.")
    rows.append("")
    rows.append("## Guaranteed trigger phrases")
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
                f"| `{safe}` | **{skill}**: {what} | {status} |"
            )

    rows.append("")
    rows.append("## When NOT to fire")
    rows.append("")
    rows.append(
        "The phrase table only ever argues for firing. Ten siblings compete "
        "for every prompt, and the clause that argues *against* one is what "
        "keeps a contrast question away from the a11y linter and a hex map "
        "away from the cartographer. Each skill carries its own, in the same "
        "`description` an agent reads to choose — not only here."
    )
    rows.append("")
    rows.append("| Skill | Not this one when |")
    rows.append("|---|---|")
    for skill in SHIPPED_SKILLS:
        skip: str = _extract_skip(_description(skill))
        rows.append(f"| **{skill}** | {skip.replace('|', chr(92) + '|')} |")
    rows.append("")
    rows.append("## How discovery works")
    rows.append("")
    rows.append(
        "Claude Code / OpenCode read every installed skill's "
        "`SKILL.md` frontmatter at conversation start. When the user's "
        "prompt matches a description, that skill is loaded and its "
        "instructions become available. The agent matches "
        "semantically: phrases above are illustrative, not "
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
        "3. Commit both files together; the test will refuse a "
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

    # Repo-root index plus one catalogue per skill: the index is for a human
    # scanning ten skills at once, the catalogue ships *inside* the skill, so
    # an agent that has chosen can read the exhaustive list without the repo.
    targets: dict[Path, str] = {OUTPUT: build()}
    for skill in SHIPPED_SKILLS:
        targets[REPO_ROOT / skill / "references" / "triggers.md"] = (
            build_skill_reference(skill)
        )

    if args.check:
        drifted: list[Path] = [
            path for path, generated in targets.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != generated
        ]
        if drifted:
            for path in drifted:
                print(
                    f"{path.relative_to(REPO_ROOT)} is out of sync with the "
                    f"SKILL.md descriptions.",
                    file=sys.stderr,
                )
            print(
                "Re-run scripts/build_triggers.py and commit the files "
                "together.",
                file=sys.stderr,
            )
            return 1
        print(f"{len(targets)} trigger files are in sync.")
        return 0

    for path, generated in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generated, encoding="utf-8")
    print(f"Wrote {len(targets)} trigger files.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
