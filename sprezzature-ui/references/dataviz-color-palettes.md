# Dataviz Color Palettes (Accessible)

Accessible color choices for data visualization. Read alongside `color-psychology.md` (the curated brand palette), `charts-svg.md` (hand-authored SVG house style), and `ui-guidelines/foundations/accessibility.md`.

Color in a data visualization carries a dimension. It is not decoration. Picking colors badly makes the chart unreadable for color-blind users, illegible at small sizes, or actively misleading.

## Three palette types: pick one before you start

| Type | Use | Example |
|---|---|---|
| Sequential | Ordered values along one axis | Temperature, volume, density |
| Divergent | Deviation from a neutral midpoint | Year-over-year growth (+/−) |
| Categorical | Distinct groups with no order | Countries, products, departments |

You can't pick colors well until you know which of these three you're building.

## House defaults

### Sequential

- One hue, varying luminance from light to dark.
- Use a perceptual color space (OKLCH preferred, LCH acceptable) so steps look evenly spaced.
- Avoid hue jumps: they read as category boundaries when there are none.
- Default: light blue → `brand-blue` (`#CCE4FF` → `#007AFF`).

### Divergent

- Two opposing hues meeting at a light neutral.
- Symmetric around the midpoint (same number of steps on each side).
- Default for "growth": a neutral mid-gray at zero with two opposing ends. Two choices, and the first is the default:
  - **Colour-blind-safe (prefer this): blue ↔ red** (`#007AFF` ↔ `#808080` ↔ `#FF3B30`). The red ↔ green pair is hostile to red-green colour blindness (~8 % of men): under protanopia / deuteranopia both ends drift to a muddy tan and collapse into one hue, so the sign can no longer be read from colour. Blue ↔ red stays discriminable: blue survives, red darkens toward brown. `_style.diverging_pair(cvd_safe=True)` returns it (blue also carries *Trust*, red *Danger* in `color-psychology.md`).
  - **Conventional red ↔ green** (`#FF3B30` ↔ `#808080` ↔ `#28CD41`). Finance-idiomatic and intuitive for the sighted majority, but only reach for it when the sign is *also* encoded another way (a +/- glyph, position above/below zero) **and** you have confirmed it survives in `simulate_cvd.py`.
- Reserve this shape for actual divergent data, not for "category A vs. category B".

### Categorical

- Max 8 categories. More than that, the eye stops distinguishing reliably: collapse small categories into "Other" or use a different chart.
- Use the brand categorical sequence from `charts-svg.md`:
  `["#007AFF", "#28CD41", "#FF9500", "#AF52DE", "#FF2D55", "#FFCC00", "#79DBDC", "#FF3B30"]`
- Avoid simultaneous red + green; they read as the same color to red-green color-blind users (about 8 % of men).

## Heuristics that beat intuition

1. **Vary luminance more than hue** for ordered data: the eye reads luminance first.
2. **Avoid rainbow scales.** They aren't perceptually uniform and they imply category breaks where the data has none.
3. **Prefer perceptual scales**: Viridis, Cividis, Magma, Inferno are battle-tested for accessibility.
4. **Cap visible colors per tile** at ~5. Anything more is decoration competing with the data.
5. **Test in grayscale.** If the chart doesn't read in grayscale, color is doing too much work. Add shape, pattern, or stroke distinctions.

## Accessibility workflow

A four-step workflow before any chart ships.

### 1. Pick palette type

Sequential / divergent / categorical. Decide before generating.

### 2. Generate the palette

- For categorical, use the brand sequence above.
- For sequential / divergent, generate in a perceptual color space. Tools that help:
  - [Huetone](https://huetone.ardov.me/): palette generator built around APCA contrast.
  - [Adobe Color](https://color.adobe.com/): harmonies (kept simple).
  - [Coolors](https://coolors.co/): fast palette ideation.

### 3. Verify perception

Run the palette through color-blindness simulators:

- [Color Oracle](https://colororacle.org/): desktop simulator for protanopia, deuteranopia, tritanopia.
- [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/): browser-based.

The chart should still be readable under each simulation. If two series collapse to the same color, change one of them.

### 4. Verify contrast (WCAG)

- Text on tiles: ≥ 4.5:1 (WCAG AA) for body, ≥ 3:1 for large.
- Chart elements against the tile background: ≥ 3:1.
- Tools:
  - [Contrast Finder](https://app.contrast-finder.org/): given a brand color, returns the closest accessible alternative.
  - [GetWCAG](https://getwcag.com/): quick fore/back checks.

WCAG alone is not enough for charts. Pair contrast with **distinct luminance**, **distinct hue**, and where needed **distinct shape** (stroke style, marker symbol, fill pattern).

## Bake into design tokens

Once the palette passes, formalize as Tailwind tokens so it's used uniformly. Suggested token shape:

```js
// tailwind.config.js — excerpt for charts
extend: {
  colors: {
    'data-sequential': {
      100: '#CCE4FF', 200: '#99CAFF', 300: '#66B0FF',
      400: '#3395FF', 500: '#007AFF', 600: '#0062CC',
      700: '#004999', 800: '#003166', 900: '#001833',
    },
    'data-categorical': {
      1: '#007AFF', 2: '#28CD41', 3: '#FF9500', 4: '#AF52DE',
      5: '#FF2D55', 6: '#FFCC00', 7: '#79DBDC', 8: '#FF3B30',
    },
    'data-diverging': {
      neg: '#FF3B30', mid: '#808080', pos: '#28CD41',
    },
  },
},
```

The house tokens in `charts-svg.md` already reference these hues via the categorical range. Re-use the tokens in any chart or KPI output so they stay in sync.

## Checklist

- [ ] Palette type chosen (sequential / divergent / categorical) before picking colors.
- [ ] Perceptual color space used for sequential / divergent.
- [ ] No rainbow scale.
- [ ] ≤ 8 categorical hues; small categories collapsed to "Other".
- [ ] Color blindness simulators passed (protanopia, deuteranopia, tritanopia).
- [ ] WCAG contrast met for text and chart elements.
- [ ] Chart still readable in grayscale: color is not load-bearing alone.
- [ ] Tokens defined in Tailwind config; no raw hex in chart code.
