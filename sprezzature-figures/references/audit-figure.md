# Figure auditor — rule catalogue

Static rules for `audit_figure.py`. Each rule is decidable from the
input (Vega-Lite JSON, matplotlib SVG, or an HTML document with
`<figure>` blocks). No browser, no model, no network.

## Rule catalogue

| Rule ID | Severity | Applies to | What the parser flags | False-positive note |
|---|---|---|---|---|
| `missing-axis-title` | error | Vega-Lite, matplotlib SVG | Quantitative axis without a non-empty `title` (Vega) or `<title>` in the SVG's axis group. | Sparklines with a single visible metric: pass `--ignore missing-axis-title`. |
| `dual-y-axis` | error | Vega-Lite | Two `y` encodings resolved to independent scales (`resolve.scale.y = "independent"`). | Rare intentional twin-axis charts; always misleading, keep the error. |
| `truncated-baseline` | warning | Vega-Lite (bar mark) | `mark.type` in `("bar", "rect")` with a `y` scale carrying `zero: false`. | Ratio scales (`log`, `pow`, `sqrt`, `symlog`) are auto-exempted. |
| `pie-3d` | error | Vega-Lite, HTML | `mark.type == "arc"` with a rotate/skew transform, or an SVG `<g>` with `transform="matrix(...)"` containing a perspective. | None: 3D pies are always wrong. |
| `rainbow-palette` | error | Vega-Lite (color scheme), matplotlib SVG | `scale.scheme` in `("rainbow", "sinebow", "hsv", "hsl", "spectral" on quantitative)`; or a matplotlib SVG whose color palette matches `jet`/`hsv`/`rainbow`. | Explicit spectrum renderings: `--ignore rainbow-palette`. |
| `cvd-unsafe` | warning | Vega-Lite (categorical) | Categorical palette contains a red + green pair (hex distance thresholded) with no lightness delta. | Delegated preview: run `sprezzature-colors/scripts/simulate_cvd.py` on the rendered PNG. |
| `missing-polarity` | warning | Vega-Lite, matplotlib SVG | Axis title matches a known polarised-metric pattern (`latency`, `response`, `error`, `bug`, `conversion`, `revenue`, `cost`, `churn`, `retention`, …) without a trailing polarity tag `(higher is better)` / `(lower is better)` / `(target …)`. | Metrics with genuinely ambiguous polarity: `--ignore missing-polarity`. |
| `chartjunk` | warning | Vega-Lite, matplotlib SVG | Vega `config` with `background: gradient(...)` or `mark.shadow`; matplotlib SVG with `<filter>` blur/shadow on marks. | Editorial illustrations: `--ignore chartjunk`. |
| `role-img-missing` | error | HTML | `<figure>` without `role="img"` and no `<figcaption>`. | Purely decorative figures: mark `role="presentation"` and `--ignore role-img-missing`. |
| `alt-missing` | error | HTML (embedded `<img>`) | `<img>` inside a `<figure>` with no `alt` attribute. Empty `alt=""` is correct for decorative; omitting is not. | Delegated to `sprezzature-accessibility/scripts/lint_a11y.py` for standalone `<img>` outside a figure. |
| `pie-too-many-slices` | warning | Vega-Lite | `mark.type == "arc"` with more than 4 category values in the data source. | Legitimate small-count breakdowns: override with `--ignore pie-too-many-slices`. |
| `zero-encoded-as-null` | warning | Vega-Lite | `data.format.parse` maps a field to `"null"` when the sample contains zero values. | Rare; usually a real bug. |

## Severity semantics

- `error` — exit non-zero. The chart will mislead most readers.
- `warning` — exit zero by default; exit non-zero under `--strict`.
- `info` — exit zero always; printed for reviewer awareness.

## Output shapes

### Human-readable (default)

```text
audit_figure.py fig.json
  fig.json:1:1  error   missing-axis-title  y encoding has no title
  fig.json:1:1  error   dual-y-axis         two independent y scales
  fig.json:1:1  warn    missing-polarity    "response_time_ms" looks polarised
2 errors, 1 warning
```

### JSON (`--json`)

```json
{
  "path": "fig.json",
  "findings": [
    {"rule": "missing-axis-title", "severity": "error", "message": "y encoding has no title"},
    {"rule": "dual-y-axis", "severity": "error", "message": "two independent y scales"},
    {"rule": "missing-polarity", "severity": "warning", "message": "\"response_time_ms\" looks polarised"}
  ],
  "summary": {"errors": 2, "warnings": 1, "info": 0}
}
```

## Auto-fix (`--fix`)

A small subset of rules is mechanically fixable:

- **`missing-polarity`** — the fixer appends the polarity tag inferred
  from the metric name (`response_time_ms` → `(lower is better)`).
- **`role-img-missing`** — adds `role="img"` to the `<figure>`.
- **`alt-missing`** — adds `alt=""` (empty) to the `<img>`, deferring
  the real description to `sprezzature-vision/scripts/alt_from_ollama.py`.

All other rules require a design decision and are **not** auto-fixed.
`audit_figure.py --fix` iterates until convergence; idempotent.

## Composition

Pair with the runtime auditors for a full pre-ship gate:

```bash
python sprezzature-figures/scripts/audit_figure.py fig.json                     # static viz rules
python sprezzature-colors/scripts/audit_contrast.py --palette palette.json      # WCAG on the palette
python sprezzature-colors/scripts/simulate_cvd.py fig.png --grid                # CVD preview
python sprezzature-accessibility/scripts/lint_a11y.py public/report.html        # a11y around it
python sprezzature-ux-laws/scripts/audit_laws_of_ux.py public/report.html       # Laws of UX
```
