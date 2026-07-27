# Components — Toggles (Switches)

## When to consult this file

- A binary on/off state that takes effect immediately
- Settings, preferences, feature flags

## Core principles

- **A toggle changes state immediately**, no save button required. If a save step is needed, use a checkbox in a form.
- **Use a switch shape, not a checkbox.** Visually it's a pill with a circle inside.
- **Color in the "on" state**: green for "system-feeling" semantics, brand-blue for accent.
- **Label on the leading side** for left-to-right reading.

## Concrete rules

1. Use `<input type="checkbox" role="switch">`: semantic and accessible.
2. Visual styling on the sibling element via `peer-checked:`.
3. Min target 44 px overall, even though the visual switch is 28–32 px tall.
4. **Disabled** uses `disabled:opacity-50 disabled:cursor-not-allowed`.

## Pattern

```html
<label class="flex items-center justify-between gap-3 py-2">
  <span class="text-[17px]">Email me about new releases</span>
  <input type="checkbox" role="switch" checked class="peer sr-only">
  <span aria-hidden="true"
        class="relative inline-block h-7 w-12 flex-none rounded-full bg-label-tertiary/40
               transition-colors peer-checked:bg-brand-green
               peer-focus-visible:ring-2 peer-focus-visible:ring-brand-blue peer-focus-visible:ring-offset-2
               dark:peer-focus-visible:ring-offset-surface-primary-dark">
    <span class="absolute left-0.5 top-0.5 h-6 w-6 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5"></span>
  </span>
</label>
```

## Checklist

- [ ] `role="switch"` on the input.
- [ ] Visible focus ring on the visual switch.
- [ ] 44 px effective tap target.
- [ ] Reduced-motion: keep the color change, drop the slide if `motion-reduce:translate-x-0`.
