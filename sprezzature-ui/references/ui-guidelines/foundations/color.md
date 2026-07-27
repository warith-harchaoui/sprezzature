# Foundations — Color

## When to consult this file

- Choosing a tint or accent for a screen, component, or brand
- Building a dark mode palette
- Picking semantic colors (success / warning / destructive / info)
- Auditing contrast for accessibility

## Core principles

- **Every hue should encode meaning:** state, hierarchy, mood, or system semantic. If a color does not communicate something, remove it.
- **Use the curated base palette** in `references/color-psychology.md` for all hue choices.
- **Design for both color schemes from the start.** Each color needs a light-mode value and a dark-mode value; do not just invert.
- **Don't rely on color alone.** Pair color with shape, label, or icon so color-blind users and screen-reader users can still parse state.
- **Preserve sufficient contrast.** Body text ≥ 4.5:1 against its background, large text and UI controls ≥ 3:1. Aim higher when readability matters (long-form reading, low-vision users).
- **Reserve red for destructive or critical states**, not for primary CTAs.
- **Use accent color sparingly.** A single tint should anchor a screen; secondary colors are supportive, not competing.

## Semantic color tokens (light / dark)

These are the only colors authors should reference. Hex values come from the curated palette plus dark-mode pairs tuned for OLED comfort.

| Role | Light | Dark |
|---|---|---|
| Tint primary (Blue) | `#007AFF` | `#0A84FF` |
| Danger (Red) | `#FF3B30` | `#FF453A` |
| Success (Green) | `#28CD41` | `#30D158` |
| Warning (Orange) | `#FF9500` | `#FF9F0A` |
| Attention (Yellow) | `#FFCC00` | `#FFD60A` |
| Accent (Purple) | `#AF52DE` | `#BF5AF2` |
| Joy (Pink) | `#FF2D55` | `#FF375F` |
| Info (Turquoise) | `#79DBDC` | `#64D2FF` |
| Label primary (text) | `#000000` | `#FFFFFF` |
| Label secondary | `rgba(60,60,67,0.6)` | `rgba(235,235,245,0.6)` |
| Label tertiary | `rgba(60,60,67,0.3)` | `rgba(235,235,245,0.3)` |
| Surface primary | `#FFFFFF` | `#000000` |
| Surface secondary | `#F2F2F7` | `#1C1C1E` |
| Surface tertiary | `#FFFFFF` | `#2C2C2E` |
| Separator | `rgba(60,60,67,0.36)` | `rgba(84,84,88,0.65)` |

## Mapping to Tailwind

Authors should write semantic class names (never raw hex) so the system stays consistent.

```js
// tailwind.config.js — excerpt
colors: {
  brand: {
    blue:      { DEFAULT: '#007AFF', dark: '#0A84FF', light: '#CCE4FF' },
    red:       { DEFAULT: '#FF3B30', dark: '#FF453A', light: '#FFD8D6' },
    green:     { DEFAULT: '#28CD41', dark: '#30D158', light: '#D4F5D9' },
    orange:    { DEFAULT: '#FF9500', dark: '#FF9F0A', light: '#FFEACC' },
    yellow:    { DEFAULT: '#FFCC00', dark: '#FFD60A', light: '#FFF5CC' },
    purple:    { DEFAULT: '#AF52DE', dark: '#BF5AF2', light: '#EFDCF8' },
    pink:      { DEFAULT: '#FF2D55', dark: '#FF375F', light: '#FFD5DD' },
    turquoise: { DEFAULT: '#79DBDC', dark: '#64D2FF', light: '#00FFEF' },
  },
  label: {
    primary:   { DEFAULT: '#000000', dark: '#FFFFFF' },
    secondary: { DEFAULT: 'rgba(60,60,67,0.6)', dark: 'rgba(235,235,245,0.6)' },
    tertiary:  { DEFAULT: 'rgba(60,60,67,0.3)', dark: 'rgba(235,235,245,0.3)' },
  },
  surface: {
    primary:   { DEFAULT: '#FFFFFF', dark: '#000000' },
    secondary: { DEFAULT: '#F2F2F7', dark: '#1C1C1E' },
    tertiary:  { DEFAULT: '#FFFFFF', dark: '#2C2C2E' },
  },
  separator: 'rgba(60,60,67,0.36)',
}
```

## Checklist before shipping

- [ ] No raw hex in markup: use Tailwind tokens (`bg-brand-blue`, not `bg-[#007AFF]`).
- [ ] Both `light` and `dark:` variants set for every meaningful surface and text token.
- [ ] Body text ≥ 4.5:1, UI ≥ 3:1, verified with a contrast tool.
- [ ] Red used only for destructive/critical states.
- [ ] State (selected, disabled, error) communicated by more than color.
- [ ] Semantic intent picked using the Concept/Psychology tables in `color-psychology.md`.
