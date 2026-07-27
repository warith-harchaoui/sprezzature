# Foundations — Accessibility


## When to consult this file

- Building any interactive component
- Reviewing a page for shippability
- Resolving low-vision, motor, or cognitive concerns

## Core principles

- **Treat accessibility as a baseline.** Every component you ship must work for VoiceOver, keyboard, and assistive switches.
- **Match the system's accessibility primitives.** Use real semantic HTML (`<button>`, `<a>`, `<label>`, `<input>`) so platform AT just works. Only reach for `role=` if no native element fits.
- **Respect user preferences.** Honor `prefers-reduced-motion`, `prefers-color-scheme`, `prefers-contrast`, `prefers-reduced-transparency`, dynamic type, and reduced data.
- **Names, roles, values, states.** Every interactive element must expose all four to assistive tech.
- **Don't trap focus** except inside modal contexts (sheet, alert, popover). Always provide an escape.

## Concrete rules — every component

1. **Use semantic HTML first.** `<button>` not `<div onclick>`. `<a href>` not `<span onclick>`.
2. **Visible focus ring.** Tailwind: `focus-visible:ring-2 focus-visible:ring-brand-blue focus-visible:ring-offset-2`. Never `outline-none` without a replacement.
3. **Minimum target size 44×44 px** for any tappable control. Tailwind: `min-h-11 min-w-11` (with `px-4` padding to give label room).
4. **Label every input.** `<label for>` or `aria-label`. Placeholder is not a label.
5. **Announce dynamic state changes** with `aria-live="polite"` for status, `assertive` for errors, plus `role="status"` / `role="alert"`.
6. **Keyboard parity.** Every mouse interaction has a keyboard equivalent. Modal close on `Escape`. Menu close on `Escape`. Tab order matches visual order.
7. **Color contrast.** Body text ≥ 4.5:1, UI/large text ≥ 3:1. Test in both themes.
8. **Don't use color alone** to convey state. Pair with icon, text, or shape.
9. **Reduced motion.** Wrap large animations in `@media (prefers-reduced-motion: no-preference)`. Default to instant transitions otherwise.
10. **Don't auto-play audio or video.** Provide controls; honor mute state across sessions.
11. **Skip links.** Every page has a "Skip to main content" link as the first focusable element.

## Patterns to remember

### Visible focus ring (Tailwind)

```html
<button class="rounded-full bg-brand-blue px-5 py-3 font-medium text-white
               focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue
               focus-visible:ring-offset-2 focus-visible:ring-offset-white
               dark:focus-visible:ring-offset-black">
  Continue
</button>
```

### Reduced motion (Tailwind)

```html
<div class="transition-transform duration-300 motion-reduce:transition-none motion-reduce:transform-none">
  …
</div>
```

### Live region for status

```html
<p id="status" class="sr-only" role="status" aria-live="polite"></p>
<script type="module">
  document.getElementById('status').textContent = 'Saved';
</script>
```

### Screen-reader-only utility

```html
<span class="sr-only">Loading…</span>
```

Tailwind already provides `sr-only` and `not-sr-only`.

### Keyboard handling for dialogs

```js
function openDialog(dialog) {
  const previouslyFocused = document.activeElement;
  dialog.showModal();
  const onKey = (e) => { if (e.key === 'Escape') closeDialog(dialog, previouslyFocused); };
  dialog.addEventListener('keydown', onKey);
  dialog._cleanup = () => dialog.removeEventListener('keydown', onKey);
}
function closeDialog(dialog, restoreTo) {
  dialog._cleanup?.();
  dialog.close();
  restoreTo?.focus();
}
```

## Checklist before shipping

- [ ] Page passes axe / WAVE with no critical issues.
- [ ] Tab through the whole page: order matches the visual order.
- [ ] Every interactive element has a visible focus ring.
- [ ] `prefers-reduced-motion` honored.
- [ ] Live regions announce dynamic changes.
- [ ] Form errors are announced and tied to the input with `aria-describedby`.
- [ ] All inputs have visible labels.
- [ ] Tested at 200% zoom and with VoiceOver.
- [ ] Color contrast verified in light AND dark mode.
