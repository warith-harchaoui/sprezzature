# Components — Menus

## When to consult this file

- "More" actions on a list item or toolbar
- Selecting one option from a small set
- Right-click / long-press contextual actions

## Core principles

- **A menu is a list of actions or choices.** Keep items short and parallel (all verbs, or all nouns).
- **Group with separators** for ≥ 5 items.
- **Destructive items at the bottom** with red text.
- **Keyboard-driven**: arrow keys move, Enter activates, Escape closes.

## Concrete rules

1. Use a `<dialog>` or native `popover` for the menu surface.
2. Mark items with `role="menuitem"` inside `role="menu"` only if not using semantic `<button>`s, but prefer real `<button>`s.
3. **Min item height 44 px** so each is tappable.
4. **Icons left** of labels, optional, monochrome.
5. **Keyboard shortcuts right** of labels, in `text-label-tertiary tabular-nums`.

## Pattern

```html
<button popovertarget="row-menu" aria-label="More options" class="grid h-11 w-11 place-items-center rounded-full hover:bg-surface-secondary dark:hover:bg-surface-secondary-dark">
  <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
    <circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/>
  </svg>
</button>

<div id="row-menu" popover class="min-w-48 rounded-xl bg-surface-primary p-1 shadow-lg ring-1 ring-separator/40 dark:bg-surface-primary-dark">
  <button class="flex w-full min-h-11 items-center gap-3 rounded-lg px-3 hover:bg-surface-secondary dark:hover:bg-surface-secondary-dark">Edit</button>
  <button class="flex w-full min-h-11 items-center gap-3 rounded-lg px-3 hover:bg-surface-secondary dark:hover:bg-surface-secondary-dark">Duplicate</button>
  <hr class="my-1 border-separator/40">
  <button class="flex w-full min-h-11 items-center gap-3 rounded-lg px-3 text-brand-red hover:bg-brand-red/10">Delete</button>
</div>
```

## Checklist

- [ ] Items parallel in form (all verbs or all nouns).
- [ ] Destructive at bottom, red.
- [ ] Min item height 44 px.
- [ ] Arrow keys / Enter / Escape work.
