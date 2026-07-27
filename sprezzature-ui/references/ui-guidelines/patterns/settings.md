# Patterns — Settings

## When to consult this file

- A "Settings" or "Preferences" screen
- Account, profile, notification preferences
- Feature flags exposed to users

## Core principles

- **Group by user mental model**, not by code module.
- **One column on mobile, optional master/detail on desktop.**
- **Defaults are settings.** Always have a sensible default; let the user reset.
- **Immediate apply**, no "Save" button, for most toggles.
- **Destructive settings (Delete account)** at the bottom, in their own section, with a confirmation.

## Concrete rules

1. Real `<ul>` of grouped rows with `divide-y divide-separator/40`.
2. Section headers `text-[13px] uppercase tracking-wider text-label-secondary mb-2 mt-6 ps-4`.
3. Row internals: `flex items-center justify-between gap-3 min-h-11 px-4`.
4. Use chevron icons (rotated in RTL) to indicate drill-down rows.
5. Toggle for binary; select for ≤ 5 enum; sheet picker for > 5.

## Pattern

```html
<main class="mx-auto w-full max-w-2xl px-2 py-6 sm:px-4">
  <h1 class="sr-only">Settings</h1>

  <h2 class="ps-4 mt-2 text-[13px] uppercase tracking-wider text-label-secondary dark:text-label-secondary-dark">Account</h2>
  <ul class="mt-1 rounded-2xl bg-surface-secondary dark:bg-surface-secondary-dark divide-y divide-separator/40">
    <li><a href="/me/profile"   class="flex min-h-11 items-center justify-between gap-3 px-4 py-3"><span>Profile</span><svg class="rtl:rotate-180 h-5 w-5 text-label-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg></a></li>
    <li><a href="/me/password"  class="flex min-h-11 items-center justify-between gap-3 px-4 py-3"><span>Password</span><svg class="rtl:rotate-180 h-5 w-5 text-label-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg></a></li>
  </ul>

  <h2 class="ps-4 mt-6 text-[13px] uppercase tracking-wider text-label-secondary dark:text-label-secondary-dark">Notifications</h2>
  <ul class="mt-1 rounded-2xl bg-surface-secondary dark:bg-surface-secondary-dark divide-y divide-separator/40">
    <li class="flex min-h-11 items-center justify-between gap-3 px-4 py-3">
      <span>Email me about new releases</span>
      <input type="checkbox" role="switch" class="peer sr-only" checked>
      <span aria-hidden="true" class="relative inline-block h-7 w-12 rounded-full bg-label-tertiary/40 transition-colors peer-checked:bg-brand-green">
        <span class="absolute left-0.5 top-0.5 h-6 w-6 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5"></span>
      </span>
    </li>
  </ul>

  <h2 class="ps-4 mt-6 text-[13px] uppercase tracking-wider text-brand-red">Danger zone</h2>
  <ul class="mt-1 rounded-2xl bg-surface-secondary dark:bg-surface-secondary-dark">
    <li><button class="flex min-h-11 w-full items-center px-4 py-3 text-brand-red">Delete account</button></li>
  </ul>
</main>
```

## Checklist

- [ ] Grouped by mental model.
- [ ] Toggles apply immediately.
- [ ] Drill-down rows use chevron (mirrored in RTL).
- [ ] Destructive in its own labeled section.
