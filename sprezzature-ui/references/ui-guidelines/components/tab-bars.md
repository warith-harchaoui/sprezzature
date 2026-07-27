# Components — Tab Bars

## When to consult this file

- Bottom navigation on mobile-feeling apps
- Top-level destinations (3–5)

## Core principles

- **3–5 tabs.** Fewer is a button row; more is a sidebar.
- **Same tabs across the entire app.** Tab bar is global, not contextual.
- **Each tab opens a sibling view**, not a modal.
- **Icon + label.** Labels stay visible; they carry accessibility and scan-ability.

## Concrete rules

1. **`<nav>` with `<ul>` of `<a>` items** — real navigation semantics.
2. **`aria-current="page"`** on the active tab.
3. **Min target 44 px**; equally-spaced columns.
4. **Sticky bottom with safe-area padding** on mobile (`pb-[max(env(safe-area-inset-bottom),8px)]`).
5. **Translucent material** (`backdrop-blur-ultra`) with a 1 px top border.
6. **No badge counts inside the label**; use a small dot or pill at top-right of the icon.

## Pattern

```html
<nav class="sticky bottom-0 z-30 border-t border-separator/40 bg-surface-primary/70 backdrop-blur-ultra
            pb-[max(env(safe-area-inset-bottom),8px)] pt-2 dark:bg-surface-primary-dark/70">
  <ul class="mx-auto grid max-w-md grid-cols-4 gap-1 px-2">
    <li>
      <a href="/" aria-current="page" class="grid place-items-center gap-1 rounded-lg py-1 text-[11px] text-brand-blue">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 12l9-9 9 9M5 10v10h14V10"/></svg>
        Home
      </a>
    </li>
    <!-- … -->
  </ul>
</nav>
```

## Checklist

- [ ] 3–5 tabs.
- [ ] `aria-current="page"` on active tab.
- [ ] Icon + label.
- [ ] Safe-area inset respected.
- [ ] `dark:` peer set.
