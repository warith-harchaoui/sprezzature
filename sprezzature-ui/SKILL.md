---
name: sprezzature-ui
description: >-
  Generate vanilla JS + Tailwind CSS UI code: components, pages, forms,
  dialogs, dashboards, for teams shipping internal tools without a designer.
  Semantic HTML + Tailwind utilities + vanilla ES modules, with dark-mode
  peers, focus rings and reduced-motion guards; default typography is the
  three-Roboto rule (sans + serif + mono). Use it whenever you are holding a
  screen to build. Trigger phrases: "build a UI", "create a component",
  "design a page", "make a form / modal / button / nav", "scaffold a landing",
  "build a web app", "audit this UI", "dashboard / data table", "settings
  page", "i18n to YAML", "audit i18n". Not this one when: the thing to wrap is
  a command-line tool (sprezzature-cli-gui); the source is Markdown that must
  become a site (sprezzature-publish); or the HTML exists already and the
  question is whether it is accessible (sprezzature-accessibility), how it
  feels (sprezzature-ux-laws) or whether a colour passes (sprezzature-colors).
  The exhaustive trigger catalogue is in `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. No Python runtime required to use
  the skill itself (output is HTML + CSS + vanilla JS). The two i18n tools
  ship as the `sprezzature-ui` package (`pip install sprezzature-ui`, Python
  3.10+); the audit itself imports only the standard library. Network access
  not required.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.4
---

# sprezzature-ui — vanilla JS (JavaScript, the programming language web browsers run) + Tailwind UI (user interface, the screens, buttons and forms a person uses) generation

> The two deterministic tools below ship as the standalone package [`sprezzature-ui`](https://github.com/warith-harchaoui/sprezzature-ui) (`pip install sprezzature-ui`, one line, no extras), invoked as `sprezzature-ui-i18n-audit` and `sprezzature-ui-i18n-make`, or through the click front door under either name, `make-ui <tool>` or `sprezzature-ui <tool>` (`sprezzature-ui tools` lists them). The audit is also served over HTTP (`POST /v1/i18n-audit`, plus `GET /health`, from `sprezzature_ui.api:app` or the package's Docker image) and over MCP (`sprezzature-ui-mcp`, endpoint `/mcp`, tools `audit_i18n` and `health`). The make tool writes files, so it has no route and no MCP tool. The generation half is this file: writing an interface is the model's work, and no command or route can carry it. The `scripts/` folder has moved out. The pre-ship content gate stayed in the monorepo as `validate_content.py`, beside the other repository-level validators: it validates a skill folder *here* rather than anything in a user's project.

## Audience

Solo developers and small teams (≤ 5 people) shipping **internal tools**: dev dashboards, admin panels, ML (machine learning, software that learns from examples instead of hand-written rules) / data-science demo apps, settings screens, prototypes, docs landing pages. You don't have a designer on the team and don't want to fight a framework. You want output that looks deliberate, ships immediately, and survives a year without React-version churn.

This skill is **not** the right pick for:
- Consumer-app brand work that needs a custom visual identity.
- Marketing landing pages where a tool like Webflow or Framer is faster.
- Apps where the team has chosen React / Vue / Svelte; use shadcn / Headless UI instead.

## When to use this skill

Trigger phrases:

- A new component (button, card, modal, form, nav, tab bar, sheet, alert, popover, …).
- A new page, landing surface, or admin screen.
- A redesign or ergonomic audit of an existing piece of UI.
- A design system token set or starter template.
- A dashboard, a BI (business intelligence, the charts a company reads to steer itself) screen, a KPI (key performance indicator, one number a team watches, such as weekly sign-ups) summary, or a dataviz tile.
- A migration **away** from a framework toward vanilla JS.

For other work, use the companion skills:

| Task | Skill |
|---|---|
| Wrap an existing CLI (command-line interface, a program you run by typing a command in a terminal) in a web GUI (graphical user interface, windows, buttons and forms you click instead of typing commands) | `sprezzature-cli-gui` |
| Turn a folder of Markdown into a website + meta tags + favicons + site indexes | `sprezzature-publish` |
| Static HTML a11y lint | `sprezzature-accessibility` |
| WCAG (Web Content Accessibility Guidelines, the international rules a web page must follow to be usable by people with disabilities) contrast audit, CVD (colour-vision deficiency, the medical name for colour blindness: red and green that look alike, for instance) simulation, curated palette | `sprezzature-colors` |
| W3C (World Wide Web Consortium, the body that writes the web's standards) alt text via local Ollama vision | `sprezzature-accessibility` |
| WebVTT / SRT (SubRip, the most common subtitle file: numbered captions, each with a start and end time) captions via local whisper.cpp | `sprezzature-audio` |
| Apply / audit the canonical Laws of UX (Hick, Fitts, Miller, Jakob, Peak-End, …) on emitted HTML | `sprezzature-ux-laws` |
| Screenshot a rendered page, look at it, and refine the markup (the Ralph Eyeball Loop) | `sprezzature-figures` (`sprezzature-figures/references/ralph-eyeball-loop.md`) |

The companion skills assume the same stack rules below.

## Two modes: make and audit

This skill ships both halves of the sprezzature-* loop:

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — generate UI | `references/` + `assets/components/*.html` + `assets/starter-page.html` + `assets/fonts/` + `sprezzature-ui-i18n-make` | Generation playbook: token map, decision tree below, copy-and-adapt component shapes, three-Roboto webfonts. `sprezzature-ui-i18n-make` scaffolds + compiles `locales/i18n.yaml` (GUI strings **and** prompts) and emits two loaders: a vanilla-JS one for the browser and `i18n_prompts.py` for Python. |
| **Audit** — gate before ship | `sprezzature-ui-i18n-audit` + `references/checklist.md` + `references/anti-patterns.md` + `references/ergonomics-criteria.md` | Pre-ship quality gate; eight-criteria ergonomic review; anti-pattern refusal list. `sprezzature-ui-i18n-audit` flags GUI translations embedded in JS/HTML (`I18N001`) and LLM (large language model, the kind of AI behind chatbots such as ChatGPT or Claude) prompts inlined in Python (`I18N002`); they belong in `locales/i18n.yaml`. |

Pair with `sprezzature-ux-laws` for canonical-law audits and `sprezzature-colors`
for contrast / CVD audits on the emitted output.

### i18n — one `locales/i18n.yaml` for GUI *and* prompts

Translatable strings (GUI labels and LLM prompts) share one concern
(language), so they share one per-project catalog: **`locales/i18n.yaml`**
(`gui:` and `prompts:` namespaces, each `message.id → { en: …, fr: … }`).
Never hardcode a UI string in JavaScript, never inline a prompt in Python.

```bash
# make: scaffold, compile to locales/i18n.json, emit i18n.js + i18n_prompts.py
sprezzature-ui-i18n-make --dir .
# audit: flag any string/prompt living in code instead of the catalog
sprezzature-ui-i18n-audit src/          # I18N001 (JS dict) / I18N002 (py prompt)
# extract: move what it found into the catalog, and say what to call instead
sprezzature-ui-i18n-audit --fix src/
```

What the audit sees, and nothing more:

- **`I18N001`** (`.js`, `.mjs`, `.cjs`, `.jsx`, `.ts`, `.tsx`, `.html`, `.htm`): a line declaring a table under a telltale name (`const i18n = {`, `translations`, `messages`, `locales`, `strings`, `dictionary`, `lang`, …), or an object literal with two or more locale keys (`{ en: …, fr: … }`).
- **`I18N002`** (`.py`): a module-level or class-level constant whose name contains `PROMPT` or `INSTRUCTION`, assigned a string literal or an f-string. A prompt stored under another name is not seen.

Exit 1 on any finding, exit 2 on a path that does not exist, `--json` for machine output. `--fix` writes the catalogue (`--catalog PATH` to change it), prints the call to paste, never rewrites the call site, and still exits 1. `sprezzature-ui-i18n-make` runs four steps by default (`--init`, `--compile`, `--emit-loader`, `--emit-python` run one each, `--dir` sets the project root), and the compile step refuses a prompt with no `validated:` locale. Report findings as evidence: "0 findings" means neither shape was found, not that the interface is ready.

**A counting message maps a locale to CLDR (Common Locale Data Repository, the Unicode tables that say, for instance, that Polish has three plural forms) plural categories**, not to a
string, and the runtime picks one with `Intl.PluralRules` — so French gets its
own boundaries (`0` is `one` there and `other` in English) and Arabic its six
forms. `{name}` placeholders are filled from the params. Never `if (n === 1)`;
see `sprezzature-publish/references/i18n.md`.

```yaml
results.count:
  en: {one: "{count} result",   other: "{count} results"}
  fr: {one: "{count} résultat", other: "{count} résultats"}
```

**A prompt is not a label**, so every `prompts:` entry declares the one locale
it was engineered and tested in:

```yaml
summarize.system:
  validated: en
  en: "Summarise the input in three bullet points."
  fr: "Résumez l'entrée en trois puces."
```

A locale with no entry resolves to the **validated** text — never to the first
declared locale, and never to the message id, which as a prompt would hand the
model the string `summarize.system`. A locale that *has* an entry gets it, and
the caller is told it is not the validated one. Nothing is translated at call
time: a machine translation of a prompt is a behavioural change nobody
measured. `sprezzature-ui`'s `tests/eval/test_prompt_locale_eval.py` measures
it — the French prompt above answered *in English* on two of three inputs,
three bullets and no error, which is the failure the rule exists to prevent.

In the browser: `import { initI18n, t } from "./locales/i18n.js"; await
initI18n(); el.textContent = t("results.count", {count: n});`. In Python:
`from locales.i18n_prompts import prompt; p = prompt("summarize.system",
locale)` — check `p.validated_locale_used` before you trust it.

## Hard rules

1. **No framework imports.** Output never contains `react`, `vue`, `svelte`, `solid-js`, `next`, `nuxt`, `angular`. If asked, refuse and offer the vanilla equivalent.
2. **Tailwind utility classes only**, never inline `style="…"`. The single allowed exception is a one-off CSS (Cascading Style Sheets, the language that sets a web page's colours, fonts and layout) custom property whose value references an existing token (e.g. `style="--accent: var(--brand-blue)"`). **Never** put a raw hex literal in markup, even inside `style="--accent: #007AFF"`. If a new accent is needed, add the token to `tailwind.config.js` (`theme.extend.colors.brand`) and reference it via `var(--brand-…)` or a Tailwind class. This keeps rule 7 (no raw hex) and rule 2 in lockstep.
3. **The three-Roboto rule — for generation, not for audits.** **When generating fresh UI / site output and no typeface has been specified by the user**, ship exactly three downloaded webfonts, all from the Roboto super-family: **Roboto** for sans, **Roboto Serif** for serif, **Roboto Mono** for code / monospace. No other downloaded family is allowed by default: not Inter, not Montserrat, not IBM Plex, not JetBrains Mono. Use Roboto for body / UI text by default; lift Roboto Serif when a surface wants editorial weight (longform reading, quote pulls, prose-heavy landings); use Roboto Mono for `<code>`, `<pre>`, kbd / samp, terminal panels. Self-host always (no Google Fonts CDN (content-delivery network, servers around the world that hand each reader a copy of a file from nearby), no jsDelivr GitHub proxy in production builds); system-font fallback stacks (`ui-monospace`, `system-ui`, `serif`, `sans-serif`) are fine and expected. **The rule does NOT apply when:** (a) **auditing an existing site / UI**: respect the existing fonts; don't propose a font swap unless the user specifically asks about typography; (b) **the user names a typeface** ("use Inter", "we ship IBM Plex", "stick to system fonts"), use what they ask for; (c) **the user asks for a fourth family explicitly for brand reasons**: carry it out and record the choice in the project README so a future maintainer knows why.
4. **Semantic HTML first.** `<button>`, `<a href>`, `<label for>`, `<dialog>`, `<form>`. ARIA (Accessible Rich Internet Applications, HTML attributes that tell a screen reader what an element is, such as role="dialog") only when no semantic element fits.
5. **Both color schemes.** Every styled element gets a `dark:` peer.
6. **Accessibility is shipping-required.** See `references/ui-guidelines/foundations/accessibility.md`.
7. **No raw hex** in markup: use semantic Tailwind tokens (`bg-brand-blue`, `text-label-primary`). **Curated default — user colors win** (mirror of rule 3, but for palette): when generating fresh output and no palette has been specified, use the 8 saturated brand hues from `sprezzature-colors/references/palette.csv` (regenerable with `sprezzature-colors-palette-to-tailwind`). **The default does NOT apply when:** (a) **auditing an existing UI**: respect the project's tokens; do not propose a CSV (comma-separated values, a table saved as plain text: here the curated palette file) swap; (b) **the user names colors** ("our brand is #8B5CF6", "use Material's primary"), use those; (c) **the project already has a `tailwind.config.js`** with brand tokens, leave them alone unless asked. Either way, rule 7's "no raw hex in markup" still holds: add the user's color to the config as a token, then reference the token.
8. **Bilingual-ready copy** (EN/FR by default). This skill runs no model-backed script; write copy in the language of the request. For translatable UI strings and prompts, use one `locales/i18n.yaml` catalog (see `sprezzature-ui-i18n-make` and `sprezzature-publish/references/i18n.md`).
9. **No third-party trademarks** in defaults (logos, product names, operating-system branding). Use generic, neutral language.

## Build vs prototype

Tailwind has a build step. The skill emits **prototype-grade single-file deliverables** by default: fine for demos, mockups, internal tools and small landing pages, **not** for production sites at scale. Two paths:

- **Prototype** (single-file demo, internal POC (proof of concept, a quick build that shows an idea works), throwaway, small landing): use the Tailwind Play CDN as shipped in `assets/starter-page.html`. Tailwind itself warns this is for prototyping only. The class names emitted by the skill are stable, so the same HTML works under the production path below.
- **Production**: run **Tailwind CLI** (single command, no JS framework needed) or **Vite + Tailwind** over the emitted HTML before shipping. See `references/stack-tailwind.md`.

The "zero build, drop into Nginx / S3 / Pages" pitch only holds for the prototype path. A real production site needs the build step. State which path you are on in the project README so the next maintainer knows whether the CDN tag is intentional or a leftover.

## Workflow — every task

```text
1. Identify the surface (page / component / token / audit).
2. Read ONLY the relevant reference files (do not preload all).
3. Pick colors via color-psychology.md → semantic intent first.
4. Map to Tailwind tokens (see stack-tailwind.md).
5. Write semantic HTML with Tailwind classes.
6. Add vanilla JS only where needed (form state, dialog open/close, theme).
7. Run the pre-ship checklist in references/checklist.md.
8. Return code + a one-paragraph rationale.
```

## Decision tree — picking the right component

| User says… | Read | Emit |
|---|---|---|
| "primary button" | `ui-guidelines/components/buttons.md` | `<button>` with `bg-brand-blue rounded-full px-5 py-3 text-white font-medium` |
| "destructive button" | `ui-guidelines/components/buttons.md` | `<button>` with `bg-brand-red text-white` (or text-only red for low-emphasis) |
| "modal" / "dialog" | `ui-guidelines/components/sheets.md` + `ui-guidelines/patterns/modality.md` | `<dialog>` element + open/close JS, `Escape` key, focus restore |
| "bottom sheet" | `ui-guidelines/components/sheets.md` | `<dialog>` bottom-anchored, slide-up animation, swipe-down handle |
| "alert" | `ui-guidelines/components/alerts.md` | `<dialog>` centered, 1–2 buttons, no scroll inside |
| "popover" / "tooltip" | `ui-guidelines/components/popovers.md` | `popover` attribute (modern), anchor positioning |
| "menu" | `ui-guidelines/components/menus.md` | `<details>` or `<dialog>` with menuitems |
| "tab bar" | `ui-guidelines/components/tab-bars.md` | Bottom nav with icons + labels, max 5 items |
| "navigation bar" | `ui-guidelines/components/navigation-bars.md` | Sticky top, translucent material, back/title/action layout |
| "form" / "input" | `ui-guidelines/components/text-fields.md` + `ui-guidelines/foundations/inclusion.md` | `<label>` + `<input>` with `autocomplete`, error pattern |
| "toggle" | `ui-guidelines/components/toggles.md` | `<input type="checkbox" role="switch">` styled as pill |
| "settings page" | `ui-guidelines/patterns/settings.md` | List sections with separators, no card chrome |
| "loading" | `ui-guidelines/patterns/loading.md` | Skeleton if > 300 ms, spinner only if unknown duration |
| "search" | `ui-guidelines/patterns/searching.md` | `<input type="search">` with debounced JS, results live region |
| "onboarding" | `ui-guidelines/patterns/onboarding.md` | One idea per screen, ≤ 8-word headline, skippable |
| "theme switch" | `ui-guidelines/foundations/dark-mode.md` | `data-color-scheme` attribute + persisted choice |
| "chart" / "graph" / "dashboard tile" | `charts-svg.md` + `dataviz-chart-selection.md` + `dataviz-color-palettes.md` | Hand-authored inline SVG (Scalable Vector Graphics, an image made of shapes rather than pixels, so it stays sharp at any zoom; no chart library at all), Roboto, 10 px rounded corners, palette from `color-psychology.md`, no top/right spines. State polarity when well-defined (*↑ higher is better* / *↓ lower is better* / *target = N ± k*). |
| "dashboard" / "BI" / "KPI summary" | `dashboard-ergonomics.md` (+ chart references above) | One question per tile, title as a question, polarity tag on every measurable tile, sticky filters, 12-column grid, skeleton tiles while loading. |
| "map" / "choropleth" | `dataviz-maps.md` | Title states the message, ≤ 7 classes, locator inset, accessible text alternative below the map |
| "audit" / "ergonomic review" / "UX review" | `ergonomics-criteria.md` | Walk the 8 criteria: guidance, workload, explicit control, adaptability, error management, consistency, label significance, compatibility. **Respect the existing typeface stack**: do not propose a three-Roboto swap unless the user explicitly asks about typography. |
| "make it look less AI" / "designer review" | `anti-patterns.md` | Refuse gradient text, glassmorphism on body, side-stripe borders, "boost your productivity" copy, three-card grids |
| "psychology" / "conversion" / "flow not working" | `ux-psychology.md` | Pick ONE applicable principle per screen (Hick / Anchoring / Default Bias / Peak-End / Goal Gradient) and apply concretely |
| "Laws of UX" / "Hick" / "Fitts" / "Miller" / "Jakob" / "Doherty" / "Tesler" / "Peak-End" / "Postel" / "Paradox of the Active User" | (see `sprezzature-ux-laws`) | Canonical Jon YABLONSKI set (30 laws). Reference: `sprezzature-ux-laws/references/laws-of-ux.md`. Auditor: `sprezzature-ux-laws-audit <file-or-dir>`. |
| "IBAN (International Bank Account Number, the long account number printed on a bank statement) field" / "success screen" / "checkout progress" / "loading skeleton" / "primary CTA (call to action, the one thing a page asks its reader to do: book a call, buy, install)" / "settings page" / "resume onboarding" / "form fields" | `assets/snippets/INDEX.md` | Law-keyed snippet catalog. Pick the snippet whose trigger phrase matches, copy-and-adapt the strings. Each snippet already carries dark-mode peers + focus rings + reduced-motion guards. |
| "material" / "Material 3" / "M3" | `material-design.md` | Map Material roles to skill tokens; emit plain HTML + Tailwind (no `mdc-*` classes) |

## Quality checklist (pre-ship)

Run `references/checklist.md` before returning code. Short version:

- [ ] No framework imports.
- [ ] Three-Roboto rule: only Roboto / Roboto Serif / Roboto Mono, all self-hosted.
- [ ] Semantic HTML; ARIA only where no semantic fits.
- [ ] Visible focus ring everywhere; `Escape` closes dialogs.
- [ ] `dark:` peer set for every styled element.
- [ ] Min hit area 44×44 for any interactive control.
- [ ] Body ≥ 16 px; line length ≤ 75 ch on long-form.
- [ ] `prefers-reduced-motion` honored: no translate/scale under reduce.
- [ ] Color choice traceable to `color-psychology.md`.
- [ ] No raw hex in markup.
- [ ] Copy is sentence case, verb-first on buttons, no "OK"/"please".

Pair with `sprezzature-accessibility` for `sprezzature-accessibility-lint` and `sprezzature-colors` for `sprezzature-colors-contrast` / `sprezzature-colors-cvd` runs.

## Examples

Two worked shapes with the hard rules applied together (primary CTA button;
destructive confirm `<dialog>`) live in `references/examples.md`. The generic
per-surface primaries are in `assets/components/*.html`; the law-keyed catalog
is in `assets/snippets/INDEX.md`.

## References

Load these only when needed.

**Stack & tokens**
- `references/color-psychology.md` — Choice / Emotion / Concept / Psychology palettes.
- `references/stack-vanilla-js.md` — Vanilla JS patterns.
- `references/stack-tailwind.md` — Config tokens, plugins, dark-mode strategy, the three-Roboto typography rule.
- `references/checklist.md` — Pre-ship quality gate.

**Dataviz**
- `references/charts-svg.md` — hand-authored inline SVG house style.
- `references/dataviz-chart-selection.md` — Picking the right chart shape.
- `references/dataviz-color-palettes.md` — Sequential / divergent / categorical.
- `references/dataviz-maps.md` — Choropleth and map ergonomics.
- `references/dashboard-ergonomics.md` — Tile-by-tile dashboard layout.

**Design system**
- `references/ui-guidelines/INDEX.md` — Full map (foundations, patterns, components, inputs, platforms).
- `references/material-design.md` — Material 3 → skill-token mapping.
- `references/anti-patterns.md` — Visual + copy tells to refuse.
- `references/ux-psychology.md` — Applied cognitive principles.
- `references/ergonomics-criteria.md` — Eight ergonomic criteria for UX review.
- `references/examples.md` — Two worked component shapes (CTA button, confirm dialog).

## Assets

- `assets/starter-page.html` — single-file bootstrap (Tailwind Play CDN, prototype-grade; swap to Tailwind CLI / Vite before shipping a real production site).
- `assets/components/button.html`, `card.html`, `modal.html`, `form-field.html`, `nav.html`, `theme-toggle.html`, `figure-fullscreen.html` — component-shape primaries (one file per generic UI surface).
- `assets/components/chart-bar.svg`, `chart-line.svg` — hand-authored SVG charts.
- `assets/snippets/` — **law-keyed** snippet catalog (one file per mechanically-implementable Law of UX: Miller / Peak-End / Goal-Gradient / Doherty / Von Restorff / Jakob / Chunking / Zeigarnik). See `assets/snippets/INDEX.md` for the law ↔ snippet ↔ trigger-phrase mapping. Every snippet passes both `sprezzature-ux-laws` and `sprezzature-accessibility` auditors with zero findings; they are the make-side counterpart to `sprezzature-ux-laws-audit --fix`.
- `assets/fonts/roboto/` — Roboto WOFF2 (Web Open Font Format 2, the compressed font file browsers download) + OFL (SIL Open Font License, which lets anyone use and ship the font for free) + `fonts.css` (sans). The `fonts.css` declares the `@font-face` blocks and also exposes the `--font-sans / --font-serif / --font-mono` custom properties and the base `html { font-family: var(--font-sans) }` / `code, pre, kbd, samp { font-family: var(--font-mono) }` wiring.
- `assets/fonts/roboto-serif/` — Roboto Serif WOFF2 + OFL + `fonts.css` (serif).
- `assets/fonts/roboto-mono/` — Roboto Mono WOFF2 + OFL + `fonts.css` (code / monospace).
- The three-Roboto rule itself + the full wiring recipe (Tailwind config, `@import` ordering, HTML preload, fallback stacks) lives in `references/ui-guidelines/foundations/typography.md`; no per-asset README, per the Anthropic skill spec.

## Scripts

- `sprezzature-ui-i18n-audit`, `sprezzature-ui-i18n-make` — the two i18n tools, from the `sprezzature-ui` package (see the i18n section above).
- `validate_content.py`, in the monorepo's own scripts folder — the pre-ship content gate. Stdlib only. Checks SKILL.md frontmatter, forbidden framework imports, trademarked platform terms, marketing phrases, reference path resolution. Exit non-zero on any failure.
