# Polarity and color: why an axis says "(higher is better)", and where the color comes from

A bar chart of latency going up looks, at a glance, exactly like a bar
chart of revenue going up: two bars, the second one taller. But one of
those is bad news and the other is good news. Nothing in the shape of the
chart tells a reader which is which, that information lives only in what
the metric means, and a chart that does not say so out loud is asking the
reader to already know. `sprezzature-figures` calls this a metric's
**polarity**, whether a higher value is the goal, a lower value is the
goal, or the goal is a fixed target rather than a direction at all, and
states it directly on every quantitative axis that has one. This file
documents how that polarity is guessed, how it is worded, and how its
reinforcing color is actually picked in the code, which is a narrower
mechanism than "reads the palette's psychology columns" might suggest.

## Guessing the polarity from a metric's name

`infer_polarity()` in `_style.py` takes an axis title or column name and
checks it, lowercased, against a fixed table of substrings,
`POLARITY_HINTS`. A name containing `latency`, `cost`, `churn`, `error`,
`mae`, `rmse`, or a dozen similar substrings resolves to
`"lower-better"`; one containing `revenue`, `accuracy`, `retention`,
`throughput`, `f1`, or `auc` resolves to `"higher-better"`. Anything not
matching any substring in that fixed list returns `None`, meaning no
polarity tag is added, not that the metric has no polarity in reality.
This is a lookup table, not a model: a metric named something the table
does not recognize, or named only in a language other than the substrings
listed, will not get a tag even where a human reader would immediately
see the direction.

## Wording the tag

`polarity_tag()` turns the inferred polarity into the parenthesized
suffix that gets appended to the axis title: `" (higher is better)"`,
`" (lower is better)"`, or, for a fixed target rather than a direction,
`" (target = N)"` when the polarity string itself is `"target=N"`. The
function also carries French, German, and Spanish translations of the
first two phrases, keyed by a BCP-47 language tag, `" (plus c'est haut,
mieux c'est)"` and its siblings, though the target phrasing keeps the `=`
sign literal across all four languages rather than localizing the
punctuation.

## Where the reinforcing color actually comes from

This is the part worth being precise about, because the mechanism is more
specific than "picked from the palette's psychology projections" would
suggest on its own.

`_style.py` defines a small, fixed lookup, `POLARITY_COLOR`, mapping
polarity *intent* to a palette *base-color name*:

```python
POLARITY_COLOR = {
    "higher-better": "Green",
    "lower-better":  "Green",
    "target":        "Blue",
    "breach":        "Red",
    "neutral":       "Gray",
}
```

Both goal-directed polarities, `higher-better` and `lower-better`, map to
the same base color, Green, the code comment's reasoning is that both are
cases where the reader wants to see the metric move toward its goal,
regardless of which direction that motion points on the axis; a fixed
`target=N` shifts to Blue instead, because there the metric itself is
neutral and the frame is compliance with a number, not directional
improvement; a `breach` overlay, used to flag an SLA violation without
co-opting the primary encoding, uses Red.

`polarity_color()` takes that base-color name and resolves it to an
actual hex value by calling `load_palette()`, which reads
`sprezzature-colors/references/palette.csv`'s `Base` column, the same
canonical palette every other `sprezzature-figures` generator draws its
qualitative colors from, and returns the hex in that row's `Hexcode`
column.

So the two-step mechanism is: **polarity intent to a fixed base-color
name** (a five-entry lookup table in Python), then **base-color name to
hex** (a CSV lookup by the `Base` column). The palette's
`PsychologyPositive` and `PsychologyNegative` columns, which hold
free-text descriptors like "Health, Hope, Freshness, Nature, Growth,
Prosperity" for Green, are not parsed or matched against at runtime
anywhere in this path; they appear only as the *documented rationale*, in
a code comment above `POLARITY_COLOR`, for why Green was chosen as the
goal-directed color and Blue as the compliance color. If you are looking
for a function that scores an arbitrary polarity phrase against the CSV's
psychology text and picks the best-matching hue automatically, it does
not exist; the mapping is the fixed five-entry table above, and changing
it means editing that table, not the CSV.

`polarity_color()` also takes a `role` argument (`"primary"` or
`"breach"`) to pick between the goal color and the SLA-violation overlay,
and a `dark` flag that the docstring notes is currently unused, reserved
for a future light/dark hex variant, every curated base hex already meets
contrast on both background modes today.

## A color is reinforcement, never the only signal

The polarity color is explicitly documented as a *reinforcement* layer on
top of the text tag, never a substitute for it: roughly 8% of male
viewers cannot reliably read a red/green or similar color distinction at
all (see `sprezzature-colors/references/accessibility-levels.md` for the
fuller CVD picture), so a chart that only encoded polarity through hue
would be silently unreadable to a meaningful share of readers. The text
tag from `polarity_tag()` carries the meaning on its own; the color is
there for readers who can use it, not the ones who cannot.

## The emotion and concept accessors

Beyond polarity, `_style.py` exposes two more ways to reach into the same
palette CSV by meaning rather than by hex code: `emotion_to_hex(emotion)`
looks up a base color by its single `Emotion` label (the CSV's `Emotion`
column pairs one emotion word per base color, "Anger" for Red, "Disgust"
for Green, and so on, following Wong's categorical-palette convention
adapted with a psychology framing rather than the original neutral
labels), and `concept_search(term)` scans the `Concepts` column (a
comma-separated free-text field per color, "Peaceful, Growth, Health" for
Green) for a substring match and returns every base-color name whose
concepts mention it. Both are read via `load_semantic_palette()`, which
loads every column of the CSV (`Hexcode`, `Base`, `LightHex`, `Emotion`,
`Concepts`, `PsychologyPositive`, `PsychologyNegative`) into one
dictionary keyed by base-color name. Unlike `polarity_color()`, these two
accessors genuinely do read the CSV's free-text columns at call time,
they are the tools to reach for if you want a palette pick grounded in
the psychology projections directly, rather than the fixed five-entry
polarity table.

The semantic mapping itself, which emotion and which concepts belong to
which base color, is documented at
<https://harchaoui.org/warith/colors/> and mirrored in
`sprezzature-colors/references/palette.csv`; this file documents the
`sprezzature-figures` code that reads it, not the palette's own design
rationale.
