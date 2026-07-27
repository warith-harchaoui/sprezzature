"""
gather_gapminder_variants — two extra Rosling series on the SAME entity set.

The first tribute (``gather_gapminder.py`` → ``tribute-hans-rosling-1950-2025.csv``)
already resolves every country/year on Rosling's rules: present-border
countries, the three federations (USSR / Yugoslavia / Czechoslovakia)
synthesised until dissolution, and the divided pairs (West/East Germany,
North/South Vietnam, North/South Yemen) shown split until they merge.
This script keeps **exactly that entity set** and merges two more Our
World in Data series onto it so the sibling bubble charts share the first
one's countries, names, population sizes and colours:

* **Fertility rate** (births per woman) — UN World Population Prospects,
  OWID ``children-per-woman-un`` (estimates 1950-2023).
* **Child survival** (% surviving to age 5) = ``100 − under-5 mortality
  rate``, OWID ``child-mortality`` (UN IGME, the rate is already a
  percentage of live births).

Outputs two crunched CSVs next to the first tribute:

* ``tribute-fertility-life-1950-2025.csv`` — ``country,year,continent,fertility,lifeExp,pop``
* ``tribute-childsurvival-income-1950-2025.csv`` — ``country,year,continent,childSurvival,gdpPercap,pop``

Data honesty (the point of the exercise):

* Present-border countries carry their own OWID series, densified onto the
  annual grid (interior linear interpolation, left back-fill, a short
  clamped trend for 2024-2025 — the same densify rule the first tribute
  uses).
* The federations carry the **population-weighted mean** of their
  successors' series (successor populations from the same UN source).
* The divided pairs (West/East Germany, N/S Vietnam, N/S Yemen) are a
  documented approximation: UN WPP / IGME publish fertility and child
  mortality for the **present-border** parent only, so both halves carry
  the parent's value for those years. Income and life expectancy keep the
  first tribute's reconstructed split; fertility and child survival do
  not, because splitting them here would be invention, not data.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

BASE = "https://ourworldindata.org/grapher"
SUFFIX = "?v=1&csvType=full&useColumnShortNames=true"

FERT = ("children-per-woman-un", "fertility_rate__sex_all__age_all__variant_estimates")
CHILDMORT = ("child-mortality", "child_mortality_rate")   # % of live births dying < age 5
POP = ("population-with-un-projections",
       ["population__sex_all__age_all__variant_estimates",
        "population__sex_all__age_all__variant_medium__projected"])

Y0, Y1 = 1950, 2025
YEARS = list(range(Y0, Y1 + 1))
MIN_REAL = 12                 # min real observations to keep a country's series
TREND_CLAMP = (0.985, 1.015)  # per-year band for the 2024-2025 trend fill

# The first tribute's entity backbone — its (country, year) rows already
# carry continent, gdpPercap, lifeExp and pop on Rosling's rules.
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "assets" / "data"
TRIBUTE = DATA / "tribute-hans-rosling-1950-2025.csv"

# Federations → successor ISO codes (population-weighted mean while the
# federation is one bubble). Mirrors gather_gapminder.py.
FED_SUCCESSORS = {
    "Czechoslovakia": ["CZE", "SVK"],
    "Yugoslavia": ["HRV", "SVN", "BIH", "MKD", "MNE", "SRB"],
    "USSR": ["RUS", "EST", "LVA", "LTU", "UKR", "BLR", "MDA", "ARM", "AZE",
             "GEO", "KAZ", "KGZ", "TJK", "TKM", "UZB"],
}
# Divided halves → present-border parent ISO whose series both halves carry.
DIVIDED_PARENT = {
    "West Germany": "DEU", "East Germany": "DEU",
    "North Vietnam": "VNM", "South Vietnam": "VNM",
    "North Yemen": "YEM", "South Yemen": "YEM",
}
# Tribute country name → ISO overrides where the name differs from OWID's.
NAME_ISO_OVERRIDE = {
    "Democratic Republic of Congo": "COD", "Congo": "COG",
    "Cote d'Ivoire": "CIV", "Timor": "TLS", "Laos": "LAO",
    "Micronesia (country)": "FSM", "Czechia": "CZE",
}


def fetch(slug: str) -> list[dict[str, str]]:
    """Download one OWID grapher CSV and return its rows as dicts."""
    url = f"{BASE}/{slug}.csv{SUFFIX}"
    # OWID rejects the default urllib user-agent (403), so present a browser one.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (sprezzature-figures data gather)"})
    with urllib.request.urlopen(req, timeout=120) as resp:   # noqa: S310 (trusted host)
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))


def is_country(code: str) -> bool:
    """Real countries carry a 3-letter ISO code; OWID aggregates use OWID_*."""
    return len(code) == 3 and code.isalpha() and code.upper() == code


def index(rows: list[dict[str, str]], cols: list[str]) -> dict[str, dict[int, float]]:
    """Return {iso3: {year: value}} taking the first non-empty of ``cols``."""
    out: dict[str, dict[int, float]] = {}
    for r in rows:
        code = r.get("code", "")
        if not is_country(code):
            continue
        try:
            year = int(r["year"])
        except (ValueError, KeyError):
            continue
        for col in cols:
            raw = r.get(col, "")
            if raw not in ("", None):
                out.setdefault(code, {})[year] = float(raw)
                break
    return out


def densify(series: dict[int, float], lo_clamp: float, hi_clamp: float) -> list[float] | None:
    """Onto the full 1950-2025 grid: interpolate gaps, back-fill left, trend-fill right."""
    if len(series) < MIN_REAL:
        return None
    known = sorted(series)
    first, last = known[0], known[-1]
    recent = known[-min(10, len(known)):]
    span = max(recent[-1] - recent[0], 1)
    base = series[recent[0]]
    cagr = (series[recent[-1]] / base) ** (1 / span) if base > 0 else 1.0
    cagr = min(max(cagr, lo_clamp), hi_clamp)
    dense: list[float] = []
    for y in YEARS:
        if y in series:
            dense.append(series[y])
        elif y < first:
            dense.append(series[first])
        elif y > last:
            dense.append(series[last] * cagr ** (y - last))
        else:
            klo = max(k for k in known if k < y)
            khi = min(k for k in known if k > y)
            t = (y - klo) / (khi - klo)
            dense.append(series[klo] + t * (series[khi] - series[klo]))
    return dense


def main() -> None:
    """Fetch the two series, merge onto the tribute entity set, write both CSVs."""
    print("downloading fertility + child-mortality + population from OWID ...")
    fert_rows = fetch(FERT[0])
    cm_rows = fetch(CHILDMORT[0])
    pop_rows = fetch(POP[0])

    # OWID entity name -> ISO, for mapping tribute country names.
    name_iso = {r["entity"]: r["code"] for r in fert_rows if is_country(r.get("code", ""))}
    name_iso.update(NAME_ISO_OVERRIDE)

    fert = index(fert_rows, [FERT[1]])
    cmort = index(cm_rows, [CHILDMORT[1]])
    surv = {iso: {y: max(0.0, 100.0 - v) for y, v in s.items()} for iso, s in cmort.items()}
    pop = index(pop_rows, POP[1])

    # Densify every ISO series onto the grid (fertility/survival move slowly).
    fert_d = {iso: d for iso in fert if (d := densify(fert[iso], *TREND_CLAMP))}
    surv_d = {iso: d for iso in surv if (d := densify(surv[iso], *TREND_CLAMP))}
    pop_d = {iso: d for iso in pop if (d := densify(pop[iso], 0.90, 1.10))}
    yi = {y: i for i, y in enumerate(YEARS)}

    def fed_mean(succs: list[str], year: int, table: dict[str, list[float]]) -> float | None:
        """Population-weighted mean of successors' densified value in ``year``."""
        num = den = 0.0
        for s in succs:
            if s in table and s in pop_d:
                w = pop_d[s][yi[year]]
                num += table[s][yi[year]] * w
                den += w
        return num / den if den else None

    def value_for(name: str, year: int, table: dict[str, list[float]]) -> float | None:
        """The densified series value for a tribute entity name in a year."""
        if name in FED_SUCCESSORS:
            return fed_mean(FED_SUCCESSORS[name], year, table)
        iso = DIVIDED_PARENT.get(name) or name_iso.get(name)
        if iso and iso in table:
            return table[iso][yi[year]]
        return None

    # Walk the tribute rows and attach the two series.
    tribute = list(csv.DictReader(TRIBUTE.open()))
    rows_a: list[tuple] = []   # fertility vs life
    rows_b: list[tuple] = []   # child survival vs income
    missing: set[str] = set()
    for r in tribute:
        name, year = r["country"], int(r["year"])
        cont, gdp, life, p = r["continent"], r["gdpPercap"], r["lifeExp"], r["pop"]
        f = value_for(name, year, fert_d)
        s = value_for(name, year, surv_d)
        if f is None or s is None:
            missing.add(name)
        if f is not None:
            rows_a.append((name, year, cont, round(f, 3), life, p))
        if s is not None:
            rows_b.append((name, year, cont, round(s, 3), gdp, p))

    out_a = DATA / "tribute-fertility-life-1950-2025.csv"
    out_b = DATA / "tribute-childsurvival-income-1950-2025.csv"
    with out_a.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country", "year", "continent", "fertility", "lifeExp", "pop"])
        w.writerows(rows_a)
    with out_b.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country", "year", "continent", "childSurvival", "gdpPercap", "pop"])
        w.writerows(rows_b)

    print(f"wrote {out_a.name}: {len(rows_a)} rows")
    print(f"wrote {out_b.name}: {len(rows_b)} rows")
    if missing:
        print(f"entities with no fertility/survival match ({len(missing)}): "
              f"{', '.join(sorted(missing))}")


if __name__ == "__main__":
    main()
