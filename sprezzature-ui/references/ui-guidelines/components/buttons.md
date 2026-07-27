# Components — Buttons

## When to consult this file

- Any clickable action, anywhere
- Deciding primary vs. secondary vs. tertiary vs. destructive
- Sizing, spacing, and state design

## Core principles

- **A button performs an action.** A link goes somewhere. Use `<a href>` for navigation, `<button>` for actions.
- **One primary action per surface.** Multiple primary buttons compete for attention; pick one.
- **Verb-first labels.** "Send message" beats "Submit". Name the consequence; never use "OK" on consequential actions.
- **Predictable visual order**: dismiss/cancel on the left (start), confirm/primary on the right (end). In RTL, mirror automatically with logical properties.
- **Destructive buttons name the consequence**: "Delete account", not "Yes".

## Variants

| Variant | Use | Tailwind |
|---|---|---|
| Primary | Single main action | `bg-brand-blue text-white rounded-full px-5 py-3 font-semibold` |
| Secondary | Alternate action | `bg-surface-secondary text-label-primary rounded-full px-5 py-3 font-medium` |
| Tertiary (text) | Low-emphasis action | `text-brand-blue px-3 py-2 font-medium hover:underline` |
| Destructive | Removes data | `bg-brand-red text-white rounded-full px-5 py-3 font-semibold` |
| Icon-only | Tight chrome | `grid h-11 w-11 place-items-center rounded-full` + `aria-label` |

## Concrete rules

1. **Real `<button>`** — never `<div role="button">`.
2. **Min hit area 44×44 px** (`min-h-11` with padding to give label space).
3. **Visible focus ring** with `focus-visible:ring-2 focus-visible:ring-offset-2`.
4. **Press feedback** via `active:scale-[0.97] motion-reduce:active:scale-100`.
5. **Disabled state** uses `disabled:opacity-50 disabled:pointer-events-none`; never `pointer-events-none` alone (no focus).
6. **Loading state** disables the button and inserts a spinner; announce via `aria-busy="true"`.
7. **Icon spacing** uses `gap-2` between icon and label.

## Patterns

See `assets/components/button.html` for primary, secondary, tertiary, destructive, icon-only, and loading.

## Checklist

- [ ] Verb-first label.
- [ ] One primary per surface.
- [ ] `min-h-11`, visible focus ring.
- [ ] `active:scale-[0.97]` with `motion-reduce:` guard.
- [ ] `dark:` peer set.
- [ ] Destructive named the consequence.
