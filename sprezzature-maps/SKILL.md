---
name: sprezzature-maps
description: >-
  Real geography: a choropleth on an actual basemap with an actual projection,
  and a layered areas-of-control "situation" plate for any region. The trigger
  is data attached to PLACES, not the word "map": a column of country names,
  ISO codes, states or départements is a map waiting to be drawn. Trigger
  phrases: "map this by country", "colour the regions by score", "which country
  is worst affected", "break this down by region", "where is this happening",
  "show me the spread across Europe", "world map", "choropleth", "thematic map",
  "areas of control", "front line", "contested zones", "who controls what",
  "situation map", "situational awareness plate", « une carte par département »,
  « carte de situation ». Schematic place-shaped charts — hex map, dot density,
  spike map, binned grid — are NOT here; they live in sprezzature-figures.
  Output is SVG (PNG / PDF on request).
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Ships as the standalone
  `sprezzature-maps` package (Python 3.10+). The basemap is bundled Natural
  Earth data — no network, no tile server, no API key at any point.
metadata:
  author: Warith HARCHAOUI
  version: 1.3.4
---

> The generators below ship as the standalone package [`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps) (`pip install sprezzature-maps`), invoked as `make-map …`. There is no `scripts/` folder in this monorepo; the SKILL.md here is the agentic contract.

# sprezzature-maps — choropleths and situation maps on real geography

## The trigger, stated once

**Data attached to *places* is the trigger.** Not the word "map". "Which
countries are worst affected", "break this down by région", "where is this
happening", "show me the spread across Europe" — a column of country names,
ISO codes, states or départements is a map waiting to be drawn, and the only
open question is which kind.

## The one routing decision that matters

This package draws **real geography**: actual coastlines, an actual
projection, bundled Natural Earth outlines. That is the whole scope, and it
is also the line an agent gets wrong.

| The user wants… | Go to | Why |
|---|---|---|
| Territories shaded by a value, on real coastlines | **here** — `make-map choropleth` | the shape of the land carries meaning |
| Who holds which ground, front lines, contested zones | **here** — `make-map situation_map` | same |
| A hex map, dot density, spike map, binned grid, cartogram | **`sprezzature-figures`** | those are layout conventions, not geography |

Ask the question plainly: **does the shape of the land matter?** If it does,
this skill. If the map is a seating chart that happens to look like a country,
`sprezzature-figures` has those five kinds and `list_kinds` will name them.

## Honest framing of what each generator covers

| Generator | Catches | Misses |
|---|---|---|
| `choropleth` | one fill colour per territory on a perceptual OKLCH ramp, Equal Earth projection, hillshade relief, automatic diverging scale when the values span both signs, neutral grey for territories with no data | it maps a value per *territory*, so it inherits the choropleth's own bias: a large sparsely-populated region shouts louder than a small dense one. If the story is about people rather than land, say so, and consider a cartogram or a per-capita normalisation before drawing. |
| `situation_map` | a layered plate for any region: auto-centred Lambert conformal conic projection, real national outlines, bathymetry halo near the coast, zones filled by category, flashpoint markers, a scale bar in kilometres **and** miles | it has **no view on whether a claim of control is true**. It draws exactly what the config says. |

## One contract an agent must not break

**A situation map draws exactly what you send it.** A plate that looks like a
professional intelligence product gets read as one. When you hand such a map
to a user, or a user hands it onward, say where the underlying assessment came
from. That is not a disclaimer to append at the bottom — it is part of the
map's meaning, and omitting it is how a rough sketch becomes someone's
evidence.

## Decision tree

| Trigger | Call | Run |
|---|---|---|
| "map this by country" / "colour the regions by score" / "which country is highest" / « une carte par département » | `choropleth` | `make-map choropleth --data rows.json --out world.svg [--title "…"]`. Rows are `{"id": "<ISO-3166-1 numeric>", "value": <number>}` — `"840"` for the United States, `"124"` for Canada. Send nothing at all and you get the demo map, which is the fastest way to show someone the shape of the input before they commit real data to it. |
| "areas of control" / "front line" / "who controls what" / « carte de situation » | `situation_map` | `make-map situation_map --config region.yaml --out region.svg`. The region, the zones, the categories and the flashpoints all live in the YAML, so the CLI is usually the better surface here; the bundled Western-Europe demo config runs with no arguments. |
| "what kinds of map can you draw" | `list_kinds` | Two. If the answer the user needs is a third, it is in `sprezzature-figures`. |

## The situation map is configured, not flagged

Everything a situation plate shows lives in one YAML file, and **almost
nothing is on by default** — they are modes, and a plate that switches them
all on says less than one that picks. The keys the generator reads:

`title`, `subtitle`, `caption`, `as_of` · `projection`, `basemap`, `frame`,
`padding`, `canvas_width` · `areas_of_control`, `front`, `frontiers`,
`internal_borders` · `forces`, `events`, `infrastructure`, `labels`,
`rivers` · `legend_position`, `legend_footer`, `marker_legend` ·
`source`, `attribution`, `method`.

The last three are the provenance block, and they are the ones to fill in
first rather than last: `source` and `as_of` are what stop a plate from being
read as current when it is not, and `method` is where the assessment behind
the zones is named. See the contract above.

Rivers taper by prominence when `rivers` asks them to; they are absent
otherwise. The same is true of every other layer — ask for what the map is
about, not for everything the generator can draw.

## Two modes: make and audit

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — a choropleth on real geography | `make-map choropleth` | Territories shaded by a value, Equal Earth, OKLCH ramp, relief. |
| **Make** — an areas-of-control plate | `make-map situation_map` | Layered situation map for any region from one YAML config. |
| **Audit** | _(none here — see `sprezzature-figures`' `audit_figure.py`)_ | The rendered SVG is a figure like any other, so the data-viz auditor and the colour-vision accessibility levels apply to it unchanged. Run them there rather than duplicating a second auditor here. |

The gap in the audit column is real and deliberate: a second SVG auditor in
this package would drift from the one in `sprezzature-figures` within a
release. One auditor, two producers.

## The five surfaces

Every tool in this suite is reachable five ways, and maps is no exception.

| Surface | How |
|---|---|
| Library | `from sprezzature_maps import make_choropleth, make_situation_map` |
| CLI | `make-map choropleth --out world.svg` |
| HTTP API | `POST /render_choropleth`, `POST /render_situation_map` (`pip install 'sprezzature-maps[api]'`) |
| MCP | the `render_choropleth` / `render_situation_map` / `list_kinds` tools, derived from those routes (`[mcp]`) |
| Skill | this file |

Both render surfaces take every field as optional: send an empty body and you
get the demo map.

## When NOT to use this skill

- **The shape of the land does not matter.** A hex map of US states, a dot
  density, a spike map, a binned grid: `sprezzature-figures`.
- **You need an interactive slippy map** (pan, zoom, tiles): this emits one
  static SVG per call. Leaflet / MapLibre are the right tools.
- **You need routing, geocoding, or spatial joins.** This draws; it does not
  compute geography. Bring the rows already keyed by territory.
- **You need a basemap the bundle does not carry.** The Natural Earth data
  ships with the package precisely so nothing phones home; a custom basemap is
  outside that bargain.

## References

- `references/choosing-a-map.md` — which of the three map families (real
  geography, schematic, cartogram) answers which question, and the failure
  each one is prone to.

## Companion skills

| You also need… | Install |
|---|---|
| Charts, including the schematic place-shaped ones | `sprezzature-figures` |
| Contrast audit and colour-vision simulation on the rendered plate | `sprezzature-colors` |
| Alt text for the emitted SVG | `sprezzature-vision` |
| Static a11y lint on the page that embeds it | `sprezzature-accessibility` |
