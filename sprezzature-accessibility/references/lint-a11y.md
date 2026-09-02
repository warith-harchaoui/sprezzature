# A11y linter: `lint_a11y.py`

Static, no-DOM lint for CI and pre-commit hooks. No browser, no JS execution; it runs over HTML source. Catches **14 source-decidable WCAG / WAI-ARIA failures**.

**Not a replacement for axe-core, Pa11y, or Lighthouse.** Those run a real browser and catch the dynamic / runtime failures that no static parser can see: colour-only state after JS, focus order after a route change, name/role/value after ARIA mutation, contrast after a runtime theme switch, live-region announcement order. Use `lint_a11y.py` in pre-commit; use axe-core (or Pa11y, or Lighthouse) in your end-to-end suite. Run both.

## Install

The linter is stdlib-only: no `pip install` required. Python 3.9+.

## Run

```bash
# A single page
python scripts/lint_a11y.py public/index.html

# A whole tree
python scripts/lint_a11y.py public/

# JSON output for CI
python scripts/lint_a11y.py --format json public/index.html

# Skip a couple of rules
python scripts/lint_a11y.py --ignore heading-skip,motion-no-reduce-guard public/
```

Exit code is `0` when no findings, `1` when any finding is present. Pipe-friendly for CI.

## Rules

Each rule has a stable identifier so the `--ignore` flag and JSON output reference them.

| Rule | What it catches | Standard |
|---|---|---|
| `html-missing-lang` | `<html>` without a `lang` attribute. | WCAG SC 3.1.1 |
| `img-missing-alt` | `<img>` with no `alt` attribute at all (different from `alt=""`). | WCAG SC 1.1.1, W3C image decision tree. |
| `img-redundant-aria` | `alt=""` *plus* `role="presentation"` or `aria-hidden="true"`. `alt=""` alone is enough. | W3C WAI tutorial on decorative images. |
| `a-missing-href` | `<a>` without `href` (should be `<button>`). | WAI-ARIA Authoring Practices. |
| `a-empty` | `<a>` with no text, no `aria-label`, no `title`, no inline image. | WCAG SC 2.4.4. |
| `button-empty` | `<button>` with no text, no `aria-label`, no inline icon. | WCAG SC 4.1.2. |
| `div-onclick` | `<div>` / `<span>` with `onclick` but no `role="button"` and no `tabindex`. | WCAG SC 2.1.1. |
| `input-missing-label` | `<input>` not wrapped in a `<label>` and not referenced by a `<label for=>`. | WCAG SC 3.3.2. |
| `dialog-missing-close` | `<dialog>` without an obvious close affordance (a button with `value="cancel"`, `autofocus`, or accessible name "Close" / "Cancel" / "Fermer" / "Annuler" / "Schließen"). | WAI-ARIA modal pattern. |
| `tabindex-positive` | `tabindex` ≥ 1, which breaks DOM tab order. | WAI-ARIA Authoring Practices. |
| `aria-hidden-interactive` | `aria-hidden="true"` on a `<button>` / `<a>` / `<input>` / `<select>` / `<textarea>`, which removes the control from AT but leaves it focusable. | WAI-ARIA spec. |
| `heading-skip` | Heading levels jump downward (e.g. `<h2>` followed by `<h4>`). | WCAG SC 1.3.1. |
| `color-only-state` | Tailwind `*-red-*` / `*-green-*` token on an element with no text and no inline icon. State must not rely on color alone. | WCAG SC 1.4.1. |
| `motion-no-reduce-guard` | `animate-{spin,ping,pulse,bounce}`, `transition-transform`, or `transition-all` without a `motion-reduce:` peer. | WCAG SC 2.3.3 / `prefers-reduced-motion`. |

## When a finding is wrong

Three escape valves:

1. **`--ignore rule-id[,rule-id…]`** for a single run.
2. **Fix the markup.** Most findings have a one-line fix (add `alt=""`, wrap in `<label>`, add `motion-reduce:transition-none`).
3. **File-level suppression** is not supported. It would invite the linter to be silenced for a whole page. Per-element exemption belongs in the markup itself (the `role="button"` + `tabindex` escape for `div-onclick`, for example).

## CI integration

```yaml
# .github/workflows/a11y.yml
- name: A11y lint
  run: |
    python3 scripts/lint_a11y.py --format json public/ > a11y-report.json
    python3 -c "import json,sys; d=json.load(open('a11y-report.json')); sys.exit(1 if d['findings_total'] else 0)"
```

The linter's exit code is also CI-friendly on its own; the JSON dump above is just for an artifact.

## What this linter does *not* check

- Live ARIA state (`aria-expanded`, `aria-selected` consistency): depends on JS behavior.
- Color contrast: see `references/dataviz-color-palettes.md` and `audit_contrast.py` (planned).
- Focus order within a JS-built widget: needs runtime.
- Captioned audio / video presence: `<track>` placement depends on the source's content.
- Form error association (`aria-describedby` between input and a sibling message): pattern is too varied for a static rule.

For those, pair with axe-core in dev tools and manual testing with a screen reader.

## Colour-blindness & grayscale: the image-layer check

Static markup can't tell whether colour is *load-bearing*: whether two series
collapse to one hue for a red-green–blind reader, or a diverging +/− sign
vanishes in grayscale. That needs the rendered pixels, so it lives one layer
out from the linter: `sprezzature-colors/scripts/simulate_cvd.py`.

It reinforces the two existing sprezzature-figures steps rather than replacing them:

- **make** (the Ralph Eyeball Loop): after the render step, run
  `python sprezzature-colors/scripts/simulate_cvd.py render.png` to get a contact
  sheet (grayscale + protanopia + deuteranopia + tritanopia) and *look*. The
  loop becomes **render → simulate → look**.
- **audit** (`audit_figure.py`, static): the auditor flags rainbow ramps and
  filters in the markup; the simulator catches what only shows in pixels. Same
  goal (colour is never the sole channel), two layers.

The transform is done in **linear light** (sRGB → linear → Machado-2009 matrix
or luminance → sRGB), the physically correct pipeline; applying the matrices to
gamma-encoded sRGB is a common shortcut that shifts every colour. When a series
or a sign becomes unreadable in the sheet, add a second channel: a sign, a value
label, a marker shape, or a stroke style.

## Checklist (when adding a new rule)

- [ ] Stable identifier (kebab-case, suggestive of the violation).
- [ ] Citation of the WCAG SC or WAI-ARIA section in this doc.
- [ ] Implementation in `lint_a11y.py`, registered in `ALL_RULES`.
- [ ] Smoke test on at least one positive fixture and one negative.
- [ ] Validator green (`python sprezzature-ui/scripts/validate.py`).
