# Map Ergonomics

Map-specific ergonomics. Read alongside `dashboard-ergonomics.md` and `dataviz-color-palettes.md`.

A map is a chart with a built-in coordinate system. The same dataviz rules apply, plus a small set of map-specific ones.

## Before you draw a map

Ask the same two questions every chart asks (see `dataviz-chart-selection.md`):

1. What is the message?
2. Who is the audience? What's their familiarity with the territory shown?

If the audience already knows the territory (a French audience reading a map of France), some elements are optional. For a foreign audience, the same elements become essential.

## General rule

Strip distracting graphics. Varied colors and over-loaded legends prevent the user from seeing the overall pattern. The eye wants to read a trend before reading details.

## What a good map must answer

Three quick checks before shipping:

1. **Can the message be understood in a few seconds, from the title alone, without the legend?**
2. **Can the map stand without supplementary information?**
3. **Is it readable in grayscale?**

If two of the three fail, simplify.

## Required vs. optional elements

| Element | Purpose | Required? |
|---|---|---|
| **Title** | States the message | Required |
| **Territory reminder** (named in full in the title) | Anchors the geographic scope | Required |
| **Legend** | Decodes colors / sizes | Required |
| **Copyright** | Use rights | Required by data licence |
| **Sources** | Origin of the data | Required |
| **Scale** | Real-world distance vs. screen distance | Required |
| **Locator inset** | Shows the map's territory inside a wider geography | Optional (often required for foreign audiences) |
| **North arrow** | Direction of north | Optional if the map is oriented north-up |
| **Frame / chrome** | Visual containment | Optional |

There is no formal global standard for map semiology; what is optional in one context may be required in another (publication norms, regulatory contexts). When in doubt, include.

## Visual conventions

- **Use commonly accepted color codes** for known categories — political party colors, traffic-light semantics, climate intensity. Inventing breaks reader expectations.
- **Convey intensity / abundance with luminance** — cool colors fading to warm colors, or a single hue increasing in saturation. Avoid hue jumps within an ordered scale.
- **One message per map.** A second message means a second map.
- **Uniformity across a series.** The same indicator must use the same color and same classification across a multi-map publication.

## Analysis vs. synthesis

There's a tradeoff between aesthetic appeal and analytical precision.

- A **many-step gradient** with close shades reads as a smooth surface: appealing, easy to grasp the overall trend, but the eye has trouble distinguishing precise values.
- A **few-step palette** with clearly separated shades reads as discrete zones: less elegant, but every region's class is unambiguous.

Pick based on use:

| Use | Palette |
|---|---|
| Quick scan / overview | Many close shades (sequential) |
| Precise comparison / ratio reading | Few well-separated classes (typically 5–7) |

For ratios and rate indicators, cap the number of classes so each zone is distinguishable.

## Choropleth pitfalls

- **Don't choropleth raw counts** — a populous region will always be "high", regardless of intensity. Normalize (per capita, per area, per unit).
- **Pick a sensible classification**: equal intervals, quantiles, natural breaks (Jenks). Different methods tell different stories from the same data; document the choice.
- **Avoid > 7 classes**. The eye can't reliably distinguish more than that on a map.

## Map types — quick guide

| What you're showing | Best map |
|---|---|
| A value per region (ordered) | **Choropleth** (sequential or divergent) |
| A category per region | **Categorical choropleth** (≤ 8 categories) |
| Locations of events / things | **Dot map** (one dot per occurrence) or **proportional symbol map** (size by value) |
| Density of events | **Heatmap** over the basemap |
| Flow between origin and destination | **Flow map** with arrowed paths |
| Multi-variate per region | **Cartogram** or **small multiples of choropleths** |

## Web implementation hooks

- Prefer SVG basemaps for vector territories (regions, countries) — they scale, they accept Tailwind / CSS classes, they're accessible.
- For interactive map UIs at scale, use Vega-Lite's `geoshape` or a dedicated library (MapLibre GL, Leaflet). Keep the house chart style — same Roboto type, same brand palette, same 10 px rounded corners on chrome — see `charts-vega.md`.
- Provide a textual alternative below the map: a sentence stating the takeaway, plus a table of the top / bottom regions. Screen readers can't read a map.
- Make hover / focus an interaction parity: every clickable region must also be keyboard-reachable with arrow keys, and the active region must expose name + value via an accessible name.

## Pattern — choropleth tile (SVG basemap + Tailwind chrome)

```html
<figure class="rounded-[10px] bg-surface-secondary p-4 dark:bg-surface-secondary-dark">
  <figcaption class="text-[17px] font-semibold">Unemployment rate by region, Q3</figcaption>
  <p class="mt-1 text-[13px] text-label-secondary dark:text-label-secondary-dark">Source: INSEE · 5 classes, natural breaks</p>
  <div id="map" role="img"
       aria-label="Choropleth of France by region: the highest rates are in the south-east; the lowest in the west and Île-de-France"
       class="mt-3 aspect-[4/3]">
    <!-- inline SVG basemap, each <path data-region="…" data-value="…" class="fill-data-sequential-N"> -->
  </div>
  <details class="mt-3 text-[15px]">
    <summary>Data table</summary>
    <!-- accessible fallback table -->
  </details>
</figure>
```

## Checklist

- [ ] Message stated in the title; map readable without the legend at first glance.
- [ ] Title names the territory in full.
- [ ] Legend, sources, copyright, scale present.
- [ ] Locator inset and north arrow included if the audience may not know the territory.
- [ ] Map readable in grayscale.
- [ ] One message per map.
- [ ] Uniform colors / scale across a series.
- [ ] Counts normalized (per capita, per area, …).
- [ ] ≤ 7 classes on a choropleth.
- [ ] Categorical maps ≤ 8 hues, no red/green pair.
- [ ] Accessible textual alternative below the map.
- [ ] Keyboard reachable and announced via `aria-label`.
