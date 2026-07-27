#!/usr/bin/env python3
"""
gather_gapminder — crunch one tidy dataset from multiple real sources.

Hans Rosling's famous bubble chart needs three time series per country — income
per person, life expectancy and population — on one shared, **annual** year grid,
1950 to 2025. No single public file carries all three cleanly for every country
across that span, so we gather them from the most reliable open sources and merge
them ourselves into one vendored comma-separated-values (CSV) file that the
figure builder reads offline:

======================  ==================================================  ==========
Series                  Source (Our World in Data grapher export)           Coverage
======================  ==================================================  ==========
income per person       Maddison Project Database (real GDP per capita, PPP  1–2022
                        adjusted), **extended to 2024 with World Bank PPP
                        growth rates** applied to the Maddison level so the
                        dollar base stays consistent (no cross-source splice
                        of *levels*); 2025 is a one-year trend extrapolation.
life expectancy         OWID life-expectancy incl. UN projections            1543–2100
                        (estimates to 2023, UN medium variant 2024-2025)
population              OWID population incl. UN projections                  ..–2100
                        (estimates to 2023, UN medium variant 2024-2025)
world region            OWID continents                                      static
======================  ==================================================  ==========

So of the trailing years only **income for 2025** is our own extrapolation
(everything else to 2025 is real data or the standard UN medium-variant
projection). We keep only countries with at least ``MIN_REAL`` real income
observations, interpolate the few interior gaps linearly, and back-fill the left
edge — so no bubble is mostly invented.

Output: ``assets/data/tribute-hans-rosling-1950-2025.csv`` with columns
``country,year,continent,gdpPercap,lifeExp,pop`` — the single file we provide
ourselves and the one ``make_gapminder.py`` consumes.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets" / "data" / "tribute-hans-rosling-1950-2025.csv"

# Our World in Data grapher CSV endpoints (full series, short column names).
BASE = "https://ourworldindata.org/grapher"
SUFFIX = "?v=1&csvType=full&useColumnShortNames=true"
GDP_MADDISON = ("gdp-per-capita-maddison-project-database", ["gdp_per_capita"])
GDP_WORLDBANK = ("gdp-per-capita-worldbank", ["ny_gdp_pcap_pp_kd"])   # PPP, reaches 2024
LIFE = ("life-expectancy-at-birth-including-the-un-projections",
        ["life_expectancy__sex_all__age_0__variant_estimates",
         "life_expectancy__sex_all__age_0__variant_medium__projected"])
POP = ("population-with-un-projections",
       ["population__sex_all__age_all__variant_estimates",
        "population__sex_all__age_all__variant_medium__projected"])
REGION = ("continents-according-to-our-world-in-data", "owid_region")

Y0, Y1 = 1950, 2025
YEARS = list(range(Y0, Y1 + 1))
MIN_REAL = 20                # min real income observations to keep a country
GDP_CLAMP = (0.94, 1.06)     # per-year growth band for the 2025 income extrapolation

# Collapse OWID's six continents onto Gapminder's five world regions.
REGION_MAP = {
    "Africa": "Africa", "Asia": "Asia", "Europe": "Europe", "Oceania": "Oceania",
    "North America": "Americas", "South America": "Americas",
}

# Real splits & merges. A federation is shown as **one bubble while it existed**
# and then **disappears the year it dissolved**, as its successors appear — no
# anachronism (no Czechia in 1950; no Czechoslovakia in 2000). The federation's
# income is the Maddison series for that entity; its population is the sum of the
# successors' present-border populations, and its life expectancy the
# population-weighted mean of theirs. Germany is a genuine merge but Maddison
# carries only the unified series, so it stays one continuous bubble.
FED_SUCCESSORS = {
    "Czechoslovakia": ["CZE", "SVK"],
    "Yugoslavia": ["HRV", "SVN", "BIH", "MKD", "MNE", "SRB"],
    "USSR": ["RUS", "EST", "LVA", "LTU", "UKR", "BLR", "MDA", "ARM", "AZE",
             "GEO", "KAZ", "KGZ", "TJK", "TKM", "UZB"],
}
DISSOLVE = {"Czechoslovakia": 1992, "Yugoslavia": 1991, "USSR": 1991}
FED_REGION = {"Czechoslovakia": "Europe", "Yugoslavia": "Europe", "USSR": "Europe"}
# Successor -> first year it appears as its own bubble (the year after dissolution).
APPEAR = {s: DISSOLVE[fed] + 1 for fed, succs in FED_SUCCESSORS.items() for s in succs}
APPEAR["DEU"] = 1991     # unified Germany appears at reunification; West/East before it
APPEAR["VNM"] = 1976     # unified Vietnam appears at reunification; North/South before it
APPEAR["YEM"] = 1991     # unified Yemen appears at unification; North/South before it

# Divided Germany (real merge, reunification 3 Oct 1990), benchmark data every 5
# years 1950-1990. West Germany income == Maddison's German series pre-1991
# (West-based, our 2011$ basis); East income = West x the East/West real-GDP
# ratio, which is basis-invariant (from the OWID "two Germanies" / Maddison
# 1990-Geary-Khamis series, ±5%). Population: DESTATIS (FRG) and GDR statistical
# yearbooks. East life expectancy = the (West-proxy) German series minus the
# Human-Mortality-Database-anchored East-below-West gap. See PROVENANCE.
GER_BENCH = list(range(1950, 1991, 5))
WEST_POP = [50.958e6, 52.382e6, 55.958e6, 59.297e6, 61.001e6, 61.645e6, 61.658e6, 61.020e6, 63.726e6]
EAST_POP = [18.388e6, 17.832e6, 17.188e6, 17.048e6, 17.057e6, 16.820e6, 16.740e6, 16.640e6, 16.028e6]
EAST_WEST_GDP_RATIO = [0.491, 0.457, 0.464, 0.446, 0.440, 0.483, 0.463, 0.479, 0.273]
EAST_LIFE_GAP = [0.0, 0.0, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 2.5]

# North/South Vietnam (merge 2 Jul 1976) and Yemen (unification 22 May 1990),
# split as two bubbles until they merge. Population from censuses/estimates
# (benchmarks, interpolated). Income: the unified Maddison level is split by a
# per-capita North/South ratio drawn from contemporary estimates, keeping the
# population-weighted mean equal to the Maddison national figure. Split life
# expectancy is not published, so both halves carry the national value.
# ``code`` is the unified Maddison entity; halves exist over ``span``.
DIVIDED = {
    "Vietnam": {
        "code": "VNM", "region": "Asia", "span": (1954, 1975),
        "bench": [1955, 1960, 1965, 1970, 1975],
        "north": ("North Vietnam", [16.1e6, 16.7e6, 18.7e6, 21.6e6, 24.0e6]),
        "south": ("South Vietnam", [12.0e6, 14.0e6, 16.3e6, 18.3e6, 19.6e6]),
        "ratio_ns": [0.645, 0.486, 0.508, 0.741, 1.0],   # North per-capita / South
    },
    "Yemen": {
        "code": "YEM", "region": "Asia", "span": (1970, 1990),
        "bench": [1970, 1975, 1980, 1985, 1990],
        "north": ("North Yemen", [4.8e6, 5.3e6, 5.8e6, 6.5e6, 7.161e6]),
        "south": ("South Yemen", [1.5e6, 1.7e6, 1.9e6, 2.2e6, 2.585e6]),
        "ratio_ns": [1.30, 1.30, 1.335, 1.221, 1.433],   # North per-capita / South
    },
}


def fetch(slug: str) -> list[dict[str, str]]:
    """Download one OWID grapher CSV and return its rows as dicts."""
    url = f"{BASE}/{slug}.csv{SUFFIX}"
    with urllib.request.urlopen(url, timeout=90) as resp:   # noqa: S310 (trusted host)
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))


def is_country(code: str) -> bool:
    """Real countries carry a 3-letter ISO code; OWID aggregates use OWID_* etc."""
    return len(code) == 3 and code.isalpha() and code.upper() == code


def index(rows: list[dict[str, str]], cols: list[str]) -> dict[str, dict[int, float]]:
    """Return {iso3: {year: value}}, taking the first non-empty of ``cols``."""
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


def extend_gdp(mad: dict[int, float], wb: dict[int, float]) -> dict[int, float]:
    """Extend a Maddison income series past 2022 using World Bank growth rates."""
    s = dict(mad)
    last = max(mad)
    for y in range(last + 1, Y1 + 1):
        if y in wb and (y - 1) in wb and (y - 1) in s and wb[y - 1] > 0:
            s[y] = s[y - 1] * (wb[y] / wb[y - 1])     # real growth, Maddison base
    return s


def densify(series: dict[int, float], min_real: int) -> list[float] | None:
    """Onto the full grid: interpolate interior gaps, back-fill left, trend-fill right."""
    if len(series) < min_real:
        return None
    known = sorted(series)
    first, last = known[0], known[-1]
    recent = known[-min(10, len(known)):]              # last decade of real points
    span = max(recent[-1] - recent[0], 1)
    cagr = (series[recent[-1]] / series[recent[0]]) ** (1 / span) if series[recent[0]] > 0 else 1.0
    cagr = min(max(cagr, GDP_CLAMP[0]), GDP_CLAMP[1])
    dense: list[float] = []
    for y in YEARS:
        if y in series:
            dense.append(series[y])
        elif y < first:
            dense.append(series[first])                # back-fill the left edge
        elif y > last:
            dense.append(series[last] * cagr ** (y - last))   # short trend extrapolation
        else:
            lo = max(k for k in known if k < y)        # linear interior interpolation
            hi = min(k for k in known if k > y)
            t = (y - lo) / (hi - lo)
            dense.append(series[lo] + t * (series[hi] - series[lo]))
    return dense


def main() -> None:
    """Gather the three series + regions and write the one crunched CSV."""
    print("downloading sources from Our World in Data ...")
    mad_rows = fetch(GDP_MADDISON[0])
    maddison = index(mad_rows, GDP_MADDISON[1])
    worldbank = index(fetch(GDP_WORLDBANK[0]), GDP_WORLDBANK[1])
    life = index(fetch(LIFE[0]), LIFE[1])
    pop = index(fetch(POP[0]), POP[1])

    # Federation income series (Czechoslovakia / USSR / Yugoslavia), by entity name.
    fed_gdp: dict[str, dict[int, float]] = {}
    for r in mad_rows:
        if r["entity"] in FED_SUCCESSORS and r.get("gdp_per_capita", ""):
            fed_gdp.setdefault(r["entity"], {})[int(r["year"])] = float(r["gdp_per_capita"])

    name_of = {r["code"]: r["entity"] for r in mad_rows if is_country(r.get("code", ""))}
    region_of: dict[str, str] = {}
    for r in fetch(REGION[0]):
        code = r.get("code", "")
        if is_country(code) and r.get(REGION[1]) in REGION_MAP:
            region_of[code] = REGION_MAP[r[REGION[1]]]
        name_of.setdefault(code, r.get("entity", code))

    rows: list[tuple] = []
    kept = 0
    for code in sorted(set(maddison) & set(life) & set(pop) & set(region_of)):
        gdp = extend_gdp(dict(maddison[code]), worldbank.get(code, {}))
        dg = densify(gdp, MIN_REAL)
        dl = densify(life[code], MIN_REAL)
        dp = densify(pop[code], MIN_REAL)
        if not (dg and dl and dp):
            continue
        kept += 1
        name, region = name_of.get(code, code), region_of[code]
        appear = APPEAR.get(code, Y0)                 # successors hidden before independence
        for i, y in enumerate(YEARS):
            if y >= appear:
                rows.append((name, y, region, round(dg[i], 2), round(dl[i], 2), int(dp[i])))

    # Federation bubbles: real Maddison income; population = sum of successors'
    # present-border populations; life expectancy = their population-weighted mean.
    # Written only for the years the federation existed (up to dissolution).
    for fed, succs in FED_SUCCESSORS.items():
        dg = densify(fed_gdp[fed], 1)
        for i, y in enumerate(YEARS):
            if y > DISSOLVE[fed]:
                break
            pops = [pop[s][y] for s in succs if s in pop and y in pop[s]]
            lifes = [(life[s][y], pop[s][y]) for s in succs
                     if s in life and s in pop and y in life[s] and y in pop[s]]
            if not pops or not lifes:
                continue
            tot = sum(pops)
            wlife = sum(lf * w for lf, w in lifes) / sum(w for _, w in lifes)
            rows.append((fed, y, FED_REGION[fed], round(dg[i], 2), round(wlife, 2), int(tot)))
        kept += 1

    # Divided nations: two bubbles until they merge, then one unified bubble.
    def interp(bench: list[int], vals: list[float], y: int) -> float:
        if y <= bench[0]:
            return vals[0]
        if y >= bench[-1]:
            return vals[-1]
        j = next(k for k in range(len(bench) - 1) if bench[k] <= y <= bench[k + 1])
        t = (y - bench[j]) / (bench[j + 1] - bench[j])
        return vals[j] + t * (vals[j + 1] - vals[j])

    # Germany (reunification 1990): West income is the Maddison German series
    # (West-based pre-1991); East income = West x the documented ratio.
    de_gdp, de_life = maddison.get("DEU", {}), life.get("DEU", {})
    for y in range(Y0, 1991):
        wg, wl = de_gdp.get(y), de_life.get(y)
        if wg is None or wl is None:
            continue
        ratio, gap = interp(GER_BENCH, EAST_WEST_GDP_RATIO, y), interp(GER_BENCH, EAST_LIFE_GAP, y)
        rows.append(("West Germany", y, "Europe", round(wg, 2), round(wl, 2),
                     int(interp(GER_BENCH, WEST_POP, y))))
        rows.append(("East Germany", y, "Europe", round(wg * ratio, 2), round(wl - gap, 2),
                     int(interp(GER_BENCH, EAST_POP, y))))
    kept += 2

    # Vietnam, Yemen: population-weighted split of the unified Maddison level, so
    # the two halves' population-weighted mean income equals the national figure.
    for cfg in DIVIDED.values():
        u_gdp = extend_gdp(dict(maddison.get(cfg["code"], {})), worldbank.get(cfg["code"], {}))
        u_life = life.get(cfg["code"], {})
        (nname, npop), (sname, spop) = cfg["north"], cfg["south"]
        for y in range(cfg["span"][0], cfg["span"][1] + 1):
            ug, ul = u_gdp.get(y), u_life.get(y)
            if ug is None or ul is None:
                continue
            pn, ps = interp(cfg["bench"], npop, y), interp(cfg["bench"], spop, y)
            r = interp(cfg["bench"], cfg["ratio_ns"], y)
            gs = ug * (pn + ps) / (pn * r + ps)      # keeps the pop-weighted mean == ug
            rows.append((nname, y, cfg["region"], round(r * gs, 2), round(ul, 2), int(pn)))
            rows.append((sname, y, cfg["region"], round(gs, 2), round(ul, 2), int(ps)))
        kept += 2

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country", "year", "continent", "gdpPercap", "lifeExp", "pop"])
        w.writerows(rows)
    print(f"wrote {OUT} — {kept} countries x {len(YEARS)} years ({Y0}-{Y1}) = {len(rows)} rows")


if __name__ == "__main__":
    main()
