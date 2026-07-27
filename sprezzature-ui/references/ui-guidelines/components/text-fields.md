# Components — Text Fields

## When to consult this file

- Any `<input>`, `<textarea>`, or contenteditable surface
- Email / password / phone / search / number inputs

## Core principles

- **Labels above the field, always visible.** Placeholder is not a label.
- **`autocomplete` and `inputmode` are mandatory**: they unlock device keyboards and saved data.
- **`dir="auto"`** on user-content fields so RTL strings render correctly.
- **Error inline, below the field**, tied with `aria-describedby`.
- **One input style across the app.** Mixing pills and rectangles confuses.

## Concrete rules

1. **`<label for>`** wraps or precedes the input.
2. **Required indicator**: a visible "Required" word or `*` outside the label, never relying on the asterisk alone (also use `required`).
3. **44 px min height** with comfortable padding (`py-2.5`).
4. **Visible focus** via `focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/30`.
5. **Error state**: red border + red helper text + `aria-invalid="true"` + `role="alert"` on the helper.
6. **Disabled state**: `disabled:bg-surface-tertiary disabled:cursor-not-allowed disabled:text-label-tertiary`.

## Pattern

See `assets/components/form-field.html` for text, error, textarea, select, toggle.

## Keyboard / autocomplete map

| Field | type | inputmode | autocomplete |
|---|---|---|---|
| Email | `email` | `email` | `email` |
| Password | `password` | — | `current-password` / `new-password` |
| Phone | `tel` | `tel` | `tel` |
| OTP | `text` | `numeric` | `one-time-code` |
| Search | `search` | `search` | `off` |
| Postal code | `text` | `numeric` | `postal-code` |
| URL | `url` | `url` | `url` |

## Checklist

- [ ] Visible label above the field.
- [ ] `type`, `inputmode`, `autocomplete` set.
- [ ] `dir="auto"` on user content fields.
- [ ] 44 px min height.
- [ ] Error tied with `aria-describedby`, `aria-invalid`, `role="alert"`.
- [ ] `dark:` peer set.
