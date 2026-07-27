#!/usr/bin/env python3
"""
make_gapminder_variants — two more animated Gapminder bubble charts (Rosling homage).

Reuses the first tribute's engine (``make_gapminder.py``) on the **same entity
set** (same countries, same population sizes, same region colours, same
period-correct historical names) but on two other pairs of variables, so the
three charts read as one family:

Variant A — **Fertility vs life expectancy**
    x = fertility (births per woman), LINEAR, domain [1, 8]; countries start on
    the right (large families) and sweep left as fertility falls.
    y = life expectancy (years), LINEAR, domain [8, 92] — the same y as the
    first tribute. As families shrink, lives lengthen.

Variant B — **Child survival vs income**
    x = child survival (% of children reaching age 5), on a *spread* scale
    ``u = -log10(100 - s)`` so 90 %, 99 %, 99.9 % are equally spaced — a plain
    50..100 linear axis would crush every country against 100 by the end and
    hide the whole story. y = GDP per capita, LOG, domain [$300, $200k] —
    the very scale (and money formatter) the first tribute uses on its x, now
    vertical. Survival and income rise together.

Both figures carry **all** the first tribute's features: the embedded player
(play / pause / scrub / step / speed / restart / follow-country via
``postMessage``), dynamic top-10 population labels, period-correct names,
hover ``<title>`` tooltips, appear/disappear windows for federations and
divided nations, a region legend, a nested population-size legend, fullscreen
pan/zoom, and a full English + French pair each.

Nothing in ``make_gapminder.py`` or the original ``gapminder-animated.svg`` is
touched: the shared pieces (``REGION_COLOR``, ``NAME_HISTORY``, the i18n tables)
are **imported**, and the parts that differ per variant — the axis scales, the
grid, and the player's inverse functions ``invX`` / ``invY`` — are generalised
here so the follow-country readout reports the right quantity for each scale
(linear, log, and the ``-log10(100 - s)`` spread).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import csv
import math
import sys
from _interactive import fullscreen_control  # noqa: E402
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from gapminder_i18n import COUNTRIES_FR, HISTORY_FR, REGIONS_FR
from _style import forced_color_patterns, leveled_colors, os_adaptive_style, os_dark_style

# Import the pieces that are identical across the whole tribute family, so the
# three charts stay in lockstep and the originals stay the single source.
from make_gapminder import NAME_HISTORY, REGION_COLOR

# ------------------------------------------------------------------
# Layout — kept identical to the first tribute so the three charts stack
# together as one series (same margins, same plot box, same bubble sizes).
# ------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "assets" / "data"
SVG_DIR = HERE.parent / "assets" / "svg-examples"

W, H = 1020, 520
X0, X1 = 100, 710       # plot x range; the wide right margin holds the legends
Y0, Y1 = 448, 60        # plot y range (y is inverted, i.e. Y0 is the bottom)
R_MIN, R_MAX = 2.6, 46.0
TOP_LABELS = 10
SEC_PER_YEAR = 1        # one year of the sweep lasts one second


# ------------------------------------------------------------------
# Parametrised player. Same behaviour as make_gapminder.PLAYER_JS, but the
# inverse functions read a per-build scale flag so the follow-country readout
# reports the RIGHT quantity for each axis: invX/invY switch between linear,
# log and the -log10(100 - s) "survival spread" transform.
#
# Extra consts prepended per build (beyond the first tribute's):
#   XKIND, YKIND  in {"lin","log","surv"}  — how to invert screen x / y
#   XLO, XHI                                — x data-domain ends (values, not px)
# ------------------------------------------------------------------
PLAYER_JS = r"""(function(){
var S=document.documentElement,B=(S.getAttribute("viewBox")||"0 0 1 1").split(/\s+/).map(Number),V=B.slice();
var t=0,playing=true,speed=1,following=null,last=0,ticks=0;
var reduce=false;try{reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;}catch(e){}
S.pauseAnimations();if(reduce){playing=false;t=DUR-0.01;}S.setCurrentTime(t);
function P(m){try{if(window.parent&&window.parent!==window)window.parent.postMessage(m,"*");}catch(e){}}
function yr(){return Y0i+Math.round(t/DUR*(Y1i-Y0i));}
function setT(n){t=Math.max(0,Math.min(DUR-0.01,n));S.setCurrentTime(t);}
function esc(s){return s.replace(/["\\]/g,"\\$&");}
function fwd(kind,lo,hi){if(kind==="log")return[Math.log10(lo),Math.log10(hi)];if(kind==="surv")return[-Math.log10(100-lo),-Math.log10(100-hi)];return[lo,hi];}
function invX(x){var d=fwd(XKIND,XLO,XHI),u=d[0]+(x-X0)/(X1-X0)*(d[1]-d[0]);if(XKIND==="log")return Math.pow(10,u);if(XKIND==="surv")return 100-Math.pow(10,-u);return u;}
function invY(y){var d=fwd(YKIND,YLO,YHI),u=d[0]+(y-Y0)/(Y1-Y0)*(d[1]-d[0]);if(YKIND==="log")return Math.pow(10,u);if(YKIND==="surv")return 100-Math.pow(10,-u);return u;}
function invR(r){var k=(r-RMIN)/(RMAX-RMIN);return POPMAX*k*k;}
function report(){if(!following){return;}var g=S.querySelector('[data-c="'+esc(following)+'"]');
if(!g){P({gm:"follow",name:following,exists:false});return;}
var op=1;try{op=parseFloat(getComputedStyle(g).opacity);}catch(e){}
var tl=g.transform.animVal,c=g.querySelector("circle");
if(!tl.numberOfItems||!c){P({gm:"follow",name:following,exists:false});return;}
var m=tl.getItem(0).matrix,r=c.r.animVal.value;
P({gm:"follow",name:following,exists:op>0.06,year:yr(),x:invX(m.e),y:invY(m.f),pop:Math.round(invR(r))});}
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


# ------------------------------------------------------------------
# Scale kinds. Each maps a data value to the unit interval [0, 1]; the axis
# code turns that into a pixel and the player inverts it. Three flavours cover
# every variant: linear, log10, and the "survival spread" -log10(100 - s).
# ------------------------------------------------------------------
def _fwd(kind: str, lo: float, hi: float) -> tuple[float, float]:
    """Forward-transform the two domain ends for a scale ``kind``."""
    if kind == "log":
        return math.log10(lo), math.log10(hi)
    if kind == "surv":
        return -math.log10(100 - lo), -math.log10(100 - hi)
    return lo, hi


def _unit(kind: str, lo: float, hi: float, v: float) -> float:
    """Value → [0, 1] along a scale ``kind`` (clamped to the domain)."""
    a, b = _fwd(kind, lo, hi)
    if kind == "log":
        u = math.log10(min(max(v, lo), hi))
    elif kind == "surv":
        u = -math.log10(100 - min(max(v, lo), hi))
    else:
        u = min(max(v, lo), hi)
    return (u - a) / (b - a)


# ------------------------------------------------------------------
# A variant = the two axes (values, scale kind, ticks, label) + copy + files.
# Everything the generator needs to differ from the first tribute lives here.
# ------------------------------------------------------------------
@dataclass
class Variant:
    """One Gapminder-family chart: its data, scales, ticks and bilingual copy."""

    key: str                          # short id, only used in messages
    csv_name: str                     # base CSV file name (no .fr)
    xcol: str                         # x column in the CSV
    ycol: str                         # y column in the CSV
    xkind: str                        # "lin" | "log" | "surv"
    ykind: str                        # "lin" | "log" | "surv"
    xdom: tuple[float, float]         # x data-domain (lo, hi)
    ydom: tuple[float, float]         # y data-domain (lo, hi)
    xticks: list[float]               # x gridline values
    yticks: list[float]               # y gridline values
    out_name: str                     # base output SVG file name (no .fr)
    labels_en: dict[str, str]
    labels_fr: dict[str, str]
    fr_header: list[str]              # header row for the French CSV
    xfmt: Callable[[float], str] = str
    yfmt: Callable[[float], str] = str
    ar_frames: dict[str, int] = field(default_factory=dict)  # Ralph frames (unused here)


def money(v: float) -> str:
    """Compact dollar label, e.g. $300, $2k, $200k — the first tribute's format."""
    return f"${v / 1000:.0f}k" if v >= 1000 else f"${v:.0f}"


def surv_tick(v: float) -> str:
    """Percent label for the survival axis: 99.9 stays 99.9, 90 stays 90."""
    return f"{v:g}%"


def baby_tick(v: float) -> str:
    """Whole-number births-per-woman tick label."""
    return f"{v:g}"


def year_tick(v: float) -> str:
    """Whole-number life-expectancy tick label."""
    return f"{v:g}"


# ------------------------------------------------------------------
# The two variants. FR copy is idiomatic (no em-dash asides, no "not X but Y").
# ------------------------------------------------------------------
FERTILITY = Variant(
    key="fertility",
    csv_name="tribute-fertility-life-1950-2025.csv",
    xcol="fertility", ycol="lifeExp",
    xkind="lin", ykind="lin",
    xdom=(0.0, 9.0), ydom=(8.0, 92.0),
    xticks=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    yticks=[10, 20, 30, 40, 50, 60, 70, 80, 90],
    out_name="gapminder-fertility.svg",
    xfmt=baby_tick, yfmt=year_tick,
    fr_header=["pays", "annee", "region", "fecondite", "esperanceDeVie", "population"],
    labels_en={
        "title_link": "Tribute to Hans Rosling",
        "title_rest": " &#8212; 1950&#8211;2025",
        "subtitle": "Each bubble is a country with size for population and color for region",
        "x_axis": "&#8592; Fertility rate (births per woman)",
        "y_axis": "Life expectancy (years) &#8594;",
        "legend_region": "REGION", "legend_population": "POPULATION",
        "data_link": "Fertility and life-expectancy data",
        "title_a11y": "Fertility rate and life expectancy",
        "pop_1b": "1 billion", "pop_250m": "250 million", "pop_50m": "50 million",
        "desc": (
            "An animated bubble chart in homage to Hans Rosling, one frame per year from 1950 to "
            "2025. Each bubble is a country: horizontal is the fertility rate (births per woman, "
            "falling from right to left), vertical is life expectancy, area is population, colour is "
            "world region. As the years tick by the whole cloud sweeps up and to the left: families "
            "get smaller and lives get longer, together. In 1950 most countries sit on the right "
            "with five to seven children per woman and short lives; by 2025 nearly all have moved "
            "left below three children and up past seventy years. Africa (blue) still holds the "
            "high-fertility right edge but is closing the gap. Historical federations (USSR, "
            "Yugoslavia, Czechoslovakia) show as one bubble until they dissolve; divided nations "
            "(East and West Germany, North and South Vietnam and Yemen) show as two until they "
            "merge. Recent years are part-projected."),
    },
    labels_fr={
        "title_link": "Hommage à Hans Rosling",
        "title_rest": " &#8212; 1950&#8211;2025",
        "subtitle": "Chaque bulle représente un pays. Sa taille indique la population et sa couleur la région.",
        "x_axis": "&#8592; Indice de fécondité (naissances par femme)",
        "y_axis": "Espérance de vie (années) &#8594;",
        "legend_region": "RÉGION", "legend_population": "POPULATION",
        "data_link": "Données de fécondité et d'espérance de vie",
        "title_a11y": "Indice de fécondité et espérance de vie",
        "pop_1b": "1 milliard", "pop_250m": "250 millions", "pop_50m": "50 millions",
        "desc": (
            "Graphique à bulles animé en hommage à Hans Rosling, une image par année de 1950 à 2025. "
            "Chaque bulle est un pays : l'horizontale est l'indice de fécondité (naissances par femme, "
            "qui décroît de droite à gauche), la verticale l'espérance de vie, l'aire la population, "
            "la couleur la région du monde. Au fil des années tout le nuage glisse vers le haut et la "
            "gauche : les familles deviennent plus petites et les vies plus longues, ensemble. En "
            "1950 la plupart des pays comptent cinq à sept naissances par femme et des vies courtes ; en "
            "2025 presque tous sont passés sous trois enfants et au-delà de soixante-dix ans. "
            "L'Afrique (bleu) occupe encore le bord droit à forte fécondité mais rattrape son retard. "
            "Les fédérations (URSS, Yougoslavie, Tchécoslovaquie) apparaissent comme une seule bulle "
            "jusqu'à leur dissolution ; les nations divisées (Allemagne de l'Est et de l'Ouest, "
            "Vietnam et Yémen du Nord et du Sud) comme deux jusqu'à leur fusion. Les années récentes "
            "sont en partie projetées."),
    },
)

INCOME_SURVIVAL = Variant(
    key="incomesurvival",
    csv_name="tribute-childsurvival-income-1950-2025.csv",   # shares CHILDSURVIVAL's data
    xcol="gdpPercap", ycol="childSurvival",
    xkind="log", ykind="surv",
    xdom=(300.0, 200000.0), ydom=(50.0, 99.9),
    xticks=[300, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000],
    yticks=[50, 70, 90, 95, 99, 99.9],
    out_name="gapminder-income-survival.svg",
    xfmt=money, yfmt=surv_tick,
    fr_header=["pays", "annee", "region", "survieEnfant", "pibParHabitant", "population"],
    labels_en={
        "title_link": "Tribute to Hans Rosling",
        "title_rest": " &#8212; 1950&#8211;2025",
        "subtitle": "Each bubble is a country with size for population and color for region",
        "x_axis": "GDP per capita ($, log scale) &#8594;",
        "y_axis": "Children surviving to age 5 (% of births) &#8594;",
        "legend_region": "REGION", "legend_population": "POPULATION",
        "data_link": "GDP and child-survival data",
        "title_a11y": "GDP per capita and child survival",
        "pop_1b": "1 billion", "pop_250m": "250 million", "pop_50m": "50 million",
        "desc": (
            "An animated bubble chart in homage to Hans Rosling, one frame per year from 1950 to "
            "2025. Each bubble is a country: horizontal is GDP per capita on a log scale, vertical is "
            "the share of children who reach their fifth birthday, area is population, colour is world "
            "region. The vertical axis uses a spread scale so that 90, 99 and 99.9 percent are evenly "
            "spaced, keeping the last hard-won gains visible instead of piling every country against "
            "the top. As the years tick by the whole cloud sweeps up and to the right: as countries "
            "grow richer, far more of their children live. Historical federations (USSR, Yugoslavia, "
            "Czechoslovakia) show as one bubble until they dissolve; divided nations (East and West "
            "Germany, North and South Vietnam and Yemen) show as two until they merge. Recent years "
            "are part-projected."),
    },
    labels_fr={
        "title_link": "Hommage à Hans Rosling",
        "title_rest": " &#8212; 1950&#8211;2025",
        "subtitle": "Chaque bulle représente un pays. Sa taille indique la population et sa couleur la région.",
        "x_axis": "PIB par habitant ($, échelle log) &#8594;",
        "y_axis": "Enfants atteignant 5 ans (% des naissances) &#8594;",
        "legend_region": "RÉGION", "legend_population": "POPULATION",
        "data_link": "Données de PIB et de survie des enfants",
        "title_a11y": "PIB par habitant et survie des enfants",
        "pop_1b": "1 milliard", "pop_250m": "250 millions", "pop_50m": "50 millions",
        "desc": (
            "Graphique à bulles animé en hommage à Hans Rosling, une image par année de 1950 à 2025. "
            "Chaque bulle est un pays : l'horizontale est le PIB par habitant en échelle logarithmique, "
            "la verticale la part des enfants qui atteignent leur cinquième anniversaire, l'aire la "
            "population, la couleur la région du monde. L'axe vertical utilise une échelle étalée pour "
            "que 90, 99 et 99,9 pour cent soient également espacés, gardant visibles les derniers "
            "progrès, les plus difficiles. Au fil des années tout le nuage glisse vers le haut et la "
            "droite : à mesure que les pays s'enrichissent, bien plus de leurs enfants survivent. Les "
            "fédérations (URSS, Yougoslavie, Tchécoslovaquie) apparaissent comme une seule bulle "
            "jusqu'à leur dissolution ; les nations divisées (Allemagne de l'Est et de l'Ouest, "
            "Vietnam et Yémen du Nord et du Sud) comme deux jusqu'à leur fusion. Les années récentes "
            "sont en partie projetées."),
    },
)

VARIANTS = {
    "fertility": FERTILITY,
    "incomesurvival": INCOME_SURVIVAL,
}


def load(var: Variant) -> tuple[list[int], dict[str, dict]]:
    """Return (years grid, {country: {continent, x[], y[], pop[], appear, disappear}}).

    Same ragged-dataset handling as the first tribute: every entity is placed on
    the whole annual grid (its value edge-held for the years it did not exist,
    when it is invisible anyway) plus an appear/disappear window, so its bubble
    fades in and out at exactly the right year.
    """
    path = DATA / var.csv_name
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    years = sorted({int(r["year"]) for r in rows})
    by: dict[str, dict] = {}
    for r in rows:
        c = by.setdefault(
            r["country"], {"continent": r["continent"], "x": {}, "y": {}, "pop": {}})
        y = int(r["year"])
        c["x"][y] = float(r[var.xcol])
        c["y"][y] = float(r[var.ycol])
        c["pop"][y] = float(r["pop"])
    out: dict[str, dict] = {}
    for name, c in by.items():
        present = sorted(c["x"])
        lo, hi = present[0], present[-1]

        def edge(s: dict[int, float], lo: int = lo, hi: int = hi) -> list[float]:
            return [s[y] if y in s else s[lo] if y < lo else s[hi] for y in years]

        out[name] = {"continent": c["continent"], "x": edge(c["x"]),
                     "y": edge(c["y"]), "pop": edge(c["pop"]),
                     "appear": lo, "disappear": hi}
    return years, out


def build(var: Variant, lang: str = "en", mode: str = "external",
          accessibility: str = "universal") -> None:
    """Build one variant's animated SVG (``lang`` = 'en' or 'fr') and write it.

    Parameters
    ----------
    var : Variant
        The chart to build (its axes, ticks, copy and file names).
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
    # every bubble and legend swatch of that region (`.rg-<region>`). The
    # ~4-colour Windows High Contrast palette cannot preserve the five-way
    # region encoding, so each region reads as a distinct hatch / dot / cross
    # tile instead. Additive and only referenced inside the forced-colors media
    # query, so the default animated render is unchanged.
    fc_defs, fc_style = forced_color_patterns(
        [f".rg-{r.lower()}" for r in REGION_COLOR], prefix="gmvfc"
    )
    out_path = SVG_DIR / var.out_name
    if fr:
        out_path = out_path.with_suffix(".fr.svg")
    lab = var.labels_fr if fr else var.labels_en

    def tc(name: str) -> str:                       # translate a country label
        return COUNTRIES_FR.get(name, name) if fr else name

    def tr(region: str) -> str:                     # translate a region label
        return REGIONS_FR.get(region, region) if fr else region

    def th(disp: str) -> str:                        # translate a historical-name label
        return HISTORY_FR.get(disp, disp) if fr else disp

    years, data = load(var)
    n = len(years)
    dur_s = (int(years[-1]) - int(years[0])) * SEC_PER_YEAR
    dur = f"{dur_s}s"
    keytimes = ";".join(f"{i / (n - 1):.4f}" for i in range(n))

    pop_max = max(p for d in data.values() for p in d["pop"])
    xlo, xhi = var.xdom
    ylo, yhi = var.ydom

    def sx(v: float) -> float:
        return X0 + _unit(var.xkind, xlo, xhi, v) * (X1 - X0)

    def sy(v: float) -> float:
        return Y0 + _unit(var.ykind, ylo, yhi, v) * (Y1 - Y0)

    def sr(pop: float) -> float:
        return R_MIN + math.sqrt(pop / pop_max) * (R_MAX - R_MIN)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Roboto, system-ui, sans-serif" role="img" aria-labelledby="gm-t gm-d">',
        f'<title id="gm-t">{lab["title_a11y"]}, {years[0]} to {years[-1]}</title>',
        f'<desc id="gm-d">{lab["desc"]}</desc>',
        f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
        # OS-adaptive overrides (additive; the default render is unchanged
        # because every rule below lives inside an @media query, and the class
        # only outranks the inline bubble fill/stroke once the query matches).
        # Under prefers-contrast the five world-region hues deepen to their
        # high-contrast versions on both the bubbles and the legend swatches.
        # Under forced-colors the region is carried by colour alone in this
        # scatter, so the ~4-colour system palette cannot preserve the five-way
        # encoding. Each region instead becomes a distinct Canvas/CanvasText
        # pattern (see ``fc_style`` / ``fc_defs``), keyed on ``.rg-<region>``.
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

    # Big faint year counter — one text per year, fading in only during its window.
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
    for xv in var.xticks:
        if not (xlo <= xv <= xhi):
            continue
        x = sx(xv)
        svg.append(f'<line x1="{x:.1f}" y1="{Y1}" x2="{x:.1f}" y2="{Y0}" stroke="#EFEFF4" stroke-width="1"/>')
        svg.append(f'<text x="{x:.1f}" y="{Y0 + 18:.0f}" text-anchor="middle" font-size="12" fill="#6E6E73">{var.xfmt(xv)}</text>')
    for yv in var.yticks:
        if not (ylo <= yv <= yhi):
            continue
        y = sy(yv)
        svg.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" stroke="#EFEFF4" stroke-width="1"/>')
        svg.append(f'<text x="{X0 - 8:.0f}" y="{y + 4:.1f}" text-anchor="end" font-size="12" fill="#6E6E73">{var.yfmt(yv)}</text>')
    svg.append(f'<text x="{(X0 + X1) / 2:.0f}" y="{Y0 + 48:.0f}" text-anchor="middle" font-size="13" fill="#1D1D1F">{lab["x_axis"]}</text>')
    svg.append(f'<text x="20" y="{(Y0 + Y1) / 2:.0f}" font-size="13" fill="#1D1D1F" transform="rotate(-90 20 {(Y0 + Y1) / 2:.0f})" text-anchor="middle">{lab["y_axis"]}</text>')

    # Title (linked to Rosling's video) + subtitle + a link to the data we provide.
    svg.append('<text x="20" y="24" font-size="15" font-weight="700" fill="#1D1D1F">'
               '<a href="https://www.youtube.com/watch?v=hVimVzgtD6w" target="_blank">'
               f'<tspan fill="#007AFF" text-decoration="underline">{lab["title_link"]}</tspan></a>'
               f'{lab["title_rest"]}</text>')
    svg.append(f'<text x="20" y="40" font-size="11" fill="#6E6E73">{lab["subtitle"]}</text>')
    csv_stem = var.csv_name[:-4]                       # strip ".csv"
    csv_name = csv_stem + (".fr.csv" if fr else ".csv")
    svg.append(
        f'<a href="../../data/{csv_name}" target="_blank">'
        f'<text x="20" y="{H - 8}" text-anchor="start" font-size="10" fill="#007AFF" '
        f'text-decoration="underline">{lab["data_link"]}</text></a>')

    order = sorted(data.items(), key=lambda kv: -max(kv[1]["pop"]))
    y0i, y1i = years[0], years[-1]

    # Dynamic labelling: each year rank the countries that exist by population;
    # the biggest TOP_LABELS carry a following name label that year.
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

    # Bubbles, biggest-first so small ones stay on top and hoverable.
    for name, d in order:
        col = region_color.get(d["continent"], "#8E8E93")
        pts = ";".join(f"{sx(g):.1f},{sy(le):.1f}" for g, le in zip(d["x"], d["y"]))
        rs = ";".join(f"{sr(p):.1f}" for p in d["pop"])
        lys = ";".join(f"{-(sr(p) + 3):.1f}" for p in d["pop"])
        bx, by, br = sx(d["x"][0]), sy(d["y"][0]), sr(d["pop"][0])
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
        if wop is not None:
            parts.append(
                f'<animate attributeName="opacity" values="{wop}" keyTimes="{keytimes}" '
                f'calcMode="discrete" dur="{dur}" repeatCount="indefinite"/>')
        parts.append('</g>')
        svg.append("".join(parts))

    # Following name labels for the current biggest bubbles, period-correct.
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
        lxs = ";".join(f"{sx(g):.1f}" for g in d["x"])
        lys = ";".join(f"{sy(le) - sr(p) - 3:.1f}" for le, p in zip(d["y"], d["pop"]))
        lx0, ly0 = sx(d["x"][0]), sy(d["y"][0]) - sr(d["pop"][0]) - 3
        for start, end, disp in NAME_HISTORY.get(name, [(y0i, y1i, name)]):
            op = ";".join("1" if (label_on[name][i] and start <= years[i] <= end) else "0" for i in range(n))
            if "1" in op:
                shown = th(disp) if name in NAME_HISTORY else tc(disp)
                svg.append(label(shown, lx0, ly0, lxs, lys, op))

    # Region legend, out in the right margin.
    present = [r for r in region_color if any(d["continent"] == r for d in data.values())]
    lx, ly = X1 + 78, Y1 + 6
    svg.append(f'<text x="{lx - 6}" y="{ly - 12}" font-size="10" font-weight="700" fill="#6E6E73" letter-spacing="0.5">{lab["legend_region"]}</text>')
    for i, region in enumerate(present):
        yy = ly + i * 18
        col = region_color[region]
        svg.append(f'<circle class="rg-{region.lower()}" cx="{lx}" cy="{yy}" r="6" fill="{col}" fill-opacity="0.6" stroke="{col}"/>')
        svg.append(f'<text x="{lx + 14}" y="{yy + 4}" font-size="12" fill="#1D1D1F">{tr(region)}</text>')

    # Population-size legend: nested grey disks on a common baseline.
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

    # Player + fullscreen pan/zoom. The scale-kind consts let the player invert
    # a followed bubble back to its real fertility / survival / income / life.
    consts = (
        f'var X0={X0},X1={X1},Y0={Y0},Y1={Y1},'
        f'XLO={xlo:g},XHI={xhi:g},YLO={ylo:g},YHI={yhi:g},'
        f'XKIND="{var.xkind}",YKIND="{var.ykind}",'
        f'RMIN={R_MIN},RMAX={R_MAX},POPMAX={pop_max:.0f},'
        f'Y0i={years[0]},Y1i={years[-1]},DUR={dur_s};')
    svg.append('<script type="text/javascript"><![CDATA[' + consts + PLAYER_JS + ']]></script>')

    _fc = fullscreen_control(W, H, mode)
    if _fc:
        svg.append(_fc)
    svg.append('</svg>')
    out_path.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"wrote {out_path} — {len(data)} entities, {n} snapshots ({lang})")


def write_fr_csv(var: Variant) -> None:
    """Write the fully-translated French copy of a variant's dataset."""
    src = DATA / var.csv_name
    dst = src.with_suffix(".fr.csv")
    rows = list(csv.DictReader(src.open(encoding="utf-8")))
    with dst.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(var.fr_header)
        for r in rows:
            w.writerow([COUNTRIES_FR.get(r["country"], r["country"]), r["year"],
                        REGIONS_FR.get(r["continent"], r["continent"]),
                        r[var.xcol], r[var.ycol], r["pop"]])
    print(f"wrote {dst}")


def main(accessibility: str = "universal") -> None:
    """Build all four SVGs (2 variants × EN/FR) and both French CSVs.

    Parameters
    ----------
    accessibility : str, optional
        Colour-vision level threaded to :func:`build` for the region palette.
        ``'universal'`` (the default) keeps the shipped SVGs byte-identical.
    """
    en_only = "--en-only" in sys.argv
    fr_written: set[str] = set()
    for var in VARIANTS.values():
        build(var, "en", accessibility=accessibility)
        if not en_only:
            build(var, "fr", accessibility=accessibility)
            # Variants can share a dataset (income×survival reuses survival×income);
            # write each French CSV once so they don't clobber each other.
            if var.csv_name not in fr_written:
                write_fr_csv(var)
                fr_written.add(var.csv_name)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--en-only", action="store_true",
                        help="build only the English SVGs (skip the French pairs + CSVs)")
    parser.add_argument(
        "--accessibility", default="universal",
        choices=["universal", "high-contrast", "monochrome",
                 "deuteranopia", "protanopia", "tritanopia"],
        help="colour-vision level for the region palette (default: universal, "
             "the identity that keeps the shipped SVGs byte-identical)")
    args = parser.parse_args()

    main(accessibility=args.accessibility)
