# Inputs — Pointing Devices

## When to consult this file

- Hover, right-click, drag, precise cursor selection
- Desktop-first surfaces

## Core principles

- **Hover is bonus, not required.** Never hide essential info behind hover.
- **Cursor feedback** signals interactivity: `cursor-pointer` for clickable, `cursor-text` for text fields.
- **Right-click menu** must exist where the user expects it (lists, items), and offer the same actions as the row's "more" button.
- **Click target ≥ 44 × 44** on desktop too, large enough to forgive imprecise mice.

## Concrete rules

1. Tailwind `hover:` only for visual polish; the same state is reachable via `focus-visible:` for keyboard.
2. Provide a long-press analogue on touch (`oncontextmenu` works on most mobile browsers via long press).
3. Never disable the native context menu unless replacing it with a richer one.

## Pattern — hover + focus parity

```html
<button class="rounded-lg px-3 py-2 hover:bg-surface-secondary focus-visible:bg-surface-secondary dark:hover:bg-surface-secondary-dark dark:focus-visible:bg-surface-secondary-dark">
  …
</button>
```

## Checklist

- [ ] No essential info hidden behind hover.
- [ ] Click target ≥ 44 px.
- [ ] Right-click menu present where expected.
