---
name: sprezzature-ux-laws
description: >-
  Apply the canonical Laws of UX (Jon YABLONSKI, lawsofux.com) to vanilla-JS +
  Tailwind work, both when designing a screen and when auditing one that
  exists. The reference covers 30 laws with trigger / action / Tailwind hook;
  the auditor (CLI, API, MCP audit_interface) flags the eight
  source-decidable ones (Hick, Choice Overload, Miller, Jakob, Fitts,
  Aesthetic-Usability, Selective Attention, Tesler); --fix repairs four.
  Doherty is vocabulary, not a check. Use it when somebody is complaining
  about how an interface FEELS, and on any interface you just authored. Trigger phrases: "audit for
  Laws of UX", "too many choices / options", "cognitive load", "is my nav too
  Hick-heavy", "check my form for Postel / Tesler", "Doherty threshold",
  "reduce clutter", "this page is overwhelming". Not this one when: the defect
  is mechanical accessibility (sprezzature-accessibility), contrast
  (sprezzature-colors), or the screen has yet to be built (sprezzature-ui).
  The exhaustive trigger catalogue is in `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. One `pip install
  sprezzature-ux-laws` (Python 3.10+) brings every surface; the auditor
  itself uses the standard library only (html.parser). No network access
  required. Reference is plain Markdown with no exec deps.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.4
  source: https://lawsofux.com/
---

> The deterministic tools below now ship as the standalone package [`sprezzature-ux-laws`](https://github.com/warith-harchaoui/sprezzature-ux-laws) (`pip install`), invoked as `sprezzature-ux-laws …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-ux-laws — make and audit by the Laws of UX (user experience, how using a product feels: quick and clear, or slow and confusing)

## Audience and positioning

Solo developers and small teams who:

- Want a **shared vocabulary** for UI (user interface, the screens, buttons and forms a person uses) decisions ("we're trading Hick
  for Doherty here") without re-deriving cognitive science from
  scratch each time.
- Want a **pre-commit auditor** that fails fast when emitted HTML
  violates a mechanically-detectable law (an 11-link `<nav>`, an
  unchunked IBAN (International Bank Account Number, the long account number printed on a bank statement), a clickable `<div>` masquerading as a button).
- Need the rules without buying the book. The skill restates each
  law's trigger and action and points at the primary sources
  (Jon YABLONSKI's lawsofux.com plus Nielsen Norman Group (NN/g, the usability research firm) and the
  Wikipedia critique of Postel's Law).

This skill is **not** a substitute for usability testing. The
Aesthetic-Usability Effect itself warns that beauty can mask real
bugs ([NN/g, 2024](https://www.nngroup.com/articles/aesthetic-usability-effect/));
pair this skill with axe-core / Pa11y / Lighthouse and behavioural
observation in real user sessions.

## Two modes: make and audit

The `sprezzature-*` repo is a toolkit for **making** UI and **auditing**
the result. This skill ships both halves of that loop for the Laws
of UX specifically:

| Mode | Tool | When to load |
|---|---|---|
| **Make** — pick the right law for a screen | `references/laws-of-ux.md` | At generation time. The reference is structured for in-conversation lookup: trigger → action → Tailwind hook. Load it once per design surface; pick ONE law to apply, not five. |
| **Make** — auto-fix mechanically-fixable violations | `sprezzature-ux-laws --fix` | Closes the audit↔make loop for four laws: Fitts adds `min-h-11`; Aesthetic-Usability adds `focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue`; Miller splits a long digit-bearing run of visible text into groups of four with non-breaking spaces (names such as `GMTED2010`, and the same run inside a tag or attribute, are never touched); Jakob rewrites the clickable `<div>` / `<span>` itself (never its wrapper) to `<button>` when it opens and closes on one line and holds no real control. Up to five passes; idempotent. A fixer only extends an existing `class` attribute. A file is written only when a fixer changed it, and keeps its line endings (a CRLF (carriage return + line feed, the Windows way of ending a line) file stays CRLF). Diff the result before committing. |
| **Audit** — fail the build on detectable violations | `sprezzature-ux-laws` / MCP (Model Context Protocol, the protocol through which AI agents call tools in English) `audit_interface` | Pre-commit, pre-merge, CI (continuous integration, the automatic checks a server runs on every change pushed to a repository). Static parser, no browser, no network. Findings come as `error`, `warning` or `info`; `--json` writes them as JSON (JavaScript Object Notation, a text format in which programs store data as named fields). Exit 1 when an `error` is found (any finding with `--strict`); exit 2 on an unknown law slug or a missing path. |

## Decision tree

| Trigger phrase | Mode | Run |
|---|---|---|
| "design / build / make this screen using Hick / Fitts / Miller / Jakob / Tesler / Peak-End" | make | Load `references/laws-of-ux.md`, jump to the relevant bucket, apply the **smallest concrete change** the law asks for. |
| "what does the Laws of UX say about this onboarding flow" | make | Load reference, walk the **Time** + **Memory** buckets. |
| "is this a dark pattern" | make | Stop here, hand to `sprezzature-ui/references/anti-patterns.md`. |
| "audit this page / component / dir for Laws of UX" | audit | `sprezzature-ux-laws <file-or-dir>` (or `sprezzature-ux-laws-audit`, same flags; a directory is searched recursively for `.html` and `.htm`, in any case); from an MCP host, `audit_interface` with the HTML |
| "which laws can you check" | audit | MCP `list_laws` (`GET /v1/laws`): the eight slugs to pass to `--only` or `laws` |
| "auto-fix the easy ones" / "make my UI pass the Laws of UX" | make | `sprezzature-ux-laws-audit --fix <file-or-dir>`. Applies the four mechanical fixers (Fitts / Aesthetic-Usability / Miller / Jakob) in place. Add `--dry-run` to preview. |
| "fail the build on Hick / Jakob violations" | audit | `sprezzature-ux-laws-audit --only hick,jakob --strict <dir>` |
| "JSON for CI" | audit | `sprezzature-ux-laws-audit --json <dir>` |
| "false positive on Tesler / Miller" | audit | `sprezzature-ux-laws-audit --ignore tesler,miller <dir>` |

## Implemented audit checks

Each check maps to one law in the canonical set. The trigger column
states the heuristic the static parser uses (not the law's full
definition, which lives in the reference). False-positive rate is
the auditor's best-effort qualitative estimate against the
sprezzature-ui starter components.

| Law | Severity | What the static parser flags | False positives to expect |
|---|---|---|---|
| Hick's Law | error | `<nav>` exposing > 7 top-level `<a>` / `<button>` choices on one screen, counted per breakpoint (phone or desktop, from the Tailwind display classes), with `<details>`, `<dialog>`, `<menu>` and `role` radiogroup / tablist / menubar / listbox / combobox each counting once | Rich app shells with a documented "More" menu and a deliberate top-level surface area. |
| Choice Overload | warning | A `<div>`/`<section>` with `pricing`/`plans` + `grid`/`flex` in its class list and > 4 direct `<article>` / `<div>` children | A genuine five-tier B2B (business-to-business, sold to companies rather than to individuals) price table where each tier is concrete; mark with `--ignore choice-overload`. |
| Miller's Law | warning | A visible run of ≥ 8 letters and digits containing at least one digit, outside `<script>` / `<style>` | Purely alphabetic words are excluded; tags and their attributes are stripped before scanning (on a tag split across lines, the `class`, `id`, `href`, `src` values); letters-then-digits names (`GMTED2010`, `LANDSAT8`) are skipped. |
| Jakob's Law | error | `<div>` / `<span>` with `onclick=` / `role="button"` / `cursor-pointer` and no real interactive child | Wrappers that contain a real `<button>` / `<a>` are exempt. |
| Fitts's Law | warning | Interactive element with no `min-h-11+` / `h-11+` / `size-11+` Tailwind class (or `full` / `screen` / `auto`) | An `<a>` without `flex` / `inline-flex` / `block` / `btn` / `button` / `bg-*` / `border-*` is treated as a text link and skipped. On a page without Tailwind utilities of at least two kinds (spacing, colour, a prefix…): one `info` for the document instead, and `--fix` writes no Tailwind there. |
| Aesthetic-Usability | warning | Interactive element without `focus-visible:ring-*` or `focus:ring-*` | Type=hidden inputs are exempted. Same Tailwind precondition and single `info` as Fitts. |
| Selective Attention | warning | `<span>` coloured `text-red-*` / `text-green-*` / `text-amber-*` / `text-yellow-*` / `text-orange-*` whose visible text holds no status word, with no icon child | Spans that contain a status word ("Failed", "OK", …) or an `<svg>`/`<img>` child are exempted. |
| Tesler's Law | warning | `HH:MM` time string with no timezone token (`UTC`, `+02:00`, `Europe/Paris`, `Z`, a named time zone) within 40 chars | Times in a duration context (`duration`, `elapsed`, `remaining`, `data-ra-*`, a range input, `<progress>`, `<audio>`, `<video>`) are skipped; other durations ("Took 14:30") still fire. |
| Doherty Threshold | — | Out of scope for static analysis. Use Lighthouse + a real device. | — |

## Visual laws need the Ralph Eyeball Loop

The static parser above is the fast first pass: it catches what is decidable
from source (a fake button, a missing focus ring, an over-long nav). But most of
the Laws of UX are about how the rendered interface *looks and feels*, which no
parser can see: visual hierarchy and emphasis (Von Restorff, aesthetic-usability),
real target size and spacing (Fitts), perceived density and grouping (Hick,
Miller, proximity), and whether the eye lands where you intended (selective
attention). Judge those by rendering and looking, via the
[Ralph Eyeball Loop](../sprezzature-figures/references/ralph-eyeball-loop.md):

- **Make.** After emitting a screen, render it to a PNG
  (`python -m sprezzature_figures_scripts.ralph_eyeball_loop page.html`), look at it, and ask
  the laws out loud: is the primary action the most prominent thing? are tap
  targets comfortable? is any group past ~7 items? Fix the source and re-render
  until it holds.
- **Audit.** Do the same to someone else's page: the static report lists the
  decidable violations; the rendered look is where you assess the visual laws
  the parser marks "—" or can only guess at. Report both, and say which came
  from the parser and which from the eyeball pass.

So the two halves compose: the deterministic parser for the source-decidable
laws, the Ralph Eyeball Loop for the visual ones.

## Examples

### Make — apply Hick + Fitts to a primary CTA (call to action, the one thing a page asks its reader to do: book a call, buy, install)

User: "Design a hero CTA for a settings page that respects Hick + Fitts."

1. Load `references/laws-of-ux.md`, *Decision* and *Aesthetics*
   buckets.
2. Hick says one obvious choice; Fitts says 44 px min hit area.
3. Emit:

```html
<button class="inline-flex min-h-11 items-center justify-center gap-2
               rounded-full bg-brand-blue px-5 py-3 text-[17px]
               font-semibold text-white hover:opacity-90
               active:scale-[0.97]
               focus:outline-none focus-visible:ring-2
               focus-visible:ring-brand-blue
               focus-visible:ring-offset-2
               focus-visible:ring-offset-surface-primary
               motion-reduce:active:scale-100">
  Save changes
</button>
```

### Audit — pre-commit on the components dir

```bash
sprezzature-ux-laws-audit \
  --strict --json \
  sprezzature-ui/assets/components/ > .audit.json
test -s .audit.json && jq length .audit.json
```

CI fails on any finding when `--strict`. Drop `--strict` to let
warnings pass and only fail on real errors (Hick, Jakob).

## Tool composition

- When generating new HTML: invoke this skill's reference at design
  time; rerun the auditor on the emitted file as a self-check before
  returning code.
- When auditing existing HTML emitted by `sprezzature-ui`: run the
  auditor first, then load the reference for any flagged law to
  draft a fix.
- When the audit reports Selective-Attention warnings, also run the
  `sprezzature-accessibility` lint; the a11y skill catches the same family of
  bugs from a different angle (color-only state, missing alt,
  unlabelled inputs).

## References

- `references/laws-of-ux.md` — canonical YABLONSKI set (30 laws),
  trigger → action → Tailwind hook. Reads as both a make-time
  playbook and an audit-time refusal list. Load it on demand; not
  preloaded.

## Surfaces

Shipped by the standalone [`sprezzature-ux-laws`](https://github.com/warith-harchaoui/sprezzature-ux-laws)
package, not by this monorepo. One `pip install sprezzature-ux-laws` brings
all of them:

| Surface | Name | Notes |
|---|---|---|
| Library | `import sprezzature_ux_laws` | `audit_html`, `audit_file`, `fix_file`, `LAWS`, `LAW_REGISTRY`, `Finding` |
| CLI (command-line interface, a program you run by typing a command in a terminal) | `sprezzature-ux-laws` (click), `sprezzature-ux-laws-audit` (per-tool script) | Same handler and flags: `--json`, `--strict`, `--only`, `--ignore`, `--fix`, `--dry-run` |
| HTTP (HyperText Transfer Protocol, the language a browser and a server speak each time a page loads) API (application programming interface, the requests one program can send another, such as audit this page) | `uvicorn sprezzature_ux_laws.api:app` | `GET /health`, `GET /v1/laws`, `POST /v1/audit` (400 on an unknown law); Docker and compose in the repository |
| MCP | `sprezzature-ux-laws-mcp` (endpoint `/mcp`) | Tools = `operation_id`s: `health`, `list_laws`, `audit_interface`. No tool writes files: `--fix` is CLI and library only |
| Skill | this file | Routing rules in the package's `TRIGGERS.md` |

## Companion skills

| You also need… | Install |
|---|---|
| Vanilla-JS + Tailwind UI generation (house style, tokens, components) | `sprezzature-ui` |
| Static HTML a11y lint on the audited page | `sprezzature-accessibility` |
| WCAG (Web Content Accessibility Guidelines, the international rules a web page must follow to be usable by people with disabilities) contrast audit + CVD (colour-vision deficiency, the medical name for colour blindness: red and green that look alike, for instance) simulation | `sprezzature-colors` |
| Wrap a CLI in a GUI (graphical user interface, windows, buttons and forms you click instead of typing commands: here a web form built from argparse, Click or Typer) | `sprezzature-cli-gui` |
| Markdown → website + meta + favicons + indexes | `sprezzature-publish` |
| Data-viz / explainability / causality figures | `sprezzature-figures` |
| W3C (World Wide Web Consortium, the body that writes the web's standards) alt text via local Ollama vision | `sprezzature-accessibility` |
| Local WebVTT / SRT (SubRip, the most common subtitle file: numbered captions, each with a start and end time) captions via whisper.cpp | `sprezzature-audio` |

## Attribution

Concept names and the curated set are © Jon YABLONSKI under
the Creative Commons Attribution-NonCommercial-ShareAlike licence (CC-BY-NC-SA 4.0: share and adapt with credit, never for sale, under the same terms; lawsofux.com). Restatements in
`references/laws-of-ux.md` are fair commentary; cite the source when
surfacing a law to a user.
