# French presidential runoff results — by département

Second-round results (**% of votes cast**, `% Voix/Exprimés`) per département for the
last five French presidential elections, parsed from the official **Ministère de
l'Intérieur** open data published on [data.gouv.fr](https://www.data.gouv.fr).
Used by the small-multiples figure in
[`../../../../docs/FIGURES.md`](../../../../docs/FIGURES.md).

| File | Election | Winner / runner-up | Source shape |
|---|---|---|---|
| `pres-2002-t2-dpt.json` | 2002 | Chirac / Le Pen | *Départements T2* sheet |
| `pres-2007-t2-dpt.json` | 2007 | Sarkozy / Royal | *Départements T2* sheet |
| `pres-2012-t2-dpt.json` | 2012 | Hollande / Sarkozy | aggregated from the commune-level *Tour 2* sheet |
| `pres-2017-t2-dpt.json` | 2017 | Macron / Le Pen | *Départements Tour 2* sheet |
| `pres-2022-t2-dpt.json` | 2022 | Macron / Le Pen | *département* level file |

Each file is a list of `{code, nom, "<Candidate>": pct, …}`. Codes are the INSEE
département codes (`01`–`95`, Corsica `2A`/`2B`, plus overseas where the source
carries them). National headline figures used in the results table live in the
figure generator, not here. Public data — free to reuse with attribution to the
Ministère de l'Intérieur.
