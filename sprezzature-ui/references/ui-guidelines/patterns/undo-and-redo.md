# Patterns — Undo and Redo

## When to consult this file

- An editor (text, image, drawing)
- Any destructive operation that has a reversible path

## Core principles

- **Offer undo by default.** Most destructive actions should leave a quick undo path open.
- **Show a confirmation only when undo isn't possible.** "Move to Trash" + undo banner ≫ a confirm dialog.
- **Keyboard shortcuts**: `⌘Z` undo and `⌘⇧Z` redo where Command is the host's primary modifier; `Ctrl+Z` / `Ctrl+Y` everywhere else. Render the right glyph (see `inputs/keyboards.md`).
- **History stack scope**: per-document, not global.

## Concrete rules

1. After deleting / archiving, show a toast banner: "Item moved. Undo." with a 5–8 s window.
2. Multi-step undo: every user-visible action is a discrete history step.
3. Disable Undo/Redo buttons when the stack is empty.
4. Persist history across page reloads only if the editor is document-scoped.

## Pattern — undo banner

```html
<div id="undo" role="status" aria-live="polite"
     class="pointer-events-none fixed inset-x-0 bottom-6 z-40 mx-auto flex max-w-sm justify-center px-4">
  <div class="pointer-events-auto flex items-center gap-3 rounded-full bg-label-primary px-4 py-2 text-[15px] text-surface-primary dark:bg-label-primary-dark dark:text-surface-primary-dark">
    <span>Item moved.</span>
    <button id="undo-btn" class="font-semibold text-brand-blue">Undo</button>
  </div>
</div>
```

## Checklist

- [ ] Toast offers undo instead of pre-confirming.
- [ ] `⌘Z` / `Ctrl+Z` work (whichever matches the host's primary modifier).
- [ ] Stack scope makes sense.
- [ ] Disabled state for Undo/Redo when empty.
