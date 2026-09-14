# Choosing a map: three families, three failure modes

Someone hands you a column of place names and a column of numbers. There are
three families of map that can take it, they answer different questions, and
each one fails in its own way. Picking by habit — "a map means a choropleth" —
is how a chart ends up saying something its author did not mean.

## The three families

| Family | What it preserves | What it sacrifices | Where it lives |
|---|---|---|---|
| **Real geography** — choropleth, situation map | the shape of the land: coastlines, borders, relative position and distance under a stated projection | area is proportional to land, never to the thing being measured | `sprezzature-maps` |
| **Schematic** — hex map, binned grid, dot density, spike map | equal visual weight per unit, or one mark per event | the coastline; a viewer must already know the layout to read it | `sprezzature-figures` |
| **Cartogram** — area distorted by the value | the quantity, made directly comparable by area | recognisability; a badly distorted map is unreadable to a non-expert | neither, today — say so rather than substituting a choropleth |

## The question each one actually answers

- **Choropleth** answers *"what is the rate here?"* It is a map of a
  **ratio** — per capita, per km², a percentage, an index. Fill a choropleth
  with a raw count and it draws population, not your variable: the largest and
  most populous territories always win.
- **Situation map** answers *"who holds this ground, and where is the
  boundary?"* It is a map of **claims**, and claims have sources.
- **Hex map** answers *"which units are extreme?"* when the units matter
  equally and their size does not — fifty US states, twenty arrondissements.
- **Dot density** answers *"where are the events?"* It maps incidence, not
  rate, and it reads honestly at a glance where a choropleth of the same data
  would not.
- **Cartogram** answers *"how much, compared between places?"* when area
  really is the right encoding.

## The failure each one is prone to

**Choropleth — the large-empty-region bias.** Siberia, Nunavut, Western
Australia, the Sahara: enormous, nearly empty, and visually dominant. Before
drawing, check whether the value is a rate. If it is a count, either normalise
it or say plainly that the map shows counts and will over-weight large
territories. This is the single most common defect in published thematic maps
and the one to raise with the user before rendering, not after.

**Situation map — the authority it borrows.** A layered plate with real
coastlines, category fills and a dual-unit scale bar looks like a product from
an intelligence desk, so it is read as one. The generator has no opinion about
whether a zone is really controlled by whoever the config says. Carry the
provenance of the assessment with the map, every time it moves.

**Schematic maps — the recognition cost.** A hex map of France is unreadable
to someone who does not already know the départements by position. They work
for audiences fluent in the geography and fail for everyone else.

## The one-line decision

> Does the **shape of the land** carry meaning here?

Yes → `sprezzature-maps`. No → `sprezzature-figures`. If the honest answer is
"the quantity should be the area", say that a cartogram is what the data wants
and that this suite does not draw one yet, rather than shipping a choropleth
with the problem left in.
