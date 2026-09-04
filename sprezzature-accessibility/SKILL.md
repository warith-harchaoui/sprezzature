---
name: sprezzature-accessibility
description: >-
  Pre-commit static HTML accessibility lint for vanilla-JS + Tailwind output.
  Fifteen rules decidable from source: missing alt, unlabelled inputs,
  button-without-text, clickable div (onclick), missing dialog close, lang
  attribute, bad heading order, color-only state, motion-reduce guards,
  tight letter-spacing, and more, without a browser or runtime DOM. For
  solo developers and small teams who need a fast, deterministic,
  CI-friendly gate before shipping; NOT a replacement for axe-core / Pa11y /
  Lighthouse (runtime DOM audits catch what a static parser cannot). Color
  contrast lives in the companion ``sprezzature-colors`` skill, AI alt-text
  in ``sprezzature-vision``, AI captions in ``sprezzature-audio``. Trigger
  phrases: "a11y lint", "check this HTML for accessibility", "static a11y
  check", "WCAG-friendly lint", "a11y pre-commit", "missing alt", "unlabelled
  input", "WCAG compliance", "ARIA / keyboard check", "letter-spacing",
  "fix accessibility". Output is JSON / stdout / exit codes suitable for
  pre-commit and CI.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. The lint_a11y script needs
  Python 3.10+ stdlib only: no third-party deps, no browser, no network.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
---

> The deterministic tools below now ship as the standalone package [`sprezzature-accessibility`](https://github.com/warith-harchaoui/sprezzature-accessibility) (`pip install`), invoked as `sprezzature-accessibility …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-accessibility — static HTML a11y lint

## Audience and positioning

Solo developers and small teams who:

- Need a **pre-commit gate** that fails fast on a11y regressions in
  HTML source: no browser, no runtime DOM, no waiting for a CI
  container to spin up a headless Chromium.
- Want **stdlib-only Python** (3.10+) so the gate fits in any base
  container and adds zero install time.
- Don't ship without a designer or QA team, and want the most obvious
  static-decidable rules covered automatically before the diff lands.

This skill is **not** a substitute for runtime DOM testing. Pair it
with **axe-core** / **Pa11y** / **Lighthouse** for runtime checks
(dynamic ARIA states, focus traps after ``dialog.showModal()``,
color contrast after a runtime theme switch, name/role/value after
portal mounts), and with manual screen-reader passes for the things
only a human can verify (logical reading order, dynamic ARIA states
changing, screen-reader announcement of live regions).

## Two modes: make and audit

This skill is primarily **audit** but ships a small make-side
auto-fix mode for the rules whose violations have a one-line safe
repair:

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — repair the mechanically-fixable rules | `lint_a11y.py --fix` | Adds `lang="en"` to `<html>`, strips redundant `role="presentation"` / `aria-hidden="true"` from decorative `<img alt="">`, demotes `tabindex="N>0"` to `tabindex="0"`, strips `aria-hidden` from interactive elements, appends `motion-reduce:transform-none` to animated elements, strips `tracking-tight`/`tracking-tighter` from body text. Idempotent. Use `--dry-run` to preview. |
| **Make** — opt-in comfortable-reading CSS | `text_spacing_preset.py` | Emits a CSS block at the WCAG 1.4.12 Text Spacing minimums (line-height, paragraph spacing, letter/word spacing) for the same body-text tag set the linter checks, for pages that want to ship the fix as a reader-facing toggle rather than just removing the anti-pattern. |
| **Audit** — gate before ship | `lint_a11y.py` | 15 static rules over HTML (missing alt, unlabelled inputs, button-without-text, `div onclick`, missing dialog close, lang attr, bad heading order, color-only state, motion-reduce guards, tight letter-spacing on body text). Stdlib only, no browser. |

The unfixable rules (empty button, missing label, missing heading,
color-only state, missing dialog close) are *passed through* by the
auto-fix mode; those need a content decision the linter cannot make
for the user. `sprezzature-vision` covers the alt-text drafting side;
`sprezzature-ui` covers semantic HTML generation.

For runtime DOM audits (post-JS, dynamic ARIA, focus traps after async)
pair this skill with `axe-core` / `Pa11y` / `Lighthouse`. A green
static lint is not WCAG compliance; it catches the static-decidable
rules before the diff lands.

## What `lint_a11y.py` catches

Fifteen rules decidable from the HTML source, no JavaScript
execution required (canonical IDs used by ``--ignore`` and JSON
output in parentheses):

1. ``<img>`` without ``alt`` attribute (``img-missing-alt``).
2. ``alt=""`` decorative override paired with ``role="presentation"``
   or ``aria-hidden="true"`` (contradictory signals, ``img-redundant-aria``).
3. ``<a>`` without ``href`` (``a-missing-href``).
4. ``<a>`` with no accessible name (``a-empty``).
5. ``<button>`` with no accessible text content (no text node, no
   ``aria-label``, no labelled child icon; ``button-empty``).
6. ``<div onclick>`` / ``<span onclick>`` masquerading as a button
   (``div-onclick``).
7. ``<input>`` / ``<select>`` / ``<textarea>`` without a label or
   ``aria-label`` (``input-missing-label``).
8. ``<dialog>`` without a close mechanism (``dialog-missing-close``).
9. ``<html>`` missing the ``lang`` attribute (``html-missing-lang``).
10. Tab-order ``tabindex`` ≥ 1 anywhere (anti-pattern; use DOM order
    instead; ``tabindex-positive``).
11. ``aria-hidden="true"`` on a focusable interactive element
    (``aria-hidden-interactive``).
12. Skipped heading levels (e.g. ``<h2>`` → ``<h4>``) inside the same
    landmark (``heading-skip``).
13. Color-only state cues (no other affordance, such as text, icon, or
    border, carrying the same information; ``color-only-state``).
14. Missing ``prefers-reduced-motion`` guard on any animation block
    (``motion-no-reduce-guard``).
15. Negative letter-spacing (Tailwind ``tracking-tight``/``tracking-tighter``)
    on running body text (``body-text-tracking-tight``, WCAG 1.4.12).

Exit code is non-zero on any finding. Use ``--format json`` for CI
parsing, ``--format text`` for terminal review.

> "Passed the static gate" ≠ "WCAG-compliant". State this when
> reporting results; the rules above cover the *decidable* a11y
> regressions; everything dependent on runtime DOM still needs a
> browser-based audit.

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "a11y lint" / "check this HTML for accessibility" / "static a11y check" | `lint_a11y.py` | `sprezzature-accessibility-lint <file-or-dir>` (15 rules, exit 1 on any finding). Falls back to `python -m sprezzature_accessibility_scripts.lint_a11y` if the console script is not on `$PATH`. |
| "text spacing" / "letter-spacing" / "comfortable reading CSS" | `text_spacing_preset.py` | `sprezzature-accessibility-text-spacing <file-or-dir>` (emits the opt-in WCAG 1.4.12 CSS preset). Falls back to `python -m sprezzature_accessibility_scripts.text_spacing_preset`. |
| "contrast audit" / "WCAG ratio" / "colorblind preview" | (see `sprezzature-colors`) | `python -m sprezzature_colors_scripts.audit_contrast [--palette p.json] [--fix]` and `python -m sprezzature_colors_scripts.simulate_cvd <image>` (the `sprezzature-colors` package ships no console script, only these importable modules). |
| "alt text" / `<img>` with no `alt` / "describe this image" | (see `sprezzature-vision`) | `python sprezzature-vision/scripts/alt_from_ollama.py [--kind informative\|decorative\|functional\|text\|complex\|group] [--lang fr] [--in DOC] [--vocab-from DIR] <src>`. |
| "captions" / "transcribe video" / "transcribe audio" / "subtitle file" | (see `sprezzature-audio`) | `python -m sprezzature_audio_scripts.install_captions` then `sprezzature-audio-captions <audio-or-video> [--format vtt\|srt\|text] [--lang fr] [--vocab-from DIR] [--auto-project]`. |

## Tool composition

For a UI deliverable end-to-end. Commands below assume the standalone
packages are pip-installed (`pip install sprezzature-accessibility
sprezzature-colors sprezzature-vision sprezzature-audio`); `sprezzature-colors`
exposes no console script, so its two calls go through `python -m`:

```bash
sprezzature-accessibility-lint public/                                        # static a11y gate
python -m sprezzature_colors_scripts.audit_contrast --palette palette.json    # WCAG ratios
python -m sprezzature_colors_scripts.simulate_cvd screenshot.png --grid       # CVD pass
python sprezzature-vision/scripts/alt_from_ollama.py public/hero.jpg          # AI alt text
sprezzature-audio-captions public/podcast.mp4                                 # AI captions
```

Then pair with a runtime audit (axe-core / Pa11y / Lighthouse) before
shipping.

## When NOT to use this skill

- You need **runtime DOM-aware a11y testing** (React-mounted components,
  dynamic ARIA states, focus management after async state change) →
  use **axe-core** + Playwright.
- You need **a designer-grade palette / contrast audit** with
  OKLCH-neighbour fix hints: use the companion ``sprezzature-colors`` skill.
- You need **AI alt text** drafted from images: use the companion
  ``sprezzature-vision`` skill.
- You need **AI captions / transcripts** from audio / video: use the
  companion ``sprezzature-audio`` skill.

## References

- ``references/lint-a11y.md`` — Static a11y linter rule catalogue (15
  rules) and CI integration.

## Scripts

Shipped by the standalone [`sprezzature-accessibility`](https://github.com/warith-harchaoui/sprezzature-accessibility)
package (`pip install sprezzature-accessibility`), not by this monorepo:

| Script | Console entry point | Purpose |
|---|---|---|
| ``lint_a11y.py`` | ``sprezzature-accessibility-lint`` | 15-rule static a11y lint. Exit 1 on any finding. **Not** a substitute for runtime audit. |
| ``text_spacing_preset.py`` | ``sprezzature-accessibility-text-spacing`` | Emits the opt-in WCAG 1.4.12 Text Spacing CSS preset, the make-side counterpart to the ``body-text-tracking-tight`` rule. |
| ``_argparse.py`` | (internal helper, no entry point) | Argparse parser factory shared across the skill family (duplicated per-skill for autonomy). |

## Companion skills

| You also need… | Install |
|---|---|
| WCAG contrast audit, CVD simulation, curated palette, perceptual lighten / darken | ``sprezzature-colors`` |
| W3C alt text via local Ollama vision (``qwen3-vl:8b``) | ``sprezzature-vision`` |
| Local WebVTT / SRT captions via whisper.cpp | ``sprezzature-audio`` |
| Vanilla-JS + Tailwind UI generation | ``sprezzature-ui`` |
| Wrap a CLI in a GUI | ``sprezzature-cli-gui`` |
| Markdown → website + meta + favicons + indexes | ``sprezzature-publish`` |
