# Foundations — Materials


## When to consult this file

- Translucent surfaces, blurred chrome, vibrant overlays
- Sticky toolbars, sheets, popovers, modal backgrounds

## Core principles

- **Materials hint at depth.** A blurred top bar tells the user the page scrolls beneath it.
- **Use materials for chrome, not content.** Translucency belongs to navigation bars, tab bars, popovers, sheets — never the article body.
- **Two materials per surface, max.** A single blur level reads as native; three reads as chaos.
- **Honor `prefers-reduced-transparency`.** Fall back to a solid color.

## Material levels (Material levels)

| Level | Light | Dark | Notes |
|---|---|---|---|
| Ultra-thin | `rgba(255,255,255,0.55)` + 20 px blur | `rgba(0,0,0,0.55)` + 20 px blur | Top toolbar, search bar |
| Thin | `rgba(255,255,255,0.7)` + 24 px blur | `rgba(0,0,0,0.7)` + 24 px blur | Standard chrome |
| Regular | `rgba(255,255,255,0.82)` + 32 px blur | `rgba(0,0,0,0.82)` + 32 px blur | Sheet background |
| Thick | `rgba(255,255,255,0.92)` + 40 px blur | `rgba(0,0,0,0.92)` + 40 px blur | Alert / popover |

## Tailwind config

```js
backdropBlur: {
  'ultra': '20px',
  'thin': '24px',
  'regular': '32px',
  'thick': '40px',
}
```

## Pattern — translucent sticky toolbar

```html
<header class="sticky top-0 z-30 border-b border-separator/40
               bg-surface-primary/55 backdrop-blur-ultra
               supports-[backdrop-filter]:bg-surface-primary/55
               dark:bg-surface-primary-dark/55
               motion-reduce:backdrop-blur-none
               [@media(prefers-reduced-transparency:reduce)]:bg-surface-primary
               dark:[@media(prefers-reduced-transparency:reduce)]:bg-surface-primary-dark">
  …
</header>
```

## Concrete rules

1. **`backdrop-filter: blur(…)`** is required; without it, fall back to a solid color (handled by the `supports-[]` guard above).
2. **Add a 1 px separator** (`border-b border-separator/40`) so the chrome reads as a layer.
3. **Don't blur over critical content** the user must read (long text).
4. **Avoid blur inside scrollable containers** — perf cost is significant on low-end devices.
5. **Test on dark mode**; pure black + blur loses contrast quickly.

## Checklist

- [ ] Materials only on chrome (toolbar, tab bar, sheet, popover).
- [ ] `prefers-reduced-transparency` fallback present.
- [ ] At most two blur levels in use.
- [ ] No blur over body text.
- [ ] Separator line accompanies translucent chrome.
