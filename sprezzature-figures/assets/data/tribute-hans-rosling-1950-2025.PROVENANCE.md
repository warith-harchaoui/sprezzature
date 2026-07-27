# tribute-hans-rosling-1950-2025.csv — provenance

Income, life expectancy and population per country, **one row per country per
year, 1950–2025**, the crunched dataset behind the animated bubble chart
(`assets/svg-examples/gapminder-animated.svg`), a tribute to Hans Rosling. We
assemble it ourselves from authoritative open series, because no single public
file carries all three cleanly, annually, for every country across that span.

## Sources (Our World in Data grapher exports)

| Column | Series | Source | Real coverage |
|--------|--------|--------|---------------|
| `gdpPercap` | income per person (real GDP per capita, PPP) | Maddison Project Database (via OWID), **extended 2023–2024 with World Bank PPP growth rates** on the Maddison level | 1–2022 (+WB growth to 2024) |
| `lifeExp` | life expectancy at birth | OWID *life-expectancy incl. UN projections* (estimates + UN medium variant) | 1543–2100 |
| `pop` | population | OWID *population incl. UN projections* (estimates + UN medium variant) | –2100 |
| `continent` | world region (Asia, Africa, Americas, Europe, Oceania) | OWID *continents* | static |

The grid is **1950→2025**. Of the trailing years, only **income for 2025** is our
own one-year trend extrapolation (clamped to ±6%/yr); life expectancy and
population for 2024–2025 are the **standard UN medium-variant projections**, and
income for 2023–2024 uses **real World Bank growth** applied to Maddison's level
(so the dollar base stays consistent: never a cross-source splice of levels).
The figure and the CSV footnote both flag the recent years as part-projected.

## Splits & merges (real historical entities)

The dataset is **ragged** and historically honest: an entity has rows only for
the years it existed.

- **Federations** — the **USSR (to 1991)**, **Yugoslavia (to 1991)** and
  **Czechoslovakia (to 1992)** each appear as one bubble while they existed and
  then vanish the year they dissolved, as their successor states appear
  (Russia + 14 others in 1992, the six ex-Yugoslav states in 1992, Czechia &
  Slovakia in 1993). A federation's **income** is that entity's own Maddison
  series; its **population** is the sum of its successors' present-border
  populations; its **life expectancy** is their population-weighted mean.
- **Merges** — **West + East Germany → Germany (1991)**, **North + South
  Vietnam → Vietnam (1976)** and **North + South Yemen → Yemen (1991)** each show
  as two bubbles until they merge, then one. Because Maddison and the UN carry
  only the *unified* series for these, the halves are reconstructed from the best
  published sources, clearly as **estimates**:
  - *Population* — from national statistics / censuses (DESTATIS & GDR yearbooks;
    Vietnamese and Yemeni census anchors), interpolated between benchmark years.
  - *Income* — the two halves are placed on our purchasing-power basis from the
    **unified Maddison level and a documented per-capita ratio** (basis-invariant,
    so no cross-currency splice). For Germany the West half is the Maddison German
    series (West-based pre-1991) and the East half is that × the East/West ratio
    (OWID "two Germanies" / Maddison 1990 Geary-Khamis, ±5%). For Vietnam and
    Yemen the split is population-weighted so the two halves' mean equals the
    national Maddison figure; the North/South ratio comes from contemporary
    estimates (nominal-USD-derived: **used only as a ratio, never as a level**).
  - *Life expectancy at birth* — a published split is **not available** for these
    halves, so both carry the national value (Germany additionally applies the
    small HMD-anchored East-below-West gap). These trailing caveats are the honest
    limits of the sources; they are estimates, not measurements.

- **Columns:** `country, year, continent, gdpPercap, lifeExp, pop`.
- **Rows:** 11 759 (174 entities incl. 3 federations + 6 divided-nation halves;
  ragged year spans).
- **Licence:** CC-BY. Our World in Data, the Maddison Project, the World Bank
  and Gapminder are freely reusable with attribution.

## Independent verification

Cross-checked against the **World Bank Open Data** series (a methodology
independent of Maddison): life expectancy at birth (`SP.DYN.LE00.IN`) and GDP per
capita PPP (`NY.GDP.PCAP.PP.KD`), every overlapping country-year.

- **Life expectancy** matches for **161 of 164** comparable entities within
  ~1–2 years; the three exceptions (Kyrgyzstan, Armenia, Kuwait) are single-year
  war / earthquake spikes on which sources legitimately differ.
- **Income** agrees within the expected PPP base-year offset (World Bank is in
  2021 international dollars, this dataset in Maddison 2011); the ~38 residual
  divergences are the well-known hard cases, oil economies (Qatar, Kuwait, UAE,
  Saudi Arabia, Oman, Iraq) and conflict states (Syria, Libya, Angola), where any
  two sources disagree. Rosling's convention keeps the Maddison family here.

No crunching errors were found. Reconstructed and non-WB entities (the
federations, the divided-nation halves, Cuba, North Korea, Taiwan, Venezuela)
have no World Bank counterpart and stand on the sources documented above.

## Reproduce

```bash
python sprezzature-figures/scripts/gather_gapminder.py   # re-download + re-crunch this CSV
python sprezzature-figures/scripts/make_gapminder.py     # rebuild the animated SVG
```

`make_gapminder.py` reads only this vendored CSV (offline); `gather_gapminder.py`
is the online refresh step. A copy is served to site visitors at
`web/data/tribute-hans-rosling-1950-2025.csv`.
