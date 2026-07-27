# Inputs — Touch

## When to consult this file

- Mobile and tablet surfaces
- Gesture-driven interactions (swipe, pinch, long-press)

## Core principles

- **44 × 44 px minimum target.** Smaller is unusable for many fingers.
- **8 px minimum gap** between adjacent tap targets.
- **Long-press = right-click**, treat them symmetrically.
- **Don't override system gestures** (edge swipe, pinch-to-zoom) without strong reason.
- **Pointer Events API** unifies mouse + touch + pen.

## Concrete rules

1. Use Pointer Events (`pointerdown`, `pointermove`, `pointerup`) instead of `touchstart` + `mousedown`.
2. **Disable double-tap zoom** on interactive controls with `touch-action: manipulation;` (Tailwind: `touch-manipulation`).
3. **Allow panning** on lists and scrollers: `touch-action: pan-y;`.
4. **Long-press**: `pointerdown` + 500 ms timer; cancel on `pointermove` beyond ~10 px.
5. **No tooltip-on-hover** as the only way to discover info; touch has no hover.

## Pattern — long press

```js
function onLongPress(el, fn) {
  let t;
  el.addEventListener('pointerdown', () => { t = setTimeout(fn, 500); });
  ['pointerup','pointercancel','pointermove'].forEach(e => el.addEventListener(e, () => clearTimeout(t)));
}
```

## Checklist

- [ ] 44 × 44 px targets.
- [ ] `touch-action` chosen explicitly.
- [ ] Pointer Events, not touch+mouse twin handlers.
- [ ] No info gated behind hover only.
