# Components — Sheets

## When to consult this file

- A modal that needs more than two buttons
- A form or list of choices that opens in context
- A "share" or "options" surface on mobile

## Core principles

- **Bottom-rising on mobile, centered on desktop.** A sheet anchors at the bottom on phone, centers on tablet/desktop.
- **Drag handle on mobile** (a 4 px tall, ~48 px wide pill at the top) signals dragability.
- **Scrollable body, sticky footer.** If content overflows, the body scrolls; the action footer stays pinned.
- **Dismissible by drag-down, backdrop click, and Escape.**
- **Match material to context.** Solid surface for content-rich sheets; translucent only for chrome-only sheets.

## Concrete rules

1. **Use `<dialog>` with `.showModal()`**: focus trap and Escape are free.
2. **Translate-y enter/exit** with `cubic-bezier(.32,.72,0,1)` for ~300 ms.
3. **Safe-area padding bottom** for home-indicator on mobile (`pb-[max(env(safe-area-inset-bottom),16px)]`).
4. **No nested modals.** If a sheet needs to open another, redesign the flow.

## Pattern

```html
<dialog id="share" class="m-0 mt-auto w-full max-w-none translate-y-full rounded-t-2xl bg-surface-primary p-5
                           backdrop:bg-black/40 transition-transform duration-300 ease-native
                           open:translate-y-0 motion-reduce:transition-none
                           sm:m-auto sm:max-w-md sm:translate-y-0 sm:rounded-2xl
                           dark:bg-surface-primary-dark">
  <div class="mx-auto mb-3 h-1 w-12 rounded-full bg-label-tertiary/40 sm:hidden" aria-hidden="true"></div>
  <h2 class="text-[17px] font-semibold">Share</h2>
  <ul class="mt-3 divide-y divide-separator/40">
    <li><button class="w-full py-3 text-left">Copy link</button></li>
    <li><button class="w-full py-3 text-left">Email</button></li>
    <li><button class="w-full py-3 text-left">Export PDF</button></li>
  </ul>
</dialog>
```

## Checklist

- [ ] Bottom on mobile, centered on desktop.
- [ ] Drag handle visible on mobile.
- [ ] Safe-area inset respected at the bottom.
- [ ] Escape / backdrop / drag-down all close.
- [ ] No nested modal.
