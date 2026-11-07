---
name: sprezzature-accessibility
description: >-
  Static HTML accessibility lint **and** the alt text it tells you is
  missing. Twenty rules decidable from source without a browser: missing
  alt, unlabelled inputs, button-without-text, clickable div, missing
  dialog close, lang attribute, bad heading order, colour-only state,
  motion-reduce guards, video and audio captions; JSON / exit codes for
  CI. Then `--fix-alt` drafts the alt with a local vision
  model, using the image and the surrounding text of that same page. Use
  it whenever you are holding HTML, above all HTML you just wrote. Trigger
  phrases: "a11y lint", "check this HTML for accessibility", "WCAG
  compliance", "missing alt", "write alt text", "describe this image",
  "unlabelled input", "fix accessibility". Not this one when: the question
  is contrast or colour-blindness (sprezzature-colors), captions for speech
  (sprezzature-audio), or how the interface feels (sprezzature-ux-laws).
  NOT a replacement for axe-core / Pa11y / Lighthouse. The exhaustive
  trigger catalogue is in `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10 to 3.13, one
  `pip install sprezzature-accessibility`. The lint imports only the
  standard library: no browser, no network. Drafting alt text also needs a
  local Ollama with qwen3-vl:8b (`sprezzature-accessibility-install-alt`).
metadata:
  author: Warith HARCHAOUI
  version: 1.8.2
---

> The tools below ship as the standalone package
> [`sprezzature-accessibility`](https://github.com/warith-harchaoui/sprezzature-accessibility)
> (`pip install sprezzature-accessibility`, everything in one install),
> invoked as `sprezzature-accessibility <tool>` or `make-a11y <tool>` (one
> click command, two names) over four tools: `lint`, `text-spacing`, `alt`,
> `install-alt`. Each is also its own command
> (`sprezzature-accessibility-lint` and so on), which is what a script should
> call. This SKILL.md is the agent contract; the code lives in that package.

# sprezzature-accessibility: static HTML a11y lint and alt-text drafting

## Audience and positioning

Solo developers and small teams who:

- Need a **pre-commit gate** that fails fast on accessibility regressions in
  HTML source: no browser, no runtime DOM (Document Object Model), no waiting
  for a CI container to start a headless Chromium.
- Want the gate light: the lint imports only the Python standard library, and
  a hook can install it as two packages
  (`pip install --no-deps sprezzature-accessibility`, then `pip install click`).
- Have no designer or QA team, and want the static-decidable rules covered
  automatically before the diff lands, and the missing alt text drafted.

This skill is **not** a substitute for runtime DOM testing. Pair it with
**axe-core** / **Pa11y** / **Lighthouse** for runtime checks (dynamic ARIA
states, focus traps after ``dialog.showModal()``, colour contrast after a
runtime theme switch, name/role/value after portal mounts), and with manual
screen-reader passes for what only a person can verify (logical reading
order, announcement of live regions).

## Two modes: make and audit

| Mode | Tool | Purpose |
|---|---|---|
| **Make**: repair the mechanically fixable rules | `sprezzature-accessibility-lint --fix` | Six fixers: adds `lang` to `<html>` (the language is detected from the page text; left unfixed when it cannot be), strips redundant `role="presentation"` / `aria-hidden="true"` from decorative `<img alt="">`, demotes `tabindex="N>0"` to `tabindex="0"`, strips `aria-hidden` from focusable interactive elements, appends `motion-reduce:transform-none` to animated elements, strips `tracking-tight`/`tracking-tighter` from body text. Idempotent. `--dry-run` previews and always exits 0. |
| **Make**: draft the alt the audit says is missing | `sprezzature-accessibility-lint --fix-alt` | For every `<img>` with no `alt`, drafts one with the local vision model, from the image **and the text around it in that same page**, plus the proper nouns the page uses. Language: `--alt-lang`, else the page's `<html lang>`, else detection on the page text, else the environment locale. Remote or missing images are left alone and reported. Separate from `--fix` on purpose: that one is mechanical, offline and idempotent; this calls a model and writes prose a person should read. |
| **Make**: draft alt for one image | `sprezzature-accessibility-alt` (alias `make-alt`) | Same engine, one image at a time, with `--kind` (the six W3C purposes), `--context`, `--lang`, `--longdesc`, `--in DOC`, `--vocab`, `--vocab-from`, `--auto-project`, `--resize`, `--no-cache`. Alt text on stdout, capped at 150 characters. |
| **Make**: opt-in comfortable-reading CSS | `sprezzature-accessibility-text-spacing` | Emits a CSS block at the WCAG 1.4.12 Text Spacing minimums (line height 1.5, letter spacing 0.12em, word spacing 0.16em, paragraph spacing 2em) for the body-text tags the linter checks. `--attr`, `--value`, `--out` and one flag per value. |
| **Audit**: gate before ship | `sprezzature-accessibility-lint` | Twenty static rules over HTML, listed below. Exit 1 on any finding, 0 on a clean run; `--format json` for CI; `--ignore` takes rule ids. |

The fourteen rules without a fixer are *passed through* by `--fix`: they need
a content decision nothing here can make for the user. `img-missing-alt` is
the one of them that `--fix-alt` repairs, because the drafting half can look
at the image and at the page around it. `sprezzature-ui` covers semantic HTML
generation.

A green static lint is not WCAG compliance; it catches the
static-decidable rules before the diff lands.

## What the lint catches

Twenty rules decidable from the HTML source, no JavaScript execution
required (the ids used by ``--ignore`` and the JSON output in parentheses):

1. ``<img>`` without ``alt`` attribute (``img-missing-alt``).
2. ``alt=""`` paired with ``role="presentation"`` or ``aria-hidden="true"``,
   redundant (``img-redundant-aria``, warning).
3. ``<a>`` without ``href`` (``a-missing-href``).
4. ``<a>`` with no accessible name (``a-empty``).
5. ``<button>`` with no accessible name and no ``<svg>`` / ``<img>`` child
   (``button-empty``).
6. ``<div onclick>`` / ``<span onclick>`` without ``role="button"`` and
   ``tabindex`` (``div-onclick``).
7. ``<input>`` without a ``<label>`` (wrapping or ``for=``) and without
   ``aria-label``; hidden, submit, button, reset and image inputs are exempt
   (``input-missing-label``).
8. ``<dialog>`` without a close mechanism (``dialog-missing-close``).
9. ``<html>`` missing the ``lang`` attribute (``html-missing-lang``).
10. ``tabindex`` ≥ 1 anywhere (``tabindex-positive``).
11. ``aria-hidden="true"`` on an interactive element a keyboard can still
    reach (``aria-hidden-interactive``).
12. Heading levels that skip downward, e.g. ``<h2>`` → ``<h4>``
    (``heading-skip``).
13. A Tailwind red / green token with no icon or text carrying the same
    information (``color-only-state``, warning).
14. ``animate-spin`` / ``-ping`` / ``-pulse`` / ``-bounce``,
    ``transition-transform`` or ``transition-all`` without a
    ``motion-reduce:`` peer (``motion-no-reduce-guard``, warning).
15. Negative letter-spacing (``tracking-tight`` / ``tracking-tighter``) on
    running body text (``body-text-tracking-tight``, warning, WCAG 1.4.12).
16. ``<video>`` with sound and no captions or subtitles track
    (``video-missing-captions``, WCAG 1.2.2).
17. ``<audio>`` with no track and no accessible name pointing at a
    transcript (``audio-missing-transcript``, WCAG 1.2.1).
18. ``<track>`` without ``srclang`` (``track-missing-srclang``, warning).
19. ``<video>`` / ``<audio>`` without ``controls`` (``media-missing-controls``,
    WCAG 2.1.1).
20. ``autoplay`` without ``muted`` (``media-autoplay-sound``, WCAG 1.4.2).

A video that is ``muted`` and has no ``controls`` counts as decorative and is
exempt from 16 and 19. The severities are the ones the HTTP API reports; the
command line exits 1 on any finding, warnings included.

> "Passed the static gate" ≠ "WCAG-compliant". State this when reporting
> results; everything dependent on the runtime DOM still needs a
> browser-based audit.

## Decision tree

| Trigger | Run |
|---|---|
| "a11y lint" / "check this HTML for accessibility" / "static a11y check" | `sprezzature-accessibility-lint <file-or-dir>` (twenty rules, exit 1 on any finding). |
| "fix accessibility" | `sprezzature-accessibility-lint --fix <file-or-dir>`, then lint again; report what remains. |
| "missing alt" on a page / "img has no alt" | `sprezzature-accessibility-lint --fix-alt <file-or-dir>`; tell the user the alt texts are drafts to review. |
| "alt text" / "describe this image" for one image | `sprezzature-accessibility-alt [--kind informative\|decorative\|functional\|text\|complex\|group] [--lang fr] [--in DOC] [--vocab-from DIR] <src>`. |
| "text spacing" / "letter-spacing" / "comfortable reading CSS" | `sprezzature-accessibility-text-spacing [--out reading.css]`. |
| The drafter cannot reach a model | `sprezzature-accessibility-install-alt` (installs Ollama, starts it, pulls `qwen3-vl:8b`). |
| "contrast audit" / "WCAG ratio" / "colorblind preview" | Not this skill: `sprezzature-colors` (`sprezzature-colors-contrast`, `sprezzature-colors-cvd`). |
| "captions" / "transcribe video" / "subtitle file" | Not this skill: `sprezzature-audio` (`sprezzature-audio-install`, then `sprezzature-audio-captions`). |

## The five surfaces

| Surface | Entry point |
|---|---|
| Library | `from sprezzature_accessibility import lint_file, fix_file, describe, describe_long, KINDS` |
| Command line | `sprezzature-accessibility` / `make-a11y` and the per-tool commands above; `sprezzature-accessibility tools` says which tools can run here |
| HTTP API (FastAPI) | `uvicorn sprezzature_accessibility.api:app`, or `docker compose up -d` (`--profile alt` adds an Ollama container) |
| MCP server | `sprezzature-accessibility-mcp [--host H] [--port P]`, endpoint at `/mcp` |
| Skill | this file |

The MCP tools are the HTTP routes, named by their `operation_id`:

| MCP tool | Route | Use |
|---|---|---|
| `lint_html` | `POST /v1/lint` | Lint a string of HTML; findings with line, rule, severity, plus error and warning counts. |
| `list_rules` | `GET /v1/rules` | Every rule id and its severity. Check ids here before passing `ignore`: an unknown id is silently ignored. |
| `list_kinds` | `GET /v1/kinds` | The six image purposes, each with what it is for. |
| `draft_alt_text` | `POST /v1/alt` | Draft alt text (and a long description with `long: true`) for one image. 502 when the model is unreachable. |
| `health` | `GET /health` | Liveness; use only to diagnose a connection. |

`--fix`, `--fix-alt`, the text-spacing CSS and the model install are
command-line only: they write to a project or a machine.

## W3C image-purpose mapping

| Purpose | What it is | What this skill emits |
|---|---|---|
| **informative** | Conveys content (photos, illustrations carrying meaning) | Short description biased by the surrounding text. |
| **decorative** | Pure ornament, no information value | ``alt=""``: no model call, nothing printed. |
| **functional** | Image acts as a control or link | Describes the *action or destination*, not the picture. |
| **text** | Image of text | Verbatim transcription of the text only. |
| **complex** | Charts, diagrams, infographics | Short alt, plus a long Markdown description with ``--longdesc`` (written to ``<image>.longdesc.md``) for a ``<figcaption>`` or ``aria-describedby`` target. |
| **group** | Multiple images conveying one idea | One unified description across the set. |

When the caller does not pass ``--kind``, the command uses ``informative``.
`--fix-alt` drafts every image as ``informative``; a person decides which
ones are really decorative.

## Model

The one model is **``qwen3-vl:8b``**, a multimodal model served through
Ollama, in the public registry so ``ollama pull`` works on any machine. It is
**not selectable** on the command line: there is no ``--model`` flag.
``OLLAMA_MODEL`` is honoured only as a test seam. The call goes through
``best-engine-ai-helper``. The endpoint defaults to
``http://localhost:11434`` and can be overridden with ``OLLAMA_URL``.

## Caching

Drafts are cached in a ``wallet-helper`` ledger under
``~/.cache/sprezzature-skill/alt/`` by default. The key covers the image bytes
sent, the purpose, the output language, the context and the model tag, so
changing any of those produces a fresh draft. Two processes drafting the same
image share one model call. Override the cache root with
``SPREZZATURE_CACHE_DIR``; bypass it for one call with ``--no-cache`` or
everywhere with ``SPREZZATURE_NO_CACHE=1``.

## When NOT to use this skill

- You need **runtime DOM-aware testing** (React-mounted components, dynamic
  ARIA states, focus management after async state change): use **axe-core**
  with Playwright.
- You need **a contrast audit or a colour-vision simulation**: use the
  companion ``sprezzature-colors`` skill.
- You need **captions or transcripts** from audio or video: use the companion
  ``sprezzature-audio`` skill. This skill only checks that a caption track is
  declared.
- You need to judge **how an interface feels**: ``sprezzature-ux-laws``.

## References

- ``references/lint-a11y.md``: the static linter's rule catalogue and CI
  integration.
- ``references/triggers.md``: the exhaustive trigger catalogue.

## Commands

Shipped by the standalone
[`sprezzature-accessibility`](https://github.com/warith-harchaoui/sprezzature-accessibility)
package, not by this monorepo:

| Console entry point | Purpose |
|---|---|
| ``sprezzature-accessibility`` / ``make-a11y`` | Front door over the four tools, plus ``tools``. |
| ``sprezzature-accessibility-lint`` | Twenty-rule static lint, ``--fix``, ``--fix-alt``. Exit 1 on any finding. **Not** a substitute for a runtime audit. |
| ``sprezzature-accessibility-text-spacing`` | The opt-in WCAG 1.4.12 Text Spacing CSS, the make-side counterpart to ``body-text-tracking-tight``. |
| ``sprezzature-accessibility-alt`` / ``make-alt`` | Alt text for one image. |
| ``sprezzature-accessibility-install-alt`` | Installs Ollama, starts it, pulls ``qwen3-vl:8b``. |
| ``sprezzature-accessibility-mcp`` | The MCP server over the HTTP API. |

## Companion skills

| You also need… | Install |
|---|---|
| WCAG contrast audit, CVD simulation, curated palette, perceptual lighten / darken | ``sprezzature-colors`` |
| Local WebVTT / SRT captions via whisper.cpp | ``sprezzature-audio`` |
| Vanilla-JS + Tailwind UI generation | ``sprezzature-ui`` |
| Wrap a CLI in a GUI | ``sprezzature-cli-gui`` |
| Markdown → website + meta + favicons + indexes | ``sprezzature-publish`` |
| Laws of UX audit | ``sprezzature-ux-laws`` |
