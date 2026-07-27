# Inputs — Focus and Selection

## When to consult this file

- Focus rings, tab order, modal focus
- Text selection, item selection in lists

## Core principles

- **A visible focus ring on every focusable element.** Never `outline: none` without replacement.
- **Use `:focus-visible`** so mouse clicks don't show a ring unnecessarily, but keyboard users always do.
- **Focus stays within modal surfaces** while open; restores to trigger on close.
- **Selection styled** to match the brand tint without overwhelming text.

## Concrete rules

1. Base CSS:
   ```css
   *:focus { outline: none; }
   *:focus-visible {
     box-shadow: 0 0 0 2px var(--surface-primary), 0 0 0 4px #007AFF;
     border-radius: inherit;
   }
   ```
2. Tailwind utility: `focus-visible:ring-2 focus-visible:ring-brand-blue focus-visible:ring-offset-2 focus-visible:ring-offset-surface-primary dark:focus-visible:ring-offset-surface-primary-dark`.
3. **Skip link** as the first focusable element on every page: "Skip to main content" → `#main`.
4. **Initial focus** in a modal: the first interactive element, or the cancel button for destructive prompts.

## Selection

```css
::selection {
  background-color: rgba(0, 122, 255, 0.25); /* brand-blue at 25% */
  color: inherit;
}
html[data-color-scheme="dark"] ::selection {
  background-color: rgba(10, 132, 255, 0.35);
}
```

## Checklist

- [ ] `focus-visible` ring on every interactive element.
- [ ] Skip link first.
- [ ] Modal focus trap + restore.
- [ ] Selection styled to brand tint.
