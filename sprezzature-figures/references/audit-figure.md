# `audit_figure.py` rule catalogue

`audit_figure.py` is a static checker: it reads a rendered chart (an SVG
file, or an HTML page containing `<figure>` blocks) and flags the small set
of data-visualization mistakes that tend to survive human review because
they are easy to miss at a glance and boring to check by hand.

Because every figure in this stack is authored as SVG directly, the
rendered markup *is* the source. There is no separate chart spec to audit,
so every rule below reads the output itself.

That also sets the ceiling on what this tool can tell you. These are
surface rules read off the markup: a chart can pass all of them and still
encode the wrong variable, mislead on scale, or simply look bad. The
auditor is a gate against careless output, not a review.

## Rule catalogue

Findings apply to one of two input formats: **SVG**, a chart file; **HTML**,
a page with `<figure>` blocks. A rule listed under only one format is not
checked in the other.

| Rule | Severity | Format(s) | What triggers it |
|---|---|---|---|
| `pie-3d` | error | SVG | A `transform="matrix(...)"` attribute containing `perspective`. |
| `rainbow-palette` | error | SVG | The literal substrings `jet`, `hsv`, or `rainbow` appear anywhere in the file. A coarse text match, not a semantic one, so a filename or comment containing one of those words also triggers it. `viridis` and the other perceptually-uniform ramps are not in this set and pass clean. |
| `chartjunk` | warning | SVG | The file contains a `<filter>` element combined with `feDropShadow` or `feGaussianBlur`. |
| `radius-over-cap` | warning | SVG | Any `rx="…"` attribute exceeds 16, the project's corner-radius cap (see the house style's corner policy). |
| `unformatted-tick` | warning | SVG | At least three distinct tick labels are raw magnitudes of five digits or more (`200000` rather than `200k` or `200 000`), so a reader has to count zeros. Four-digit years are exempt. |
| `iso-date-tick` | warning | SVG | Four or more tick labels are raw ISO dates (`2024-07-01`). A time axis reading that twenty-four times, rotated to fit, is machine output shown to a human. |
| `role-img-missing` | error | HTML | A `<figure>` element whose `role` attribute is not `"img"` and which has no `<figcaption>` child. A figure that sets `role="img"`, or that has a caption, passes either way; the rule only fires when neither accessibility signal is present. |
| `alt-missing` | error | HTML | An `<img>` element nested inside a `<figure>` block with no `alt` attribute at all. An empty `alt=""`, the correct markup for a purely decorative image, does **not** trigger this; only a missing attribute does. |

## Severities and the escape hatches

Findings carry `error`, `warning`, or `info`. The CLI's exit code is `1`
when any `error` finding exists, or when `--strict` is set and any
`warning` exists; otherwise `0`. Two flags narrow what runs:

- **`--ignore rule-a,rule-b`** drops specific rule IDs from the output.
- **`--only rule-a,rule-b`** keeps only the listed rule IDs (the code
  treats `--ignore` and `--only` as independent filters you could combine,
  though combining them is rarely useful).

## Known false-positive shapes

- **`rainbow-palette`** is a bare substring search across the whole file
  text, not a check that the substring actually names a colormap in use. An
  SVG whose `<title>` or embedded metadata happens to contain the word
  "rainbow" for an unrelated reason will trigger it.
- **`unformatted-tick`** cannot tell a tick label from any other five-digit
  run of text between tags, so a data label or an annotation carrying a
  large raw number counts toward the three-hit threshold.
- **`iso-date-tick`** likewise matches any ISO-shaped date in text content,
  including one deliberately spelled out in a caption or a footnote.

## Usage

```bash
python -m sprezzature_figures_scripts.audit_figure fig.svg                        # human-readable
python -m sprezzature_figures_scripts.audit_figure public/*.html --json           # CI, machine-readable
python -m sprezzature_figures_scripts.audit_figure fig.svg --strict               # warnings fail the build too
python -m sprezzature_figures_scripts.audit_figure fig.svg --ignore chartjunk
```

Passing a directory instead of a file expands to every `.svg`, `.html`, and
`.htm` file found under it (`iter_files`), so a whole `./explain/` or
`./causal/` output directory from `explain_model.py` or
`causal_estimate.py` can be audited in one call, as `SKILL.md`'s tool
composition example does.
