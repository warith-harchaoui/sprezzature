---
name: sprezzature-colors
description: >-
  Colour tooling for vanilla-JS + Tailwind output, make and audit alike: WCAG
  contrast audit with OKLCH-neighbour fix suggestions, colour-vision-deficiency
  (protanopia / deuteranopia / tritanopia) simulation on screenshots, six
  accessibility levels of the palette, a curated Apple-inspired palette CSV
  with colour psychology, perceptual lighten / darken on the OKLCH L axis, and
  a Tailwind emitter that turns the CSV into a drop-in tailwind.config.js.
  Deterministic: no model, no network.
  Use it when a colour is being chosen, varied, judged or exported, in any
  context. Trigger phrases: "WCAG check", "contrast audit", "is my palette
  accessible", "colorblind preview", "CVD", "lighten this color", "OKLCH",
  "Apple palette", "palette to tailwind", "color-blind safe". Not this one
  when: the markup has structural defects rather than a colour question
  (sprezzature-accessibility), or the colours belong to a chart being drawn
  (sprezzature-figures). The exhaustive trigger catalogue is in
  `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10+; one
  `pip install sprezzature-colors` brings everything (click, Pillow, FastAPI,
  uvicorn, fastapi-mcp). The colour arithmetic is standard library only.
  No network or model required at any point.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.2
---

> The deterministic tools below ship as the standalone package [`sprezzature-colors`](https://github.com/warith-harchaoui/sprezzature-colors) (`pip install sprezzature-colors`), invoked as `sprezzature-colors …` (also spelled `make-colors`) or one command per tool. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

## Five surfaces

| Surface | Entry point |
|---|---|
| Library | `import sprezzature_colors as sc` |
| Command line | `sprezzature-colors <tool>` (click front door: `contrast`, `cvd`, `levels`, `palette-to-tailwind`, `tools`), or `sprezzature-colors-contrast`, `-cvd`, `-levels`, `-palette-to-tailwind` |
| HTTP API | `uvicorn sprezzature_colors.api:app`, or `docker compose up` in the package repository |
| MCP server | `sprezzature-colors-mcp` (default `127.0.0.1:8000`, endpoint `/mcp`) |
| Skill | this file |

The MCP tools are the routes' `operation_id`s: `health`, `get_palette`, `check_contrast`, `simulate_color_blindness`, `adjust_lightness`, `get_color_psychology`, `search_concepts`. Each accepts a hex code or a palette name wherever it takes a colour. Levels, the Tailwind export and image simulation are command-line only, because they read or write files.

# sprezzature-colors — color audit, curation, and perceptual transforms

## Audience and positioning

Solo developers and small teams who:

- Need a **pre-commit gate** that fails fast on contrast regressions.
- Want a curated starter palette rather than picking colors at random.
- Want CVD (color-blindness) review without a browser extension or SaaS.
- Need perceptual color shifts (lighten / darken) for
  generating tints and shades, not the naïve RGB offsets that wash
  saturated hues into pastels.

This skill is **not** a substitute for designer judgment. The
auto-fix from `sprezzature-colors-contrast --fix` is a *starting point*: it walks
the OKLCH lightness axis to find the nearest accessible neighbour, but
it can't tell you whether the resulting tonal hierarchy still matches
your brand. Loop a designer in for the final call.

## Honest framing of what each tool covers

| Tool | Catches | Misses |
|---|---|---|
| `sprezzature-colors-contrast` | WCAG ratio violations on (label × surface) pairs; suggests nearest OKLCH-neighbour fix | does not verify brand identity or tonal hierarchy. The fix is a hint, not a final decision. |
| `sprezzature-colors-cvd` | how a surface looks to a protanope / deuteranope / tritanope (MACHADO et al. 2009 matrices, full severity), plus an optional grayscale render. Catches red/green pairing before ship. | does not test motion sensitivity, low-vision blur, or contrast sensitivity beyond color. |
| `sprezzature-colors-levels` | the palette remapped to `universal`, `high-contrast` (7:1), `monochrome`, `deuteranopia`, `protanopia` or `tritanopia`, keeping every colour name | a level is an option for a known need, not a replacement for an accessible default. |
| `_colors.py` | shared primitives: sRGB ↔ linear, hex parsing, alpha compositing, WCAG luminance / contrast, OKLab / OKLCH (Björn OTTOSSON), CVD matrices, perceptual `lighten` / `darken`, palette and psychology accessors | not a full-blown color library — no CMYK, no Lab D50, no gamut mapping beyond the OKLCH L axis search. |

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "contrast audit" / "WCAG ratio" / "is my palette accessible" | `sprezzature-colors-contrast`; MCP `check_contrast` for single pairs | `sprezzature-colors-contrast [--palette p.json] [--target 4.5\|7\|3] [--fix] [--format json]`. Walks the (label, surface) pairs that co-occur in a rendered theme (`--all-pairs` for the full cross-product), suggests OKLCH-neighbour fix. Exit 0 all pass, 1 a pair fails, 2 no key matched `label-` / `brand-` against `surface-`. |
| "color blind preview" / "CVD check" / "how does this look to a deuteranope" | `sprezzature-colors-cvd`; MCP `simulate_color_blindness` for colours | `sprezzature-colors-cvd <image> [--types prot,deut,trit] [--grid] [--grayscale] [--out PATH]`. Renders protanopia / deuteranopia / tritanopia, one `<stem>-<type>.png` each (always PNG, whatever the source's extension). |
| "high-contrast palette" / "a palette for deuteranopes" / "monochrome version" | `sprezzature-colors-levels` | `sprezzature-colors-levels --level <level> [--csv palette.csv]`. Prints name, hex and contrast against white per colour. |
| "what's the hex for Red" / "give me an emotion color" / "Apple palette" | library accessors; MCP `get_palette`, `search_concepts`, `get_color_psychology` | `import sprezzature_colors as sc`, then `sc.name_to_hex`, `sc.emotion_to_hex`, `sc.concept_search`, `sc.psychology_for`, `sc.apple_palette` |
| "lighten this color" / "darken" / "tint" / "shade" | `sc.lighten` / `sc.darken`; MCP `adjust_lightness` | OKLCH L-axis shift; hue and chroma preserved (unlike a naïve RGB offset). |
| "palette to tailwind" / "regenerate brand tokens" / "wire palette.csv into my Tailwind config" | `sprezzature-colors-palette-to-tailwind` | `sprezzature-colors-palette-to-tailwind [--emit theme\|config] [--with-dark] [--include-neutrals] [--theme corporate\|academic] [--out tailwind.config.js]`. `--theme academic` emits the Okabe-Ito colour-blind-safe set instead. Emits the canonical `brand: { ... }` block (or a complete config) from `references/palette.csv`. Single source of truth for brand colors across every sprezzature-* consumer. |

## The unified palette

`references/palette.csv` is **one canonical row per color**, with semantic
projections as columns:

| Hex | Base | Emotion | Concepts | Psychology (+) | Psychology (−) |
|---|---|---|---|---|---|
| #FF3B30 | Red | Anger | Excitement, Youthful, Bold | Power, Passion, Energy… | Anger, Danger, Warning… |
| #FF9500 | Orange | Surprise | Friendly, Cheerful, Confidence | Courage, Confidence… | Deprivation, Frustration… |
| … | … | … | … | … | … |

The same hex can serve multiple semantics: `#FF3B30`, for example, is *Red* (base), *Anger* (emotion), and carries both
"Excitement" (concept) and "Power" (psychology positive). A single source
of truth keeps these projections consistent.

Accessors, re-exported by the package:

```python
from sprezzature_colors import (
    apple_palette,         # {"Red": "#FF3B30", "Orange": "#FF9500", ...}
    name_to_hex,           # "Red"     → "#FF3B30"
    name_to_rgb,           # "Red"     → (255, 59, 48)
    light_variant,         # "Red"     → "#FFD8D6" (curated)
    emotion_to_hex,        # "Anger"   → "#FF3B30"
    concept_search,        # "Bold"    → ["#FF3B30"]
    psychology_for,        # "Red"     → {"positive": [...], "negative": [...]}
)
```

## Perceptual lighten / darken

The classical "add 70 to each RGB channel" approach washes saturated
hues into pastels and shifts apparent hue. `_colors.lighten` and
`_colors.darken` shift the OKLCH **L** axis instead, keeping chroma
and hue intact:

```python
from sprezzature_colors import lighten, darken
from sprezzature_colors_scripts._colors import Color  # not re-exported

lighten("#007AFF", 0.15)   # "#47ABFF": same hue, lighter
darken("#FFCC00", 0.10)    # "#DEAB00": same hue, darker

# Or via the Color class
brand = Color("#007AFF")
brand.contrast_with("#FFFFFF")                          # 4.02
brand.meets_wcag("#FFFFFF", level="AA", size="normal")  # False: needs 4.5
brand.meets_wcag("#FFFFFF", level="AA", size="large")   # True
```

## Two modes: make and audit

This skill covers both sides of color: one make-side
emitter, two audit-side gates, all backed by the same CSV.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — emit Tailwind config from the curated palette | `sprezzature-colors-palette-to-tailwind` | Render `references/palette.csv` as a `theme.extend.colors` block (default) or a complete `tailwind.config.js`. |
| **Audit** — gate before ship | `sprezzature-colors-contrast`, `sprezzature-colors-cvd` | WCAG ratio audit with **suggest-only** OKLCH-neighbour fix; CVD simulation (protanopia / deuteranopia / tritanopia). |

**Note on `--fix` semantics.** Other sprezzature-* auditors (`sprezzature-ux-laws-audit --fix`, `sprezzature-accessibility-lint --fix`, `sprezzature-publish-lint --fix`) apply mechanical edits in place: adding `min-h-11`, stripping redundant ARIA, chunking digits. `sprezzature-colors-contrast --fix` is intentionally **suggest-only** because changing a brand hex is a design decision, not a mechanical repair. The script proposes the nearest accessible OKLCH neighbour for each failing pair; a human reviews and applies. This asymmetry is by design; do not "harmonise" it without a designer in the loop.

The two halves agree on the source of truth; see the next section.

## Curated default — user colors win

`references/palette.csv` carries an **opinionated default** (the 8
saturated Apple-system hues plus the four neutrals) chosen for
balanced contrast, semantic projections that already exist (emotion,
concepts, psychology), and OKLCH-derivable light/dark neighbours.

**The default applies only when the user has not supplied colors.**
Mirror of the three-Roboto rule in `sprezzature-ui/SKILL.md`:

- **Generation, no user palette specified:** use the CSV's curated
  set — `sprezzature-colors-palette-to-tailwind` is the make-side primary.
- **User names colors or supplies a palette** ("our brand is
  #8B5CF6", "we already have a tailwind.config.js with our
  tokens"): use theirs. Do not propose the CSV swap.
- **Audit mode (existing project with established colors):** respect
  the existing tokens; do not refactor the palette to the CSV
  unless the user specifically asks. `sprezzature-colors-contrast` should
  flag contrast failures against the user's palette, not against
  ours.

The carve-out exists so the skill is useful to the dataviz / startup /
internal-tools shipper who has zero palette opinion (the CSV gives
them a defensible starting point) **and** to the brand-conscious
team that already owns a palette (the auditor still works, the
emitter is just unused).

## Single source of truth — make ↔ audit loop

`references/palette.csv` is the **one canonical place** brand hexes
live in the sprezzature-* ecosystem when the curated default is in play.
Both halves of the loop read it:

- **Audit:** `sprezzature-colors-contrast` walks the (label × surface) pairs that
  co-occur in a rendered theme by default (`--all-pairs` for the full
  cross-product) against the CSV's hexes and emits an OKLCH-neighbour
  fix when contrast fails.
- **Make:** `sprezzature-colors-palette-to-tailwind` emits the same hexes as a
  Tailwind `theme.extend.colors` block (or a complete
  `tailwind.config.js`). The block in
  `sprezzature-ui/references/stack-tailwind.md` is written by hand and
  does not match this output: it carries Apple's own `dark` hexes, which
  the CSV has no column for (`--with-dark` derives them on the OKLCH L
  axis instead), and it predates the CSV's correction of the Turquoise
  `light` tint. When the two disagree, the CSV wins.

For a UI deliverable end-to-end:

```bash
# Generate the Tailwind config from the canonical palette.
sprezzature-colors-palette-to-tailwind \
    --emit config --with-dark --out tailwind.config.js

# Then audit the resulting palette.
sprezzature-colors-contrast --palette palette.json --fix  # WCAG ratios
sprezzature-colors-cvd screenshot.png --grid              # CVD pass
sprezzature-accessibility-lint public/                    # static a11y gate
```

Pair with a runtime audit (axe-core / Pa11y / Lighthouse) before shipping.

## When NOT to use this skill

- You need a full-featured design-token pipeline (Style Dictionary / Theo /
  Tokens Studio): use those; this skill is a deterministic gate, not a
  pipeline.
- You need print color (CMYK, Pantone matching): out of scope.
- You need a designer-grade palette redesign. `sprezzature-colors-contrast --fix`
  is a hint, not a final decision. Loop a designer in.
- You need automatic theming (light/dark generation from a single hue).
  The perceptual primitives are here, but a thoughtful theme is a design
  decision, not an algorithmic one.

## References

- `references/contrast-audit.md` — WCAG contrast audit and OKLCH-neighbour fix suggester.
- `references/cvd-simulation.md` — Color-blindness simulator (protanopia / deuteranopia / tritanopia).
- `references/accessibility-levels.md` — Design for the greyscale worst case by default, offer stronger and deficiency-specific levels on top; the literature and what this project does.
- `references/triggers.md` — The exhaustive trigger catalogue.
- `references/palette.csv` — Curated palette with semantic projections.

## Scripts

Shipped by the standalone [`sprezzature-colors`](https://github.com/warith-harchaoui/sprezzature-colors)
package (`pip install sprezzature-colors`, which includes Pillow for the CVD
renderer). Each entry below is a console script the package registers, and a
sub-command of the `sprezzature-colors` front door.

| Script | Install | Purpose |
|---|---|---|
| `audit_contrast.py` → `sprezzature-colors-contrast` | click (base install) | WCAG contrast audit + OKLCH-neighbour fix suggester. Hint to designer, not final decision. |
| `simulate_cvd.py` → `sprezzature-colors-cvd` | click + Pillow (base install) | Protanopia / deuteranopia / tritanopia rendering (MACHADO matrices), optional grayscale. |
| `accessibility_levels.py` → `sprezzature-colors-levels` | click (base install) | The palette at one of six accessibility levels, same names. |
| `_colors.py` | stdlib only | Shared color primitives: sRGB ↔ linear, hex ↔ RGB, OKLab / OKLCH, WCAG, CVD matrices, perceptual lighten / darken, palette accessors, `Color` class. Internal helper; not invoked directly via the CLI router. |
| `palette_to_tailwind.py` → `sprezzature-colors-palette-to-tailwind` | click (base install) | Render `references/palette.csv` as a Tailwind v3+ `theme.extend.colors` block (`--emit theme`, default) or a complete `tailwind.config.js` (`--emit config`). Optional `--with-dark` for OKLCH-derived dark-mode variants; `--include-neutrals` opts in to Brown / Black / Gray / White. The make-side counterpart to `sprezzature-colors-contrast`: closes the CSV → emitted-config loop so brand tokens cannot drift. |

## Companion skills

| You also need… | Install |
|---|---|
| Static HTML a11y lint | `sprezzature-accessibility` |
| AI alt text via local Ollama vision | `sprezzature-accessibility` |
| Local WebVTT / SRT captions via whisper.cpp | `sprezzature-audio` |
| Vanilla-JS + Tailwind UI generation | `sprezzature-ui` |
| Wrap a CLI in a GUI | `sprezzature-cli-gui` |
| Markdown → website + meta + favicons + indexes | `sprezzature-publish` |
