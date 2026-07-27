# Patterns — Onboarding

## When to consult this file

- First-run experience
- Introducing a major new feature
- Teaching a non-obvious gesture

## Core principles

- **One idea per screen.** Don't try to teach everything at once.
- **Skippable.** Always offer "Skip" or "I'll explore on my own".
- **≤ 8-word headline.** If you need more, redesign the feature, not the onboarding.
- **No interstitial gates.** Don't block usage on signing up if browsing is possible.
- **Prefer in-context hints** over upfront walkthroughs.

## Concrete rules

1. ≤ 4 screens total. 1–2 is ideal.
2. Skip button always present, top-trailing.
3. Progress dots at the bottom; current dot highlighted.
4. Last screen has a clear primary CTA, never just "Next" again.
5. Don't ask for permissions (notifications, location) in onboarding; ask when the feature needs them.

## Pattern (single screen)

```html
<section class="grid min-h-dvh place-items-center px-6 text-center">
  <div class="w-full max-w-sm">
    <img src="/welcome.svg" alt="" class="mx-auto h-40 w-40">
    <h1 class="mt-6 text-3xl font-bold tracking-tight">Stay in sync</h1>
    <p class="mt-2 text-[17px] text-label-secondary dark:text-label-secondary-dark">
      Everything you save shows up across your devices in seconds.
    </p>
    <div class="mt-8 flex items-center justify-between">
      <button class="px-3 py-2 text-brand-blue font-medium">Skip</button>
      <button class="min-h-11 rounded-full bg-brand-blue px-5 font-semibold text-white">Continue</button>
    </div>
    <ul class="mt-6 flex justify-center gap-1.5" aria-hidden="true">
      <li class="h-1.5 w-6 rounded-full bg-brand-blue"></li>
      <li class="h-1.5 w-1.5 rounded-full bg-label-tertiary/50"></li>
      <li class="h-1.5 w-1.5 rounded-full bg-label-tertiary/50"></li>
    </ul>
  </div>
</section>
```

## Checklist

- [ ] ≤ 4 screens.
- [ ] Skip always visible.
- [ ] No permission asks during onboarding.
- [ ] Last screen CTA clearly leads into the app.
