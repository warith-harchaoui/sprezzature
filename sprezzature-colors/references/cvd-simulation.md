# Color-blind simulation — `sprezzature-colors-cvd`

Render an image (a chart, a UI screenshot, an asset) as a color-blind viewer would see it. Three simulations are produced by default: protanopia, deuteranopia, tritanopia. Pillow + published transformation matrices. No model.

## Why it matters

Roughly 1 in 12 men and 1 in 200 women have some form of color vision deficiency (CVD): the eye's cone cells, which normally split incoming light into red-, green-, and blue-sensitive signals, are missing or malfunctioning for one of the three. Deuteranopia (green-sensitive cones affected) and protanopia (red-sensitive cones affected) both collapse the red/green distinction and are by far the most common; tritanopia (blue-sensitive cones affected) is rare and collapses blue/yellow instead. A UI that leans on red-for-bad / green-for-good without a secondary cue (icon, label, shape) becomes unreadable for the first two groups.

The simulation is qualitative: a real viewer's experience varies with severity and adaptation. The output is faithful enough for review.

## Install

```bash
pip install sprezzature-colors
```

Pillow and click, the two libraries this tool needs, are base dependencies. From a source checkout, `pip install -r requirements-cvd.txt` installs those two alone.

## Run

Installed, the command is `sprezzature-colors-cvd` (or `sprezzature-colors cvd`). From a source checkout of the package, `python scripts/simulate_cvd.py` takes the same arguments.

```bash
# Default: three sibling PNGs (one per CVD type)
sprezzature-colors-cvd public/hero.png

# Side-by-side mosaic for a design review
sprezzature-colors-cvd public/hero.png --grid --out public/hero-cvd.png

# Subset (use shorthand: prot / deut / trit)
sprezzature-colors-cvd public/hero.png --types prot,deut

# Add a relative-luminance grayscale version
sprezzature-colors-cvd public/hero.png --grayscale
```

Output filenames:

| Mode | Output |
|---|---|
| Default | `<stem>-protanopia.png`, `<stem>-deuteranopia.png`, `<stem>-tritanopia.png` siblings of the source, or in the directory given to `--out`. |
| `--grayscale` | Adds `<stem>-grayscale.png`, or a "Grayscale" panel in the mosaic. |
| `--grid` | One mosaic at `<stem>-cvd-grid.png` (override with a file path in `--out`, whose directories are created): the original and each variant, two per row, so 2×2 for the three types and three rows with `--grayscale`. |

Every file is written as PNG and named `.png`, whatever the source's extension: `hero.jpg` gives `hero-protanopia.png`.

## How to read the output

For each variant, ask:

1. **Is the chart / UI still parseable?** Categories distinguishable, state legible.
2. **Did any pair collapse?** Red-vs-green pair becoming the same hue is the classic failure.
3. **Does the takeaway still come across?** A chart's headline message must survive desaturation.

If the answer to (2) is yes:

- Add a non-color cue (icon, label, shape).
- Switch the palette: prefer a Colour-Universal-Design set such as Okabe-Ito (`_colors.academic_palette`), which already avoids simultaneous red + green.
- For sequential data, use a single-hue luminance ramp (Viridis-style) instead of red → green.

## The math

The script implements the MACHADO, OLIVEIRA & FERNANDES (2009) precomputed CVD matrices at severity 1.0 ("dichromat" / fully missing cone type). The matrices are applied in **linear sRGB**: the source is degamma-decoded before the matrix, then re-encoded with the standard sRGB transfer.

This is not the only model. BRETTEL / VIÉNOT / MOLLON (1997) work in LMS space and are often cited. MACHADO et al. matrices are easier to ship (just three numbers per output channel), faithful at severity 1, and used by major design tools (e.g., Figma's CVD preview).

## Limitations

- Only severity 1 (full dichromacy). Real CVD ranges from mild anomalous trichromacy to full dichromacy.
- Achromatopsia (no cones at all) has no matrix of its own; `--grayscale` is the render to look at for that case.
- The simulation is per-pixel: it does not account for surround / context adaptation.
- Animated content needs frame-by-frame simulation; this script handles still images only.

## Continuous integration (CI)

Combine with `sprezzature-accessibility-lint` (from the `sprezzature-accessibility` package) to catch color-only state at the markup layer, and the CVD simulation to catch palette failures at the design layer. Continuous integration (CI) is the practice of running checks automatically on every code change; a CI job that produces the grid mosaic as an artifact is a low-friction review step, since a reviewer can glance at the mosaic instead of running the script locally:

```yaml
- name: CVD preview
  run: |
    pip install sprezzature-colors
    sprezzature-colors-cvd public/hero.png --grid \
            --out artifacts/hero-cvd-grid.png
- uses: actions/upload-artifact@v4
  with: { name: cvd, path: artifacts/ }
```

## Checklist

- [ ] Run on every UI screenshot before review.
- [ ] Run on every chart before publishing.
- [ ] Pair with `sprezzature-accessibility-lint` to catch `color-only-state` markup violations.
- [ ] If a pair collapses, change the palette or add a non-color cue.
- [ ] Cite the model in design docs ("MACHADO et al. 2009, severity 1.0").
