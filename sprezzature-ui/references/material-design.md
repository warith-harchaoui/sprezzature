# Material Design 3: mapping table

Canonical source: <https://m3.material.io/>. This file is a **mapping** from Material 3 vocabulary onto the skill's stack (vanilla JS + Tailwind, configurable typeface). It is not a paraphrase of Material's docs; when the user names a Material component or token, emit the skill's equivalent instead.

Where Material's spec disagrees with the skill (typeface defaults, brand colour tokens), the skill's choices win.

## Color roles → skill tokens

| Material 3 role | Skill token | Use |
|---|---|---|
| `primary` | `brand-blue` | Main accent, primary CTAs, focus rings |
| `on-primary` | white text on `brand-blue` | Text / icons on primary surfaces |
| `primary-container` | `brand-blue-light` | Filled containers tied to primary |
| `secondary` | `brand-purple` (or accent) | Less prominent components |
| `tertiary` | `brand-turquoise` | Contrasting accents in dense UI |
| `error` | `brand-red` | Destructive / error |
| `surface` | `surface-primary` | Default surfaces |
| `surface-container-low/high` | `surface-secondary` / `surface-tertiary` | Elevated containers without shadows |
| `on-surface` | `label-primary` | Body text |
| `on-surface-variant` | `label-secondary` | Secondary text, icons, separators |
| `outline` | `separator` | Borders and dividers |

Dynamic-colour generation: the skill ships static `DEFAULT` / `dark` / `light` variants (`color-psychology.md`). No auto-extraction from user images.

## Typography scale → skill scale

| Material 3 | Skill | Tailwind |
|---|---|---|
| Display large / medium / small | Display / Title 1 | `text-5xl` / `text-4xl` |
| Headline large / medium / small | Title 2 / Title 3 | `text-2xl` / `text-xl` |
| Title large / medium / small | Headline | `text-[17px] font-semibold` |
| Body large / medium / small | Body / Callout / Subhead | `text-[17px]` / `text-base` / `text-[15px]` |
| Label large / medium / small | Footnote / Caption | `text-[13px]` / `text-xs` |

Reference type: Material uses Roboto Flex. The skill ships the classic Roboto super-family (Roboto / Roboto Serif / Roboto Mono: the three-Roboto rule) under `sprezzature-ui/assets/fonts/roboto*/`; see `ui-guidelines/foundations/typography.md`.

## Shape → corner radius

| Material 3 | px | Tailwind |
|---|---|---|
| None | 0 | `rounded-none` |
| Extra small | 4 | `rounded` |
| Small | 8 | `rounded-lg` |
| Medium | 12 | `rounded-xl` |
| Large | 16 | `rounded-2xl` |
| Extra large | 28 | `rounded-3xl` |
| Full | half-height | `rounded-full` |

House defaults: pill buttons (`rounded-full`), cards `rounded-2xl`, inputs `rounded-xl`, chart tiles `rounded-[10px]`. Avoid `rounded-3xl` on small components.

## Elevation → tonal surfaces

| Material 3 elevation | Skill |
|---|---|
| Level 0 | `surface-primary` |
| Level 1 | `surface-secondary` |
| Level 2 | `surface-secondary` + `border border-separator/40` |
| Level 3 | `surface-tertiary` |
| Level 4–5 | `surface-tertiary` + `shadow-sm` (modals, popovers only) |

Solid `shadow-lg` belongs on transient overlays only. Cards stay flat.

## Motion durations

| Material 3 token | ms | Skill use |
|---|---|---|
| Short 1 | 50 | Hover tint |
| Short 2 | 100 | Press scale, simple toggles |
| Medium 1 | 250 | Modal reveal |
| Medium 2 | 300 | Sheet rise, page transition |
| Long 1 | 450 | Hero element transitions |
| Long 2 | 500 | Cross-screen container transform |

Cap interactions at 500 ms. Easing: `cubic-bezier(0.2, 0, 0, 1.0)` (`ease-native` / `ease-standard`).

## Components → skill equivalents

| Material 3 component | Skill equivalent |
|---|---|
| Filled / Tonal / Outlined / Elevated / Text Button | Primary / Secondary / Tertiary Button |
| Floating Action Button (FAB) | Bottom-anchored primary button on mobile; circular `rounded-full bg-brand-blue` only when a FAB is truly required |
| Top App Bar (all sizes) | Sticky `<header>` with `backdrop-blur-ultra` |
| Bottom App Bar / Navigation Bar | Sticky bottom tab bar |
| Navigation Drawer | Off-canvas `<dialog>` from the start edge |
| Navigation Rail | Sidebar with icon + label, hidden on mobile |
| Text Field (Filled / Outlined) | Outlined input (`form-field.html`) |
| Card (Filled / Outlined / Elevated) | `rounded-2xl bg-surface-secondary` (filled), optional `border-separator/40` (outlined). No elevated variant. |
| Dialog | Native `<dialog>` |
| Bottom Sheet | `<dialog>` bottom-anchored |
| Snackbar | Toast with live region |
| Banner | Top inline banner |
| Chips | Pill buttons / toggles |
| Menu | `<details>` or native `popover` |
| Tabs | Horizontal segmented control (not the bottom tab bar) |
| Switch | Toggle with `role="switch"` |
| Slider | Native `<input type="range">` |
| Progress Indicator | `<progress>` or animated spinner |
| Date / Time Picker | Native `<input type="date|time">` |
| Tooltip | Native `title` on icon-only buttons, or anchored popover |
| Badge | `inline-flex items-center rounded-full px-2 py-0.5 text-xs` on a `relative` parent |
| Icon Button | `aria-label`'d icon-only button |
| Search | `<input type="search">` with debounce |

The skill never emits Material Web Components (`mdc-*`, `md-*`) or imports Material's CSS. Output behaves like the Material equivalent but ships as plain HTML + Tailwind.

## Accessibility alignment

Material's mandates and the skill's: identical in spirit. Differences:

- Touch target: Material 48 dp ≥, skill 44 px ≥ (still WCAG-compliant). Raise to 48 if Material parity is required.
- Contrast: WCAG AA (≥ 4.5:1 body, ≥ 3:1 large / UI).
- Visible keyboard focus, `prefers-reduced-motion`, dynamic type, colour scheme: all honoured.

## When to consult this file

- User names a Material component or token ("filled tonal button", "FAB", "surface-container-high").
- User says "M3" or "Material Design".
- Migrating a Material-built UI to the skill's stack.

## Checklist

- [ ] Material role mapped to a skill token; no raw Material hex.
- [ ] Typeface from the skill's stack, not Roboto.
- [ ] Corner radius from the skill's set.
- [ ] Elevation via surface colour, not shadow (except transient overlays).
- [ ] Touch target ≥ 44 px (≥ 48 px if Material parity matters).
- [ ] Motion ≤ 500 ms per interaction.
- [ ] No `mdc-*` / `md-*` classes shipped.
