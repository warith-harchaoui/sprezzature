# Anti-patterns: design tells to avoid

What NOT to emit. These are the reflexive visual choices that mark an interface as "AI-generated" or "designer-by-default". Refuse them unless the user explicitly asks. Most have a simple alternative listed.

## Visual anti-patterns

### Gradient text

A heading filled with `background-clip: text` and a two-stop linear gradient (purple→pink, blue→indigo, etc.).

- **Why it's a tell:** signals visual ambition without contributing to hierarchy. Hurts contrast.
- **Instead:** use a single solid color from the brand palette. If you need emphasis, use `font-weight` or size.

### Purple gradients on chrome

Hero sections and CTA backgrounds bathed in `linear-gradient(135deg, #6a5cff, #b266ff)` or similar.

- **Why it's a tell:** generic "AI vibe". Not anchored in any brand.
- **Instead:** flat surface from the brand palette. If a gradient is justified, pick from `color-psychology.md` colors and limit to a 15 % overlay on an existing brand hue.

### Glassmorphism on cards

Translucent cards floating over abstract gradients with `backdrop-filter: blur(20px)` and a 1 px white border.

- **Why it's a tell:** decorative effect borrowed from a 2021 trend, applied without reason.
- **Instead:** translucent material belongs on chrome (top bar, tab bar, sheet) over real content underneath. See `ui-guidelines/foundations/materials.md`. Body cards stay solid.

### Side-stripe borders

A vertical 3–4 px colored bar on the left edge of a card or callout.

- **Why it's a tell:** template aesthetic. Adds visual noise without semantic value.
- **Instead:** use color in the icon and the label. If the callout needs a category, an icon and a label do that without chrome.

### "AI color palette"

Eight bright primary hues used together (red, orange, yellow, green, blue, indigo, violet, pink) as if every brand color must appear at once.

- **Why it's a tell:** zero discipline. Every color competes.
- **Instead:** one accent color anchors the screen. Secondary colors are semantic only (success / warning / danger). See `color-psychology.md`.

### Excessive border-radius

Every card at `rounded-3xl`, every button as a perfect pill, every input bubble-shaped.

- **Why it's a tell:** "softness as a substitute for taste". Removes architectural feel.
- **Instead:** the skill's radii are `rounded-xl` (12 px) for inputs and cards, `rounded-2xl` (16 px) for surfaces, `rounded-full` for pill buttons and avatars, `rounded-[10px]` for chart tiles. That's it.

### Drop shadows everywhere

Layered shadows on every element to fake depth.

- **Why it's a tell:** noise. Hides real hierarchy under cosmetic depth.
- **Instead:** shadows on elevated surfaces only (modal, popover, raised card). Use `shadow-sm` sparingly; use a soft border (`border-separator/40`) on flat surfaces.

### Decorative emoji in chrome

`✨ Get started`, `🚀 Launch`, `💡 Tip` in section headers and CTAs.

- **Why it's a tell:** signals informality without contributing meaning. Inconsistent across cultures.
- **Instead:** clear verb-first labels. If the heading needs a visual anchor, use a real icon (`ui-guidelines/foundations/icons.md`).

### Skeleton-everything

Skeleton loaders for every fetch, including ones that finish in < 200 ms.

- **Why it's a tell:** designer reflex. Adds flicker without helping.
- **Instead:** skeletons for waits ≥ 300 ms only. See `ui-guidelines/patterns/loading.md`.

### Animation on first paint

Whole sections fading and translating in on page load.

- **Why it's a tell:** delays content; adds nothing.
- **Instead:** content is in the DOM immediately. Reserve motion for state changes the user initiated.

## Copy anti-patterns

The phrases below are LLM-marketing default voice. Refuse them and use the plainer alternative on the right.

| Avoid | Use |
|---|---|
| "Boost your productivity" | the actual outcome ("Send invoices in two clicks") |
| "Unleash the power of …" | the actual capability ("Generate reports from your data") |
| "Seamless / seamlessly" | the actual mechanism ("Sync runs every 5 minutes") |
| "Leverages" | "Uses" |
| "Cutting-edge" / "world-class" / "state-of-the-art" | drop entirely |
| "Robust and scalable" | drop or quantify |
| "Effortless" | drop or quantify |
| "Empower" / "enable" | "let" / "give" |
| "Crafted with care" | drop |
| "Engineered for" | "for" |
| "We're excited to …" | drop |
| "Get started today!" | "Get started" |
| "Click here" (link text) | the actual destination ("Read the docs") |

See `ui-guidelines/foundations/writing.md` for the broader voice rules.

## Layout anti-patterns

### Three-card "features grid" with the same icon style and 4-word headline each

The default landing-page layout.

- **Why it's a tell:** template. Three identical-rhythm cards make the differences look smaller than they are.
- **Instead:** vary the card shape to match content weight. One large highlighted card + supporting items reads as editorial.

### Hero with a fake screenshot of the product

A laptop or phone mockup PNG with placeholder UI inside.

- **Why it's a tell:** signals "marketing site that hasn't been built". Sets the wrong expectations.
- **Instead:** the real product UI, in an iframe or a screenshot at correct DPI. Or no screenshot: a clear sentence and a CTA.

### Stat strip with arbitrary numbers

`100K+ users · 99.9 % uptime · 50+ integrations` with no source.

- **Why it's a tell:** invented numbers. Bad-faith.
- **Instead:** one verified number with the source. Or none.

### Triple-bullet "value props"

Every section laid out as "headline / three bullets / button".

- **Why it's a tell:** every AI landing page does this.
- **Instead:** mix sections: a quote, a comparison, a screenshot, a short paragraph, a chart. The rhythm should vary.

## Component anti-patterns

| Pattern | Why bad | Instead |
|---|---|---|
| `<div onclick>` button | Not keyboard-accessible | `<button>` |
| Disabled buttons with no explanation | User can't tell what's wrong | Disabled + tooltip naming the missing requirement |
| Toasts that auto-dismiss critical errors | User misses the error | Toasts only for non-actionable success; persistent banner for errors |
| Carousels for primary content | Most users only see slide 1 | List + see-more, or scrollable rail clearly labeled |
| Infinite scroll on settings / docs | Can't navigate to a known section | Pagination or a TOC sidebar |
| Modal on page load | Pop-up behavior | Inline banner or in-context hint |

## How to use this file

Treat it as a refusal list. Before emitting code, scan the requested output for matches. If the user explicitly asks for one of these (e.g. "I want a glassmorphic card"), warn them once with a one-line explanation of the tradeoff, then comply.

## Checklist

- [ ] No gradient text in headings.
- [ ] No glassmorphic body cards.
- [ ] No side-stripe borders.
- [ ] No "rainbow" multi-color decoration.
- [ ] Border-radius limited to the skill's set.
- [ ] No drop shadow on flat surfaces.
- [ ] No marketing buzzwords in copy.
- [ ] No template three-card grid as default.
- [ ] No unverified stat strip.
- [ ] No `<div onclick>` buttons.
