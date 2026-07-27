# Provenance — Rosling variant series (fertility, child survival)

Two sibling series built on the **same entity set** as
`tribute-hans-rosling-1950-2025.csv`, by
`sprezzature-figures/scripts/gather_gapminder_variants.py`. They exist so the
sibling bubble charts share the first tribute's countries, period-correct
names, population sizes and region colours.

## Files

- `tribute-fertility-life-1950-2025.csv` — `country,year,continent,fertility,lifeExp,pop`
- `tribute-childsurvival-income-1950-2025.csv` — `country,year,continent,childSurvival,gdpPercap,pop`

`lifeExp`, `gdpPercap` and `pop` are copied verbatim from the first
tribute (so a country's bubble is the same size and height across all
three charts); only `fertility` and `childSurvival` are new here.

## Sources (Our World in Data, downloaded live)

| series | OWID grapher | provider | span used |
|---|---|---|---|
| Fertility rate (births per woman) | `children-per-woman-un` | UN World Population Prospects 2024 | 1950–2023 estimates |
| Child mortality (under-5, % of live births) | `child-mortality` | UN IGME | 1950–2024 |
| Population (successor weights) | `population-with-un-projections` | UN WPP 2024 | estimates + medium variant |

**Child survival** = `100 − under-5 mortality rate` (the OWID rate is
already a percentage of live births, so no unit conversion is needed).

## Rules (identical spirit to the first tribute)

- **Present-border countries** carry their own OWID series, densified onto
  the annual 1950–2025 grid: interior linear interpolation, left
  back-fill, and a short clamped trend (±1.5 %/yr) for 2024–2025 only,
  the same densify rule the first tribute uses. Fertility/mortality move
  slowly, so the trailing two projected years are a gentle extrapolation,
  not invention.
- **Federations** (USSR, Yugoslavia, Czechoslovakia) carry the
  **population-weighted mean** of their successors' series (successor
  populations from the same UN source) until dissolution, then the
  successors appear as their own bubbles, matching the first tribute.
- **Divided pairs** (West/East Germany, North/South Vietnam, North/South
  Yemen): a **documented approximation**. UN WPP / IGME publish fertility
  and child mortality for the *present-border parent only*, so both halves
  carry the parent's value for the split years. (The first tribute *did*
  reconstruct split income and life expectancy from documented ratios;
  we deliberately do **not** split fertility and child survival, because
  there is no authoritative half-country source and inventing one would
  betray the whole point of the exercise.)

## Spot checks (verified on build)

- Fertility: Niger 6.06 (2023), South Korea 0.72 (2023), Germany 1.44
  (2023), USSR 2.37 (1989, synthesised).
- Child survival: Sweden / Japan 99.76 % (2023), Niger 88.65 % (2023),
  Niger 67.89 % (1950).
- Row alignment: `lifeExp` / `gdpPercap` / `pop` match the first tribute
  row-for-row (e.g. Germany 2000: lifeExp 78.06, pop 81 797 255).

Not covered (no UN fertility/mortality series): Hong Kong, Puerto Rico.
