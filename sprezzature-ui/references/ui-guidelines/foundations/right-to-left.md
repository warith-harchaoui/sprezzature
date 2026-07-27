# Foundations — Right to Left


## Core principles

- **Mirror the layout.** Reading order, navigation, chevrons, sliders: all flip.
- **Don't mirror what shouldn't flip.** Logos, clocks, media controls (play/pause/skip), bar charts of time series, code/numerals.
- **Use logical CSS properties**, not directional ones. `margin-inline-start` instead of `margin-left`; `padding-inline-end` instead of `padding-right`.
- **Set `dir="rtl"`** on `<html>` or the relevant container; let CSS logical properties do the work.
- **Auto-detect inside fields** with `dir="auto"` so a user typing Arabic in a French UI still renders correctly.

## Concrete rules

1. **Tailwind RTL plugin or logical utilities**: prefer `ps-4 pe-3` (padding-start/end) over `pl-4 pr-3`. Modern Tailwind supports these out of the box.
2. **`text-start` / `text-end`** instead of `text-left` / `text-right`.
3. **Chevrons in nav rows flip**: a right-chevron pointing into a detail screen becomes a left-chevron in RTL. Use a directional CSS transform or inline SVG that mirrors via `[dir="rtl"] &` selector.
4. **Numbers stay LTR** inside RTL text — handled by the browser bidi algorithm, but verify edge cases.
5. **Mirror illustrations** that imply forward motion (a person walking, an arrow); don't mirror brand logos.

## Pattern — directional chevron

```html
<a class="flex items-center justify-between px-4 py-3" href="#">
  <span>Account</span>
  <svg class="rtl:rotate-180" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
    <path d="M9 18l6-6-6-6"/>
  </svg>
</a>
```

## Checklist

- [ ] `dir` is set per locale.
- [ ] Logical properties (`ps-*`, `pe-*`, `ms-*`, `me-*`, `start-*`, `end-*`) used throughout.
- [ ] Directional icons mirrored.
- [ ] Logos and media controls NOT mirrored.
- [ ] User-content fields use `dir="auto"`.
