# Contrast audit — `sprezzature-colors-contrast`

Audit a palette's (foreground, background) pairs against the contrast-ratio thresholds published by the Web Content Accessibility Guidelines (WCAG, the reference standard for making web content usable by people with disabilities), and propose the nearest accessible alternative for failing pairs. The contrast ratio itself is a single number from 1 (identical brightness, unreadable) to 21 (pure black on pure white): the higher it is, the easier the two colors are to tell apart at a glance. Deterministic, no model; the arithmetic is standard library only.

## What this tool is — and isn't

This tool **flags WCAG contrast failures** on the (foreground, background) pairs that co-occur in a rendered theme — light labels on light surfaces, dark labels (`*-dark`) on dark surfaces, theme-neutral brand accents on every surface (`--all-pairs` restores the exhaustive cross-product) — and **proposes a minimal-edit nudge** along the OKLCH lightness axis. The proposed fix preserves the WCAG ratio at the cost of moving along the L axis only: same hue, same chroma, brighter or darker. That is a useful starting suggestion when nothing else is on the line; it is **not** a designer-approved replacement.

Brand-critical colours (the primary CTA, accent colours that carry semantic meaning across the product, anything tied to a logo) should be reviewed by a designer. A neighbour that passes 4.5:1 can still violate brand identity, tonal hierarchy, or the relationship between sibling tokens. Treat `--fix` as a flagged failure with a proposed minimum edit, not as the final swatch.

## Why it matters

WCAG 2.x contrast thresholds:

| Threshold | Use |
|---|---|
| 4.5:1 | Body text, normal weight (WCAG SC 1.4.3 AA). |
| 3:1 | Large text (≥ 18 pt, ≥ 14 pt bold) and UI components (WCAG SC 1.4.11 AA). |
| 7:1 | Body text (WCAG SC 1.4.6 AAA). |

Designers iterate on palettes by eye. An automated audit catches the pairs the eye missed: typically `label-secondary` on `surface-tertiary` and accent colours on accent surfaces. The "fix" suggester saves the manual trial-and-error: it walks the OKLCH lightness axis and returns the closest hue that meets the target.

## Run

Installed, the command is `sprezzature-colors-contrast` (or `sprezzature-colors contrast`). From a source checkout of the package, `python scripts/audit_contrast.py` takes the same arguments.

```bash
# Audit the skill's built-in palette at AA body (4.5:1)
sprezzature-colors-contrast

# AAA threshold
sprezzature-colors-contrast --target 7

# Large-text / UI threshold
sprezzature-colors-contrast --target 3

# Audit an external palette and suggest fixes
sprezzature-colors-contrast --palette my-palette.json --fix

# JSON output for CI
sprezzature-colors-contrast --format json

# Exhaustive cross-product, cross-theme pairs included
sprezzature-colors-contrast --all-pairs
```

Exit code is `0` when every checked pair passes, `1` when any pair fails, `2` when the palette yields no pair to check. The exit code is the same regardless of `--fix`; the script reports the failures even when it suggests alternatives.

## Palette format

Two shapes are accepted.

**Flat:**

```json
{
  "label-primary": "#000000",
  "surface-primary": "#FFFFFF"
}
```

**Nested with variants (Tailwind-style):**

```json
{
  "brand-blue": { "DEFAULT": "#007AFF", "dark": "#0A84FF", "light": "#CCE4FF" },
  "label-primary": { "DEFAULT": "#000000", "dark": "#FFFFFF" }
}
```

Variant names other than `DEFAULT` become suffixes (`brand-blue-dark`, `brand-blue-light`).

## Which pairs are checked

| Role pattern | Treated as |
|---|---|
| `label-…` (not `-light`) | foreground (text / icon) |
| `brand-…` (not `-light`) | foreground |
| `surface-…` | background |

`-light` brand tints are wash backgrounds and are never checked as text. `-dark` variants are the dark theme's foregrounds and surfaces. By default a pair is checked only when it can co-occur in a rendered theme: an unsuffixed label goes on unsuffixed surfaces, a `-dark` label on `-dark` surfaces, and a brand accent on every surface. `--all-pairs` drops that filter.

Other roles are ignored. Rename your palette keys to fit this scheme, or extend the prefix tests in `is_foreground` / `is_background`. A palette with no matching key produces no pair at all: the script says so on standard error and exits `2`, so an unchecked palette cannot pass for a checked one.

## The suggestion search

For each failing pair, the script:

1. Converts the foreground to OKLCH, a color model published by Björn OTTOSSON (2020) in which moving the lightness value by a fixed amount produces a change the eye perceives as equally large everywhere in the color space, unlike raw RGB.
2. Walks the L axis from 0.00 to 1.00 in 0.01 steps, keeping C (chroma) and H (hue) fixed.
3. Returns the candidate with the smallest `|ΔL|` that meets the target ratio.

Adjusting only L preserves the hue and saturation of the original choice: you get a brighter or darker variant of the same colour, not a different colour entirely. This matches how designers usually want to fix contrast.

If no candidate meets the target across the full L axis, the suggestion is omitted. That outcome usually means the background itself is too close to mid-gray; widen the target's background variant instead of the foreground.

## Standards cited

- WCAG 2.x SC 1.4.3 — Contrast (Minimum).
- WCAG 2.x SC 1.4.6 — Contrast (Enhanced).
- WCAG 2.x SC 1.4.11 — Non-text Contrast.
- OKLab / OKLCH: Björn OTTOSSON, "A perceptual color space for image processing", <https://bottosson.github.io/posts/oklab/>.

## Continuous integration (CI)

Continuous integration (CI) is the practice of running checks automatically on every code change, in this case as a step in a GitHub Actions workflow, so a contrast regression is caught before it reaches production rather than after a user reports it:

```yaml
- name: Contrast audit
  run: |
    pip install sprezzature-colors
    sprezzature-colors-contrast \
            --palette tokens/colors.json \
            --target 4.5 --format json > artifacts/contrast.json
- uses: actions/upload-artifact@v4
  with: { name: contrast-audit, path: artifacts/ }
```

The audit's exit code is the gating signal: non-zero on any failing pair.

## Checklist

- [ ] Audit at AA body (4.5:1) before shipping any new palette.
- [ ] Audit at AAA (7:1) for any long-form reading surface.
- [ ] When a fix is suggested, treat it as a starting point: the OKLCH neighbour is the closest visual match on the L axis, but a designer still picks the final swatch for any brand-critical colour.
- [ ] Re-audit after every palette tweak.
