# Components — Progress Indicators

## When to consult this file

- A wait > 300 ms
- A long-running operation with known or unknown duration

## Core principles

- **Determinate** (known %): use a bar with `aria-valuenow`.
- **Indeterminate** (unknown duration): use a small spinner, never a giant one.
- **Prefer skeleton screens** for content loads ≥ 300 ms; spinners only for one-off operations.
- **Don't combine indeterminate + determinate** in the same surface.

## Concrete rules

1. Determinate: `<progress max="100" value="50">`, native and accessible.
2. Indeterminate spinner: 20–28 px diameter, animated `transform: rotate`, paired with `aria-busy="true"` on the container.
3. **Respect reduced motion**: replace spin with a subtle pulse if `motion-reduce`.
4. **Announce completion** via a live region.

## Pattern — determinate

```html
<label class="block">
  <span class="text-[15px]">Uploading…</span>
  <progress max="100" value="42" class="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface-secondary [&::-webkit-progress-bar]:bg-surface-secondary [&::-webkit-progress-value]:bg-brand-blue dark:bg-surface-secondary-dark">42 %</progress>
</label>
```

## Pattern — indeterminate spinner

```html
<button aria-busy="true" disabled
        class="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand-blue px-5 py-3 text-white opacity-90">
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin motion-reduce:animate-pulse" aria-hidden="true">
    <path d="M21 12a9 9 0 11-6.219-8.56"/>
  </svg>
  Working…
</button>
```

## Checklist

- [ ] Determinate when % is known.
- [ ] Skeleton screen instead of spinner for ≥ 300 ms content loads.
- [ ] Reduced-motion variant present.
- [ ] Completion announced.
