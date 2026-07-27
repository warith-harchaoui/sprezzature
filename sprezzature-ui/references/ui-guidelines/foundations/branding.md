# Foundations — Branding

## When to consult this file

- Placing logos, wordmarks, brand color in product UI
- Balancing brand identity with platform-native feel

## Core principles

- **Express brand through experience.** Consistent voice, motion, and visual hierarchy do more than a giant logo on every screen.
- **Subtle and consistent.** Repeat brand cues (a tint, a typeface pairing, a corner radius, a motion curve) instead of stamping the logo everywhere.
- **Don't restyle native controls in brand color.** Keep system-feeling controls (alerts, sheets, menus) neutral so users trust them.
- **No splash screens beyond a brief launch.** Don't gate the user behind branded interstitials.
- **Respect the user's content.** Brand should frame content, never compete with it.
- **Don't use third-party trademarks** (logos, product names) as part of your brand expression.

## Concrete rules — web context

1. **Logo placement**: top-left on desktop, top-center or top-left on mobile. Never in the content body.
2. **Logo size**: 24–40 px tall in the chrome. Larger only on the marketing landing surface.
3. **Wordmark vs. logomark**: use the wordmark in the chrome (more legible), keep the standalone mark for favicons / very tight spots.
4. **Brand tint**: one accent color (`bg-brand-blue`) applied to primary CTAs, links, focus rings. Secondary colors stay reserved for semantics.
5. **Brand voice**: see `foundations/writing.md`. Voice carries the brand.

## Pattern

```html
<header class="sticky top-0 z-30 flex items-center gap-3 border-b border-separator/60 bg-surface-primary/80 px-4 py-3 backdrop-blur dark:bg-surface-primary-dark/80">
  <a href="/" class="flex items-center gap-2 font-semibold text-label-primary dark:text-label-primary-dark">
    <img src="/logo.svg" alt="" width="24" height="24" class="rounded" />
    <span>Sprezzature</span>
  </a>
  <nav class="ml-auto flex items-center gap-1">
    <a href="/docs" class="rounded-lg px-3 py-2 text-sm text-label-secondary hover:bg-surface-secondary">Docs</a>
    <a href="/login" class="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:opacity-90">Sign in</a>
  </nav>
</header>
```

## Checklist

- [ ] Brand expressed through tint, type, motion, not just logo.
- [ ] Logo is unobtrusive in the chrome, never in body content.
- [ ] System-feeling components remain neutral.
- [ ] No persistent splash, popup, or "powered by" overlay.
- [ ] Brand color reserved for one role (primary action / link / focus).
