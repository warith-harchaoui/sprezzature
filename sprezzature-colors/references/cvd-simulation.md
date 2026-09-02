# Color-blind simulation: `simulate_cvd.py`

Render an image (a chart, a UI screenshot, an asset) as a color-blind viewer would see it. Three simulations are produced by default: protanopia, deuteranopia, tritanopia. Pillow + published transformation matrices. No model.

## Why it matters

Roughly 1 in 12 men and 1 in 200 women have some form of color vision deficiency. The most common (deuteranomaly / deuteranopia) collapses the red / green channel. UIs that lean on red-for-bad / green-for-good without a secondary cue (icon, label, shape) become unreadable.

The simulation is qualitative: a real viewer's experience varies with severity and adaptation. The output is faithful enough for review.

## Install

```bash
pip install -r scripts/requirements-cvd.txt
```

Pillow is the only dependency.

## Run

```bash
# Default: three sibling PNGs (one per CVD type)
python scripts/simulate_cvd.py public/hero.png

# Side-by-side mosaic for a design review
python scripts/simulate_cvd.py public/hero.png --grid --out public/hero-cvd.png

# Subset (use shorthand: prot / deut / trit)
python scripts/simulate_cvd.py public/hero.png --types prot,deut
```

Output filenames:

| Mode | Output |
|---|---|
| Default | `<stem>-protanopia.png`, `<stem>-deuteranopia.png`, `<stem>-tritanopia.png` siblings of the source. |
| `--grid` | One mosaic at `<stem>-cvd-grid.png` (override with `--out`). |

## How to read the output

For each variant, ask:

1. **Is the chart / UI still parseable?** Categories distinguishable, state legible.
2. **Did any pair collapse?** Red-vs-green pair becoming the same hue is the classic failure.
3. **Does the takeaway still come across?** A chart's headline message must survive desaturation.

If the answer to (2) is yes:

- Add a non-color cue (icon, label, shape).
- Switch the palette: see `references/dataviz-color-palettes.md` (categorical guidance: max 8 hues, no simultaneous red + green).
- For sequential data, use a single-hue luminance ramp (Viridis-style) instead of red → green.

## The math

The script implements the Machado, Oliveira & Fernandes (2009) precomputed CVD matrices at severity 1.0 ("dichromat" / fully missing cone type). The matrices are applied in **linear sRGB**: the source is degamma-decoded before the matrix, then re-encoded with the standard sRGB transfer.

This is not the only model. Brettel / Viénot / Mollon (1997) work in LMS space and are often cited. Machado et al. matrices are easier to ship (just three numbers per output channel), faithful at severity 1, and used by major design tools (e.g., Figma's CVD preview).

## Limitations

- Only severity 1 (full dichromacy). Real CVD ranges from mild anomalous trichromacy to full dichromacy.
- Achromatopsia (no cones at all) is not simulated; for that case, view the image desaturated.
- The simulation is per-pixel: it does not account for surround / context adaptation.
- Animated content needs frame-by-frame simulation; this script handles still images only.

## CI integration

Combine with `lint_a11y.py` to catch color-only state at the markup layer, and the CVD simulation to catch palette failures at the design layer. A CI job that produces the grid mosaic as an artifact is a low-friction review step:

```yaml
- name: CVD preview
  run: |
    python3 scripts/simulate_cvd.py public/hero.png --grid \
            --out artifacts/hero-cvd-grid.png
- uses: actions/upload-artifact@v4
  with: { name: cvd, path: artifacts/ }
```

## Checklist

- [ ] Run on every UI screenshot before review.
- [ ] Run on every chart before publishing.
- [ ] Pair with `lint_a11y.py` to catch `color-only-state` markup violations.
- [ ] If a pair collapses, change the palette or add a non-color cue.
- [ ] Cite the model in design docs ("Machado et al. 2009, severity 1.0").
