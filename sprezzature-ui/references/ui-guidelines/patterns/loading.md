# Patterns — Loading

## When to consult this file

- Any wait between user action and result
- Network fetches, file processing, long computations

## Core principles

- **0–100 ms: no indicator.** Instant.
- **100–300 ms: nothing yet, but freeze hover/press feedback.**
- **300 ms – 2 s: skeleton screen.** Show the *shape* of what's coming.
- **2 s+: skeleton + label.** "Crunching numbers…", "Almost there…".
- **Unknown duration: indeterminate spinner.**
- **Never block the whole app** for one tile loading.

## Concrete rules

1. Skeletons match the shape of real content; don't show a generic "loading" pulse.
2. Animate skeletons subtly (opacity 0.6 → 1 over 1.5 s, `prefers-reduced-motion` removes the pulse).
3. Don't hide a button after pressing it; show its disabled state with a small spinner.
4. **Cancelable** for any wait > 5 s.
5. **Optimistic UI**: update the UI immediately, roll back on failure.

## Pattern — skeleton row

```html
<ul class="divide-y divide-separator/40">
  <li class="flex items-center gap-3 px-4 py-3">
    <span class="h-9 w-9 animate-pulse rounded-full bg-surface-secondary dark:bg-surface-secondary-dark motion-reduce:animate-none"></span>
    <span class="flex-1">
      <span class="block h-3 w-32 animate-pulse rounded bg-surface-secondary dark:bg-surface-secondary-dark motion-reduce:animate-none"></span>
      <span class="mt-2 block h-3 w-44 animate-pulse rounded bg-surface-secondary dark:bg-surface-secondary-dark motion-reduce:animate-none"></span>
    </span>
  </li>
</ul>
```

## Checklist

- [ ] Skeleton not spinner for content loads.
- [ ] Spinner for unknown-duration actions.
- [ ] Reduced-motion variant.
- [ ] Cancelable for waits > 5 s.
- [ ] Optimistic UI where safe.
