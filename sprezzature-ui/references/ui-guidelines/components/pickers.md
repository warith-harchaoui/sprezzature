# Components — Pickers

## When to consult this file

- A date / time / color / value picker
- A "choose from a long list" surface

## Core principles

- **Pickers are scoped to a single value.** Multi-select belongs in a list with checkboxes.
- **Prefer native HTML pickers** for date / time / color: they integrate with the device's input method.
- **Confirm + cancel.** A picker tied to a form should preview the value until the user confirms (Done) or backs out (Cancel).

## Concrete rules

1. **`<input type="date|time|datetime-local|month|week|color">`** when usable: accessible and free.
2. Wheel-style pickers (scrollable columns) only for "feel-native" mobile cases; otherwise stick to the platform input.
3. When custom, render inside a sheet (`components/sheets.md`) with sticky Done/Cancel.
4. **Format display in the user's locale** with `Intl.DateTimeFormat`.

## Pattern — native date input

```html
<label class="block">
  <span class="block text-[15px] font-medium">Pick a date</span>
  <input type="date" name="when"
         class="mt-1 block w-full rounded-xl border border-separator bg-surface-secondary px-3 py-2.5 text-[17px]
                focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30
                dark:bg-surface-secondary-dark">
</label>
```

## Pattern — custom picker inside a sheet

```html
<dialog id="picker" class="m-auto w-full max-w-sm rounded-2xl bg-surface-primary p-5 backdrop:bg-black/40 dark:bg-surface-primary-dark">
  <h2 class="text-[17px] font-semibold">Choose a color</h2>
  <div role="radiogroup" aria-label="Color" class="mt-4 grid grid-cols-6 gap-2">
    <!-- buttons styled as color swatches -->
  </div>
  <div class="mt-5 flex justify-end gap-2">
    <button value="cancel" class="min-h-11 rounded-xl bg-surface-secondary px-4 dark:bg-surface-secondary-dark">Cancel</button>
    <button value="done"   class="min-h-11 rounded-xl bg-brand-blue px-4 font-semibold text-white">Done</button>
  </div>
</dialog>
```

## Checklist

- [ ] Native HTML picker first.
- [ ] Done / Cancel actions in custom pickers.
- [ ] Value formatted via `Intl` in the user's locale.
