# Components — Popovers

## When to consult this file

- A small contextual UI anchored to a trigger (filter dropdown, color picker, profile menu)
- A tooltip with structured content

## Core principles

- **Anchor to the trigger.** Position relative to the button that opened it, with smart flip when near a viewport edge.
- **Non-blocking.** Unlike modals, popovers don't darken the background.
- **Light-dismiss.** Click outside, Escape, or focus leaving closes it.
- **Keep content short.** A popover that needs scrolling probably wants to be a sheet.

## Concrete rules

1. **Use the native `popover` attribute** (`<div popover>` + `popovertarget` on the button) where supported; fall back to `<dialog>` for older browsers.
2. **CSS Anchor Positioning** (`position-anchor` + `inset-area`) for placement when supported. Fallback: absolute positioning + JS measurement.
3. **Animate from the anchor side** (small scale + translate, ≤ 200 ms).
4. **Restore focus** to the trigger on close.

## Pattern (native `popover`)

```html
<button popovertarget="filters" class="rounded-full bg-surface-secondary px-4 py-2 dark:bg-surface-secondary-dark">
  Filters
</button>

<div id="filters" popover anchor="filters"
     class="rounded-2xl bg-surface-primary p-3 shadow-lg ring-1 ring-separator/40 dark:bg-surface-primary-dark">
  <label class="flex items-center gap-2 py-1.5"><input type="checkbox"> Unread</label>
  <label class="flex items-center gap-2 py-1.5"><input type="checkbox"> Starred</label>
  <label class="flex items-center gap-2 py-1.5"><input type="checkbox"> Archived</label>
</div>
```

## Checklist

- [ ] Anchored to the trigger.
- [ ] Light-dismiss (click outside, Escape, focus out).
- [ ] Focus restored to trigger.
- [ ] Content short; no scroll.
- [ ] Animate ≤ 200 ms; reduced motion honored.
