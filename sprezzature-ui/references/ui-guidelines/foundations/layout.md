# Foundations — Layout


## When to consult this file

- Choosing spacing, alignment, breakpoints
- Building any page or component grid
- Deciding when to stack, split, or scroll

## Core principles

- **Content first, chrome last.** Layout exists to make content readable; nothing else.
- **One alignment per surface.** Pick left, center, or trailing for a region and stick to it.
- **Generous whitespace.** When in doubt, add more padding. Tight UIs feel cluttered, not efficient.
- **Predictable rhythm.** Use a single spacing scale (multiples of 4 px). Random gaps break trust.
- **Respect safe areas.** On mobile, account for notches, home indicators, status bars (`env(safe-area-inset-*)`).
- **Reflow, don't shrink.** When the viewport narrows, restructure (column-to-stack), don't just scale text down.
- **Touch targets ≥ 44 px** on any platform that might be touched.

## Spacing scale (Tailwind defaults work)

| Token | px | Use |
|---|---|---|
| `0.5` | 2 | Hairline separators |
| `1` | 4 | Compact icon spacing |
| `2` | 8 | Inline elements inside a row |
| `3` | 12 | Form field internal padding |
| `4` | 16 | Section body padding mobile |
| `5` | 20 | Card padding |
| `6` | 24 | Section body padding desktop |
| `8` | 32 | Between sibling sections |
| `10` | 40 | Hero vertical |
| `12` | 48 | Top-level page padding |
| `16` | 64 | Big hero / marketing rhythm |

## Breakpoints (Tailwind defaults work)

| Token | Min width | Typical device |
|---|---|---|
| `sm` | 640 px | Large phones landscape |
| `md` | 768 px | Tablet portrait |
| `lg` | 1024 px | Tablet landscape / small laptop |
| `xl` | 1280 px | Desktop |
| `2xl` | 1536 px | Wide desktop |

Design **mobile-first**: write base classes for the smallest size, then layer `md:` / `lg:` overrides.

## Concrete rules

1. **Page container**: `mx-auto w-full max-w-3xl px-4 sm:px-6` for content-heavy pages, `max-w-6xl` for apps.
2. **Vertical rhythm**: `space-y-{n}` inside sections; never blank `<br>` or empty divs.
3. **Grid**: `grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3` — change column count, not text scale.
4. **Sticky chrome**: `sticky top-0 z-30` with `backdrop-blur` and a translucent background.
5. **Safe areas on mobile/PWA**:
   ```html
   <body class="pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]">
   ```
   Or in Tailwind config, define `safe` utilities.
6. **Min line-length**: ~45–75 characters for body text. Tailwind: `max-w-prose`.
7. **Cards**: rounded `rounded-2xl`, soft shadow `shadow-sm` (or none on chrome-style layouts), generous padding `p-5`.

## Pattern — responsive content page

```html
<main class="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
  <header class="mb-8 space-y-2">
    <h1 class="text-3xl font-semibold tracking-tight text-label-primary dark:text-label-primary-dark sm:text-4xl">Title</h1>
    <p class="text-base text-label-secondary dark:text-label-secondary-dark">Subtitle that explains the page.</p>
  </header>
  <section class="space-y-6">
    <article class="space-y-4 rounded-2xl bg-surface-secondary p-5 dark:bg-surface-secondary-dark">…</article>
    <article class="space-y-4 rounded-2xl bg-surface-secondary p-5 dark:bg-surface-secondary-dark">…</article>
  </section>
</main>
```

## Pattern — app shell with sticky toolbar and safe areas

```html
<div class="grid min-h-dvh grid-rows-[auto_1fr_auto] bg-surface-primary dark:bg-surface-primary-dark">
  <header class="sticky top-0 z-30 border-b border-separator/60 bg-surface-primary/80 px-4 pt-[max(env(safe-area-inset-top),12px)] pb-3 backdrop-blur dark:bg-surface-primary-dark/80">…</header>
  <main class="mx-auto w-full max-w-3xl px-4 py-6">…</main>
  <nav class="sticky bottom-0 border-t border-separator/60 bg-surface-primary/80 px-2 pb-[max(env(safe-area-inset-bottom),8px)] pt-2 backdrop-blur dark:bg-surface-primary-dark/80">…</nav>
</div>
```

## Checklist

- [ ] One alignment per region.
- [ ] Spacing uses the scale; no magic px values.
- [ ] Tested at 320 px, 768 px, 1280 px.
- [ ] Body text inside `max-w-prose`.
- [ ] Safe-area insets respected.
- [ ] No horizontal scroll at any breakpoint.
- [ ] Sticky chrome uses `backdrop-blur` for platform-native feel.
