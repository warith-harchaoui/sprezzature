# Components — Navigation Bars

## When to consult this file

- The top chrome of a page or screen
- A view that needs a back action + title + trailing action

## Core principles

- **Title centered or leading.** Centered is more "app-like"; leading is more "doc-like".
- **One trailing action** (rarely two). Crowded nav bars confuse the user.
- **Sticky with translucent material** (`backdrop-blur`) so the user perceives content scrolling beneath.
- **Back button shows the previous view's name** when space allows; an icon-only chevron when not.

## Concrete rules

1. **Real `<header>` + `<nav>` semantics.**
2. **Min height 44 px**; with `safe-area-inset-top` padding on mobile installs.
3. **Translucent background** uses the "ultra" or "thin" material levels (see `foundations/materials.md`).
4. **1 px separator** at the bottom (`border-b border-separator/40`).
5. **Avoid hamburger menus** on desktop; use a real nav.

## Pattern

```html
<header class="sticky top-0 z-30 border-b border-separator/40
               bg-surface-primary/70 backdrop-blur-ultra
               pt-[max(env(safe-area-inset-top),0px)]
               dark:bg-surface-primary-dark/70">
  <div class="mx-auto flex w-full max-w-3xl items-center gap-2 px-2 py-3">
    <button class="grid h-11 w-11 place-items-center rounded-full text-brand-blue hover:bg-surface-secondary dark:hover:bg-surface-secondary-dark" aria-label="Back">
      <svg class="rtl:rotate-180" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>
    </button>
    <h1 class="flex-1 text-center text-[17px] font-semibold">Settings</h1>
    <button class="grid h-11 w-11 place-items-center rounded-full text-brand-blue hover:bg-surface-secondary dark:hover:bg-surface-secondary-dark" aria-label="Edit">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 113 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>
    </button>
  </div>
</header>
```

## Checklist

- [ ] Translucent background with `backdrop-blur` and `border-b separator`.
- [ ] At most one trailing action.
- [ ] Back button chevron mirrored in RTL.
- [ ] Safe-area inset respected on mobile.
- [ ] `dark:` peer set.
