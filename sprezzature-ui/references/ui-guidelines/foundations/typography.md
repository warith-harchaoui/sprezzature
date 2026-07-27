# Foundations — Typography

## When to consult this file

- Picking sizes, weights, line heights
- Building a type scale
- Auditing readability

## The fonts: the three-Roboto rule (generation-only default)

This skill ships **exactly three downloaded webfonts**, all from the
Roboto super-family. This is the **default for fresh generation** when
the user has not specified a typeface — no other downloaded family is
introduced by the skill on its own. System-font fallback stacks
(`ui-monospace`, `system-ui`, `serif`, `sans-serif`) are fine and
expected.

**The rule does NOT apply to audits.** When the user asks to review,
audit, redesign, or "make less AI" an *existing* page, respect the
typefaces already in use. Don't propose a font swap as part of an
ergonomic / a11y / anti-pattern review unless the user specifically
asks about typography — that would be scope creep and would imply a
rebrand they didn't ask for. The same goes when the user names a
typeface ("use Inter", "we ship IBM Plex", "stick to system fonts"):
use what they ask for and stop. The three-Roboto rule is a *default*,
not a hard constraint.

| Role             | Family         | When to lift it                                                |
| ---------------- | -------------- | -------------------------------------------------------------- |
| Sans (default)   | Roboto         | UI chrome + body across every surface                          |
| Serif            | Roboto Serif   | Editorial / longform / quote pulls / prose-heavy landings      |
| Code / monospace | Roboto Mono    | `<code>`, `<pre>`, kbd / samp, terminal panels, log output     |

Why one super-family: Roboto sans / serif / mono share metrics,
x-height, and visual rhythm by design, so prose-heavy and code-heavy
surfaces stay typographically coherent and the WOFF2 payload stays
small (~290 KB total, latin subset, all three families combined).

- License: SIL Open Font License (OFL) for all three, free for commercial use.
- Sources:
  - <https://github.com/googlefonts/roboto-3-classic>
  - <https://github.com/googlefonts/RobotoSerif>
  - <https://github.com/googlefonts/RobotoMono>
- Self-host the WOFF2 files (don't load from a third-party CDN) for performance + privacy.

### Self-hosting recipe

The skill ships ready-to-use folders. Copy them into your project's
public path:

```text
public/fonts/
├── roboto/         Roboto-Variable.woff2          + Roboto-Italic-Variable.woff2          + OFL.txt + fonts.css
├── roboto-serif/   Roboto-Serif-Variable.woff2    + Roboto-Serif-Italic-Variable.woff2    + OFL.txt + fonts.css
└── roboto-mono/    Roboto-Mono-Variable.woff2     + Roboto-Mono-Italic-Variable.woff2     + OFL.txt + fonts.css
```

Each family ships one variable upright file + one variable italic
file, covering weights 100–900 via the variation axis. Declare each
with `font-display: swap` (already wired in the bundled `fonts.css`).

```css
@font-face {
  font-family: 'Roboto';
  font-style: normal;
  font-weight: 100 900;
  font-display: swap;
  src: url('/fonts/roboto/Roboto-Variable.woff2') format('woff2-variations'),
       url('/fonts/roboto/Roboto-Variable.woff2') format('woff2');
}
```

(`fonts.css` in each folder ships the four blocks: upright + italic
for Roboto, Roboto Serif, Roboto Mono. The `roboto/fonts.css` also
exposes the CSS variables and base wiring below.)

### CSS variables

```css
:root {
  --font-sans:  'Roboto', sans-serif;
  --font-serif: 'Roboto Serif', serif;
  --font-mono:  'Roboto Mono', ui-monospace, monospace;
}
html { font-family: var(--font-sans); }
code, pre, kbd, samp { font-family: var(--font-mono); }
```

The fallback stack only renders if the bundled WOFF2 fails — the FOUT
(flash of unstyled text) is intentional and acceptable.

### Tailwind config

```js
// tailwind.config.js
theme: {
  extend: {
    fontFamily: {
      sans:  ['Roboto', 'sans-serif'],
      serif: ['Roboto Serif', 'serif'],
      mono:  ['Roboto Mono', 'ui-monospace', 'monospace'],
    },
  },
},
```

`font-sans` (Tailwind default) maps to Roboto after this override;
`font-serif` and `font-mono` map to the matching siblings. Authors
need to call out `font-serif` or `font-mono` explicitly only when a
surface deviates from the default sans.

### HTML preload (optional but recommended)

```html
<link rel="preload" href="/fonts/roboto/Roboto-Variable.woff2"           as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/roboto-mono/Roboto-Mono-Variable.woff2" as="font" type="font/woff2" crossorigin>
```

Preload Roboto Serif only on pages that actually use it (typically
longform / blog routes).

## Core principles

- **One super-family, three siblings.** Stick to Roboto / Roboto Serif / Roboto Mono. No fourth downloaded family.
- **Focused weights.** 400 / 500 / 700 cover all of chrome and body; the variable axis means weight is free at any value, but only use named steps in markup so the design stays scannable.
- **Define a small set of styles.** Don't ad-hoc sizes. Build a scale with semantic names (`display`, `title`, `headline`, `body`, `subhead`, `footnote`, `caption`).
- **Respect user font-size preferences** — use `rem` and let `html { font-size: 100% }` honor user settings.
- **Body 16–17 px** desktop, 16 px minimum mobile.
- **Line height proportional to size**: tight for display (`1.1–1.2`), generous for body (`1.5–1.6`).
- **Line length** 45–75 characters — `max-w-prose` in Tailwind.
- **Hierarchy through weight and size, not color.** Subtle color shifts are secondary cues.
- **Tracking (letter-spacing)** tightens slightly for large display sizes. Roboto sits well at `tracking-tight` for titles ≥ 24 px.

## Type scale

Built on `rem`. Authors should use Tailwind utility classes — every step has a name.

| Role | Size (rem / px) | Weight | Line-height | Tailwind |
|---|---|---|---|---|
| Display | 2.75 / 44 | 700 | 1.1 | `text-5xl font-bold tracking-tight` |
| Title 1 | 2 / 32 | 700 | 1.15 | `text-4xl font-bold tracking-tight` |
| Title 2 | 1.5 / 24 | 700 | 1.2 | `text-2xl font-semibold tracking-tight` |
| Title 3 | 1.25 / 20 | 600 | 1.25 | `text-xl font-semibold` |
| Headline | 1.0625 / 17 | 600 | 1.4 | `text-[17px] font-semibold` |
| Body | 1.0625 / 17 | 400 | 1.5 | `text-[17px]` |
| Callout | 1 / 16 | 400 | 1.4 | `text-base` |
| Subhead | 0.9375 / 15 | 400 | 1.4 | `text-[15px]` |
| Footnote | 0.8125 / 13 | 400 | 1.4 | `text-[13px]` |
| Caption 1 | 0.75 / 12 | 400 | 1.3 | `text-xs` |
| Caption 2 | 0.6875 / 11 | 400 | 1.3 | `text-[11px]` |

## Concrete rules

1. **Three Roboto families only.** No fourth downloaded face. If a surface calls for a "display" look, render it with Roboto Serif weight + size changes rather than introducing a new family.
2. **At most three weights per surface** in use: 400 / 500 / 700 covers > 95 % of cases.
3. **Numeric tables** use tabular figures: `font-variant-numeric: tabular-nums` (Tailwind: `tabular-nums`).
4. **Avoid all caps for body**; allow it sparingly for very short labels with letter-spacing.
5. **Italic for true emphasis only**, not for decoration. The italic-variable files cover all three families; use real italics, don't fake-slant.
6. **Wrap long words** with `overflow-wrap: anywhere` (Tailwind `break-words`) inside narrow containers.

## Pattern — typography component classes (Tailwind `@layer components`)

```css
@layer components {
  .h-display   { @apply text-5xl font-bold tracking-tight; }
  .h-title-1   { @apply text-4xl font-bold tracking-tight; }
  .h-title-2   { @apply text-2xl font-semibold tracking-tight; }
  .h-headline  { @apply text-[17px] font-semibold; }
  .t-body      { @apply text-[17px] leading-relaxed; }
  .t-callout   { @apply text-base; }
  .t-subhead   { @apply text-[15px]; }
  .t-footnote  { @apply text-[13px] text-label-secondary; }
  .t-caption   { @apply text-xs text-label-tertiary; }
  /* Longform editorial surfaces lift the serif. */
  .t-prose     { @apply font-serif text-[17px] leading-relaxed; }
}
```

## Checklist

- [ ] Roboto / Roboto Serif / Roboto Mono self-hosted as WOFF2; no fourth downloaded family.
- [ ] Only the named weight steps (400 / 500 / 700) used in markup.
- [ ] `font-display: swap` on every `@font-face`.
- [ ] Tailwind `font-sans` resolves to Roboto first; `font-serif` to Roboto Serif; `font-mono` to Roboto Mono.
- [ ] Body text ≥ 16 px.
- [ ] Line length 45–75 ch on long-form pages.
- [ ] No more than ~6 distinct sizes in use across the page.
- [ ] Hierarchy works without color (test in grayscale).
- [ ] Tabular numerals on tables / counters.
- [ ] Headings use real `<h1>`–`<h6>` in order.
