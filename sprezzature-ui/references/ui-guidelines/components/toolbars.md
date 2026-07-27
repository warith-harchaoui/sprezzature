# Components — Toolbars

## When to consult this file

- A row of contextual actions inside a view (text editor, drawing app, file browser)
- Not the global nav (that's a navigation bar or tab bar)

## Core principles

- **Toolbars are contextual**, scoped to the current view.
- **Icon-first**, label optional. Hover/long-press exposes a tooltip with the label.
- **Group related actions** with separators.
- **Top OR bottom**, not both.

## Concrete rules

1. Use `<div role="toolbar">` with `aria-label`.
2. Each control is a real `<button>` with `aria-label`.
3. Min target 44 px; gap 2–3 px between controls.
4. Use the same icon family across the toolbar.
5. Don't combine destructive and primary in the same toolbar without a separator.

## Pattern

```html
<div role="toolbar" aria-label="Formatting" class="flex items-center gap-1 rounded-2xl bg-surface-secondary p-1 dark:bg-surface-secondary-dark">
  <button aria-label="Bold"   class="grid h-9 w-9 place-items-center rounded-lg hover:bg-surface-tertiary dark:hover:bg-surface-tertiary-dark"><b>B</b></button>
  <button aria-label="Italic" class="grid h-9 w-9 place-items-center rounded-lg hover:bg-surface-tertiary dark:hover:bg-surface-tertiary-dark"><i>I</i></button>
  <button aria-label="Underline" class="grid h-9 w-9 place-items-center rounded-lg hover:bg-surface-tertiary dark:hover:bg-surface-tertiary-dark"><u>U</u></button>
  <span class="mx-1 h-5 w-px bg-separator" aria-hidden="true"></span>
  <button aria-label="Link" class="grid h-9 w-9 place-items-center rounded-lg hover:bg-surface-tertiary dark:hover:bg-surface-tertiary-dark">
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1M14 11a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1"/></svg>
  </button>
</div>
```

## Checklist

- [ ] `role="toolbar"` with `aria-label`.
- [ ] All controls have `aria-label`.
- [ ] Single icon family.
- [ ] Groups separated by hairline.
