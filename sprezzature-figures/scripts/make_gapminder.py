#!/usr/bin/env python3
"""
make_gapminder — build the animated Gapminder bubble chart (Hans Rosling homage).

Reads the **real** crunched dataset (``assets/data/tribute-hans-rosling-1950-2025.csv`` — income,
life expectancy and population per country, **one row per country per year,
1952-2022**, gathered from Our World in Data; see the sibling ``.PROVENANCE.md``)
and emits one self-contained animated Scalable Vector Graphics (SVG) file with
**pure SMIL** animation — no JavaScript, no charting library, no build step.

Every country in the dataset is a bubble: horizontal = GDP per capita (log
scale), vertical = life expectancy, area = population, colour = world region.
The bubbles animate **year by year** (one frame per year, five seconds per year),
sweeping up and to the right as countries grow richer and healthier — the point
Rosling made famous. The largest countries carry a name label that follows the
bubble, and a big year counter ticks every year behind the cloud.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from gapminder_i18n import COUNTRIES_FR, HISTORY_FR, LABELS_FR, REGIONS_FR
from _interactive import fullscreen_control
from _style import forced_color_patterns, leveled_colors, os_adaptive_style, os_dark_style

# English interface strings, mirroring LABELS_FR so the builder is fully bilingual.
LABELS_EN = {
    "title_link": "Tribute to Hans Rosling",
    "title_rest": " &#8212; Health and Wealth of Nations &#8212; 1950&#8211;2025",
    "subtitle": "Each bubble is a country with size for population and color for region",
    "x_axis": "GDP per capita ($, log scale) &#8594;",
    "y_axis": "Life expectancy (years) &#8594;",
    "legend_region": "REGION", "legend_population": "POPULATION",
    "data_link": "Tribute to Hans Rosling Data",
    "title_a11y": "Tribute to Hans Rosling — Health and Wealth of Nations",
    "pop_1b": "1 billion", "pop_250m": "250 million", "pop_50m": "50 million",
    "desc": (
        "An animated bubble chart in homage to Hans Rosling, built from real data for all countries, "
        "one frame per year from 1950 to 2025. Each bubble is a country: horizontal is GDP per capita "
        "(log scale), vertical is life expectancy, area is population, colour is world region. "
        "A year counter ticks year by year as the bubbles sweep up and to the right — Asia (red) moves "
        "the most, Africa (blue) stays lower-left, Europe (amber) and the Americas (green) sit rich and "
        "high. Historical federations (USSR, Yugoslavia, Czechoslovakia) show as one bubble until they "
        "dissolve, then their successor states appear; divided nations (East/West Germany, North/South "
        "Vietnam and Yemen) show as two bubbles until they merge into one. Recent years are "
        "part-projected: life expectancy and population for 2024-2025 are UN medium-variant projections "
        "and income for 2025 is a short trend extrapolation."),
}

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "assets" / "data" / "tribute-hans-rosling-1950-2025.csv"
OUT = HERE.parent / "assets" / "svg-examples" / "gapminder-animated.svg"

# Countries to plot. Empty = ALL countries — the true Rosling "cloud".
COUNTRIES: list[str] = []
# At each instant the biggest TOP_LABELS countries (by that year's population)
# carry a following name label; the selection changes as the animation plays.
# Every other bubble still reveals its name on hover (and via a <title> tooltip).
TOP_LABELS = 10

# World-region colour — the Okabe-Ito colour-blind-safe qualitative set.
# The classic Gapminder scheme paints Asia red and the Americas green, the
# one pairing that collapses into a single muddy tone under deuteranopia and
# protanopia (red-green colour blindness) — and those are the two most
# populous regions, the biggest clouds of bubbles on the chart. Okabe & Ito's
# eight-colour palette (Okabe & Ito, 2008) is engineered so every pair stays
# distinct across all three common deficiencies, so we map the five regions
# onto it: blue, orange, bluish-green, reddish-purple and vermillion. Region
# is a secondary cue here anyway — position is wealth-and-health and the named
# bubbles carry their country label — but no reader now loses the grouping to
# a colour-vision deficiency.
REGION_COLOR = {
    "Asia": "#0072B2", "Africa": "#E69F00", "Americas": "#009E73",
    "Europe": "#CC79A7", "Oceania": "#D55E00",
}

# Period-accurate names: a country's label reads the name in use that year, so
# there is no anachronism (e.g. no "Myanmar" in 1960 — it was Burma). Only the
# same-territory renames within 1950-2025 are listed; splits/merges keep their
# present name (present-day-borders convention). Keyed by the dataset's present
# name; each tuple is (first_year, last_year_inclusive, name_used_then).
NAME_HISTORY = {
    "Myanmar": [(1950, 1988, "Burma"), (1989, 2025, "Myanmar")],
    "Sri Lanka": [(1950, 1971, "Ceylon"), (1972, 2025, "Sri Lanka")],
    "Tanzania": [(1950, 1963, "Tanganyika"), (1964, 2025, "Tanzania")],
    "Zimbabwe": [(1950, 1979, "Rhodesia"), (1980, 2025, "Zimbabwe")],
    "Bangladesh": [(1950, 1954, "East Bengal"), (1955, 1970, "East Pakistan"),
                   (1971, 2025, "Bangladesh")],
    "Democratic Republic of Congo": [
        (1950, 1959, "Belgian Congo"), (1960, 1970, "Congo-Kinshasa"),
        (1971, 1996, "Zaire"), (1997, 2025, "DR Congo")],
}

W, H = 1020, 520
X0, X1 = 100, 710       # plot x range (income, log; 3 decades $100-$100k); wide right margin = legend
Y0, Y1 = 448, 60        # plot y range (life expectancy; y is inverted)
R_MIN, R_MAX = 2.6, 46.0
SEC_PER_YEAR = 1        # pacing: one year of the sweep lasts one second


# Player engine embedded in the SVG. It takes over the SMIL timeline (pause +
# setCurrentTime driven by requestAnimationFrame) so the page can play/pause,
# scrub, step year by year, change speed, restart and follow a country — all via
# postMessage, which works both over http and from file://. Honours
# prefers-reduced-motion (starts on the final frame, paused). The scale constants
# are prepended per build so it can invert a followed bubble back to its values.
PLAYER_JS = r"""(function(){
var S=document.documentElement,B=(S.getAttribute("viewBox")||"0 0 1 1").split(/\s+/).map(Number),V=B.slice();
var t=0,playing=true,speed=1,following=null,last=0,ticks=0;
var reduce=false;try{reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;}catch(e){}
S.pauseAnimations();if(reduce){playing=false;t=DUR-0.01;}S.setCurrentTime(t);
function P(m){try{if(window.parent&&window.parent!==window)window.parent.postMessage(m,"*");}catch(e){}}
function yr(){return Y0i+Math.round(t/DUR*(Y1i-Y0i));}
function setT(n){t=Math.max(0,Math.min(DUR-0.01,n));S.setCurrentTime(t);}
function esc(s){return s.replace(/["\\]/g,"\\$&");}
function invX(x){return Math.pow(10,(x-X0)/(X1-X0)*(Math.log10(GHI)-Math.log10(GLO))+Math.log10(GLO));}
function invY(y){return LLO+(y-Y0)/(Y1-Y0)*(LHI-LLO);}
function invR(r){var k=(r-RMIN)/(RMAX-RMIN);return POPMAX*k*k;}
function report(){if(!following){return;}var g=S.querySelector('[data-c="'+esc(following)+'"]');
if(!g){P({gm:"follow",name:following,exists:false});return;}
var op=1;try{op=parseFloat(getComputedStyle(g).opacity);}catch(e){}
var tl=g.transform.animVal,c=g.querySelector("circle");
if(!tl.numberOfItems||!c){P({gm:"follow",name:following,exists:false});return;}
var m=tl.getItem(0).matrix,r=c.r.animVal.value;
P({gm:"follow",name:following,exists:op>0.06,year:yr(),income:Math.round(invX(m.e)),life:Math.round(invY(m.f)*10)/10,pop:Math.round(invR(r))});}
function setFollow(name){var p=S.querySelector(".gm-follow");if(p)p.classList.remove("gm-follow");
following=name||null;if(following){var g=S.querySelector('[data-c="'+esc(following)+'"]');if(g){g.classList.add("gm-follow");S.appendChild(g);}}report();}
function loop(ts){if(last&&playing){t+=(ts-last)/1000*speed;if(t>=DUR)t-=DUR;S.setCurrentTime(t);}last=ts;
if((ticks++%6)===0){P({gm:"tick",year:yr(),playing:playing});report();}requestAnimationFrame(loop);}
requestAnimationFrame(loop);
window.addEventListener("message",function(e){var m=e.data;if(!m||!m.gm)return;
if(m.gm==="toggle")playing=!playing;else if(m.gm==="play")playing=true;else if(m.gm==="pause")playing=false;
else if(m.gm==="seekYear")setT((m.year-Y0i)/(Y1i-Y0i)*DUR);
else if(m.gm==="step"){playing=false;setT(t+m.d/(Y1i-Y0i)*DUR);}
else if(m.gm==="speed")speed=m.v;else if(m.gm==="restart"){setT(0);playing=true;}
else if(m.gm==="follow")setFollow(m.name);
else if(m.gm==="hello")P({gm:"ready",y0:Y0i,y1:Y1i,countries:names,reduced:reduce});});
S.addEventListener("click",function(e){var g=e.target.closest?e.target.closest(".gm-b"):null;
if(g&&g.getAttribute("data-c")){setFollow(g.getAttribute("data-c"));P({gm:"picked",name:g.getAttribute("data-c")});}});
var names=[];S.querySelectorAll(".gm-b").forEach(function(g){var c=g.getAttribute("data-c");if(c&&names.indexOf(c)<0)names.push(c);});
names.sort();P({gm:"ready",y0:Y0i,y1:Y1i,countries:names,reduced:reduce});
var dg=false,lx=0,ly=0;
function big(){try{if(window.parent&&window.parent!==window&&window.parent.document.fullscreenElement)return true;}catch(e){}return !!document.fullscreenElement;}
function ap(){S.setAttribute("viewBox",V.join(" "));}
function toS(x,y){var r=S.getBoundingClientRect();return[V[0]+(x-r.left)/r.width*V[2],V[1]+(y-r.top)/r.height*V[3]];}
S.addEventListener("wheel",function(e){if(!big())return;e.preventDefault();var f=e.deltaY<0?1.15:1/1.15,nw=Math.min(B[2],Math.max(B[2]/12,V[2]/f)),nh=nw*(B[3]/B[2]),p=toS(e.clientX,e.clientY);V[0]=p[0]-(p[0]-V[0])*(nw/V[2]);V[1]=p[1]-(p[1]-V[1])*(nh/V[3]);V[2]=nw;V[3]=nh;ap();},{passive:false});
S.addEventListener("mousedown",function(e){if(!big()||V[2]>=B[2]-0.5)return;dg=true;lx=e.clientX;ly=e.clientY;e.preventDefault();});
window.addEventListener("mousemove",function(e){if(!dg)return;var r=S.getBoundingClientRect();V[0]-=(e.clientX-lx)/r.width*V[2];V[1]-=(e.clientY-ly)/r.height*V[3];lx=e.clientX;ly=e.clientY;ap();});
window.addEventListener("mouseup",function(){dg=false;});
try{window.parent.document.addEventListener("fullscreenchange",function(){if(!big()){V=B.slice();ap();}});}catch(e){}
})();"""


def load() -> tuple[list[int], dict[str, dict]]:
    """Return (years grid, {country: {continent, gdp[], life[], pop[], appear, disappear}}).

    The dataset is **ragged**: historical federations end the year they dissolved
    and their successor states begin the year they became independent. Every
    entity is still placed across the whole grid (its value edge-held for the
    years it did not exist, when it is invisible anyway) plus an appear/disappear
    window, so its bubble can fade in and out at exactly the right year.
    """
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    years = sorted({int(r["year"]) for r in rows})
    picked = set(COUNTRIES)
    by: dict[str, dict] = {}
    for r in rows:
        if picked and r["country"] not in picked:
            continue
        c = by.setdefault(r["country"], {"continent": r["continent"], "gdp": {}, "life": {}, "pop": {}})
        y = int(r["year"])
        c["gdp"][y], c["life"][y], c["pop"][y] = float(r["gdpPercap"]), float(r["lifeExp"]), float(r["pop"])
    out: dict[str, dict] = {}
    for name, c in by.items():
        present = sorted(c["gdp"])
        lo, hi = present[0], present[-1]

        def edge(s: dict[int, float], lo: int = lo, hi: int = hi) -> list[float]:
            return [s[y] if y in s else s[lo] if y < lo else s[hi] for y in years]

        out[name] = {"continent": c["continent"], "gdp": edge(c["gdp"]),
                     "life": edge(c["life"]), "pop": edge(c["pop"]),
                     "appear": lo, "disappear": hi}
    return years, out


def main(lang: str = "en", mode: str = "external", accessibility: str = "universal") -> None:
    """Build the animated SVG (``lang`` = 'en' or 'fr') and write it to disk.

    Parameters
    ----------
    lang : str, optional
        Interface language, ``'en'`` or ``'fr'``. Defaults to ``'en'``.
    mode : str, optional
        Fullscreen-control mode passed to :func:`fullscreen_control`
        (``'external'`` or ``'self-contained'``). Defaults to ``'external'``.
    accessibility : str, optional
        Colour-vision level applied to the categorical region palette via
        :func:`_style.leveled_colors`. ``'universal'`` (the default) is the
        identity, so the shipped SVG stays byte-for-byte the same; the other
        levels (``'high-contrast'``, ``'monochrome'``, ``'deuteranopia'``,
        ``'protanopia'``, ``'tritanopia'``) remap the five region hues.
    """
    fr = lang == "fr"
    # Region → colour is a genuine categorical set, so it answers to the
    # accessibility level. At ``universal`` this is the identity, so the
    # default output is unchanged.
    region_color = leveled_colors(REGION_COLOR, accessibility)
    # forced-colors: one Canvas/CanvasText pattern per world region, applied to
    # every bubble and legend swatch of that region (`.rg-<region>`). In Windows
    # High Contrast the ~4-colour system palette cannot preserve the five-way
    # region encoding, so each region reads as a distinct hatch / dot / cross
    # tile instead. The defs + block are additive and only referenced inside the
    # forced-colors media query, so the default animated render is unchanged.
    fc_defs, fc_style = forced_color_patterns(
        [f".rg-{r.lower()}" for r in REGION_COLOR], prefix="gmfc"
    )
    out_path = OUT if not fr else OUT.with_suffix(".fr.svg")
    lab = LABELS_FR if fr else LABELS_EN

    def tc(name: str) -> str:                       # translate a country label
        return COUNTRIES_FR.get(name, name) if fr else name

    def tr(region: str) -> str:                     # translate a region label
        return REGIONS_FR.get(region, region) if fr else region

    def th(disp: str) -> str:                        # translate a historical-name label
        return HISTORY_FR.get(disp, disp) if fr else disp

    years, data = load()
    n = len(years)
    dur_s = (int(years[-1]) - int(years[0])) * SEC_PER_YEAR
    dur = f"{dur_s}s"                                              # 1 year = 1 s
    keytimes = ";".join(f"{i / (n - 1):.4f}" for i in range(n))

    pop_max = max(p for d in data.values() for p in d["pop"])
    glo, ghi = 300, 200000  # fixed income domain: $300 ... $200k
    llo, lhi = 8, 92        # fixed life-expectancy domain so the 10..90 ticks all show

    def sx(g: float) -> float:
        g = min(max(g, glo), ghi)   # clamp the few outliers to the axis ends
        t = (math.log10(g) - math.log10(glo)) / (math.log10(ghi) - math.log10(glo))
        return X0 + t * (X1 - X0)

    def money(v: float) -> str:
        return f"${v / 1000:.0f}k" if v >= 1000 else f"${v:.0f}"

    def sy(le: float) -> float:
        return Y0 + (le - llo) / (lhi - llo) * (Y1 - Y0)

    def sr(pop: float) -> float:
        return R_MIN + math.sqrt(pop / pop_max) * (R_MAX - R_MIN)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Roboto, system-ui, sans-serif" role="img" aria-labelledby="gm-t gm-d">',
        f'<title id="gm-t">{lab["title_a11y"]}, {years[0]} to {years[-1]}</title>',
        f'<desc id="gm-d">{lab["desc"]}</desc>',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        # Hover any bubble (when the SVG is live, e.g. embedded via <object>) to
        # reveal that country's name; the biggest carry an always-on label.
        # OS-adaptive overrides (additive; the default render is unchanged
        # because every rule below lives inside an @media query, and the class
        # only outranks the inline bubble fill/stroke once the query matches).
        # Under prefers-contrast the five world-region hues deepen to their
        # high-contrast versions on both the bubbles and the legend swatches.
        # Under forced-colors (Windows High Contrast) the region is carried by
        # colour alone — bubbles are placed by wealth and health, not grouped —
        # so the ~4-colour system palette cannot preserve the five-way encoding.
        # Each region instead becomes a distinct Canvas/CanvasText pattern (see
        # ``fc_style`` / ``fc_defs``), keyed on the shared ``.rg-<region>`` class.
        '<style>.gm-name{opacity:0;pointer-events:none;transition:opacity .12s ease}'
        '.gm-b:hover .gm-name,.gm-b:focus-within .gm-name{opacity:1}'
        '.gm-b:hover circle{stroke-width:2.4}'
        '.gm-b.gm-follow .gm-name{opacity:1}'
        '.gm-b.gm-follow circle{stroke:#1D1D1F;stroke-width:3}'
        + os_adaptive_style(
            {f".rg-{r.lower()}": REGION_COLOR[r] for r in REGION_COLOR},
            role="both",
        )
        + fc_style
        # Additive dark mode: flip paper + the two ink tiers, and lift the
        # follow-ring stroke (dark ink) to the light ink so it stays visible.
        + os_dark_style(extra=".gm-b.gm-follow circle{stroke:#F2F2F7;}")
        + '</style>',
        # Forced-colors pattern tiles (inert unless forced-colors is active).
        '<defs>' + fc_defs + '</defs>',
    ]

    # Big faint year counter — every year in the series (+1, not decades). Each year
    # text fades in only during its own window; the sweep and the counter share
    # the same duration so they stay in step.
    y0, y1 = int(years[0]), int(years[-1])
    span = y1 - y0
    ykt = ";".join(f"{k / span:.4f}" for k in range(span + 1))
    for k in range(span + 1):
        vals = ";".join("0.16" if j == k else "0" for j in range(span + 1))
        svg.append(
            f'<text x="{(X0 + X1) / 2:.0f}" y="{(Y0 + Y1) / 2 + 48:.0f}" text-anchor="middle" '
            f'font-size="150" font-weight="700" fill="#1D1D1F" opacity="0">{y0 + k}'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{ykt}" '
            f'dur="{dur}" repeatCount="indefinite"/></text>')

    # Axes + gridlines.
    svg.append(f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" stroke="#1D1D1F" stroke-width="1"/>')
    svg.append(f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" stroke="#1D1D1F" stroke-width="1"/>')
    for gdp in (300, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000):   # $300 .. $200k
        if not (glo <= gdp <= ghi):
            continue
        x = sx(gdp)
        svg.append(f'<line x1="{x:.1f}" y1="{Y1}" x2="{x:.1f}" y2="{Y0}" stroke="#EFEFF4" stroke-width="1"/>')
        svg.append(f'<text x="{x:.1f}" y="{Y0 + 18:.0f}" text-anchor="middle" font-size="12" fill="#6E6E73">{money(gdp)}</text>')
    for le in range(10, 100, 10):        # 10, 20, ... 90
        if not (llo <= le <= lhi):
            continue
        y = sy(le)
        svg.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="#EFEFF4" stroke-width="1"/>')
        svg.append(f'<text x="{X0 - 8:.0f}" y="{y + 4:.1f}" text-anchor="end" font-size="12" fill="#6E6E73">{le}</text>')
    svg.append(f'<text x="{(X0 + X1) / 2:.0f}" y="{Y0 + 48:.0f}" text-anchor="middle" font-size="13" fill="#1D1D1F">{lab["x_axis"]}</text>')
    svg.append(f'<text x="20" y="{(Y0 + Y1) / 2:.0f}" font-size="13" fill="#1D1D1F" transform="rotate(-90 20 {(Y0 + Y1) / 2:.0f})" text-anchor="middle">{lab["y_axis"]}</text>')

    # Title (linked to Rosling's video) + subtitle + a link to the data we provide.
    svg.append('<text x="20" y="24" font-size="15" font-weight="700" fill="#1D1D1F">'
               '<a href="https://www.youtube.com/watch?v=hVimVzgtD6w" target="_blank">'
               f'<tspan fill="#007AFF" text-decoration="underline">{lab["title_link"]}</tspan></a>'
               f'{lab["title_rest"]}</text>')
    svg.append(f'<text x="20" y="40" font-size="11" fill="#6E6E73">{lab["subtitle"]}</text>')
    csv_name = "tribute-hans-rosling-1950-2025" + (".fr.csv" if fr else ".csv")
    svg.append(
        f'<a href="../../data/{csv_name}" target="_blank">'
        f'<text x="20" y="{H - 8}" text-anchor="start" font-size="10" fill="#007AFF" '
        f'text-decoration="underline">{lab["data_link"]}</text></a>')

    order = sorted(data.items(), key=lambda kv: -max(kv[1]["pop"]))
    y0i, y1i = years[0], years[-1]

    # Dynamic labelling: at each year rank the countries that exist that year by
    # population; the biggest TOP_LABELS carry a following name label that year.
    # The selection changes as the animation plays, so labels track the big cloud.
    label_on = {name: [False] * n for name in data}
    for i in range(n):
        alive = [nm for nm, d in data.items() if d["appear"] <= years[i] <= d["disappear"]]
        alive.sort(key=lambda nm: -data[nm]["pop"][i])
        for nm in alive[:TOP_LABELS]:
            label_on[nm][i] = True

    def exists_op(d: dict) -> str | None:
        """Discrete 1/0 opacity over the grid for a bubble that appears/disappears."""
        if d["appear"] <= y0i and d["disappear"] >= y1i:
            return None
        return ";".join("1" if d["appear"] <= years[i] <= d["disappear"] else "0" for i in range(n))

    # Bubbles as groups, biggest-first so small ones stay on top and hoverable.
    # One translate animation carries the circle and its hover-only name label; a
    # native <title> gives a tooltip; a dissolving federation / newborn successor
    # fades out or in via a discrete opacity window at exactly the right year.
    for name, d in order:
        col = region_color.get(d["continent"], "#8E8E93")
        pts = ";".join(f"{sx(g):.1f},{sy(le):.1f}" for g, le in zip(d["gdp"], d["life"]))
        rs = ";".join(f"{sr(p):.1f}" for p in d["pop"])
        lys = ";".join(f"{-(sr(p) + 3):.1f}" for p in d["pop"])
        bx, by, br = sx(d["gdp"][0]), sy(d["life"][0]), sr(d["pop"][0])
        wop = exists_op(d)
        g_op = f' opacity="{wop.split(";")[0]}"' if wop is not None else ""
        parts = [
            f'<g class="gm-b" data-c="{tc(name)}" transform="translate({bx:.1f},{by:.1f})"{g_op}>'
            f'<animateTransform attributeName="transform" type="translate" values="{pts}" '
            f'keyTimes="{keytimes}" dur="{dur}" repeatCount="indefinite"/>'
            f'<circle class="rg-{str(d["continent"]).lower()}" r="{br:.1f}" '
            f'fill="{col}" fill-opacity="0.55" stroke="{col}" stroke-width="1.1">'
            f'<title>{tc(name)} ({tr(d["continent"])})</title>'
            f'<animate attributeName="r" values="{rs}" keyTimes="{keytimes}" dur="{dur}" repeatCount="indefinite"/>'
            f'</circle>'
            f'<text class="gm-name" y="{-(br + 3):.1f}" text-anchor="middle" font-size="10" '
            f'font-weight="600" fill="#1D1D1F" stroke="#FFFFFF" stroke-width="2.4" paint-order="stroke">{tc(name)}'
            f'<animate attributeName="y" values="{lys}" keyTimes="{keytimes}" dur="{dur}" repeatCount="indefinite"/>'
            f'</text>',
        ]
        wop = exists_op(d)
        if wop is not None:
            parts.append(
                f'<animate attributeName="opacity" values="{wop}" keyTimes="{keytimes}" '
                f'calcMode="discrete" dur="{dur}" repeatCount="indefinite"/>')
        parts.append('</g>')
        svg.append("".join(parts))

    # Following name labels for the current biggest bubbles. Each entity is emitted
    # once per historical-name era, shown only in the years it is BOTH in that era
    # AND among the biggest — so the name on screen is always period-correct.
    def label(disp: str, lx0: float, ly0: float, lxs: str, lys: str, opacity: str) -> str:
        return (
            f'<text x="{lx0:.1f}" y="{ly0:.1f}" opacity="{opacity.split(";")[0]}" text-anchor="middle" font-size="10" '
            f'font-weight="600" fill="#1D1D1F" stroke="#FFFFFF" stroke-width="2.4" paint-order="stroke" '
            f'style="pointer-events:none">{disp}'
            f'<animate attributeName="x" values="{lxs}" keyTimes="{keytimes}" dur="{dur}" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{lys}" keyTimes="{keytimes}" dur="{dur}" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="{opacity}" keyTimes="{keytimes}" '
            f'calcMode="discrete" dur="{dur}" repeatCount="indefinite"/></text>')

    for name, d in order:
        lxs = ";".join(f"{sx(g):.1f}" for g in d["gdp"])
        lys = ";".join(f"{sy(le) - sr(p) - 3:.1f}" for le, p in zip(d["life"], d["pop"]))
        lx0, ly0 = sx(d["gdp"][0]), sy(d["life"][0]) - sr(d["pop"][0]) - 3
        for start, end, disp in NAME_HISTORY.get(name, [(y0i, y1i, name)]):
            op = ";".join("1" if (label_on[name][i] and start <= years[i] <= end) else "0" for i in range(n))
            if "1" in op:
                shown = th(disp) if name in NAME_HISTORY else tc(disp)
                svg.append(label(shown, lx0, ly0, lxs, lys, op))

    # Region legend, out in the right margin (clear of the plot).
    present = [r for r in region_color if any(d["continent"] == r for d in data.values())]
    lx, ly = X1 + 78, Y1 + 6        # pushed well right, clear of the rich bubbles
    svg.append(f'<text x="{lx - 6}" y="{ly - 12}" font-size="10" font-weight="700" fill="#6E6E73" letter-spacing="0.5">{lab["legend_region"]}</text>')
    for i, region in enumerate(present):
        yy = ly + i * 18
        col = region_color[region]
        svg.append(f'<circle class="rg-{region.lower()}" cx="{lx}" cy="{yy}" r="6" fill="{col}" fill-opacity="0.6" stroke="{col}"/>')
        svg.append(f'<text x="{lx + 14}" y="{yy + 4}" font-size="12" fill="#1D1D1F">{tr(region)}</text>')

    # Population-size legend: nested grey disks on a common baseline (same area
    # scale as the bubbles), with a leader line + value for each reference size.
    refs = [(1_000_000_000, lab["pop_1b"]), (250_000_000, lab["pop_250m"]), (50_000_000, lab["pop_50m"])]
    refs = [(p, txt) for p, txt in refs if p <= pop_max]
    scx = lx + 4
    rmax = sr(refs[0][0])
    base = ly + len(present) * 18 + 30 + 2 * rmax
    svg.append(f'<text x="{lx - 6}" y="{base - 2 * rmax - 14:.0f}" font-size="10" font-weight="700" fill="#6E6E73" letter-spacing="0.5">{lab["legend_population"]}</text>')
    for p, txt in refs:
        r = sr(p)
        cy = base - r
        svg.append(f'<circle cx="{scx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="#AEAEB2" stroke-width="1"/>')
        top = cy - r
        svg.append(f'<line x1="{scx:.1f}" y1="{top:.1f}" x2="{scx + rmax + 10:.1f}" y2="{top:.1f}" stroke="#C7C7CC" stroke-width="0.7"/>')
        svg.append(f'<text x="{scx + rmax + 13:.1f}" y="{top + 3.5:.1f}" font-size="10" fill="#6E6E73">{txt}</text>')

    # Player + fullscreen pan/zoom, embedded so it works over http and file://.
    consts = (f'var X0={X0},X1={X1},Y0={Y0},Y1={Y1},GLO={glo},GHI={ghi},'
              f'LLO={llo},LHI={lhi},RMIN={R_MIN},RMAX={R_MAX},POPMAX={pop_max:.0f},'
              f'Y0i={years[0]},Y1i={years[-1]},DUR={dur_s};')
    svg.append('<script type="text/javascript"><![CDATA[' + consts + PLAYER_JS + ']]></script>')

    # Page-embedded via <object>; default mode 'external' emits no button
    # (the page provides fullscreen). Pass mode='self-contained' for standalone.
    _fc = fullscreen_control(W, H, mode)
    if _fc:
        svg.append(_fc)
    svg.append('</svg>')
    out_path.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"wrote {out_path} — {len(data)} entities, {n} snapshots ({lang})")


def write_fr_csv() -> None:
    """Write the fully-translated French copy of the crunched dataset."""
    src = CSV
    dst = src.with_suffix(".fr.csv")
    rows = list(csv.DictReader(src.open(encoding="utf-8")))
    with dst.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["pays", "annee", "region", "revenuParPersonne", "esperanceDeVie", "population"])
        for r in rows:
            w.writerow([COUNTRIES_FR.get(r["country"], r["country"]), r["year"],
                        REGIONS_FR.get(r["continent"], r["continent"]),
                        r["gdpPercap"], r["lifeExp"], r["pop"]])
    print(f"wrote {dst}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--en-only", action="store_true",
                        help="build only the English SVG (skip the French pair + CSV)")
    parser.add_argument(
        "--accessibility", default="universal",
        choices=["universal", "high-contrast", "monochrome",
                 "deuteranopia", "protanopia", "tritanopia"],
        help="colour-vision level for the region palette (default: universal, "
             "the identity that keeps the shipped SVG byte-identical)")
    args = parser.parse_args()

    main("en", accessibility=args.accessibility)
    if not args.en_only:
        main("fr", accessibility=args.accessibility)
        write_fr_csv()
