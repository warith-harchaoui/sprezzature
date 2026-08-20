# Auditor rule catalogue for `audit_figure.py`

`audit_figure.py` is a static checker: it reads a chart's source (a
Vega-Lite JSON spec, a matplotlib-emitted SVG, or an HTML page containing
`<figure>` blocks) and flags the small set of data-visualization mistakes
that tend to survive human review because they are easy to miss at a
glance and easy to catch by parsing the source directly. No model, no
network, stdlib plus PyYAML. This file documents every rule actually
implemented, its severity, its input format, and where it produces false
positives.

## What the module docstring promises versus what runs

`audit_figure.py`'s own docstring lists twelve rule names. Reading the
rule-implementing code (`rules_for_vega`, `_unit_rules`, `rules_for_html`,
`rules_for_svg`) finds eleven implemented, plus three more that exist in
code but are absent from that docstring list. One promised rule,
`zero-encoded-as-null`, is not implemented anywhere in the file, this is
worth saying plainly rather than pretending the rule runs: if you are
relying on the auditor to catch a chart that encodes a zero value as a
missing point, it will not, today.

## Rule catalogue

Findings apply to one of three input formats: **Vega**, a Vega-Lite v5
JSON spec; **SVG**, a matplotlib-emitted SVG; **HTML**, a page with
`<figure>` blocks. A rule listed under only one format is not checked in
the others.

| Rule | Severity | Format(s) | What triggers it |
|---|---|---|---|
| `missing-axis-title` | error | Vega | A quantitative x or y channel appears on at least one visible layer with no title set anywhere across the chart (checked chart-wide, so one titled layer covers an untitled reference line or diagonal on the same axis). An axis explicitly hidden with `"axis": null` or `"axis": false` is exempt, that is a legitimate choice for vector fields or small-multiple insets, not an oversight. |
| `dual-y-axis` | error | Vega | An explicit `resolve.scale.y = "independent"` appears at any layering level. Two layers that both encode `y` without that resolve (a confidence band and its center line, an error bar and its point) share a scale by default in Vega-Lite and are correctly **not** flagged; an earlier version of this rule used to false-flag exactly that pattern and has been removed. |
| `truncated-baseline` | warning | Vega | A `bar` or `rect` mark's y-encoding has `scale.zero: false` on a linear scale. Log, power, square-root, and symlog scales are exempt, a non-zero baseline is the correct choice on those. |
| `pie-3d` | error | Vega, SVG | Vega: an `arc` mark whose `transform` array contains an entry with both `"angle"` and the substring `"rotate"` (a heuristic proxy for a perspective/3D effect, not a direct 3D-flag field in the spec). SVG: a `transform="matrix(...)"` attribute containing `perspective`. |
| `pie-too-many-slices` | warning | Vega | An `arc` mark whose inline `data.values` array has more than 4 entries. Only fires when the data is inlined in the spec; a chart that binds to external data is not checked by this rule. |
| `rainbow-palette` | error | Vega, SVG | Vega: a `color`, `fill`, or `stroke` channel's `scale.scheme` is one of `rainbow`, `sinebow`, `hsv`, `hsl`, `jet` (case-insensitive). `viridis` and the other perceptually-uniform schemes are not in this set and pass clean. SVG: the literal substrings `jet`, `hsv`, or `rainbow` appear anywhere in the file, a coarse text match, not a semantic one, so a filename or comment containing one of those words would also trigger it. |
| `cvd-unsafe` | warning | Vega | A `color`/`fill`/`stroke` channel's explicit `scale.range` list contains both a red-family hex (from a fixed set: `#FF0000`, `#F00`, `#E11`, `#D22`, `#D00`, `#FF3B30`, `#EF4444`, `#DC2626`) and a green-family hex (`#00FF00`, `#0F0`, `#22C55E`, `#34C759`, `#16A34A`, `#059669`) with no third channel to separate them. This only checks an explicit hex range; a named `scheme` is not scanned by this rule. |
| `missing-polarity` | warning | Vega | A quantitative x/y axis has a title whose lowercased text contains one of the metric-name substrings in `_style.POLARITY_HINTS` (`latency`, `cost`, `revenue`, `accuracy`, and the rest of that fixed list) but does **not** also contain a direction phrase (`higher is better`, `lower is better`, `target`, or the French equivalents `plus haut`, `plus bas`, `cible`). A metric name outside that fixed hint list is never flagged, even if it genuinely has a polarity a human would recognize. |
| `chartjunk` | warning | Vega, SVG | Vega: the mark object sets a truthy `shadow` key, or the chart's `config.background` / top-level `background` string contains `gradient`. SVG: the file contains an `<filter>` element combined with `feDropShadow` or `feGaussianBlur`. |
| `role-img-missing` | error | HTML | A `<figure>` element whose `role` attribute is not `"img"` and which has no `<figcaption>` child. A figure that sets `role="img"`, or that has a caption, passes either way; the rule only fires when neither accessibility signal is present. |
| `alt-missing` | error | HTML | An `<img>` element nested inside a `<figure>` block with no `alt` attribute at all (an empty `alt=""`, which is the correct markup for a purely decorative image, does **not** trigger this, only a missing attribute does). |
| `grid-cell-rounded` | warning | Vega | A `rect` mark (the mark type used for heatmap/matrix cells) sets any `cornerRadius*` property above 1. Not documented in the module's docstring rule list, but implemented and active. |
| `bar-baseline-rounded` | warning | Vega | A `bar` mark sets `cornerRadius` (rounding every corner) instead of `cornerRadiusEnd` (rounding only the value end, leaving the baseline square). Also undocumented in the module docstring, also active. |
| `radius-over-cap` | warning | Vega, SVG | Vega: any `cornerRadius*` property on a mark exceeds 16px, the project's corner-radius cap (see the house style's corner policy). SVG: any `rx="…"` attribute on the file exceeds 16. A third undocumented-but-active rule. |
| `zero-encoded-as-null` | *(not implemented)* | *(none)* | Listed in the module docstring's rule summary; no corresponding check exists in `rules_for_vega`, `_unit_rules`, `rules_for_html`, or `rules_for_svg` as of this writing. Do not rely on it. |

## Composition rules versus per-mark rules

Two of the Vega rules, `missing-axis-title` and `dual-y-axis`, are
**composition** checks: they look at the whole spec, walking every nested
`layer` / `concat` / `hconcat` / `vconcat` / `facet` / `repeat` container
via `_iter_specs`, because the thing they check (a shared axis title, an
independent-scale resolve) can legitimately live at any layering level,
not necessarily on the top spec. Everything else runs per mark-bearing
"unit" spec, found by the sibling walk `_iter_units`, so a rule like
`truncated-baseline` is evaluated separately for each bar layer inside a
composed chart, not once for the whole thing.

## Severities and the escape hatches

Findings carry `error`, `warning`, or `info`. The CLI's exit code is `1`
when any `error` finding exists, or when `--strict` is set and any
`warning` exists; otherwise `0`. Two flags narrow what runs:

- **`--ignore rule-a,rule-b`** drops specific rule IDs from the output.
- **`--only rule-a,rule-b`** keeps only the listed rule IDs (the code
  treats `--ignore` and `--only` as independent filters you could combine,
  though combining them is rarely useful).

## Known false-positive shapes

- **`rainbow-palette` on SVG** is a bare substring search across the whole
  file text, not a check that the substring actually names a colormap in
  use. An SVG whose `<title>` or embedded metadata happens to contain the
  word "rainbow" for an unrelated reason will trigger it.
- **`cvd-unsafe`** only inspects an explicit hex `scale.range`; a chart
  that reaches the same red-and-green collision through a named `scheme`
  string, or through per-datum `color` values set outside the `scale`
  block, is invisible to this rule.
- **`missing-polarity`** is keyed to a fixed, English-biased substring
  list (`POLARITY_HINTS` in `_style.py`). A metric named something the
  list does not recognize, or an axis titled only in French without the
  literal substrings the rule checks for, will not be flagged even when a
  human reviewer would immediately see the polarity.
- **`pie-too-many-slices`** only fires on inlined `data.values`; a pie
  chart backed by an external data URL or a named dataset reference is not
  counted, regardless of how many slices it actually renders.

## Usage

```bash
python -m sprezzature_figures_scripts.audit_figure fig.json                       # human-readable
python -m sprezzature_figures_scripts.audit_figure public/*.html --json           # CI, machine-readable
python -m sprezzature_figures_scripts.audit_figure fig.svg --strict               # warnings fail the build too
python -m sprezzature_figures_scripts.audit_figure fig.json --ignore truncated-baseline,chartjunk
```

Passing a directory instead of a file expands to every `.json`, `.svg`,
`.html`, and `.htm` file found under it (`iter_files`), so a whole
`./explain/` or `./causal/` output directory from `explain_model.py` or
`causal_estimate.py` can be audited in one call, as `SKILL.md`'s tool
composition example does.
