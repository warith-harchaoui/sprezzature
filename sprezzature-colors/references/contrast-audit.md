# Contrast audit: `audit_contrast.py`

Audit a palette's (foreground, background) pairs against the WCAG contrast ratio thresholds, and propose the nearest accessible alternative for failing pairs. Deterministic, stdlib-only, no model.

## What this tool is (and isn't)

This tool **flags WCAG contrast failures** on the (foreground, background) pairs that co-occur in a rendered theme by default: light labels on light surfaces, dark labels (`*-dark`) on dark surfaces, theme-neutral brand accents on every surface. Pass `--all-pairs` to restore the exhaustive cross-theme cross-product (useful for a full audit, noisy as a default: it flags things like a light-theme label on a dark surface, a pairing that never actually renders together). It then **proposes a minimal-edit nudge** along the OKLCH lightness axis. The proposed fix preserves the WCAG ratio at the cost of moving along the L axis only: same hue, same chroma, brighter or darker. That is a useful starting suggestion when nothing else is on the line; it is **not** a designer-approved replacement.

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

```bash
# Audit the skill's built-in palette at AA body (4.5:1)
python scripts/audit_contrast.py

# AAA threshold
python scripts/audit_contrast.py --target 7

# Large-text / UI threshold
python scripts/audit_contrast.py --target 3

# Audit an external palette and suggest fixes
python scripts/audit_contrast.py --palette my-palette.json --fix

# JSON output for CI
python scripts/audit_contrast.py --format json

# Exhaustive cross-product, cross-theme pairs included
python scripts/audit_contrast.py --all-pairs
```

Exit code is `0` when every checked pair passes, `1` when any pair fails. The exit code is the same regardless of `--fix`; the script reports the failures even when it suggests alternatives.

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
| `label-…` (not `-light` or `-dark`) | foreground (text / icon) |
| `brand-…` (not `-light` or `-dark`) | foreground |
| `surface-…` | background |

Other roles are ignored. Re-name your palette keys to fit this scheme, or extend the regexes in `is_foreground` / `is_background`.

By default, a `-dark`-suffixed foreground is only checked against a `-dark`-suffixed surface (and vice versa for light); theme-neutral `brand-…` accents are checked against every surface. This avoids flagging pairs that never actually render together, such as a light-theme label composited against a dark surface. Pass `--all-pairs` to check the full cross-product instead, including those cross-theme pairs.

## The suggestion search

For each failing pair, the script:

1. Converts the foreground to OKLCH (Björn Ottosson's published matrices).
2. Walks the L axis from 0.00 to 1.00 in 0.01 steps, keeping C (chroma) and H (hue) fixed.
3. Returns the candidate with the smallest `|ΔL|` that meets the target ratio.

Adjusting only L preserves the hue and saturation of the original choice: you get a brighter or darker variant of the same colour, not a different colour entirely. This matches how designers usually want to fix contrast.

If no candidate meets the target across the full L axis, the suggestion is omitted. That outcome usually means the background itself is too close to mid-gray; widen the target's background variant instead of the foreground.

## Standards cited

- WCAG 2.x SC 1.4.3: Contrast (Minimum).
- WCAG 2.x SC 1.4.6: Contrast (Enhanced).
- WCAG 2.x SC 1.4.11: Non-text Contrast.
- OKLab / OKLCH: Björn Ottosson, "A perceptual color space for image processing", <https://bottosson.github.io/posts/oklab/>.

## CI integration

```yaml
- name: Contrast audit
  run: |
    python3 scripts/audit_contrast.py \
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
