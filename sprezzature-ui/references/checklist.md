# Pre-ship Quality Checklist

Run this before returning any non-trivial UI code. Each item is a hard gate — if it fails, fix before shipping.

## Two kinds of rule: universal vs house style

The checklist mixes two things; know which is which before you adapt it to
another brand.

- **Universal engineering — keep no matter the brand.** These are correctness
  and accessibility, not taste: semantic HTML (`<button>`, `<label for>`,
  `<nav>`, one `<h1>`, ordered headings), a visible focus ring on every
  interactive element, `prefers-reduced-motion` guards, dark-mode peers, labelled
  form controls, correct ARIA, full keyboard operability, no clickable
  `<div>`/`<span>`. Dropping any of these is a bug in any design system.
- **House style — opinionated, swap for your own brand.** The three-Roboto
  typography, the specific palette (`brand-blue` and friends), `rounded-2xl`
  corners, the exact spacing scale, the emoji-in-heading convention. These make
  output look like *this* system; another team can substitute their tokens and
  keep the universal rules intact.

The emitter is its own customer: every shipped template passes
`sprezzature-accessibility` and the `sprezzature-ux-laws` audit with zero error-severity
findings (enforced by `tests/test_dogfood_audits.py`).

## Stack purity

- [ ] No framework imports (`react`, `vue`, `svelte`, `solid-js`, `next`, `nuxt`, `angular`).
- [ ] All scripts are ES modules (`<script type="module">`).
- [ ] No inline `onclick=` / `onsubmit=` in HTML — JS-side `addEventListener` only.
- [ ] Tailwind classes only; no inline `style="…"` except CSS custom-property values.
- [ ] Three-Roboto rule: only Roboto / Roboto Serif / Roboto Mono, all self-hosted; no third-party CDN for fonts.

## Semantics & accessibility

- [ ] Real semantic HTML (`<button>`, `<a href>`, `<label for>`, `<dialog>`, `<form>`).
- [ ] Every interactive element has an accessible name (visible text OR `aria-label`).
- [ ] Visible focus ring (`focus-visible:ring-2 …`).
- [ ] Min hit area 44×44 for any tappable control.
- [ ] `Escape` closes dialogs, popovers, menus.
- [ ] Tab order matches visual order.
- [ ] Dynamic state changes announced via `aria-live` / `role="status"` / `role="alert"`.
- [ ] Headings use real `<h1>`–`<h6>` in order; no `<div class="text-xl">` masquerading.
- [ ] Form errors tied to inputs via `aria-describedby`.

## Color & contrast

- [ ] No raw hex in markup — semantic Tailwind tokens.
- [ ] Body text ≥ 4.5:1; UI / large text ≥ 3:1 — verified in BOTH themes.
- [ ] Red used only for destructive/critical states.
- [ ] Color choice traceable to `color-psychology.md` (Choice/Emotion/Concept/Psychology).
- [ ] State communicated by more than color (icon, text, shape).

## Dark mode

- [ ] `dark:` peer set for every styled element.
- [ ] Layered surfaces lighten as they rise (primary darker than tertiary).
- [ ] Body text not pure `#FFFFFF` on dark.
- [ ] `theme-color` meta set for both schemes.

## Typography

- [ ] Body ≥ 16 px.
- [ ] Line length ≤ 75 ch on long-form (`max-w-prose`).
- [ ] Only weights 400 / 500 / 600 / 700 in use.
- [ ] Tabular numerals on numeric tables.

## Motion

- [ ] No interaction > 500 ms.
- [ ] Animations on `transform` / `opacity` only.
- [ ] `motion-reduce:transition-none motion-reduce:transform-none` everywhere translate/scale is used.
- [ ] Skeleton screens for waits ≥ 300 ms.

## Copy

- [ ] Sentence case throughout.
- [ ] Button labels verb-first (or single object noun if context is clear).
- [ ] No "OK" on consequential actions; name the action.
- [ ] No "please".
- [ ] Empty states give a next step.
- [ ] Errors say what + why + what to try.

## Inclusion

- [ ] No forced first/last name split.
- [ ] All `<input>` use `autocomplete` and `dir="auto"` where appropriate.
- [ ] `lang` attribute on `<html>`.
- [ ] `Intl` used for dates and numbers.

## Performance

- [ ] No layout shift on load (images, fonts have reserved space).
- [ ] `<img>` has explicit `width` and `height`.
- [ ] `loading="lazy"` below the fold.
- [ ] `font-display: swap` on every `@font-face`.

## Bilingual

- [ ] `<html lang="…">` set correctly.
- [ ] If the repo ships bilingual: `README.md` + `LISEZMOI.md` with switcher line at the top.
- [ ] Runtime copy keyed by `lang`; default fallback to English.

## Charts & dashboards

- [ ] Vega-Lite spec (not hand-written SVG), house `config` from `charts-vega.md`.
- [ ] Title states the conclusion or the question, not the dimensions.
- [ ] **Polarity decided for the chart's context and stated** on every quantitative axis / KPI whose "good direction" is well-defined for this audience (*↑ higher is better*, *↓ lower is better*, or *target = N ± k*), in the axis title, subtitle, or tile chip. Skipped for neutral axes (time, category, region) and ambiguous metrics. Never carried by color alone.
- [ ] `role="img"` + `aria-label` restates the polarity in words for screen readers.
- [ ] Bars start at zero; pies have ≤ 4 slices; no 3D.
