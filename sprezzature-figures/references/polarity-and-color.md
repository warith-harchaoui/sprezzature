# Polarity and color — "higher is better" made explicit

Every quantitative axis on a chart encodes a value the reader has to
score in 3 seconds. The first thing they ask is **"is this trend good
or bad?"**, and if the chart can't answer that without the reader
guessing, it has already failed.

The rule this skill enforces:

1. **State the polarity in text on the axis title**, always.
2. **Reinforce with color**, but never rely on color alone.
3. **Keep the palette aligned with sprezzature-colors' semantic mapping**:
   Emotion / Concepts / Psychology-Positive / Psychology-Negative.
   Source: <https://harchaoui.org/warith/colors/>.

## The polarity vocabulary

| Polarity flag | Meaning | Where it appears |
|---|---|---|
| `higher-better` | The metric is desirable when high (conversion, retention, throughput, revenue, accuracy). | Axis title tag: `(higher is better)`. |
| `lower-better` | The metric is desirable when low (latency, cost, error rate, churn, MAE). | Axis title tag: `(lower is better)`. |
| `target=<N>` | The metric has a set-point; both directions off-target are bad (temperature setpoint, SLA latency ceiling). | Axis title tag: `(target = <N>)`. |
| `auto` | Let `_style.infer_polarity` guess from the column name. | The default when `--polarity` is not passed. |
| _(unset)_ | Genuinely ambiguous or neutral metric (headcount, inventory level, month). | No tag; no polarity color. |

Auto-inference recognises around thirty common metric substrings;
see `_style.POLARITY_HINTS`. If your project uses domain-specific
names (`fraud_rate`, `csat`, `dsat`), pass `--polarity` explicitly.

## The color mapping

Colors are taken from the canonical palette
(`sprezzature-colors/references/palette.csv`, sourced from
<https://harchaoui.org/warith/colors/>). Each hex projects to four
semantic axes; the polarity mapping uses the **Psychology-Positive**
column for goal metrics and the **Psychology-Negative** column for
breach overlays.

| Polarity intent | Base color | Psychology (+) terms | Psychology (−) terms |
|---|---|---|---|
| **higher-better** — goal-directed | **Green** (`#28CD41`) | Health, Hope, Freshness, Growth, Prosperity | Boredom, Stagnation, Sickness |
| **lower-better** — goal-directed | **Green** (same) | (same as above) | (same) |
| **target = N** — compliance frame | **Blue** (`#007AFF`) | Trust, Loyalty, Logic, Serenity, Security | Coldness, Unfriendliness |
| **breach overlay** (SLA violation, threshold cross) | **Red** (`#FF3B30`) | Power, Passion, Energy | Danger, Warning, Anger |
| **neutral / no polarity** | Qualitative palette (curated 8) | — | — |

Both **higher-better** and **lower-better** map to the *same* Green
family; a common mistake is to code "lower is better" as Red because
"low = down". Both polarities are **wins**; both should read as
positive. Red is reserved for SLA breach and threshold overlays where
the reader must see failure.

## Why color alone is not enough

Around 8 % of male viewers and 0.5 % of female viewers cannot
reliably distinguish red from green (deuteranopia + protanopia).
This is exactly the *most common* CVD pattern the polarity mapping
above would collide with. So:

- Keep the text tag on the axis title even when color is applied.
- Prefer a lightness delta (`sprezzature-colors.lighten` / `.darken`) over
  a hue swap when you must indicate a secondary state.
- Pair color-coded state with a glyph or word (`↓ better`,
  `↑ better`, `target = N`).
- For **signed / diverging** data (gain vs loss, growth), default to the
  **blue ↔ red** pair rather than red ↔ green. Red ↔ green collapses to one
  muddy hue under protanopia / deuteranopia (the very population this section
  is about) while blue ↔ red stays legible (blue survives, red darkens toward
  brown). `_style.diverging_pair(cvd_safe=True)` returns it; keep the green ↔ red
  convention only when the sign is *also* encoded (a `+/-` glyph, position) and
  you have confirmed it in the simulator.
- Preview colorblind and grayscale rendering with
  `sprezzature-colors/scripts/simulate_cvd.py <fig.png> --grid --grayscale` before
  shipping, the *render → simulate → look* step that reinforces `make` and
  `audit`.

## How the skill applies the mapping

`make_figure.py` applies the polarity color to the primary encoding
whenever:

- `--polarity` is set (explicit or `auto` with a recognised metric
  name), and
- `--color <column>` is **not** set (that would clobber the caller's
  intended qualitative faceting), and
- the mark is one of `bar` / `line` / `point` / `rect` / `area`.

In every other case the qualitative palette wins. The audit rule
`missing-polarity` (see `references/audit-figure.md`) flags a chart
whose metric name matches a polarised pattern but whose axis title
has no direction tag; auto-fix rewrites the title to append the tag.

## Emotions and concepts — the wider palette

Beyond polarity, the same palette CSV projects each hex onto
Emotion / Concepts labels. `_style.emotion_to_hex` and
`_style.concept_search` expose the lookups for callers that want to
match a *feeling* to a color (e.g. a "Trust" landing page, a
"Joy" onboarding flow). Full mapping documented at
<https://harchaoui.org/warith/colors/>.

Sample lookups:

```python
from _style import emotion_to_hex, concept_search, psychology_for

emotion_to_hex("Joy")              # → "#FFCC00" (Yellow)
emotion_to_hex("Sadness")          # → "#007AFF" (Blue)
emotion_to_hex("Trust")            # → None — Trust is a concept, not an emotion
concept_search("Trust")            # → ["#007AFF"]           (Blue)
concept_search("Bold")             # → ["#FF3B30"]           (Red)
psychology_for("Green")            # → {"positive": [...Health, Hope...],
                                   #    "negative": [...Sickness...]}
```

The audit rule `chartjunk` still applies; the palette exists to
constrain choices, not to encourage every chart to become a mood
board.
