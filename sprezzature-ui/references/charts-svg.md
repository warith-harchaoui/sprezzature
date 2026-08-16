# Charts — hand-authored SVG

Source for colors: <https://harchaoui.org/warith/colors/> (see also `references/color-psychology.md`).
Source for the chart method: the `dataviz` skill (form heuristic, color formula,
validated palette, mark specs, interaction, accessibility) — this file is that
method's house-style parameters for sprezzature-ui's stack.

## When to consult this file

- Any chart, graph, dashboard tile, or data visualization
- Sparklines, distributions, time series, categorical comparisons

## Library choice

The skill hand-authors **inline SVG** directly in the generated markup. No chart
library, no JSON spec to interpret, no CDN script, no build step — the SVG the
skill writes *is* the chart. No D3, no Chart.js, no Recharts, no Vega.

```html
<!-- The chart is inline markup in the page, not a separate embed step. -->
<figure class="rounded-[10px] bg-surface-secondary p-4 dark:bg-surface-secondary-dark">
  <figcaption class="sr-only">Weekly active users</figcaption>
  <svg viewBox="0 0 480 220" role="img" aria-labelledby="chart-title" class="w-full h-auto">
    <title id="chart-title">Weekly active users</title>
    <!-- marks go here -->
  </svg>
</figure>
```

Because the SVG is inline in the HTML (not loaded via `<img src>` or a template
string with no DOM presence), its `fill`/`stroke` can use `currentColor` and pick
up Tailwind's `text-{token} dark:text-{token}` utilities on a wrapping element —
see "Dark-mode aware" below.

## House defaults

1. **Rounded corners at 10 px** on every bar/rect mark (SVG `rx="10" ry="10"`) and
   on the chart container (`rounded-[10px]`).
2. **Colors from `color-psychology.md`** — no rainbow palettes.
3. **Roboto** for every text element (labels, titles, legends): `font-family`
   attribute on each `<text>`, or inherited from the page if the SVG sets none.
4. **No top spine, no right spine** — draw only the bottom (x) and left (y)
   baselines as `<line>` elements; never a full rect frame around the plot area.
5. **No tick marks** on either axis — labels alone read fine and look cleaner
   (skip the short perpendicular `<line>` a tick usually gets).
6. **No gridlines** unless explicitly needed.
7. **No 3D**, no drop shadows, no gradients (except a single `<linearGradient>`
   fill for area charts).
8. **Tabular numerals** for value labels: `font-variant-numeric: tabular-nums`
   (inline `style` or a CSS class) on any `<text>` showing a number.
9. **Dark-mode aware** — see below.
10. **Title above** in body weight; subtitle below in label-secondary.
11. **State the polarity** of every measured axis — *higher is better*, *lower is
    better*, or *target = N*. See "Polarity — higher or lower is better" below.

## Polarity — higher or lower is better

Every quantitative axis encodes a value the reader needs to read in 3 seconds, and "is this trend good or bad?" is the first question they ask. **Whenever the answer is well-defined for the chart's context, state it on the chart.** Don't assume the reader shares your domain instinct.

### Polarity is contextual

The same metric can flip direction across products, audiences, and time horizons. A few examples:

| Metric | "Higher is better" when… | "Lower is better" when… |
|---|---|---|
| Time in app | Engagement product (social, learning, game) | Productivity tool, support flow, wellness app |
| Bugs filed per week | QA process is being scaled up / coverage improves | Codebase is mature; goal is stability |
| Server CPU usage | Capacity planning view — show utilization | Reliability view — show headroom for spikes |
| Number of meetings | Sales pipeline (more contacts) | Engineering org (less interruption) |
| Cart size | Retail conversion view | Returns-cost / fraud-risk view |

If the polarity isn't obvious from the metric name alone, decide it for **this chart, this audience, this question**, and state the *reason* in the label, not just the direction.

### When to state polarity

- **State it** for any quantitative axis whose "good direction" is well-defined for the chart's context.
- **Skip it** for neutral axes — time, category, geography — they have no direction.
- **Skip it or use a target band** when the polarity is genuinely ambiguous or non-monotonic (e.g. employee headcount, inventory level, blood-glucose target). Prefer `target = N ± k` framing over a forced up/down arrow.

### Where to put it

Pick the first that fits:

1. **Axis title.** Append a short tag in parentheses: `"Response time (ms — lower is better)"`, `"Conversion rate (% — higher is better)"`, `"Defect rate per 1k units (target ≤ 2)"`.
2. **Subtitle.** When the axis title is already long, hoist it: a second `<text>` under the chart title reading "Lower is better".
3. **Tile / figure caption** for dashboard tiles — see `dashboard-ergonomics.md`.
4. **`aria-label`.** The accessible label must restate the polarity in words: `aria-label="Response time over the last 30 days, lower is better; current value 142 ms"` on the `<svg>` or its `<title>`.

Don't lean on color alone. Green = good / red = bad fails for the ~8 % of viewers with red-green CVD (see `cvd-simulation.md`). Pair color with a glyph or word: `↓ better`, `↑ better`, "(target ≤ 2)".

For **target-with-tolerance** metrics (SLA latency, temperature setpoint, blood pressure) state the target and the acceptable band: `"Oven temperature (°C — target 180 ± 5)"`. For **bidirectional** metrics (variance from forecast) center the axis on zero and label both ends: `"Forecast error — over ←  0  → under"`.

In the SVG, put the polarity tag directly in the axis-title `<text>` content, and the long-form rationale in a `<desc>` and the wrapper's `aria-label`.

```html
<svg role="img" aria-label="p95 response time, last 30 days. Lower is better. SLA 200 ms.">
  <text x="0" y="20" font-size="16" font-weight="600">p95 response time, last 30 days</text>
  <text x="0" y="38" font-size="12" fill="var(--ink-secondary)">Lower is better — SLA = 200 ms</text>
  <text x="8" y="60" font-size="11" fill="var(--ink-secondary)">Response time (ms — lower is better)</text>
</svg>
```

## matplotlib → SVG axis cleanup translation

The skill targets the same minimalist axis look as the matplotlib idiom below. Translation table:

| matplotlib | Hand-authored SVG |
|---|---|
| `ax.spines["top"].set_visible(False)` | don't draw a top `<line>` / frame edge |
| `ax.spines["right"].set_visible(False)` | don't draw a right `<line>` / frame edge |
| `ax.spines["bottom"].set_visible(False)` | omit the bottom baseline `<line>` |
| `ax.spines["left"].set_visible(False)` | omit the left baseline `<line>` |
| `ax.tick_params(axis='x', bottom=False, top=False)` | don't draw the short tick `<line>` under each x label |
| `ax.tick_params(axis='y', left=False, right=False)` | don't draw the short tick `<line>` beside each y label |

The user's exact matplotlib snippet (top/right spines off, x/y tick marks off, bottom/left spines kept) translates to: draw exactly two `<line>` elements (the bottom baseline and the left baseline) and no others — every other "axis" is just the `<text>` labels, positioned by hand.

## House tokens (light mode)

Reuse these on every chart. Prefer CSS custom properties on the chart's wrapper
so a single override flips the whole figure (see "Dark-mode aware" below).

```css
.chart {
  --chart-ink: #000000;
  --chart-ink-secondary: #3C3C43;
  --chart-axis: rgba(60, 60, 67, 0.36);
  --chart-mark: #007AFF; /* fallback single-series color; multi-series pulls from color-psychology.md */
  font-family: Roboto, system-ui, sans-serif;
}
```

Apply `--chart-mark` (or the multi-series categorical sequence from
`dataviz-color-palettes.md`) to marks, `--chart-ink` to titles and value labels,
`--chart-ink-secondary` to axis labels and subtitles, `--chart-axis` to the two
baselines. Corner radius `10` on every bar/rect mark and on the container.

The skill ships two ready-to-adapt snippets built with this exact palette (as
fixed hex values, so they render correctly standalone):
`assets/components/chart-bar.svg` and `assets/components/chart-line.svg`. Swap
their literal fills for these CSS custom properties (or `currentColor` +
Tailwind classes) when generating a chart that needs to be dark-mode aware.

## Dark-mode aware

Two options, in order of preference:

1. **`currentColor` + Tailwind text utilities** (works because the SVG is inlined
   in the page, not loaded as an external image): give marks and text
   `fill="currentColor"`, then wrap the chart in an element carrying
   `text-neutral-900 dark:text-neutral-100` (or the relevant token pair). With
   the house `darkMode: ['class', '[data-color-scheme="dark"]']` Tailwind config
   (see `ui-guidelines/foundations/dark-mode.md`), the `dark:` variant already
   follows the page's `<html data-color-scheme="dark">` toggle, so the SVG picks
   it up for free with zero chart-specific JS.
2. **CSS custom properties**, when different elements of the same chart need
   different colors in dark mode (axis vs. ink vs. mark) rather than one shared
   `currentColor`:

```css
[data-color-scheme="dark"] .chart {
  --chart-ink: #FFFFFF;
  --chart-ink-secondary: rgba(235, 235, 245, 0.6);
  --chart-axis: rgba(84, 84, 88, 0.65);
  --chart-mark: #0A84FF;
}
```

Don't introduce a second dark-mode toggle mechanism alongside `data-color-scheme`
— see `stack-vanilla-js.md`'s theme-switcher pattern.

## Concrete rules

1. **Container radius 10 px** (`rounded-[10px]`) — matches the mark radius.
2. **One color per series** drawn from the skill palette in `color-psychology.md`.
3. **Legends only when 2+ series**; otherwise label inline (matches the `dataviz`
   skill's own hard rule: no legend box for a single series, the title names it).
4. **Hover layer, by default.** A native `<title>` per mark (bar segment, line
   point, dot) gives a browser tooltip for free, no JavaScript required; add a
   `:hover`/`:focus` CSS rule (brightness bump or stroke-width increase) so the
   hovered mark visibly lifts. `tabindex="0"` on each interactive mark group so
   keyboard users reach the same tooltip. See `dataviz/references/interaction.md`
   for the fuller crosshair+tooltip pattern on line/area charts.
5. **Accessible**: wrap in `role="img"` + `aria-label` describing the takeaway,
   not the chart shape; a `<title>` and `<desc>` on the root `<svg>`.

## Checklist

- [ ] Hand-authored inline SVG, not a chart-library spec.
- [ ] House tokens applied (`--chart-ink`, `--chart-ink-secondary`, `--chart-axis`, `--chart-mark` or the categorical sequence).
- [ ] Rounded corners 10 px on marks and on the container.
- [ ] Colors from the skill palette, validated against `dataviz/scripts/validate_palette.js`.
- [ ] Dark-mode override wired (`currentColor` + Tailwind, or the CSS custom-property flip).
- [ ] `role="img"` + `aria-label`, plus `<title>`/`<desc>` on the root `<svg>`.
- [ ] Native `<title>` tooltip + `:hover`/`:focus` lift on every mark, `tabindex="0"` for keyboard reach.
- [ ] Polarity decided for the chart's context (same metric can flip across products). Whenever well-defined, stated on the axis title or subtitle and restated in the `aria-label` (*higher is better*, *lower is better*, or *target = N ± k*). Neutral axes (time, category, region) and genuinely ambiguous metrics skip this.
- [ ] Polarity not carried by color alone — paired with a word or glyph (`↓ better`, `↑ better`, "target ≤ N").
