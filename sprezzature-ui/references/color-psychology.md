# Color Psychology — tokens and selection rules

Source: <https://harchaoui.org/warith/colors/>. The machine-readable
form lives at `sprezzature-colors/references/palette.csv` — that CSV is the
**single source of truth for hexes** in the sprezzature-* ecosystem; this
file mirrors the CSV's `Hexcode` + `LightHex` columns in human-readable
table form, with the same rows in the same order. To regenerate the
Tailwind `theme.extend.colors` block from the CSV run:

```bash
python sprezzature-colors/scripts/palette_to_tailwind.py --emit theme
```

If a row drifts between this file and the CSV, the **CSV wins** and
this file is updated to match.

**Curated default — user colors win.** When the user has supplied their
own palette, use it. The curated set below is the default for fresh
generation when no palette is in play. See rule 7 in
`sprezzature-ui/SKILL.md` for the full carve-out.

Every colour decision maps back to a row in one of these tables. The
UI guidelines define *how* colour is applied (contrast, dark mode,
semantics); this file defines *which* hue is chosen and *why*.

## Base palette

Each hue ships with a light tint for backgrounds, hover, selection.

| Name | Hex | Light variant | Hex |
|---|---|---|---|
| Red | `#FF3B30` | Light Red | `#FFD8D6` |
| Orange | `#FF9500` | Light Orange | `#FFEACC` |
| Yellow | `#FFCC00` | Light Yellow | `#FFF5CC` |
| Green | `#28CD41` | Light Green | `#D4F5D9` |
| Blue | `#007AFF` | Light Blue | `#CCE4FF` |
| Turquoise | `#79DBDC` | Light Turquoise | `#00FFEF` |
| Purple | `#AF52DE` | Light Purple | `#EFDCF8` |
| Pink | `#FF2D55` | Light Pink | `#FFD5DD` |

## Emotion → hue

| Emotion | Hex |
|---|---|
| Silence | `#000000` |
| Neutral | `#808080` |
| Anger | `#FF3B30` |
| Surprise | `#FF9500` |
| Joy | `#FFCC00` |
| Disgust | `#28CD41` |
| Happiness | `#79DBDC` |
| Sadness | `#007AFF` |
| Fear | `#AF52DE` |

## Concept → hue

| Concept | Hex |
|---|---|
| Balance, Neutral, Calm | `#808080` |
| Excitement, Youthful, Bold | `#FF3B30` |
| Friendly, Cheerful, Confidence | `#FF9500` |
| Optimism, Clarity, Warmth | `#FFCC00` |
| Peaceful, Growth, Health | `#28CD41` |
| Trust, Dependable, Reliable, Strength | `#007AFF` |
| Creative, Imaginative, Wise | `#AF52DE` |

## Positive vs negative associations

Always check the negative column before locking a colour. A hue that fits the positive list for one brand can project a negative trait you did not intend.

| Color | Hex | Positive | Negative |
|---|---|---|---|
| Red | `#FF3B30` | Power, Passion, Energy, Strength | Anger, Danger, Warning, Aggression |
| Orange | `#FF9500` | Courage, Confidence, Warmth, Innovation | Deprivation, Frustration, Frivolity, Immaturity |
| Yellow | `#FFCC00` | Optimism, Happiness, Creativity, Intellect | Irrationality, Caution, Anxiety, Cowardice |
| Green | `#28CD41` | Health, Hope, Freshness, Growth | Boredom, Envy, Blandness, Sickness |
| Turquoise | `#79DBDC` | Communication, Clarity, Calmness, Healing | Boastfulness, Secrecy, Unreliability, Aloofness |
| Blue | `#007AFF` | Trust, Loyalty, Logic, Serenity | Coldness, Emotionless, Uncaring |
| Purple | `#AF52DE` | Wisdom, Luxury, Spirituality, Sophistication | Decadence, Inferiority, Moodiness |
| Pink | `#FF2D55` | Imaginative, Passion, Creative, Innovation | Outrageousness, Flippancy, Impulsiveness |
| Brown | `#A52A2A` | Seriousness, Warmth, Reliability, Authenticity | Humorlessness, Heaviness, Sadness |
| Black | `#000000` | Sophistication, Power, Elegance, Authority | Oppression, Menace, Heaviness, Mourning |
| Gray | `#808080` | Timelessness, Neutrality, Reliability, Balance | Unconfident, Depression, Lack of energy |
| White | `#F8F8F8` | Cleanliness, Purity, Simplicity, Freshness | Sterility, Coldness, Isolation, Emptiness |

## Selection rules

1. Start from intent (emotion, concept, or system semantic), not aesthetics.
2. Read the negative column. If a negative trait clashes with brand voice, pick a neighbour.
3. Pair with the light variant for backgrounds, hover, selection. Do **not** reuse the base hue at low opacity for surfaces.
4. Always emit a Tailwind token (`bg-brand-blue`), never a hex literal (`bg-[#007AFF]`) — `stack-tailwind.md`.
5. Red is reserved for destructive / critical states. Never primary CTA.

## Semantic defaults

| Role | Default | Reason |
|---|---|---|
| Primary action / link | Blue `#007AFF` | Trust |
| Destructive | Red `#FF3B30` | Universal danger signal |
| Success | Green `#28CD41` | Growth |
| Warning | Yellow `#FFCC00` | Attention without alarm |
| Info | Turquoise `#79DBDC` | Calm, communicative |
| Premium / accent | Purple `#AF52DE` | Luxury, sparingly |
| Brand emotion (joy) | Orange `#FF9500` or Pink `#FF2D55` | Friendly, energetic |
| Neutral surfaces | Gray `#808080`, White `#F8F8F8`, Black `#000000` | Layout backbone |
