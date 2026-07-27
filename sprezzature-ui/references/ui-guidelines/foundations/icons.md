# Foundations — In-app icons

> For launcher/favicon, see `app-icons.md`.

## When to consult this file

- Picking or designing UI icons (toolbar, tab bar, inline content)
- Building an icon set for buttons, list rows, menus

## Core principles

- **Every icon must add comprehension.** If it duplicates a label without aiding scan-ability, remove it.
- **Use a consistent visual language.** One stroke weight, one corner radius family, one filled-vs-outlined convention across the app.
- **Use canonical metaphors.** Heart for favorite, gear for settings, magnifier for search. Don't invent.
- **Pair icons with labels** for primary navigation and actions. Icon-only is acceptable only when the metaphor is universally recognized (close, back, search) AND alternate text is provided.
- **Optical sizing, not pixel sizing.** Adjust visual weight so icons feel balanced at their target size.
- **Two themes.** Each icon must read on light AND dark backgrounds.

## Concrete rules — web

1. **Prefer SVG** over icon fonts (better a11y, sharper at any DPI).
2. **One sprite or inline `<svg>` per icon** — no PNG icons except in legacy fallbacks.
3. **Square viewBox** (`viewBox="0 0 24 24"` is the conventional baseline).
4. **`currentColor`** for the stroke/fill so the icon inherits text color and works in both themes.
5. **`aria-hidden="true"`** when the icon is decorative next to a text label.
6. **`role="img"` and `<title>`** when the icon stands alone (no text label).
7. **Sizes**: 16 / 20 / 24 / 32 — pick one scale and stick to it. Inline next to text: match cap-height (~16 px next to 14 px body).
8. **Stroke weight**: 1.5–2 px at 24 px viewBox is the recommended default.

## Recommended open icon sets (web-safe)

- **Lucide** (<https://lucide.dev>) — MIT-licensed, broad coverage, clean line weight. Default for this skill.
- **Heroicons** (<https://heroicons.com>) — MIT, outline + solid variants, native Tailwind fit.
- **Phosphor** (<https://phosphoricons.com>) — MIT, multiple weights, great for chrome.

Pick one and use it consistently. Do not mix sets in the same surface.

## Canonical metaphors → Lucide names

| Action | Lucide icon |
|---|---|
| Close / dismiss | `x` |
| Add / new | `plus` |
| Settings | `settings` |
| Favorite | `heart` |
| Star | `star` |
| Search | `search` |
| More | `more-horizontal` |
| Share | `share` |
| Delete | `trash-2` |
| Edit | `pencil` |
| Back | `chevron-left` |
| Forward | `chevron-right` |
| Down | `chevron-down` |
| User | `user` |
| Home | `home` |
| Calendar | `calendar` |
| Mail | `mail` |
| Notification | `bell` |

## Patterns

### Decorative icon next to label

```html
<button class="inline-flex items-center gap-2 rounded-full bg-brand-blue px-4 py-2 text-white">
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M12 5v14M5 12h14"/>
  </svg>
  New
</button>
```

### Icon-only button (must have accessible name)

```html
<button class="grid h-11 w-11 place-items-center rounded-full text-label-primary hover:bg-surface-secondary"
        aria-label="Close">
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M6 6l12 12M18 6L6 18"/>
  </svg>
</button>
```

## Checklist

- [ ] All icons are SVG, inline or sprite.
- [ ] Single icon family across the app.
- [ ] `currentColor` so icons follow text color.
- [ ] `aria-hidden` when decorative, `aria-label` when stand-alone.
- [ ] Min hit area 44×44 even when the icon is 20×20.
