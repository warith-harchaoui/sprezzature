# Foundations — Inclusion


## When to consult this file

- Writing UI copy, error messages, onboarding
- Choosing imagery, names, defaults, and example data
- Designing forms (gender, names, addresses)

## Core principles

- **Design for the breadth of human experience.** Defaults must work for someone unlike the designer.
- **Language matters.** Use clear, neutral, respectful words. Avoid metaphors that don't translate or that exclude.
- **Names, identities, addresses are diverse.** Don't require structures that exclude valid users (e.g. one given + one family name).
- **Show diverse, authentic representation** in imagery and example content, not stock tokens.
- **Don't ask for what you don't need.** Every data field is a potential exclusion vector.
- **Localize beyond translation.** Dates, numbers, names, address formats, currency, RTL — all change per locale.
- **Prefer plain language.** Aim for ~grade-8 reading level. Avoid jargon, acronyms, idioms.

## Concrete rules — web

1. **Single `<input name="name">` field** for full name (not first/last) unless you genuinely need them separated; let the user type what they want.
2. **Optional pronoun field** with free-text input, not a fixed select.
3. **Address forms**: let users skip postal code, state, etc. when irrelevant for their region. Use `autocomplete` attributes generously.
4. **`lang` attribute** on `<html>` and on any inline content in a different language.
5. **`dir="auto"`** on user-generated content fields so RTL strings render correctly.
6. **Don't gender greetings** ("Hi $NAME" not "Welcome, Mr/Ms $NAME").
7. **Skin-tone-respecting emojis and avatars** — never assume a default skin tone in seeded content.
8. **Error copy is supportive**, not accusatory. "We couldn't find that account" beats "Invalid email."
9. **No timeouts on actions a person might need to think about** (password reset, important confirmations).
10. **Provide alt text and captions** for everyone, not just screen-reader users.

## Patterns

### Inclusive name + pronoun form

```html
<div class="space-y-3">
  <label class="block">
    <span class="text-sm font-medium text-label-primary dark:text-label-primary-dark">Name</span>
    <input name="name" autocomplete="name" required dir="auto"
           class="mt-1 w-full rounded-xl border border-separator bg-surface-secondary px-3 py-2.5 text-base text-label-primary
                  placeholder:text-label-tertiary focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30
                  dark:bg-surface-secondary-dark dark:text-label-primary-dark" />
  </label>
  <label class="block">
    <span class="text-sm font-medium text-label-primary dark:text-label-primary-dark">Pronouns <span class="text-label-tertiary">(optional)</span></span>
    <input name="pronouns" placeholder="e.g. she/her, they/them, han/honom" dir="auto"
           class="mt-1 w-full rounded-xl border border-separator bg-surface-secondary px-3 py-2.5 text-base text-label-primary
                  placeholder:text-label-tertiary focus:border-brand-blue focus:outline-none focus:ring-2 focus:ring-brand-blue/30
                  dark:bg-surface-secondary-dark dark:text-label-primary-dark" />
  </label>
</div>
```

### Localized number / date — Intl

```js
const fmt = (n, locale = navigator.language) =>
  new Intl.NumberFormat(locale).format(n);

const dateFmt = (d, locale = navigator.language) =>
  new Intl.DateTimeFormat(locale, { dateStyle: 'medium' }).format(d);
```

## Checklist

- [ ] No forced first/last name split.
- [ ] No fixed-select gender unless legally required.
- [ ] All `<input>` fields use `autocomplete` and `dir="auto"`.
- [ ] Error copy is supportive, not accusatory.
- [ ] Imagery shows diverse, authentic people.
- [ ] `lang` set; RTL works; `Intl` used for dates and numbers.
- [ ] No timeouts on consequential decisions.
