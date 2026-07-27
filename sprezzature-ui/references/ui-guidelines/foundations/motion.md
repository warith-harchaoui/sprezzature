# Foundations — Motion

## When to consult this file

- Any element that moves, fades, or transforms
- Choosing transition durations, easings, springs

## Core principles

- Motion communicates causality: where something came from, where it goes.
- Keep transitions subtle. A 200 ms ease-out feels more native than a flashy 600 ms bounce.
- Spatial consistency: same origin, same destination. If a sheet rises from the bottom, it dismisses back down.
- Match material to motion: translucent elements blur and scale; solid elements slide or fade.
- Honor `prefers-reduced-motion`: replace large transitions with instant or near-instant changes. Don't just shorten duration; remove the translate/scale.
- Don't animate to signal an error. Use focus and copy. Motion is feedback, not the message.

## Default durations

| Use | Duration | Easing |
|---|---|---|
| Hover / press tint | 80–120 ms | `ease-out` |
| Small state change (toggle, switch) | 150–200 ms | `ease-out` |
| Reveal / dismiss (modal, sheet, popover) | 250–350 ms | `cubic-bezier(.32,.72,0,1)` |
| Page transition | 300–400 ms | `cubic-bezier(.4,0,.2,1)` |
| Continuous (loading) | infinite | linear or eased loop |

Avoid > 500 ms for any single interaction; it feels sluggish.

## Easing curves (Tailwind)

Add to `theme.extend.transitionTimingFunction`:

```js
transitionTimingFunction: {
  'native':       'cubic-bezier(0.32, 0.72, 0, 1)',
  'native-spring':'cubic-bezier(0.5, 1.6, 0.4, 0.7)',
  'standard':     'cubic-bezier(0.4, 0, 0.2, 1)',
}
```

Use as `ease-native`, `ease-native-spring`, `ease-standard`.

## Concrete rules

1. **CSS transition over JS animation** when possible — runs on the compositor, free perf.
2. **Animate `transform` and `opacity`**. Never animate `width`/`height` or `top`/`left` unless unavoidable.
3. **`will-change: transform`** sparingly on elements about to move; remove after.
4. **Reduced motion**: wrap any translate/scale animation in `motion-reduce:transition-none motion-reduce:transform-none`.
5. **Stagger** child entries by 20–40 ms; no more, no less.
6. **Loading**: prefer skeleton screens (≥ 300 ms) over spinners.

## Patterns

### Press feedback (Tailwind)

```html
<button class="transition-transform duration-100 ease-out active:scale-[0.97] motion-reduce:active:scale-100">
  Press me
</button>
```

### Sheet rise / dismiss (Tailwind + JS)

```html
<dialog id="sheet" class="bottom-0 m-0 w-full translate-y-full rounded-t-2xl bg-surface-primary p-5
                           backdrop:bg-black/40 transition-transform duration-300 ease-native
                           open:translate-y-0 motion-reduce:transition-none
                           dark:bg-surface-primary-dark">
  …
</dialog>
```

### Reduced motion guard (CSS)

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Checklist

- [ ] No interaction takes longer than 500 ms.
- [ ] Reduced motion fully removes translate/scale.
- [ ] Animations run on `transform`/`opacity` only.
- [ ] Same origin → same destination on dismiss.
- [ ] No looping animation outside loading/ambient contexts.
- [ ] Skeleton screens for waits ≥ 300 ms.
