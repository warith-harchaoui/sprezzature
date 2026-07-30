---
name: sprezzature-colors
description: >-
  Color tooling for vanilla-JS + Tailwind output, both make and audit: WCAG
  contrast audit with OKLCH-neighbour fix suggestions, color-vision-deficiency
  (protanopia / deuteranopia / tritanopia) simulation on screenshots, a
  curated Apple-inspired palette CSV with semantic projections (base, emotion,
  concepts, psychology), perceptual lighten / darken on the OKLCH L axis, and
  a Tailwind theme.extend.colors emitter that turns the canonical palette CSV
  into a drop-in tailwind.config.js. Deterministic, no model, no network.
  Trigger phrases: "WCAG check", "contrast audit", "is my palette accessible",
  "colorblind preview", "deuteranope", "CVD", "lighten this color", "OKLCH",
  "Apple palette", "emotion color", "palette to tailwind", "regenerate brand
  tokens", "tailwind config from palette", "brand colors", "accessible color
  pair", "color-blind safe", "protanopia / tritanopia", "generate palette".
  Output is JSON / stdout / generated config / exit codes suitable for
  pre-commit and CI.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Core scripts (audit_contrast,
  simulate_cvd) need Python 3.10+ stdlib + Pillow (for simulate_cvd only).
  No network or model required at any point.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
---

> The deterministic tools below now ship as the standalone package [`sprezzature-colors`](https://github.com/warith-harchaoui/sprezzature-colors) (`pip install`), invoked as `sprezzature-colors …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-colors — color audit, curation, and perceptual transforms

## Audience and positioning

Solo developers and small teams who:

- Need a **pre-commit gate** that fails fast on contrast regressions.
- Want a curated starter palette rather than picking colors at random.
- Want CVD (color-blindness) review without a browser extension or SaaS.
- Need perceptual color shifts (lighten / darken / hue rotate) for
  generating tints and shades, not the naïve RGB offsets that wash
  saturated hues into pastels.

This skill is **not** a substitute for designer judgment. The
auto-fix from `audit_contrast.py --fix` is a *starting point*: it walks
the OKLCH lightness axis to find the nearest accessible neighbour, but
it can't tell you whether the resulting tonal hierarchy still matches
your brand. Loop a designer in for the final call.

## Honest framing of what each tool covers

| Tool | Catches | Misses |
|---|---|---|
| `audit_contrast.py` | WCAG ratio violations on (label × surface) pairs; suggests nearest OKLCH-neighbour fix | does not verify brand identity or tonal hierarchy. The fix is a hint, not a final decision. |
| `simulate_cvd.py` | how a surface looks to a protanope / deuteranope / tritanope (Machado et al. 2009 matrices). Catches red/green pairing before ship. | does not test motion sensitivity, low-vision blur, or contrast sensitivity beyond color. |
| `_colors.py` | shared primitives: sRGB ↔ linear, hex parsing, WCAG luminance / contrast, OKLab / OKLCH (Björn Ottosson), CVD matrices, perceptual `lighten` / `darken`, palette accessors | not a full-blown color library — no CMYK, no Lab D50, no gamut mapping beyond the OKLCH L axis search. |

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "contrast audit" / "WCAG ratio" / "is my palette accessible" | `audit_contrast.py` | `python scripts/audit_contrast.py [--palette p.json] [--target 4.5\|7\|3] [--fix]` — walks every (label, surface) pair, suggests OKLCH-neighbour fix |
| "color blind preview" / "CVD check" / "how does this look to a deuteranope" | `simulate_cvd.py` | `python scripts/simulate_cvd.py <image> [--grid]` — renders protanopia / deuteranopia / tritanopia |
| "what's the hex for Red" / "give me an emotion color" / "Apple palette" | `_colors.py` accessors | `from _colors import name_to_hex, emotion_to_hex, concept_search, psychology_for, apple_palette` |
| "lighten this color" / "darken" / "tint" / "shade" | `_colors.lighten` / `_colors.darken` | OKLCH L-axis shift; hue and chroma preserved (unlike a naïve RGB offset). |
| "palette to tailwind" / "regenerate brand tokens" / "wire palette.csv into my Tailwind config" | `palette_to_tailwind.py` | `python scripts/palette_to_tailwind.py [--emit theme\|config] [--with-dark] [--include-neutrals] [--out tailwind.config.js]` — emits the canonical `brand: { ... }` block (or a complete config) from `references/palette.csv`. Single source of truth for brand colors across every sprezzature-* consumer. |

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

Accessors in `_colors.py`:

```python
from _colors import (
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
from _colors import lighten, darken, Color

lighten("#007AFF", 0.15)   # "#5FA8FF" — same hue, lighter
darken("#FFCC00", 0.10)    # "#D9AE00" — same hue, darker

# Or via the Color class
brand = Color("#007AFF")
brand.lighten(0.15).contrast_with("#FFFFFF")
brand.meets_wcag("#FFFFFF", level="AA", size="normal")  # True
```

## Two modes — make and audit

This skill covers both sides of color: one make-side
emitter, two audit-side gates, all backed by the same CSV.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — emit Tailwind config from the curated palette | `palette_to_tailwind.py` | Render `references/palette.csv` as a `theme.extend.colors` block (default) or a complete `tailwind.config.js`. |
| **Audit** — gate before ship | `audit_contrast.py`, `simulate_cvd.py` | WCAG ratio audit with **suggest-only** OKLCH-neighbour fix; CVD simulation (protanopia / deuteranopia / tritanopia). |

**Note on `--fix` semantics.** Other sprezzature-* auditors (`audit_laws_of_ux --fix`, `lint_a11y --fix`, `lint_markdown --fix`) apply mechanical edits in place: adding `min-h-11`, stripping redundant ARIA, chunking digits. `audit_contrast --fix` is intentionally **suggest-only** because changing a brand hex is a design decision, not a mechanical repair. The script proposes the nearest accessible OKLCH neighbour for each failing pair; a human reviews and applies. This asymmetry is by design; do not "harmonise" it without a designer in the loop.

The two halves agree on the source of truth; see the next section.

## Curated default — user colors win

`references/palette.csv` carries an **opinionated default** (the 8
saturated Apple-system hues plus the four neutrals) chosen for
balanced contrast, semantic projections that already exist (emotion,
concepts, psychology), and OKLCH-derivable light/dark neighbours.

**The default applies only when the user has not supplied colors.**
Mirror of the three-Roboto rule in `sprezzature-ui/SKILL.md`:

- **Generation, no user palette specified:** use the CSV's curated
  set — `palette_to_tailwind.py` is the make-side primary.
- **User names colors or supplies a palette** ("our brand is
  #8B5CF6", "we already have a tailwind.config.js with our
  tokens"): use theirs. Do not propose the CSV swap.
- **Audit mode (existing project with established colors):** respect
  the existing tokens; do not refactor the palette to the CSV
  unless the user specifically asks. `audit_contrast.py` should
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

- **Audit:** `audit_contrast.py` walks every (label × surface) pair
  against the CSV's hexes and emits an OKLCH-neighbour fix when
  contrast fails.
- **Make:** `palette_to_tailwind.py` emits the same hexes as a
  Tailwind `theme.extend.colors` block (or a complete
  `tailwind.config.js`). The block in
  `sprezzature-ui/references/stack-tailwind.md` matches this output
  exactly; running the script with no flags reproduces it. If they
  ever drift, the CSV wins and the reference doc is regenerated.

For a UI deliverable end-to-end:

```bash
# Generate the Tailwind config from the canonical palette.
python sprezzature-colors/scripts/palette_to_tailwind.py \\
    --emit config --with-dark --out tailwind.config.js

# Then audit the resulting palette.
python sprezzature-colors/scripts/audit_contrast.py --palette palette.json --fix    # WCAG ratios
python sprezzature-colors/scripts/simulate_cvd.py screenshot.png --grid             # CVD pass
python sprezzature-accessibility/scripts/lint_a11y.py public/                                # static a11y gate
```

Pair with a runtime audit (axe-core / Pa11y / Lighthouse) before shipping.

## When NOT to use this skill

- You need a full-featured design-token pipeline (Style Dictionary / Theo /
  Tokens Studio): use those; this skill is a deterministic gate, not a
  pipeline.
- You need print color (CMYK, Pantone matching): out of scope.
- You need a designer-grade palette redesign. `audit_contrast.py --fix`
  is a hint, not a final decision. Loop a designer in.
- You need automatic theming (light/dark generation from a single hue).
  The perceptual primitives are here, but a thoughtful theme is a design
  decision, not an algorithmic one.

## References

- `references/contrast-audit.md` — WCAG contrast audit and OKLCH-neighbour fix suggester.
- `references/cvd-simulation.md` — Color-blindness simulator (protanopia / deuteranopia / tritanopia).
- `references/accessibility-levels.md` — Design for the greyscale worst case by default, offer stronger and deficiency-specific levels on top; the literature and what this project does.
- `references/palette.csv` — Curated palette with semantic projections.

## Scripts

| Script | Install | Purpose |
|---|---|---|
| `audit_contrast.py` | stdlib only | WCAG contrast audit + OKLCH-neighbour fix suggester. Hint to designer, not final decision. |
| `simulate_cvd.py` | `pip install -r scripts/requirements-cvd.txt` (Pillow) | Protanopia / deuteranopia / tritanopia rendering (Machado matrices). |
| `_colors.py` | stdlib only | Shared color primitives — sRGB ↔ linear, hex ↔ RGB, OKLab / OKLCH, WCAG, CVD matrices, perceptual lighten / darken, palette accessors, `Color` class. Internal helper; not invoked directly via the CLI router. |
| `palette_to_tailwind.py` | stdlib only | Render `references/palette.csv` as a Tailwind v3+ `theme.extend.colors` block (`--emit theme`, default) or a complete `tailwind.config.js` (`--emit config`). Optional `--with-dark` for OKLCH-derived dark-mode variants; `--include-neutrals` opts in to Brown / Black / Gray / White. The make-side counterpart to `audit_contrast.py` — closes the CSV → emitted-config loop so brand tokens cannot drift. |

## Companion skills

| You also need… | Install |
|---|---|
| Static HTML a11y lint | `sprezzature-accessibility` |
| AI alt text via local Ollama vision | `sprezzature-vision` |
| Local WebVTT / SRT captions via whisper.cpp | `sprezzature-audio` |
| Vanilla-JS + Tailwind UI generation | `sprezzature-ui` |
| Wrap a CLI in a GUI | `sprezzature-cli-gui` |
| Markdown → website + meta + favicons + indexes | `sprezzature-publish` |
