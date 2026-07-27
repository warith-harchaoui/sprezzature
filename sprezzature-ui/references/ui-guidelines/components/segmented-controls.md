# Components — Segmented Controls

## When to consult this file

- Choosing one option from 2–4 mutually-exclusive choices
- A view-mode switch (list / grid), filter (all / unread), sort (newest / oldest)

## Core principles

- **2–4 segments only.** 5+ becomes a select.
- **Equal width** for each segment.
- **One selected at a time.** Behaviorally a radio group.
- **Immediate effect**: no save.

## Concrete rules

1. Use a `<fieldset role="radiogroup">` with hidden radios + visible labels styled as pill.
2. Selected segment uses `bg-surface-primary` (rises above the track), unselected stays flat.
3. Min target 44 px.

## Pattern

```html
<fieldset role="radiogroup" aria-label="View" class="inline-flex w-full max-w-xs rounded-full bg-surface-secondary p-1 dark:bg-surface-secondary-dark">
  <label class="flex-1">
    <input type="radio" name="view" value="list" class="peer sr-only" checked>
    <span class="block cursor-pointer rounded-full px-3 py-1.5 text-center text-[15px] font-medium
                  peer-checked:bg-surface-primary peer-checked:shadow dark:peer-checked:bg-surface-primary-dark">
      List
    </span>
  </label>
  <label class="flex-1">
    <input type="radio" name="view" value="grid" class="peer sr-only">
    <span class="block cursor-pointer rounded-full px-3 py-1.5 text-center text-[15px] font-medium
                  peer-checked:bg-surface-primary peer-checked:shadow dark:peer-checked:bg-surface-primary-dark">
      Grid
    </span>
  </label>
</fieldset>
```

## Checklist

- [ ] 2–4 segments.
- [ ] `role="radiogroup"`.
- [ ] Min 44 px.
- [ ] Visible focus ring on the focused segment.
