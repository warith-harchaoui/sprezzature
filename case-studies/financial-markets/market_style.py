#!/usr/bin/env python3
"""
market_style — jetons de style et primitives de mise en page du tableau de bord.

Le tableau de bord financial-markets est la page web elle-même : chaque panneau est un
petit SVG **interactif** (info-bulles au survol) et **responsive**, composé dans
une grille HTML/CSS. Ce module fournit ce que tous les panneaux partagent :

* une **palette de finance de marché** justifiée (voir le README) — le bleu pour
  la stratégie (confiance), le vert/rouge pour les gains/pertes (convention P&L),
  l'ambre pour les frais, le violet pour la variable de contrôle Kₜ, et une
  structure en ardoise froide, **jamais du noir pur** ;
* des **formats français** (virgule décimale, espace insécable avant « % ») ;
* un **axe temporel à l'année seule** (les trimestres ne portent qu'une graduation,
  sans texte « Q1/Q2 ») ;
* les primitives géométriques réutilisées de ``_svg`` (lissage, points polaires).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Tuple

# On réutilise les fondations partagées du dépôt. sprezzature-figures/scripts
# a été extrait en dépôt autonome (SPLIT.md phase M1) ; seul un pointeur reste
# dans le monorepo. On essaie d'abord ce dernier (au cas où il serait un jour
# restauré), puis le dépôt frère ``~/sprezzature-figures``.
_SCRIPTS_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "sprezzature-figures" / "scripts",
    Path.home() / "sprezzature-figures" / "scripts",
]
_SCRIPTS = next((p for p in _SCRIPTS_CANDIDATES if (p / "_svg.py").is_file()), _SCRIPTS_CANDIDATES[-1])
sys.path.insert(0, str(_SCRIPTS))
from _svg import (  # noqa: E402
    catmull_rom_beziers,
    fmt_compact,
    point_on_circle,
    xml_escape,
)

# --------------------------------------------------------------------------- #
# Palette — ancrée dans la littérature de la finance de marché                 #
# --------------------------------------------------------------------------- #
# Chaque teinte est un jeton sprezzature-colors, choisie pour le CONCEPT/PSYCHOLOGIE
# qu'elle porte (et non son étiquette d'émotion), en accord avec la littérature
# des marchés. Cf. sprezzature-colors/references/palette.csv.
# --------------------------------------------------------------------------- #
# Thème 🏫 académique / 🏭 corporate                                            #
# --------------------------------------------------------------------------- #
# Les tokens ci-dessous (BLUE, GREEN, ...) sont les valeurs CORPORATE
# (Apple-system, sprezzature-colors/references/palette.csv). set_theme()
# les réaffecte aux équivalents ACADEMIC (Okabe & Ito, 2002 -- la même
# norme scientifique colorblind-safe que web/'s toggle 🏫/🏭 et
# sprezzature-figures' _style.load_palette(theme=...)). build.py appelle
# set_theme() une fois par thème avant de rendre chaque passe du tableau de
# bord ; panels.py lit toujours S.BLUE etc au moment du rendu (import
# market_style as S, jamais `from market_style import BLUE`), donc la
# réaffectation est visible sans changement dans panels.py. Les rampes
# SÉQUENTIELLES (KRAMP, YEAR_RAMP) restent non thématisées pour l'instant --
# même report assumé que dans sprezzature-figures pour les rampes viridis.
THEME = "corporate"

_CORPORATE = {
    "BLUE": "#007AFF",        # la stratégie (« nous ») — Confiance, Fiabilité, Logique, Sécurité
    # Gain : on DÉVIE volontairement du vert-jeton pur (#28CD41) vers un vert-jade.
    # Motif accessibilité (vérifié avec simulate_cvd) : le rouge↔vert pur s'effondre
    # sous deutéranopie/protanopie (les deux virent au tan). Le jade garde le concept
    # « croissance » (famille verte) mais sa composante bleue le rend séparable du
    # rouge sous daltonisme. Le signe (+/−) et la position doublent toujours la teinte.
    "GREEN": "#0FA98A",       # gain, hausse — vert-jade, séparable du rouge sous CVD
    "GREEN_INK": "#0A7D66",   # jade assombri (traits/points) — contraste ≥ 3:1 sur blanc
    "RED": "#FF3B30",         # pertes, drawdown — Danger, Avertissement (convention P&L)
    "RED_INK": "#C42B22",     # rouge assombri pour texte
    "AMBER": "#FF9500",       # frais, coûts — Attention, Warmth (sans dramatiser)
    "AMBER_INK": "#B26200",   # ambre assombri pour texte / traits fins
    "PURPLE": "#AF52DE",      # Kₜ, contrôle automatique « intelligent » — Sagesse, Sophistication
    "TEAL_INK": "#2A93AD",    # turquoise assombri — rotation (Clarté/Calme), contraste ≥ 3:1
    "YELLOW_INK": "#B8860B",  # jaune assombri, lisible (variante)
    "BENCH": "#808080",       # achat-conservation (référence) — Gris « Neutral / Équilibre »
    "DEEPBLUE": "#0A4DA0",    # lignes héros / médiane / moyenne — bleu profond (jamais du noir)
}

# Équivalents Okabe-Ito. Vermillion/Orange/Bluish-Green/Blue/Reddish-Purple sont
# déjà colorblind-safe par construction (pas besoin du détour "vert-jade" du
# corporate) ; les variantes *_INK sont assombries par le même delta de
# luminosité (HLS) que leur pendant corporate, pour garder un contraste
# comparable sur fond blanc. BLUE/DEEPBLUE reprennent exactement les tokens
# academic du site (web/css/tailwind-input.css) pour rester cohérents avec le
# reste de la page quand le lecteur bascule 🏫.
_ACADEMIC = {
    "BLUE": "#0072B2",        # Okabe-Ito Blue -- identique au brand-blue academic du site
    "GREEN": "#009E73",       # Okabe-Ito bluish green -- safe sans détour "jade"
    "GREEN_INK": "#006D4F",
    "RED": "#D55E00",         # Okabe-Ito vermillion
    "RED_INK": "#774015",
    "AMBER": "#E69F00",       # Okabe-Ito orange
    "AMBER_INK": "#996A00",
    "PURPLE": "#CC79A7",      # Okabe-Ito reddish purple
    "TEAL_INK": "#187EB7",    # Okabe-Ito sky blue, assombri
    "YELLOW_INK": "#766F09",  # Okabe-Ito yellow, assombri
    "BENCH": "#808080",       # neutre, inchangé (Okabe-Ito ne redéfinit pas le gris)
    "DEEPBLUE": "#003C5D",    # identique au brand-navy academic du site
}

BLUE = _CORPORATE["BLUE"]
GREEN = _CORPORATE["GREEN"]
GREEN_INK = _CORPORATE["GREEN_INK"]
RED = _CORPORATE["RED"]
RED_INK = _CORPORATE["RED_INK"]
AMBER = _CORPORATE["AMBER"]
AMBER_INK = _CORPORATE["AMBER_INK"]
PURPLE = _CORPORATE["PURPLE"]
TEAL_INK = _CORPORATE["TEAL_INK"]
YELLOW_INK = _CORPORATE["YELLOW_INK"]
BENCH = _CORPORATE["BENCH"]
DEEPBLUE = _CORPORATE["DEEPBLUE"]


def set_theme(theme: str) -> None:
    """Bascule les tokens de couleur sémantiques vers ``"corporate"`` ou ``"academic"``.

    Réaffecte les globals du module (BLUE, GREEN, ... DEEPBLUE) à partir de
    :data:`_CORPORATE` ou :data:`_ACADEMIC`. ``panels.py`` fait toujours
    ``import market_style as S`` puis lit ``S.BLUE`` au moment du rendu (jamais
    ``from market_style import BLUE``), donc l'effet est visible sans aucun
    changement côté ``panels.py``. À appeler avant chaque passe de rendu, comme
    :func:`set_lang`.
    """
    global THEME, BLUE, GREEN, GREEN_INK, RED, RED_INK, AMBER, AMBER_INK
    global PURPLE, TEAL_INK, YELLOW_INK, BENCH, DEEPBLUE
    THEME = theme
    tokens = _ACADEMIC if theme == "academic" else _CORPORATE
    BLUE = tokens["BLUE"]
    GREEN = tokens["GREEN"]
    GREEN_INK = tokens["GREEN_INK"]
    RED = tokens["RED"]
    RED_INK = tokens["RED_INK"]
    AMBER = tokens["AMBER"]
    AMBER_INK = tokens["AMBER_INK"]
    PURPLE = tokens["PURPLE"]
    TEAL_INK = tokens["TEAL_INK"]
    YELLOW_INK = tokens["YELLOW_INK"]
    BENCH = tokens["BENCH"]
    DEEPBLUE = tokens["DEEPBLUE"]


# Rampe SÉQUENTIELLE pour des séries ORDONNÉES (sprezzature-ui : varier la luminance).
KRAMP = ["#6FBFD0", "#3691AB", "#1C6178"]     # K fixe : K=1 clair → K=5 foncé
YEAR_RAMP = ["#66B0FF", "#007AFF", "#004999"]  # années : 2024 clair → 2026 foncé

# Structure — ardoise froide, jamais du noir pur.
INK = "#28313A"         # texte principal (ardoise foncée)
SECONDARY = "#5B6B78"   # sous-titres, étiquettes d'axe
MUTED = "#94A3AE"       # légendes discrètes
GRID = "#E9EDF1"        # filets de grille
AXIS = "#8494A0"        # ligne d'axe (medium slate, pas d'encre noire)
PANEL_BG = "#FFFFFF"
CANVAS_BG = "#F4F6F8"

FONT = "Roboto, system-ui, sans-serif"
MONO = "Roboto Mono, ui-monospace, monospace"
NBSP = " "

f1 = fmt_compact


@dataclass
class Box:
    """Zone de tracé rectangulaire, en pixels de l'espace SVG."""

    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        """Abscisse du bord droit de la zone (``x + w``)."""
        return self.x + self.w

    @property
    def bottom(self) -> float:
        """Ordonnée du bord bas de la zone (``y + h``)."""
        return self.y + self.h

    @property
    def cx(self) -> float:
        """Abscisse du centre de la zone."""
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        """Ordonnée du centre de la zone."""
        return self.y + self.h / 2.0


# --------------------------------------------------------------------------- #
# Formats français                                                            #
# --------------------------------------------------------------------------- #
# Langue courante ("en" par défaut ; "fr" pour la
# page traduite). build.py bascule via set_lang() avant de rendre chaque page.
LANG = "en"


def set_lang(lang: str) -> None:
    """Fixe la langue courante des formats (``"en"`` ou ``"fr"``)."""
    global LANG
    LANG = lang


def fr_num(v: float, decimals: int = 2) -> str:
    """Nombre localisé : virgule décimale en FR, point en EN (ex. 1,98 / 1.98)."""
    s = f"{v:.{decimals}f}"
    return s.replace(".", ",") if LANG == "fr" else s


def fr_pct(v: float, decimals: int = 0, signed: bool = False) -> str:
    """Pourcentage localisé : « 48 % » (FR, espace) vs « 48% » (EN, collé)."""
    body = f"{abs(v):.{decimals}f}"
    if LANG == "fr":
        body = body.replace(".", ",")
    sign = "-" if v < 0 else ("+" if signed else "")
    sep = NBSP if LANG == "fr" else ""
    return f"{sign}{body}{sep}%"


_MONTHS = {
    "fr": (["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
            "sept.", "oct.", "nov.", "déc."],
           ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
            "août", "septembre", "octobre", "novembre", "décembre"]),
    "en": (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec"],
           ["January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"]),
}


def month(i: int, long: bool = False) -> str:
    """Nom du mois ``i`` (0-11) dans la langue courante ; ``long`` = forme longue."""
    return _MONTHS[LANG][1 if long else 0][i]


# --------------------------------------------------------------------------- #
# Graduations « jolies » (heuristique de Heckbert)                             #
# --------------------------------------------------------------------------- #
def nice_num(x: float, do_round: bool) -> float:
    """Nombre « rond » proche de ``x`` (1, 2, 5 × 10^k)."""
    if x <= 0:
        return 0.0
    exp = math.floor(math.log10(x))
    frac = x / (10 ** exp)
    if do_round:
        nice = 1 if frac < 1.5 else 2 if frac < 3 else 5 if frac < 7 else 10
    else:
        nice = 1 if frac <= 1 else 2 if frac <= 2 else 5 if frac <= 5 else 10
    return nice * (10 ** exp)


def nice_ticks(lo: float, hi: float, n: int = 5) -> Tuple[float, float, List[float]]:
    """Renvoie ``(lo, hi, graduations)`` couvrant ``[lo, hi]`` avec ~``n`` repères."""
    if hi <= lo:
        hi = lo + 1.0
    rng = nice_num(hi - lo, False)
    step = nice_num(rng / max(1, n - 1), True)
    nlo = math.floor(lo / step) * step
    nhi = math.ceil(hi / step) * step
    ticks: List[float] = []
    v = nlo
    while v <= nhi + step * 0.5:
        ticks.append(round(v, 9))
        v += step
    return nlo, nhi, ticks


# --------------------------------------------------------------------------- #
# Axe temporel — l'année seule porte une étiquette                            #
# --------------------------------------------------------------------------- #
def year_ticks(days: List[date]) -> Tuple[List[Tuple[float, str]], List[float]]:
    """Renvoie ``(majeures, mineures)`` pour l'axe des dates.

    Les **majeures** sont ``(fraction, "2024")`` au premier jour de chaque année
    civile présente : elles seules portent un texte. Les **mineures** sont les
    fractions de début de trimestre (avril / juillet / octobre) : de simples
    graduations sans texte, pour rythmer l'axe sans écrire « Q1/Q2/Q3/Q4 ».

    Parameters
    ----------
    days : list of datetime.date
        Le calendrier des séances.

    Returns
    -------
    tuple
        ``([(frac, "2024"), ...], [frac_mineure, ...])``.
    """
    n = len(days)
    majors: List[Tuple[float, str]] = []
    minors: List[float] = []
    seen_year = set()
    seen_q = set()
    for i, d in enumerate(days):
        frac = i / (n - 1)
        if d.month == 1 and d.year not in seen_year:
            seen_year.add(d.year)
            majors.append((frac, str(d.year)))
        elif d.month in (4, 7, 10):
            key = (d.year, d.month)
            if key not in seen_q:
                seen_q.add(key)
                minors.append(frac)
    return majors, minors


# --------------------------------------------------------------------------- #
# Lissage de courbes                                                          #
# --------------------------------------------------------------------------- #
def smooth_path(pts: List[Tuple[float, float]]) -> str:
    """Chemin ``d`` lissé (Catmull-Rom) passant par ``pts``."""
    if not pts:
        return ""
    x0, y0 = pts[0]
    return f"M{f1(x0)},{f1(y0)}" + catmull_rom_beziers(pts, f1)


def polyline_path(pts: List[Tuple[float, float]]) -> str:
    """Chemin ``d`` en segments droits passant par ``pts``."""
    if not pts:
        return ""
    d = f"M{f1(pts[0][0])},{f1(pts[0][1])}"
    return d + "".join(f" L{f1(x)},{f1(y)}" for x, y in pts[1:])


# --------------------------------------------------------------------------- #
# Enveloppe SVG d'un panneau — interactif + responsive                        #
# --------------------------------------------------------------------------- #
def _base_style() -> str:
    """Style commun injecté dans chaque panneau (fonction, pas constante : lit BLUE
    au moment de l'appel pour rester correct après :func:`set_theme`).

    Les cibles interactives portent la classe ``hit`` et révèlent leur
    info-bulle ``.tip`` au survol / focus. Aucune animation — juste un
    révélateur d'information au survol (et un focus clavier).
    """
    return (
        ".tip{opacity:0;pointer-events:none;transition:opacity .12s ease}"
        ".hit:hover~.tip,.hit:focus~.tip{opacity:1}"
        ".hit{outline:none;cursor:crosshair}"
        ".hit:focus-visible{outline:2px solid " + BLUE + ";outline-offset:1px}"
        "@media (prefers-reduced-motion:reduce){.tip{transition:none}}"
    )


def svg_open(w: float, h: float, label: str, style: str = "") -> str:
    """Ouvre un SVG de panneau responsive (viewBox + largeur fluide via CSS).

    Parameters
    ----------
    w, h : float
        Dimensions logiques (l'aspect vient du viewBox ; la taille réelle est
        pilotée par le CSS de la grille).
    label : str
        Texte ``aria-label`` du panneau.
    style : str
        CSS spécifique au panneau, ajouté après :func:`_base_style`.

    Returns
    -------
    str
        La balise ``<svg …>`` ouvrante, le ``<title>`` et le bloc ``<style>``.
    """
    return (
        f'<svg class="panel-svg" role="img" aria-label="{xml_escape(label)}" '
        f'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f1(w)} {f1(h)}" '
        f'preserveAspectRatio="xMidYMid meet" font-family="{FONT}">'
        f"<title>{xml_escape(label)}</title>"
        f"<style>{_base_style()}{style}</style>"
        # Fond blanc : chaque panneau reste une figure claire, y compris quand la
        # page passe en thème sombre (comme les figures du site).
        f'<rect x="0" y="0" width="{f1(w)}" height="{f1(h)}" fill="{PANEL_BG}"/>'
    )


def tip_group(x: float, y: float, lines: List[str], *, anchor: str = "middle", w: float = 0.0) -> str:
    """Construit une info-bulle ``.tip`` (fond blanc arrondi + lignes de texte).

    À placer **après** l'élément ``.hit`` correspondant (frères adjacents) pour
    que le sélecteur ``.hit:hover~.tip`` la révèle.

    Parameters
    ----------
    x, y : float
        Coin/ancre de l'info-bulle.
    lines : list of str
        Lignes de texte (la première en gras).
    anchor : str
        Ancrage horizontal du bloc (``start``/``middle``/``end``).
    w : float
        Largeur imposée ; sinon estimée d'après la ligne la plus longue.

    Returns
    -------
    str
        Le groupe SVG de l'info-bulle.
    """
    pad = 9.0
    lh = 16.0
    fw = w or (max(len(s) for s in lines) * 7.0 + 2 * pad)
    fh = lh * len(lines) + 2 * pad - 4
    if anchor == "middle":
        bx = x - fw / 2
    elif anchor == "end":
        bx = x - fw
    else:
        bx = x
    by = y
    parts = [
        '<g class="tip">',
        f'<rect x="{f1(bx)}" y="{f1(by)}" width="{f1(fw)}" height="{f1(fh)}" rx="9" '
        f'fill="#FFFFFF" stroke="{GRID}" stroke-width="1.2"/>',
    ]
    for i, s in enumerate(lines):
        weight = "700" if i == 0 else "400"
        col = INK if i == 0 else SECONDARY
        parts.append(
            f'<text x="{f1(bx + pad)}" y="{f1(by + pad + 12 + i * lh)}" '
            f'font-size="12.5" font-weight="{weight}" fill="{col}">{xml_escape(s)}</text>'
        )
    parts.append("</g>")
    return "".join(parts)


# On réexpose quelques primitives pour que les panneaux importent d'un seul point.
__all__ = [
    "BLUE", "GREEN", "GREEN_INK", "RED", "RED_INK", "AMBER", "AMBER_INK",
    "PURPLE", "TEAL_INK", "YELLOW_INK", "BENCH", "DEEPBLUE", "KRAMP", "YEAR_RAMP", "INK",
    "SECONDARY", "MUTED", "GRID", "AXIS", "PANEL_BG", "CANVAS_BG", "FONT",
    "MONO", "NBSP", "f1", "Box", "THEME", "set_theme", "fr_num", "fr_pct", "nice_ticks", "year_ticks",
    "smooth_path", "polyline_path", "svg_open", "tip_group",
    "point_on_circle", "xml_escape",
]
