# Charts — Vega-Lite

Source for colors: <https://harchaoui.org/warith/colors/> (see also `references/color-psychology.md`).
Source for the rendering engine: <https://vega.github.io/vega-lite/>.

## When to consult this file

- Any chart, graph, dashboard tile, or data visualization
- Sparklines, distributions, time series, categorical comparisons

## Library choice

The skill emits **Vega-Lite v5 JSON specs**, rendered with the Vega-Embed runtime. No D3 written by hand, no Chart.js, no Recharts.

```html
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
```

For production, install via npm (`vega`, `vega-lite`, `vega-embed`) and bundle.

## House defaults

1. **Rounded corners at 10 px** on every chart mark and on the chart container.
2. **Colors from `color-psychology.md`** — no rainbow palettes, no Vega defaults.
3. **Roboto** for every text element (labels, titles, legends).
4. **No top spine, no right spine** — keep only the bottom (x) and left (y) baselines.
5. **No tick marks** on either axis — labels alone read fine and look cleaner.
6. **No gridlines** unless explicitly needed.
7. **No 3D**, no drop shadows, no gradients (except a single linear fill for area charts).
8. **Tabular numerals** for value labels.
9. **Dark-mode aware** — override `config` based on `data-color-scheme`.
10. **Title above** in body weight; subtitle below in label-secondary.
11. **State the polarity** of every measured axis — *higher is better*, *lower is better*, or *target = N*. See "Polarity — higher or lower is better" below.

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
2. **Subtitle.** When the axis title is already long, hoist it: `subtitle: "Lower is better"` under the chart title.
3. **Tile / figure caption** for dashboard tiles — see `dashboard-ergonomics.md`.
4. **`aria-label`.** The accessible label must restate the polarity in words: `aria-label="Response time over the last 30 days, lower is better; current value 142 ms"`.

Don't lean on color alone. Green = good / red = bad fails for the ~8 % of viewers with red-green CVD (see `cvd-simulation.md`). Pair color with a glyph or word: `↓ better`, `↑ better`, "(target ≤ 2)".

For **target-with-tolerance** metrics (SLA latency, temperature setpoint, blood pressure) state the target and the acceptable band: `"Oven temperature (°C — target 180 ± 5)"`. For **bidirectional** metrics (variance from forecast) center the axis on zero and label both ends: `"Forecast error — over ←  0  → under"`.

Vega-Lite shorthand: put the polarity tag in `encoding.{x|y}.axis.title`, and the long-form rationale in the spec's `title.subtitle` and the wrapper's `aria-label`.

```json
{
  "title": {
    "text":     "p95 response time, last 30 days",
    "subtitle": "Lower is better — SLA = 200 ms"
  },
  "encoding": {
    "y": { "field": "ms", "type": "quantitative",
           "axis": { "title": "Response time (ms — lower is better)" } }
  }
}
```

## matplotlib → Vega-Lite axis cleanup translation

The skill targets the same minimalist axis look as the matplotlib idiom below. Translation table:

| matplotlib | Vega-Lite |
|---|---|
| `ax.spines["top"].set_visible(False)` | `config.view.stroke = "transparent"` (removes the implicit top/right plot border) |
| `ax.spines["right"].set_visible(False)` | same as above; Vega-Lite has no separate right spine by default |
| `ax.spines["bottom"].set_visible(False)` | `config.axisX.domain = false` |
| `ax.spines["left"].set_visible(False)` | `config.axisY.domain = false` |
| `ax.tick_params(axis='x', bottom=False, top=False)` | `config.axisX.ticks = false` |
| `ax.tick_params(axis='y', left=False, right=False)` | `config.axisY.ticks = false` |

The user's exact matplotlib snippet (top/right spines off, x/y tick marks off, bottom/left spines kept) translates to:

```json
{
  "config": {
    "view":  { "stroke": "transparent" },
    "axisX": { "domain": true,  "ticks": false },
    "axisY": { "domain": true,  "ticks": false }
  }
}
```

Apply this block on every chart spec; the ready-to-paste house config below already includes it.

## Skill house `config` (light mode)

Paste this `config` block into every spec.

```json
{
  "config": {
    "background": "transparent",
    "view": { "stroke": "transparent" },
    "axis": {
      "labelFont": "Roboto",
      "titleFont": "Roboto",
      "labelFontWeight": 400,
      "titleFontWeight": 600,
      "labelColor": "#3C3C43",
      "titleColor": "#000000",
      "grid": false,
      "domainColor": "rgba(60,60,67,0.36)"
    },
    "axisX": { "domain": true,  "ticks": false, "labelPadding": 6 },
    "axisY": { "domain": true,  "ticks": false, "labelPadding": 6 },
    "title":  { "font": "Roboto", "fontWeight": 600, "color": "#000000" },
    "header": { "labelFont": "Roboto", "titleFont": "Roboto" },
    "legend": { "labelFont": "Roboto", "titleFont": "Roboto", "labelColor": "#3C3C43", "titleColor": "#000000" },
    "range": {
      "category": ["#007AFF","#28CD41","#FF9500","#AF52DE","#FF2D55","#FFCC00","#79DBDC","#FF3B30"],
      "diverging": ["#FF3B30","#FFCC00","#28CD41"],
      "heatmap":   ["#CCE4FF","#007AFF"],
      "ramp":      ["#CCE4FF","#007AFF"]
    },
    "bar":  { "cornerRadiusEnd": 10, "color": "#007AFF" },
    "rect": { "cornerRadius": 10 },
    "line": { "color": "#007AFF", "strokeWidth": 2.5, "interpolate": "monotone" },
    "area": { "color": "#007AFF", "opacity": 0.2, "line": { "strokeWidth": 2.5 } },
    "point":{ "color": "#007AFF", "filled": true, "size": 60 },
    "tick": { "color": "#007AFF" }
  }
}
```

The skill ships two ready-to-include specs that already use this config: `assets/components/chart-bar.json` and `assets/components/chart-line.json`.

## Dark-mode override

When `<html data-color-scheme="dark">`, swap the config to:

```json
{
  "config": {
    "background": "transparent",
    "axis": { "labelColor": "rgba(235,235,245,0.6)", "titleColor": "#FFFFFF", "domainColor": "rgba(84,84,88,0.65)", "tickColor": "rgba(84,84,88,0.65)" },
    "title":  { "color": "#FFFFFF" },
    "legend": { "labelColor": "rgba(235,235,245,0.6)", "titleColor": "#FFFFFF" },
    "bar":  { "color": "#0A84FF" },
    "line": { "color": "#0A84FF" },
    "area": { "color": "#0A84FF", "opacity": 0.2 },
    "point":{ "color": "#0A84FF" }
  }
}
```

## Container

```html
<figure class="rounded-[10px] bg-surface-secondary p-4 dark:bg-surface-secondary-dark">
  <figcaption class="sr-only">Weekly active users</figcaption>
  <div id="chart" role="img" aria-label="Weekly active users line chart"></div>
</figure>
<script type="module">
  import 'vega'; import 'vega-lite'; import embed from 'vega-embed';
  const spec = await (await fetch('./chart-line.json')).json();
  embed('#chart', spec, { actions: false, renderer: 'svg' });
</script>
```

Use SVG renderer (sharper, smaller for typical chart sizes, themable via CSS).

## Concrete rules

1. **Container radius 10 px** (`rounded-[10px]`) — matches the mark radius.
2. **One color per series** drawn from the skill palette in `color-psychology.md`.
3. **Legends only when 2+ series**; otherwise label inline.
4. **Tooltip enabled** (Vega-Embed default) for any chart richer than a single sparkline.
5. **Accessible**: wrap in `role="img"` + `aria-label` describing the takeaway, not the chart shape.

## Checklist

- [ ] Vega-Lite JSON, not hand-written SVG.
- [ ] House `config` applied.
- [ ] Rounded corners 10 px on marks and on the container.
- [ ] Colors from the skill palette.
- [ ] Dark-mode override wired.
- [ ] `role="img"` + `aria-label`.
- [ ] SVG renderer.
- [ ] Polarity decided for the chart's context (same metric can flip across products). Whenever well-defined, stated on the axis title or subtitle and restated in the `aria-label` (*higher is better*, *lower is better*, or *target = N ± k*). Neutral axes (time, category, region) and genuinely ambiguous metrics skip this.
- [ ] Polarity not carried by color alone — paired with a word or glyph (`↓ better`, `↑ better`, "target ≤ N").
