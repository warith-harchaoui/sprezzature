# Platforms — Mobile (phone-sized)

## When to consult this file

- Viewports < 768 px
- Installed PWAs on phones

## Defaults

- **Single column.** Stack everything vertically; reserve grids for desktop.
- **Bottom-anchored primary actions.** Thumbs reach the bottom; CTAs there.
- **Sticky bottom tab bar** for app-style navigation; sticky top nav bar for doc-style.
- **Safe-area insets**: `pt-[max(env(safe-area-inset-top),0px)]` and `pb-[max(env(safe-area-inset-bottom),0px)]`.
- **Min body font 16 px** so mobile browsers don't auto-zoom on input focus.
- **Touch targets ≥ 44 × 44 px**, 8 px gaps.

## Patterns

- Bottom sheet for shares / pickers / options (`components/sheets.md`).
- Pull-to-refresh: native browser scroll, no JS attempt.
- Edge-swipe back: built into the OS; don't intercept.

## Checklist

- [ ] One column.
- [ ] Bottom CTA where the primary action lives.
- [ ] Safe-area insets respected.
- [ ] Body ≥ 16 px.
