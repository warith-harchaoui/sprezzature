---
name: sprezzature-maps
description: >-
  Real geography, three kinds: a choropleth on a true projection, a layered
  areas-of-control situation plate, and an accumulation map where point events
  draw the land with no coastline drawn; then an audit of the finished plate,
  eleven static rules. The trigger is data attached to PLACES, not the word map:
  a column of countries, ISO codes, states or departements is a map waiting to
  be drawn, and so is a list of coordinates where something happened. Output is
  SVG, PNG or PDF. Use it when you are holding a value per territory, a region
  to draw, or event positions. Trigger phrases: "map this by country", "which
  country is worst affected", "where did these incidents fall", "world map",
  "choropleth", "areas of control", "front line", "who controls what",
  "situation map", "une carte par departement", "carte de situation". Not this
  one when: the shape is schematic (hex map, spike map, binned grid, dot density
  over an outline): sprezzature-figures. The exhaustive trigger catalogue is in
  `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Ships as the standalone
  `sprezzature-maps` package (Python 3.10 to 3.13). The basemap is bundled Natural
  Earth data — no network, no tile server, no API key at any point.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.4
---

> The generators below ship as the standalone package [`sprezzature-maps`](https://github.com/warith-harchaoui/sprezzature-maps) (`pip install sprezzature-maps`), invoked as `make-map …`. There is no `scripts/` folder in this monorepo; the SKILL.md here is the agentic contract.

# sprezzature-maps: choropleths, situation maps and accumulation maps on real geography

## The trigger, stated once

**Data attached to *places* is the trigger.** Not the word "map". "Which
countries are worst affected", "break this down by région", "where is this
happening", "show me the spread across Europe" — a column of country names,
ISO (International Organization for Standardization, the body behind shared codes such as the two-letter country codes) codes, states or départements is a map waiting to be drawn, and the only
open question is which kind.

## The one routing decision that matters

This package draws **real geography**: actual coastlines, an actual
projection, bundled Natural Earth outlines. That is the whole scope, and it
is also the line an agent gets wrong.

| The user wants… | Go to | Why |
|---|---|---|
| Territories shaded by a value, on real coastlines | **here** — `make-map choropleth` | the shape of the land carries meaning |
| Who holds which ground, front lines, contested zones | **here** — `make-map situation-map` | same |
| Where events *fell* — incidents, outages, strikes, sightings | **here** — `make-map density` | positions, not a value per territory |
| A hex map, dot density, spike map, binned grid, cartogram | **`sprezzature-figures`** | those are layout conventions, not geography |

**The line between `choropleth` and `density` is the one to get right.** A
choropleth answers "what is the rate *here*"; it needs one number per
territory, and filling it with a raw count draws population rather than your
phenomenon. `density` answers "where did this happen"; it takes the positions
themselves and needs no territories at all.

Ask the question plainly: **does the shape of the land matter?** If it does,
this skill. If the map is a seating chart that happens to look like a country,
`sprezzature-figures` has those five kinds and `list_kinds` will name them.

## Honest framing of what each generator covers

| Generator | Catches | Misses |
|---|---|---|
| `choropleth` | one fill colour per territory on a perceptual OKLCH (a way of numbering colours by lightness, chroma and hue, built so that equal steps look equally different to the eye) ramp, Equal Earth projection, hillshade relief, automatic diverging scale when the values span both signs, neutral grey for territories with no data | it maps a value per *territory*, so it inherits the choropleth's own bias: a large sparsely-populated region shouts louder than a small dense one. If the story is about people rather than land, say so, and consider a cartogram or a per-capita normalisation before drawing. |
| `situation_map` | a layered plate for any region: auto-centred Lambert conformal conic projection, real national outlines, bathymetry halo near the coast, zones filled by category, flashpoint markers, a scale bar in kilometres **and** miles | it has **no view on whether a claim of control is true**. It draws exactly what the config says. |
| `density` | an accumulation map: point events binned to a luminous field. No coastline, no border, no graticule are drawn — the land appears because events fell on it and the sea stays dark because none did, so a reader recognises the shape without being shown it. Vector, binned, one path per level. | it shows *where*, never *how many per capita*: a dense city looks dense because people are there. And the form is persuasive enough to be believed, so the caption carrying the events' provenance is not decoration — the bundled demo says on the plate that its data is synthetic. |

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
| the values are skewed — income, density, counts, anything with a long tail | `choropleth` with `classes` | `make-map choropleth --classes 5 --method quantile`, or `{"classes": 5, "method": "jenks"}` on the route. Without it the ramp stretches min-to-max and most territories collapse into its bottom. See the section above for which method answers which question; the legend names whichever you pick. |
| "areas of control" / "front line" / "who controls what" / « carte de situation » | `situation_map` | `make-map situation-map --config region.yaml --out region.svg` (`situation_map`, with the underscore, is the same command). The region, the zones, the categories and the flashpoints all live in the YAML (YAML Ain't Markup Language, a plain-text format for settings, one name: value per line), so the CLI (command-line interface, a program you run by typing a command in a terminal) is usually the better surface here; the bundled Europe demo config runs with no arguments. |
| "where did these incidents fall" / a list of `[lon, lat]` events | `density` | `make-map density --points events.json --out where.svg [--bins 160]`. No coastline is drawn; say where the events came from in the caption (`caption` on the route or in the library). |
| a country or a bounding box, and no region config yet | `situation_new` | `make-map situation-new --country Sudan --out sudan.yaml` (or `situation_new`; omit `--out` for stdout) (or `--bbox west,south,east,north`). The starter renders as it stands, furnished, with `confidence` on every commented zone. |
| an ACLED (Armed Conflict Location & Event Data, a public database where each row is one dated, located clash or protest) or UCDP (Uppsala Conflict Data Program, a Swedish university's database of wars) GED (Georeferenced Event Dataset, its list of violent events, each pinned to a place and a date) export | `acled_events` / `ucdp_events`, then `situation_map` | `cfg.update(acled_events("export.csv", derive_region=True))` in Python. The loaders keep each row's precision code on its mark; UCDP rows known only to the country are not drawn, and are counted on the plate. |
| "can we publish this map" / a finished plate | `audit` | `make-map audit plate.svg` (or a folder, `--format json`). Exit 1 on any finding, 0 when clean, 2 when the target holds no SVG (Scalable Vector Graphics, an image made of shapes rather than pixels, so it stays sharp at any zoom). See the audit section below. |
| "is this readable" / "make it clearer" | `improve` | `make-map improve --kind choropleth --data rows.csv --out map.png` (`--out` is required and must be a `.png`). Needs a local vision model; never changes the classification, the class count or the frame on its own. |
| "what kinds of map can you draw" | `list_kinds` | Three: `choropleth`, `density`, `situation_map`. Anything else map-shaped is in `sprezzature-figures`. |

**Pass `--out`.** Its extension picks the format: `.svg`, `.png`,
`.jpg`, `.pdf`, `.eps` or `.html`. Without it, `choropleth`, `density` and
`situation-map` write `choropleth.svg`, `density.svg` or `situation_map.svg`
in the current directory and print the path; they never write over the
package's own examples.

## The situation map is configured, not flagged

Everything a situation plate shows lives in one YAML file, and **almost
every thematic layer is off by default** — they are modes, and a plate that
switches them all on says less than one that picks. The keys the generator
reads:

**`region`** is the only required one — `{bbox: [west, south, east, north]}`
in degrees, and what the projection auto-centres on. The rest:

`title`, `subtitle`, `caption`, `as_of` · `style`, `animate`, `north_arrow` ·
`projection`, `basemap`, `frame`,
`padding`, `canvas_width`, `print_width`, `simplify`, `interactivity` ·
`areas_of_control`, `front`, `arrows`, `change`, `values`, `frontiers`,
`internal_borders`, `admin2_borders` · `forces`, `events`, `infrastructure`,
`labels`, `annotations`, `detail_area`, `rivers`, `lakes`, `cities`, `inset`,
`small_multiples` · `legend_position`, `legend_title`, `legend_footer`,
`marker_legend` · `source`, `attribution`, `method`, `provenance`.

For a plate that runs beside an article, start from `style: editorial`:
the status quo as paper (`areas_of_control.baseline`), one saturated colour
for the ground that changed hands, the zone named on the zone
(`labels.territories`), a title that states the finding, the key below the
map. It opens with a short CSS (Cascading Style Sheets, the language that sets a web page's colours, fonts and layout) animation sequence that `prefers-reduced-motion` stops
and that a PNG never shows.

`make_situation_map`'s module docstring carries the full reference under
**Every configuration key**, and a test fails if a top-level key is added
without a line there. That guard covers the top level only, so a nested key
can still arrive undocumented — `areas_of_control.over_water` and
`lakes.depth_rings` both did, in 0.10.0.

`source`, `as_of` and `method` are the provenance block, and they are the ones
to fill in first rather than last: `source` and `as_of` are what stop a plate from being
read as current when it is not, and `method` is where the assessment behind
the zones is named. See the contract above.

### The one key that is on by default

`interactivity` is the exception to "off unless asked", and it is worth
knowing before a plate goes on a page.

| Value | What ships |
|---|---|
| `"self-contained"` *(default)* | the plate carries its own layer switches, confidence filter and clickable legend, inside the file, with no page script |
| `"external"` | the controls are left to a page-level script |
| `"static"` | none of it ships |

It only materializes when `areas_of_control` has a `palette` — a plate with
no assessment on it is unaffected. And it degrades by construction: the panel
ships hidden and the script reveals it, so an `<img>` embed, a rasteriser or
a PDF see exactly the plain map. **An `<object>` embed does not** — there the
SVG is a live document and the controls come up, which is the point, but it
means a page that enlarges plates in a lightbox is shipping an interactive
map whether or not it meant to.

The controls keep their state in the URL fragment, which sounds alarming on
a page that routes by fragment itself and is not: the script reads and writes
`svg.ownerDocument.defaultView.location`, so inside an `<object>` it addresses
its own nested document and never the host page, and it uses
`history.replaceState` rather than `pushState`, so it adds no history entries.

Two more keys arrived with it, both nested, both off by default:
`areas_of_control.over_water` (`false`) keeps a zone's own shape instead of
clipping it to land, for a claim that really is maritime; `lakes.depth_rings`
(`4`) steps shelf rings inward from a lake's shore, `0` turns them off.

On a plate, rivers are drawn at one weight by default; `rivers: {width: ranked}`
tapers them by prominence. The thematic layers stay absent until asked for —
ask for what the map is about, not for everything the generator can draw.

## What every map carries by default

Since 0.7.0 a map is of a populated planet unless you say otherwise. Three
layers come on their own, and each has an off switch rather than an on one.

| Layer | Why it is on | Turn it off with |
|---|---|---|
| **Cities** | A map with nobody on it gives a reader nowhere to stand — they see where the Andes are and not where Lima is. Chosen by cartographic prominence, **not** by "is it a capital": that list omits New York, Mumbai, São Paulo, Shanghai, Los Angeles and Karachi, six of the world's twelve largest. The selection widens as the map zooms in. | `cities=False` in the library / `"cities": false` on the route (the CLI has no flag for it); on a situation plate, `cities: {show: false}` |
| **Rivers** | Drainage is the structure of a landmass, and tapering by prominence turns a tangle of blue lines into a network you can follow. Drawn over the thematic fill, where published cartography puts water. | `rivers=False` / `"rivers": false` (no CLI flag); on a plate, `rivers: {show: false}` |
| **Relief** | Computed from real elevation — a Lambertian hillshade blended with Brown's fractional-Laplacian texture shading — not a pre-shaded picture. | `relief=False` / `--no-relief`; on a plate, `basemap: {relief: false}` |

**A label in the way is dropped, not moved.** A city name nudged clear of its
own dot points at the wrong place and the reader has no way to tell. If a name
you want is missing, widen the selection (`cities.limit`, `cities.max_rank`) or
place it by hand in `labels.places`, which always wins over the automatic layer.

## The choropleth's one real decision: how to class the values

A choropleth turns numbers into colours, and **the rule it uses is the most
consequential setting on the map**. The same dataset classed four ways tells
four stories, and a reader given no statement of the method cannot tell which
one they are being told.

By default this generator does not class at all: it stretches the ramp
linearly from the smallest value to the largest. That is fine for values
spread evenly, and it is the weakest possible choice for the right-skewed data
most indicators are — income, density, counts, GDP (gross domestic product, the value of everything a country produces in a year) per head. On GDP per head
for twenty countries it puts nine of them in the bottom quarter of the ramp,
and leaves India, at ten times Burundi's figure, a shade the eye cannot tell
from Burundi's.

**So: whenever the values are skewed, pass `classes`.** Then pick the method
for the question being asked, not by habit:

| The map has to… | `method` | What it costs |
|---|---|---|
| support ranking — "which fifth is this region in?" | `quantile` | two regions with very different values can share a class; it flattens the skew by construction |
| show the groupings the data itself has | `jenks` | classes can be very unequal in count, and a lone outlier gets a class of its own |
| mean something outside the data — decades, percentage bands | `equal` | on skewed data most regions land in one class, which is the failure above |
| handle a heavy tail — "far more small things than large" | `headtail` | the class count comes from the data, not from you, and may be small |

**On a diverging indicator, zero is always a boundary.** Growth rates,
anomalies, swings — anything where the sign is the story. A class spanning
zero takes the colour of its own centre, so a country in recession comes out
the colour of growth; that is the one thing a diverging scale exists to
prevent. The generator now classes each side on its own values and keeps zero
as a break, so you do not have to arrange it. Worth knowing because it was
broken between 0.3.0 and 0.5.0: if you have a classed diverging map from that
window, re-render it.

**When the bands are editorial, pass them.** `breaks=[5, 10, 25]` in the
library or `"breaks": [5, 10, 25]` on the route (the CLI has no `--breaks`)
overrides both `classes` and `method`: a regulatory
threshold, a figure the newsroom already published, a number the reader
arrives with — no algorithm will land on those by luck. The legend then says
the breaks were *given*, which is the provenance that matters.

The legend prints the method and the boundaries. Do not strip that: a classed
map without its method is a claim with the evidence removed. When you hand the
figure on, say which method it used and why — the choice is editorial, and it
belongs with the map.

## A mistyped config key is an error, not a missing feature

The situation map is driven by nearly forty optional keys. Get one wrong and the
generator used to read past it in silence, so a slip on `areas_of_control`
dropped a whole layer while the plate still looked finished. Since 0.6.0 an
unknown key is refused and the error names the closest known one.

So when you see *"config has key(s) this generator never reads"*, read it as a
typo with the fix already in the message — not as a capability that is
missing. The keys are listed in the section above.

## Two modes: make and audit

| Mode | Tool | Purpose |
|---|---|---|
| **Make**, a choropleth on real geography | `make-map choropleth` | Territories shaded by a value, Equal Earth, OKLCH ramp, relief. |
| **Make**, an areas-of-control plate | `make-map situation-map` | Layered situation map for any region from one YAML config. |
| **Make**, an accumulation map | `make-map density` | Point events binned to a field, with no coastline drawn. |
| **Audit**, does the plate say how it was made | `make-map audit <plate.svg\|dir>` (`sprezzature-maps audit` is the same command) | Eleven static rules the figure auditor cannot ask, because they are map questions. On any plate: a classed legend that never names its method (`method-unnamed`), class breaks missing from the key (`breaks-missing`), no-data drawn but never named so absent reads as low (`no-data-hidden`), no vintage **and** no statement that the plate is a schematic (`no-provenance`), no title (`untitled`), no accessible name (`unlabelled`), a label that collides, runs off the plate or is set too small (`text-unreadable`). On a regional plate: no locator (`no-locator`), areas of control with no date (`undated-control`), every zone at one confidence (`evidence-unclassed`), a disputed boundary without its disclaimer (`disputed-unflagged`). Saying "synthetic illustrative values" counts as provenance, and counts for more than a date would, since stamping a vintage on invented data would be a fabrication. |
| **Improve**, render, look, repair | `make-map improve` | Renders a PNG, reads it with a local vision model, applies one safe repair at a time, and prints for a person the ones that could change what the map says. |

The audit is static: it reads the SVG and never renders. It sits beside the
`sprezzature-figures` auditor rather than replacing it: that one asks chart
questions, this one asks the questions only a map has.

## A plate bound for a journal page

A plate is designed in arbitrary user units and printed in millimetres, and
nothing joins the two by itself. Nature wants 90 mm for a single column and 180
for a double; Elsevier publishes 90, 140 and 190; Science 57, 121 and 184. All
three also set a floor for the type *inside* the figure — 5 to 7 pt — and all
three say to build the figure at the width it will print at rather than scale it
afterwards.

So when the user says the figure is for a paper, a poster or a column, set
`print_width` in the region config (there is no CLI flag for it):

```bash
# region.yaml carries:  print_width: "90mm"
make-map situation-map --config region.yaml --out figure-1.pdf
```

Three things follow from that key, and an agent should expect all three:

- **The root carries the physical width**, so the file lands at that size in a
  layout instead of at whatever a consumer infers from its pixel dimensions.
- **The plate measures its own smallest label against that width and says what
  it will actually be.** The bundled Ukraine plate is 1,364 units wide and its
  smallest label is 10.8 of them — dropped into a 90 mm column that label sets
  at **2.0 pt**, a third of Elsevier's 6 pt minimum, and it renders
  without complaint because a vector file always does. The warning is the
  feature; relay it rather than swallowing it.
- **The drop shadows come off.** An SVG filter is the one construct a vector
  exporter cannot express — it rasterises the region the filter covers — and
  the cost is per *mark*, not per plate. Paper has no hover state, so the
  shadow buys nothing there and costs embedded bitmaps inside the exact format
  the journal asked for because it has none. Geometry is untouched.

Give `--out` a `.pdf` or `.eps` and the page is **drawn**, not photographed.
That needs `rsvg-convert` from librsvg (`brew install librsvg`, `apt install
librsvg2-bin`) — an optional *system* package, not a Python dependency. Without
it the page is still written at the right physical size, with a warning saying
it is a raster and naming what to install. **Do not treat that warning as
noise**: a raster PDF satisfies the extension and nothing a journal wants, and
nobody can tell the two apart until they zoom in, by which point the figure is
in review.

Pick `rsvg-convert` specifically, and do not substitute. Measured on this
project's own plates: `cairosvg` ignores `paint-order` and comes back with
**every place name erased**, because each label's white halo paints over the
letters instead of under them; headless Chromium **printed the interactive
layer panel into the figure** and fell back to Times for part of the type.

A note for whoever compares two exports: the page is not byte-reproducible.
The converter stamps a creation date, which the plate itself deliberately does
not. The drawing is identical; the bytes are not.

## The five surfaces

Every tool in this suite is reachable five ways, and maps is no exception.
One `pip install sprezzature-maps` installs all of them; there are no extras.

| Surface | How |
|---|---|
| Library | `from sprezzature_maps import make_choropleth, make_density, make_situation_map`, plus `acled_events`, `ucdp_events`, `classification_methods`, `article_sidecar`, `plate_provenance`, `replay_report` |
| CLI | `make-map` (or `sprezzature-maps`), a Click group: `list`, `choropleth`, `situation-map`, `situation-new` (each also answers to its underscore spelling), `density`, `audit`, `improve` |
| HTTP (HyperText Transfer Protocol, the language a browser and a server speak each time a page loads) API (application programming interface, the requests one program can send another, such as render this chart) | `GET /health`, `GET /v1/kinds`, `POST /v1/choropleth`, `POST /v1/situation-map`, `POST /v1/density` (`uvicorn sprezzature_maps.api:app`, or `docker compose up` in the package repository, whose image runs `sprezzature-maps-mcp`: the API and `/mcp` on port 8000) |
| MCP (Model Context Protocol, the protocol through which AI agents call tools in English) | `sprezzature-maps-mcp`, endpoint `/mcp`. Five tools named by the routes' `operation_id`: `health`, `list_kinds`, `render_choropleth`, `render_situation_map`, `render_density`. The audit, the starter and `improve` have no MCP tool: they work on files on the caller's disk |
| Skill | this file |

A person can also open the Studio, `sprezzature-maps-studio`
(`http://127.0.0.1:8010/`), to paste data and edit a map in a browser.

All three render routes take every field as optional: send an empty body and
you get the demo map.

## Worked plates

Fifteen situation plates ship as Python configs in the package repository's
examples builder (`build_situation_examples.py`): six thematic (Ukraine, the lower
Dnieper with numbered article marks, Syria, Libya, Sudan, eastern Democratic Republic of the Congo (DRC)) and
nine reference plates with no thematic layer (Switzerland, Iberia, western
Europe, the Himalaya, the Caribbean, the Andes, the Sahel, the Strait of
Hormuz, the South China Sea). Read one before writing a config from scratch.

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
| Alt text for the emitted SVG | `sprezzature-accessibility` |
| Static a11y lint on the page that embeds it | `sprezzature-accessibility` |
