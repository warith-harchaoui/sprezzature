# Dashboard Ergonomics

Translated and adapted from Synolia, *Data Visualisation : construire un tableau de bord percutant* — <https://www.synolia.com/blog/business-intelligence/data-visualisation-de-limportance-de-lergonomie-tableau-de-bord-percutant/>.

Use this file when the user asks for a dashboard, a BI tile, a KPI summary, or any data-visualization-heavy surface. Read alongside `charts-svg.md` (house style for hand-authored SVG charts) and `ergonomics-criteria.md` (Boucher's eight criteria).

## What a dashboard is for

Reformatting raw data into a form that the human eye can read in seconds. Tables, gauges, maps, scatter plots: each chosen because it carries one specific question better than a plain table does. Aim is to *save the user time* and *enable a decision*.

## The content must tell a story

A good dashboard answers a small, specific set of questions: **What? When? Who? Where? Why?** Lay out the content along a logical path — global overview first, fine-grained detail last. The user scrolls or drills down; they don't hunt.

## Before picking a chart, decide what you're showing

Four shapes the data can take:

- **Comparison** — same metric across categories.
- **Relation** — one variable against another (correlation, scatter).
- **Distribution** — how values spread.
- **Composition** — how parts make up a whole.

Two more questions:

- **Time evolution or single instant?** (A trend vs. a snapshot.)
- **How many values?** (Two series and ten categories is fine; ten series and 200 categories is not.)

These three answers eliminate most chart options before you've drawn a thing.

## Worked example

Goal: see how sales split by product category.

- **Few categories (≤ 4)** and a single instant → a pie chart works.
- **More categories (> 4)** → a pie becomes unreadable; switch to a sorted horizontal bar chart.
- **Time evolution by category** → a stacked bar chart over time, or a line chart per category.

## Ergonomic essentials for any tile

Each one is a lever; choose with intent.

| Element | Question to ask |
|---|---|
| Color | Does it encode meaning, or is it decorative? Map to `color-psychology.md`. |
| Label | Is the metric named in the user's vocabulary, not the developer's? |
| Size | Is the most important tile the largest? |
| Tooltip | Does hovering reveal the exact value and the dimension? |
| Title | Does the title state the question the tile answers? |
| Polarity | If the metric has a well-defined "good direction" *in this dashboard's context*, is it stated on the tile? (*Higher / lower is better*, or `target = N ± k`.) Skip for neutral axes and genuinely ambiguous metrics. |
| Shape | Is the chart shape the right one for the data shape? |
| Surface | Does it work on mobile, tablet, and desktop without rearranging meaning? |

## What a good dashboard buys you

### Speed of analysis

Visualizations let users draw conclusions in seconds, without exporting to a spreadsheet and re-pivoting.

### Data discovery

The deeper gain is *understanding why*, not just *seeing what*. A good dashboard lets the user:

- Filter to a specific category.
- Spot the products with the biggest swings.
- Cross-reference dimensions to find causes.
- Answer follow-up questions without leaving the tile.

That last point is the difference between a static report and a tool.

## Iterate

Once a dashboard is in users' hands, new questions surface. Self-service BI lets the user adapt the tile rather than file a ticket. Expect the dashboard to keep changing as questions change; it isn't a finished document.

## House rules (for emit)

When the skill emits a dashboard, apply these defaults — they sit on top of `charts-svg.md`.

1. **One question per tile.** A tile that tries to answer two questions answers neither well.
2. **Title as a question or assertion**, not a label. "Where do sales come from?" beats "Sales".
3. **Polarity stated on every measurable tile — when it's well-defined for *this* dashboard.** The same metric can be "higher is better" in one product and "lower is better" in another (time-in-app on a social app vs. a productivity tool; bug count on a young vs. mature codebase). Decide the polarity for the audience of this dashboard, then surface it as a tag (*↑ higher is better*, *↓ lower is better*, or *target = N ± k*) in the tile subtitle or chip next to the value. Skip the tag for neutral axes and ambiguous metrics. Never carry polarity by color alone; pair color with a word or glyph. Detail in `charts-svg.md` → "Polarity — higher or lower is better".
4. **Reading order top-to-bottom, left-to-right** matches the story: overview tile at top-left, drill-downs flowing toward the bottom-right. Reverse for RTL layouts.
5. **Same metric, same color across tiles.** If "active users" is `brand-blue` in tile 1, it's `brand-blue` in tile 4.
6. **No more than two color hues per tile**, plus neutrals. Color carries a dimension; if there's no dimension to carry, drop the color.
7. **Tabular numerals** on every numeric label (`tabular-nums`).
8. **Skeleton tiles while loading.** No spinners for ≥ 300 ms waits — see `ui-guidelines/patterns/loading.md`.
9. **Filters at the top**, applied to every tile in scope. Filter chips show what's active; one-tap clears.
10. **Per-tile timeframe selector** if tiles cover different windows.
11. **Empty state per tile.** Tell the user what to do next, not just "no data".
12. **Sticky header** (`ui-guidelines/components/navigation-bars.md`) with the dashboard name, the global filter state, and a "Reset" affordance.
13. **Print-aware**: a print stylesheet that drops translucent materials and forces solid surfaces.

## Layout patterns

### Single-column (mobile)

Stack tiles head-to-foot. Big-picture KPIs first; supporting detail below. One tile fills the viewport width.

### Two-column (tablet)

Hero tile spans both columns; supporting tiles pair up below.

### Grid (desktop)

`grid grid-cols-12 gap-4`. Hero tile `col-span-12 lg:col-span-8`; KPIs in a `col-span-12 lg:col-span-4` sidebar; drill-downs in a `lg:col-span-6` half-row.

```html
<main class="mx-auto w-full max-w-7xl grid grid-cols-12 gap-4 p-4 sm:p-6">
  <section class="col-span-12 lg:col-span-8 rounded-[10px] bg-surface-secondary p-4 dark:bg-surface-secondary-dark">
    <h2 class="text-[17px] font-semibold">Where do sales come from?</h2>
    <div id="hero" role="img" aria-label="Sales by region" class="mt-3"></div>
  </section>
  <aside class="col-span-12 lg:col-span-4 space-y-4">
    <article class="rounded-[10px] bg-surface-secondary p-4 dark:bg-surface-secondary-dark">
      <p class="text-[13px] uppercase tracking-wider text-label-tertiary">
        Revenue <span class="ml-1 normal-case tracking-normal text-label-tertiary">· ↑ higher is better</span>
      </p>
      <p class="mt-1 text-4xl font-bold tabular-nums">€1.84M</p>
      <p class="mt-1 text-[13px] text-brand-green">+8.4 % WoW</p>
    </article>
    <!-- … -->
  </aside>
  <section class="col-span-12 lg:col-span-6 rounded-[10px] bg-surface-secondary p-4 dark:bg-surface-secondary-dark">
    <h2 class="text-[17px] font-semibold">Which categories swung the most this week?</h2>
    <div id="swings" role="img" aria-label="Week-over-week change by category" class="mt-3"></div>
  </section>
  <!-- … -->
</main>
```

## Checklist

- [ ] Every tile answers one specific question.
- [ ] Titles read as questions or assertions, not labels.
- [ ] Polarity decided for the dashboard's context and stated on each tile whose "good direction" is well-defined (*↑ higher is better*, *↓ lower is better*, or *target = N ± k*), not carried by color alone.
- [ ] Same metric uses the same color across tiles.
- [ ] No tile uses more than two hues plus neutrals.
- [ ] Tabular numerals on numeric labels.
- [ ] Skeleton tiles while loading.
- [ ] Filters at the top; chips show active state; one-tap reset.
- [ ] Empty state per tile.
- [ ] Layout reflows from single-column mobile to grid desktop without losing the story order.
- [ ] Charts use the house tokens in `charts-svg.md`.
