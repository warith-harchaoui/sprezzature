---
name: sprezzature-ux-laws
description: >-
  Apply the canonical Laws of UX (Jon Yablonski, lawsofux.com) to vanilla-JS +
  Tailwind work, both when making new UI ("design this screen using Hick /
  Fitts / Miller", "what does Peak-End say here", "is this onboarding fighting
  the Paradox of the Active User") AND when auditing existing HTML ("audit for
  Laws of UX", "is my nav too Hick-heavy", "check my form for Postel /
  Tesler", "too many choices / options", "cognitive load", "Doherty
  threshold", "reduce clutter"). Reference covers 30 laws with trigger /
  action / Tailwind hook. Static auditor scripts/audit_laws_of_ux.py flags the
  mechanically-detectable subset (Hick, Miller, Fitts, Jakob, Tesler,
  Aesthetic-Usability, Selective Attention, Doherty, Choice Overload) with
  severity and JSON output. Pairs with companion skills sprezzature-ui (generation),
  sprezzature-accessibility (a11y lint), sprezzature-publish (docs site), sprezzature-colors
  (contrast). Output is HTML-aware findings via JSON or stdout, exit codes for
  pre-commit / CI.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. The auditor needs
  Python 3.10+ stdlib only (html.parser, argparse, json). No network
  access required. Reference is plain Markdown with no exec deps.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
  source: https://lawsofux.com/
---

> The deterministic tools below now ship as the standalone package [`sprezzature-ux-laws`](https://github.com/warith-harchaoui/sprezzature-ux-laws) (`pip install`), invoked as `sprezzature-ux-laws …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-ux-laws — make and audit by the Laws of UX

## Audience and positioning

Solo developers and small teams who:

- Want a **shared vocabulary** for UI decisions ("we're trading Hick
  for Doherty here") without re-deriving cognitive science from
  scratch each time.
- Want a **pre-commit auditor** that fails fast when emitted HTML
  violates a mechanically-detectable law (an 11-link `<nav>`, an
  unchunked IBAN, a clickable `<div>` masquerading as a button).
- Need the rules without buying the book. The skill restates each
  law's trigger and action and points at the primary sources
  (Yablonski's lawsofux.com plus Nielsen Norman Group and the
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
| **Make** — auto-fix mechanically-fixable violations | `audit_laws_of_ux.py --fix` | Closes the audit↔make loop: every violation that can be repaired by a one-line text edit is fixed in place (Fitts adds `min-h-11`; Aesthetic-Usability adds `focus-visible:ring-2`; Miller chunks long digit runs with NBSP; Jakob rewrites `<div>` / `<span>` to `<button>`). Iterates until convergence; idempotent. |
| **Audit** — fail the build on detectable violations | `audit_laws_of_ux.py` | Pre-commit, pre-merge, CI. Static parser, no browser, no network. Findings come as `error` or `warning`; exit non-zero only when an `error` is found unless `--strict` is set. |

## Decision tree

| Trigger phrase | Mode | Run |
|---|---|---|
| "design / build / make this screen using Hick / Fitts / Miller / Jakob / Tesler / Peak-End" | make | Load `references/laws-of-ux.md`, jump to the relevant bucket, apply the **smallest concrete change** the law asks for. |
| "what does the Laws of UX say about this onboarding flow" | make | Load reference, walk the **Time** + **Memory** buckets. |
| "is this a dark pattern" | make | Stop here, hand to `sprezzature-ui/references/anti-patterns.md`. |
| "audit this page / component / dir for Laws of UX" | audit | `python -m sprezzature_ux_laws_scripts.audit_laws_of_ux <file-or-dir>` |
| "auto-fix the easy ones" / "make my UI pass the Laws of UX" | make | `python -m sprezzature_ux_laws_scripts.audit_laws_of_ux --fix <file-or-dir>`. Applies the four mechanical fixers (Fitts / Aesthetic-Usability / Miller / Jakob) in place. Add `--dry-run` to preview. |
| "fail the build on Hick / Jakob violations" | audit | `python -m sprezzature_ux_laws_scripts.audit_laws_of_ux --only hick,jakob --strict <dir>` |
| "JSON for CI" | audit | `python -m sprezzature_ux_laws_scripts.audit_laws_of_ux --json <dir>` |
| "false positive on Tesler / Miller" | audit | `python -m sprezzature_ux_laws_scripts.audit_laws_of_ux --ignore tesler,miller <dir>` |

## Implemented audit checks

Each check maps to one law in the canonical set. The trigger column
states the heuristic the static parser uses (not the law's full
definition, which lives in the reference). False-positive rate is
the auditor's best-effort qualitative estimate against the
sprezzature-ui starter components.

| Law | Severity | What the static parser flags | False positives to expect |
|---|---|---|---|
| Hick's Law | error | `<nav>` exposing > 7 top-level *logical* choices (radiogroups / tablists collapse to one) | Rich app shells with a documented "More" menu and a deliberate top-level surface area. |
| Choice Overload | warning | A `<div>`/`<section>` with `pricing`/`plans` + `grid`/`flex` in its class list and > 4 direct column children | A genuine four-tier B2B price table where each tier is concrete; mark with `--ignore choice-overload`. |
| Miller's Law | warning | A visible alphanumeric run ≥ 8 chars in body text | English words 8–12 chars are excluded; CSS class hashes in `class=""` attributes are stripped before scanning. |
| Jakob's Law | error | `<div>` / `<span>` with `onclick=` / `role="button"` / `cursor-pointer` and no real interactive child | Wrappers that contain a real `<button>` / `<a>` are exempt. |
| Fitts's Law | warning | Interactive element with no `min-h-11+` / `h-11+` / `size-11+` Tailwind class | Plain text links inside paragraphs (heuristically exempted). |
| Aesthetic-Usability | warning | Interactive element without `focus-visible:ring-*` or `focus:ring-*` | Type=hidden inputs are exempted. |
| Selective Attention | warning | `<span>` whose only signal is `text-red-*` / `text-green-*` and whose visible text is not a status word, with no icon child | Spans that contain a status word ("Failed", "OK", …) or an `<svg>`/`<img>` child are exempted. |
| Tesler's Law | warning | `HH:MM` time string with no timezone token (`UTC`, `+02:00`, `Europe/Paris`, `Z`, named TZ) within 40 chars | Durations like "Took 14:30"; silence with `--ignore tesler`. |
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
  (`sprezzature-figures/scripts/ralph_eyeball_loop.py page.html`), look at it, and ask
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

### Make — apply Hick + Fitts to a primary CTA

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
python -m sprezzature_ux_laws_scripts.audit_laws_of_ux \
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

- `references/laws-of-ux.md` — canonical Yablonski set (30 laws),
  trigger → action → Tailwind hook. Reads as both a make-time
  playbook and an audit-time refusal list. Load it on demand; not
  preloaded.

## Scripts

Shipped by the standalone [`sprezzature-ux-laws`](https://github.com/warith-harchaoui/sprezzature-ux-laws)
package (`pip install sprezzature-ux-laws`), not by this monorepo. It
registers no console script, so it runs as `python -m
sprezzature_ux_laws_scripts.audit_laws_of_ux`.

- `audit_laws_of_ux.py`: Python 3.10+ stdlib-only static
  auditor. Run `--help` for the full flag list (`--json`, `--strict`,
  `--only LAW1,LAW2`, `--ignore LAW1,LAW2`).

## Companion skills

| You also need… | Install |
|---|---|
| Vanilla-JS + Tailwind UI generation (house style, tokens, components) | `sprezzature-ui` |
| Static HTML a11y lint on the audited page | `sprezzature-accessibility` |
| WCAG contrast audit + CVD simulation | `sprezzature-colors` |
| Wrap a CLI in a GUI (argparse → web form) | `sprezzature-cli-gui` |
| Markdown → website + meta + favicons + indexes | `sprezzature-publish` |
| Data-viz / explainability / causality figures | `sprezzature-figures` |
| W3C alt text via local Ollama vision | `sprezzature-vision` |
| Local WebVTT / SRT captions via whisper.cpp | `sprezzature-audio` |

## Attribution

Concept names and the curated set are © Jon Yablonski under
CC-BY-NC-SA 4.0 (lawsofux.com). Restatements in
`references/laws-of-ux.md` are fair commentary; cite the source when
surfacing a law to a user.
