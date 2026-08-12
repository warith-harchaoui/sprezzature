#!/usr/bin/env python3
"""
panels — les dix panneaux du tableau de bord financial-markets, chacun un SVG autonome.

Chaque fonction renvoie **un SVG inline complet** (interactif, responsive), que
``build.py`` insère directement dans la grille HTML de la page. Le titre de la
carte est en HTML ; le SVG porte le graphique, ses axes, sa légende et ses zones
de survol.

Interactivité « pro » : chaque marque interactive porte la classe ``hit`` et un
attribut ``data-tip`` (lignes séparées par ``|``, la première en gras). Un petit
script de page (``dashboard.js``) affiche une **info-bulle riche** qui suit le
curseur avec des informations **utiles à un financier** (écart à la référence en
points, poids par ligne, volatilité annualisée, coût de rotation en points de
base, drawdown…). Aucune animation.

Consignes respectées (tout en français) : palette de finance de marché,
**doubles axes** colorés (frais en points de base / cumulés en %, rotation /
moyenne mobile zoomée), axe temporel à **l'année seule**, jamais de noir pur.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import math
from typing import Callable, List, Tuple

import numpy as np

import market_style as S
from market_data import Portfolio, K_MAX

_MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
              "juil.", "août", "sept.", "oct.", "nov.", "déc."]
_MONTHS_FR_LONG = ["janvier", "février", "mars", "avril", "mai", "juin",
                   "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


# --------------------------------------------------------------------------- #
# Plomberie commune                                                           #
# --------------------------------------------------------------------------- #
def _tip(lines: List[str]) -> str:
    """Encode des lignes d'info-bulle dans un attribut ``data-tip`` (séparateur ``|``)."""
    return S.xml_escape("|".join(lines)).replace('"', "&quot;")


def _xmap(box: S.Box, n: int) -> Callable[[float], float]:
    """Return a function mapping sample index ``0..n-1`` to an x pixel in ``box``."""
    return lambda i: box.x + (i / (n - 1)) * box.w


def _ymap(box: S.Box, lo: float, hi: float) -> Callable[[float], float]:
    """Return a function mapping a value in ``[lo, hi]`` to a y pixel (top = ``hi``)."""
    span = (hi - lo) or 1.0
    return lambda v: box.bottom - (v - lo) / span * box.h


def _grid(box: S.Box, lo: float, hi: float, ticks: List[float]) -> str:
    """Return SVG horizontal gridlines for ``ticks`` inside ``box``."""
    y = _ymap(box, lo, hi)
    return "".join(
        f'<line x1="{S.f1(box.x)}" y1="{S.f1(y(t))}" x2="{S.f1(box.right)}" '
        f'y2="{S.f1(y(t))}" stroke="{S.GRID}" stroke-width="1.2"/>' for t in ticks)


def _vgrid(box: S.Box, g: Portfolio) -> str:
    """Grille verticale : filet plein à chaque année, filet léger aux trimestres.

    Doublé de l'axe des dates : les repères se lisent aussi sans souris (souhait
    de la relecture), et le survol reste là pour la valeur exacte.
    """
    majors, minors = S.year_ticks(g.days)
    out = []
    for frac in minors:
        gx = box.x + frac * box.w
        out.append(f'<line x1="{S.f1(gx)}" y1="{S.f1(box.y)}" x2="{S.f1(gx)}" '
                   f'y2="{S.f1(box.bottom)}" stroke="{S.GRID}" stroke-width="1" stroke-opacity=".6"/>')
    for frac, _ in majors:
        gx = box.x + frac * box.w
        out.append(f'<line x1="{S.f1(gx)}" y1="{S.f1(box.y)}" x2="{S.f1(gx)}" '
                   f'y2="{S.f1(box.bottom)}" stroke="{S.GRID}" stroke-width="1.4"/>')
    return "".join(out)


def _vlegend(lgx: float, cy: float, entries: List[tuple]) -> str:
    """Légende VERTICALE dans la gouttière de droite (hors de l'aire tracée).

    Un cartouche, une pastille de trait par série, son nom et une sous-ligne
    optionnelle (valeur, unité). ``entries`` : ``(nom, couleur, tirets, sous)``.
    La largeur s'ajuste au plus long libellé. Aucun texte n'est posé sur le
    graphique : on lit les couleurs ici, à droite.
    """
    has_sub = any(e[3] for e in entries)
    rh = 46.0 if has_sub else 34.0
    labels = [e[0] for e in entries] + [e[3] for e in entries if e[3]]
    bw = 60.0 + max(len(s) for s in labels) * 8.0
    sx, tx = lgx + 14, lgx + 52
    n = len(entries)
    top = cy - (n - 1) * rh / 2
    out = [f'<rect x="{S.f1(lgx)}" y="{S.f1(top - 25)}" width="{S.f1(bw)}" '
           f'height="{S.f1((n - 1) * rh + 50)}" rx="12" fill="{S.PANEL_BG}" '
           f'stroke="{S.GRID}" stroke-width="1.2"/>']
    for i, entry in enumerate(entries):
        name, colour, dash, sub = entry[0], entry[1], entry[2], entry[3]
        shape = entry[4] if len(entry) > 4 else "line"
        ry = top + i * rh
        if shape == "dot":                        # pastille = marqueur (cercle), pas un trait
            out.append(f'<circle cx="{S.f1(sx + 14)}" cy="{S.f1(ry)}" r="6.5" '
                       f'fill="{S.PANEL_BG}" stroke="{colour}" stroke-width="3.4"/>')
        else:
            da = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<line x1="{S.f1(sx)}" y1="{S.f1(ry)}" x2="{S.f1(sx + 28)}" y2="{S.f1(ry)}" '
                       f'stroke="{colour}" stroke-width="3.8"{da} stroke-linecap="round"/>')
        out.append(f'<text x="{S.f1(tx)}" y="{S.f1(ry + 5)}" font-size="15.5" '
                   f'font-weight="700" fill="{colour}">{S.xml_escape(name)}</text>')
        if sub:
            out.append(f'<text x="{S.f1(tx)}" y="{S.f1(ry + 22)}" font-size="13.6" '
                       f'font-family="{S.MONO}" fill="{S.SECONDARY}">{S.xml_escape(sub)}</text>')
    return "".join(out)


def _yaxis(box: S.Box, lo: float, hi: float, ticks: List[float],
           fmt: Callable[[float], str], *, side: str = "left",
           colour: str = S.SECONDARY, title: str = "") -> str:
    """Étiquettes d'un axe de valeurs (gauche/droite) dans ``colour`` ; titre en coin."""
    y = _ymap(box, lo, hi)
    out = []
    lx = box.x - 10 if side == "left" else box.right + 10
    anchor = "end" if side == "left" else "start"
    for t in ticks:
        out.append(
            f'<text x="{S.f1(lx)}" y="{S.f1(y(t) + 4)}" text-anchor="{anchor}" '
            f'font-size="15" font-family="{S.MONO}" fill="{colour}">{fmt(t)}</text>')
    if title:
        tx, anc = (box.x, "start") if side == "left" else (box.right, "end")
        out.append(
            f'<text x="{S.f1(tx)}" y="{S.f1(box.y - 8)}" text-anchor="{anc}" '
            f'font-size="15" font-weight="700" fill="{colour}">{S.xml_escape(title)}</text>')
    return "".join(out)


def _date_axis(box: S.Box, g: Portfolio) -> str:
    """Axe des dates : ligne de base, graduations trimestrielles muettes, année seule."""
    majors, minors = S.year_ticks(g.days)
    out = [f'<line x1="{S.f1(box.x)}" y1="{S.f1(box.bottom)}" x2="{S.f1(box.right)}" '
           f'y2="{S.f1(box.bottom)}" stroke="{S.AXIS}" stroke-width="1.4"/>']
    for frac in minors:
        gx = box.x + frac * box.w
        out.append(f'<line x1="{S.f1(gx)}" y1="{S.f1(box.bottom)}" x2="{S.f1(gx)}" '
                   f'y2="{S.f1(box.bottom + 4)}" stroke="{S.MUTED}" stroke-width="1.1"/>')
    for frac, label in majors:
        gx = box.x + frac * box.w
        out.append(f'<line x1="{S.f1(gx)}" y1="{S.f1(box.bottom)}" x2="{S.f1(gx)}" '
                   f'y2="{S.f1(box.bottom + 8)}" stroke="{S.SECONDARY}" stroke-width="1.4"/>')
        out.append(f'<text x="{S.f1(gx)}" y="{S.f1(box.bottom + 25)}" text-anchor="middle" '
                   f'font-size="15.6" font-weight="700" font-family="{S.MONO}" fill="{S.SECONDARY}">{label}</text>')
    return "".join(out)


def _series_pts(box: S.Box, series: np.ndarray, lo: float, hi: float) -> List[Tuple[float, float]]:
    """Return the ``(x, y)`` screen points for ``series`` scaled into ``box``."""
    n = len(series)
    x = _xmap(box, n)
    y = _ymap(box, lo, hi)
    return [(x(i), y(float(series[i]))) for i in range(n)]


def _date_str(g: Portfolio, i: int) -> str:
    """Return the ``"Mon YYYY"`` label for the ``i``-th day of the portfolio."""
    d = g.days[i]
    return f"{S.month(d.month - 1)} {d.year}"


def _hit_columns(box: S.Box, g: Portfolio, tipfn: Callable[[int], List[str]], stride: int = 4) -> str:
    """Colonnes transparentes de survol : chacune porte un ``data-tip`` riche.

    ``stride=4`` (≈ une colonne par semaine de bourse) plutôt que 16 (≈ une
    par mois) : beaucoup plus de points de survol pour une lecture fine,
    tout en restant largement sous ce qu'un navigateur peine à gérer (~170
    rects transparents pour deux ans de données quotidiennes).
    """
    n = len(g.days)
    x = _xmap(box, n)
    cw = box.w / (n / stride)
    out = []
    for i in range(0, n, stride):
        gx = x(i)
        out.append(
            f'<rect class="hit" x="{S.f1(gx - cw / 2)}" y="{S.f1(box.y)}" '
            f'width="{S.f1(cw)}" height="{S.f1(box.h)}" fill="transparent" '
            f'data-tip="{_tip(tipfn(i))}"/>')
    return "".join(out)


# Retour visuel discret au survol des marques (sans animation).
_HL = (".hit{cursor:crosshair}"
       ".dot:hover{r:7}.bar:hover{fill-opacity:1}.cell:hover{stroke:#28313A;stroke-width:2}"
       ".ridge:hover{fill-opacity:.42}")


# --------------------------------------------------------------------------- #
# 1 — Richesse nette comparée (courbes)                                        #
# --------------------------------------------------------------------------- #
def equity(g: Portfolio) -> str:
    """Notre stratégie (Kₜ auto) contre l'achat-conservation et trois variantes à K fixe."""
    W, H = 1300, 540
    ml, mr, mt, mb = 66, 232, 40, 56
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    curves = [
        ("Nous", g.wealth_net, S.BLUE, 4.2, ""),
        ("Achat-conservation", g.buyhold, S.BENCH, 2.6, "7 5"),
        ("K = 1", g.fixed_wealth[1], S.KRAMP[0], 2.4, ""),
        ("K = 3", g.fixed_wealth[3], S.KRAMP[1], 2.4, ""),
        ("K = 5", g.fixed_wealth[5], S.KRAMP[2], 2.4, ""),
    ]
    lo = min(float(c[1].min()) for c in curves)
    hi = max(float(c[1].max()) for c in curves)
    nlo, nhi, ticks = S.nice_ticks(lo, hi, 5)
    y = _ymap(box, nlo, nhi)
    out = [S.svg_open(W, H, "Richesse nette comparée, base 100", _HL)]
    out.append(_vgrid(box, g))
    out.append(_grid(box, nlo, nhi, ticks))
    out.append(_yaxis(box, nlo, nhi, ticks, lambda t: f"{t:.0f}", title="indice (base 100)"))
    out.append(f'<line x1="{S.f1(box.x)}" y1="{S.f1(y(100))}" x2="{S.f1(box.right)}" '
               f'y2="{S.f1(y(100))}" stroke="{S.SECONDARY}" stroke-width="1" '
               f'stroke-dasharray="2 4" stroke-opacity=".6"/>')
    finals = []
    for name, series, colour, sw, dash in curves:
        pts = _series_pts(box, series, nlo, nhi)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<path d="{S.smooth_path(pts)}" fill="none" stroke="{colour}" '
                   f'stroke-width="{sw}"{da} stroke-linecap="round" stroke-linejoin="round"/>')
        finals.append((name, colour, dash, f"indice {float(series[-1]):.0f}"))
    out.append(_vlegend(box.right + 22, box.cy, finals))

    def tip(i: int) -> List[str]:
        gv, bv = float(g.wealth_net[i]), float(g.buyhold[i])
        kt = int(g.k_series[i])
        krow = f"Kₜ {kt} titres" if kt > 0 else "hors marché (chauffe)"
        return [_date_str(g, i),
                f"Nous : {gv:.0f}  ({S.fr_pct(gv - 100, 0, True)})",
                f"Achat-conservation : {bv:.0f}  ({S.fr_pct(bv - 100, 0, True)})",
                f"Écart : {gv - bv:+.0f} pts · {krow}"]
    out.append(_hit_columns(box, g, tip))
    out.append(_date_axis(box, g))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 2 — Taille automatique Kₜ (aire en escalier)                                 #
# --------------------------------------------------------------------------- #
def k_step(g: Portfolio) -> str:
    """Le nombre de titres détenus, choisi automatiquement, dans le temps."""
    W, H = 1300, 430
    ml, mr, mt, mb = 60, 24, 30, 54
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    k = g.k_series.astype(float)
    hi = float(min(k.max() + 3, K_MAX))
    nlo, nhi, ticks = S.nice_ticks(0, hi, 5)
    x = _xmap(box, len(k))
    y = _ymap(box, nlo, nhi)
    out = [S.svg_open(W, H, "Taille automatique du portefeuille, nombre de titres Kt", _HL)]
    out.append(_vgrid(box, g))
    out.append(_grid(box, nlo, nhi, ticks))
    out.append(_yaxis(box, nlo, nhi, ticks, lambda t: f"{t:.0f}", title="titres"))
    step = [(x(0), y(k[0]))]
    for i in range(1, len(k)):
        if k[i] != k[i - 1]:
            step.append((x(i), y(k[i - 1])))
            step.append((x(i), y(k[i])))
    step.append((x(len(k) - 1), y(k[-1])))
    area = (f"M{S.f1(box.x)},{S.f1(box.bottom)} "
            + " ".join(f"L{S.f1(px)},{S.f1(py)}" for px, py in step)
            + f" L{S.f1(box.right)},{S.f1(box.bottom)} Z")
    out.append(f'<path d="{area}" fill="{S.PURPLE}" fill-opacity=".12"/>')
    out.append(f'<path d="{S.polyline_path(step)}" fill="none" stroke="{S.PURPLE}" '
               f'stroke-width="2.6" stroke-linejoin="round"/>')
    mean_k = float(k[k > 0].mean())
    my = y(mean_k)
    out.append(f'<line x1="{S.f1(box.x)}" y1="{S.f1(my)}" x2="{S.f1(box.right)}" '
               f'y2="{S.f1(my)}" stroke="{S.AMBER_INK}" stroke-width="1.6" stroke-dasharray="5 5"/>')
    out.append(f'<text x="{S.f1(box.x + 6)}" y="{S.f1(my - 8)}" font-size="15" '
               f'font-weight="700" fill="{S.AMBER_INK}">moyenne {mean_k:.0f} titres</text>')

    def tip(i: int) -> List[str]:
        kt = int(k[i])
        if kt == 0:
            return [_date_str(g, i), "Hors marché (période de chauffe)"]
        return [_date_str(g, i), f"Titres détenus : {kt}",
                f"Poids par ligne : ≈ {S.fr_pct(100 / kt, 0)}"]
    out.append(_hit_columns(box, g, tip))
    for idx in g.rebalance_idx:
        ii = int(idx)
        out.append(f'<circle class="hit dot" cx="{S.f1(x(ii))}" cy="{S.f1(y(k[ii]))}" r="3.6" '
                   f'fill="{S.PANEL_BG}" stroke="{S.PURPLE}" stroke-width="2" '
                   f'data-tip="{_tip([_date_str(g, ii), f"Réallocation : {int(k[ii])} titres"])}"/>')
    out.append(_date_axis(box, g))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 3 — Profils des 100 actions (faisceau + médiane)                            #
# --------------------------------------------------------------------------- #
def profiles(g: Portfolio) -> str:
    """Le faisceau des 100 cours, indexés base 100, sur une échelle logarithmique.

    La relecture trouvait le « log centré-réduit » illisible : on montre plutôt un
    indice base 100 (chaque action part de 100) sur une échelle log, où un même
    écart vertical vaut le même pourcentage — l'unité, l'indice, est lisible.
    """
    W, H = 1300, 540
    ml, mr, mt, mb = 60, 214, 34, 54
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    prices = g.prices
    n, kk = prices.shape
    idx = 100.0 * prices / prices[0]          # chaque action indexée à 100 au départ
    logv = np.log(idx)
    # Bornes robustes qui « respirent » : une action qui s'effondre ne doit pas
    # écraser l'axe, les gagnants (le haut) gardent de l'air au-dessus, et le bas
    # du faisceau ne colle pas au cadre. On borne chaque tracé à la fenêtre.
    lo = float(np.percentile(logv, 1.5)) - 0.10
    hi = float(logv.max()) + 0.16
    x = _xmap(box, n)
    y = _ymap(box, lo, hi)
    yc = lambda v: y(min(max(v, lo), hi))     # noqa: E731
    step_i = max(1, n // 120)
    idxs = list(range(0, n, step_i))
    med = np.median(idx, axis=1)              # indice médian, jour par jour
    WIN = "#E8730C"                            # orange gagnants (lisible sous CVD)
    out = [S.svg_open(W, H, "Profils des 100 actions, indice base 100, échelle log", _HL)]
    out.append(_vgrid(box, g))
    # graduations log lisibles (indice)
    for lvl in (25, 50, 100, 200, 400, 800, 1600):
        lv = math.log(lvl)
        if lo <= lv <= hi:
            out.append(f'<line x1="{S.f1(box.x)}" y1="{S.f1(y(lv))}" x2="{S.f1(box.right)}" '
                       f'y2="{S.f1(y(lv))}" stroke="{S.GRID}" stroke-width="1.2"/>')
            out.append(f'<text x="{S.f1(box.x - 10)}" y="{S.f1(y(lv) + 4)}" text-anchor="end" '
                       f'font-size="14.4" font-family="{S.MONO}" fill="{S.SECONDARY}">{lvl}</text>')
    out.append(f'<text x="{S.f1(box.x)}" y="{S.f1(box.y - 10)}" font-size="15" '
               f'font-weight="700" fill="{S.SECONDARY}">indice (base 100)</text>')
    for a in range(0, kk, 2):
        pts = [(x(i), yc(float(logv[i, a]))) for i in idxs]
        out.append(f'<path d="{S.polyline_path(pts)}" fill="none" stroke="{S.BLUE}" '
                   f'stroke-width="0.9" stroke-opacity=".09"/>')
    winners = list(np.argsort(idx[-1])[-3:])
    for a in winners:
        pts = [(x(i), yc(float(logv[i, a]))) for i in idxs]
        out.append(f'<path d="{S.polyline_path(pts)}" fill="none" stroke="{WIN}" '
                   f'stroke-width="2.4" stroke-opacity=".95" stroke-linecap="round" stroke-linejoin="round"/>')
    pts = [(x(i), yc(math.log(float(med[i])))) for i in idxs]
    out.append(f'<path d="{S.polyline_path(pts)}" fill="none" stroke="{S.DEEPBLUE}" '
               f'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>')
    out.append(_vlegend(box.right + 22, box.cy, [
        ("les 100 actions", S.BLUE, "", ""), ("médiane des 100", S.DEEPBLUE, "", ""),
        ("3 futurs gagnants", WIN, "", "")]))

    def tip(i: int) -> List[str]:
        return [_date_str(g, i), f"Indice médian : {float(med[i]):.0f}",
                f"Fourchette : {float(idx[i].min()):.0f} à {float(idx[i].max()):.0f}"]
    out.append(_hit_columns(box, g, tip))
    out.append(_date_axis(box, g))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 4 — Gains nets journaliers (aire bicolore autour de zéro)                    #
# --------------------------------------------------------------------------- #
def daily_pnl(g: Portfolio) -> str:
    """Le rendement net par séance : vert en hausse, rouge en baisse."""
    W, H = 1300, 430
    ml, mr, mt, mb = 60, 196, 30, 54
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    r = g.net_ret * 100.0
    amp = float(np.percentile(np.abs(r), 99)) * 1.15 or 1.0
    lo, hi = -amp, amp
    x = _xmap(box, len(r))
    y = _ymap(box, lo, hi)
    y0 = y(0.0)
    win = 20
    roll = np.convolve(r, np.ones(win) / win, mode="same")
    out = [S.svg_open(W, H, "Gains nets journaliers, rendement par séance", _HL)]
    out.append(_vgrid(box, g))
    for t in (lo / 2, 0.0, hi / 2):
        out.append(f'<line x1="{S.f1(box.x)}" y1="{S.f1(y(t))}" x2="{S.f1(box.right)}" '
                   f'y2="{S.f1(y(t))}" stroke="{S.GRID}" stroke-width="1.1"/>')
        out.append(f'<text x="{S.f1(box.x - 10)}" y="{S.f1(y(t) + 4)}" text-anchor="end" '
                   f'font-size="14.4" font-family="{S.MONO}" fill="{S.SECONDARY}">{S.fr_pct(t, 1, True)}</text>')
    for i in range(len(r)):
        px, val = x(i), float(r[i])
        col = S.BLUE if val >= 0 else S.RED  # bleu↔rouge : lisible sous daltonisme
        out.append(f'<line x1="{S.f1(px)}" y1="{S.f1(y0)}" x2="{S.f1(px)}" '
                   f'y2="{S.f1(y(val))}" stroke="{col}" stroke-width="1.1" stroke-opacity=".55"/>')
    pts = [(x(i), y(float(roll[i]))) for i in range(win, len(r) - win)]
    out.append(f'<path d="{S.smooth_path(pts)}" fill="none" stroke="{S.DEEPBLUE}" '
               f'stroke-width="2.6" stroke-linecap="round"/>')
    out.append(_vlegend(box.right + 20, box.cy, [
        ("hausse", S.BLUE, "", ""), ("baisse", S.RED, "", ""),
        ("moyenne 20 j", S.DEEPBLUE, "", "")]))

    def tip(i: int) -> List[str]:
        return [_date_str(g, i), f"Gain net : {S.fr_pct(float(r[i]), 2, True)}",
                f"Moyenne 20 j : {S.fr_pct(float(roll[i]), 2, True)}"]
    out.append(_hit_columns(box, g, tip))
    out.append(_date_axis(box, g))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 5 — Frais ponctuels (points de base) et cumulés (%) — DOUBLE AXE            #
# --------------------------------------------------------------------------- #
def fees(g: Portfolio) -> str:
    """Double axe : frais ponctuels par réallocation en points de base, cumulés en %."""
    W, H = 1300, 430
    ml, mr, mt, mb = 62, 250, 38, 54
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    n = len(g.days)
    x = _xmap(box, n)
    # axe gauche : frais ponctuels en points de base (pb = 0,01 %) — l'unité de la finance
    ev = g.fee_event * 1e4
    lo_l, hi_l, ticks_l = S.nice_ticks(0, float(ev.max()) * 1.2 or 1, 4)
    yl = _ymap(box, lo_l, hi_l)
    # axe droit : frais cumulés en % de l'actif
    cum = g.fee_cum * 100.0
    lo_r, hi_r, ticks_r = S.nice_ticks(0, float(cum.max()) * 1.15 or 1, 4)
    yr = _ymap(box, lo_r, hi_r)
    # Deux séries, deux axes : les barres (ponctuel, pb) en AMBRE, la courbe
    # cumulée (%) en BLEU PROFOND. Ambre↔bleu se distingue par la teinte ET par
    # la clarté sous daltonisme (protan/deutan/tritan), là où deux oranges
    # voisins se confondaient. Vérifié avec simulate_cvd.
    BAR, LINE = S.AMBER, S.DEEPBLUE
    out = [S.svg_open(W, H, "Frais ponctuels en points de base et frais cumulés en pourcentage", _HL)]
    out.append(_vgrid(box, g))
    out.append(_grid(box, lo_l, hi_l, ticks_l))
    out.append(_yaxis(box, lo_l, hi_l, ticks_l, lambda t: f"{t:.0f}",
                      side="left", colour=BAR))
    out.append(_yaxis(box, lo_r, hi_r, ticks_r, lambda t: S.fr_pct(t, 1),
                      side="right", colour=LINE))
    bw = max(3.0, box.w / len(g.rebalance_idx) * 0.42)
    for j, (idx, fe) in enumerate(zip(g.rebalance_idx, g.fee_event)):
        gx = x(int(idx))
        pb = fe * 1e4
        h = box.bottom - yl(pb)
        out.append(
            f'<rect class="hit bar" x="{S.f1(gx - bw / 2)}" y="{S.f1(yl(pb))}" '
            f'width="{S.f1(bw)}" height="{S.f1(h)}" rx="2.5" fill="{BAR}" fill-opacity=".92" '
            f'data-tip="{_tip([_date_str(g, int(idx)), f"Frais de réallocation : {pb:.0f} pb", f"Rotation : {S.fr_pct(g.turnover[j] * 100, 0)}"])}"/>')
    pts = [(x(i), yr(float(cum[i]))) for i in range(n)]
    out.append(f'<path d="{S.polyline_path(pts)}" fill="none" stroke="{LINE}" '
               f'stroke-width="2.8" stroke-linejoin="round"/>')
    out.append(_vlegend(box.right + 58, box.cy, [
        ("ponctuels (pb)", BAR, "", ""), ("cumulés (%)", LINE, "", "")]))

    def tip(i: int) -> List[str]:
        return [_date_str(g, i), f"Frais cumulés : {S.fr_pct(float(cum[i]), 2)} de l'actif"]
    out.append(_hit_columns(box, g, tip))
    out.append(_date_axis(box, g))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 6 — Distribution des rendements par année (ridgeline)                        #
# --------------------------------------------------------------------------- #
def ridgeline(g: Portfolio) -> str:
    """Trois densités de rendement net journalier empilées, une par année."""
    W, H = 1300, 500
    ml, mr, mt, mb = 66, 24, 34, 48
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    years = sorted({d.year for d in g.days})
    colours = S.YEAR_RAMP
    r = g.net_ret * 100.0
    lo, hi = -2.6, 2.6
    xr = lambda v: box.x + (v - lo) / (hi - lo) * box.w  # noqa: E731
    out = [S.svg_open(W, H, "Distribution des rendements nets journaliers, par année", _HL)]
    out.append(f'<line x1="{S.f1(xr(0))}" y1="{S.f1(box.y)}" x2="{S.f1(xr(0))}" '
               f'y2="{S.f1(box.bottom)}" stroke="{S.GRID}" stroke-width="1.2"/>')
    nb = 41
    edges = np.linspace(lo, hi, nb)
    centres = 0.5 * (edges[:-1] + edges[1:])
    lane = box.h / len(years)
    amp = lane * 0.86
    for row, yr in enumerate(years):
        mask = np.array([d.year == yr for d in g.days])
        rvals = r[mask]
        hist, _ = np.histogram(rvals, bins=edges, density=True)
        if hist.max() > 0:
            hist = hist / hist.max()
        base = box.y + lane * (row + 0.98)
        pts = [(xr(c), base - amp * float(hh)) for c, hh in zip(centres, hist)]
        ridge = (f"M{S.f1(box.x)},{S.f1(base)} L{S.f1(pts[0][0])},{S.f1(pts[0][1])}"
                 + "".join(f" L{S.f1(px)},{S.f1(py)}" for px, py in pts[1:])
                 + f" L{S.f1(box.right)},{S.f1(base)} Z")
        ann = float(rvals.std()) * math.sqrt(252)
        out.append(
            f'<path class="hit ridge" d="{ridge}" fill="{colours[row % 3]}" fill-opacity=".26" '
            f'data-tip="{_tip([str(yr), f"Rendement moyen : {S.fr_pct(float(rvals.mean()), 2, True)} / jour", f"Volatilité : {S.fr_pct(float(rvals.std()), 2)} / jour (~{S.fr_pct(ann, 0)} annualisée)"])}"/>')
        out.append(f'<path d="{S.smooth_path(pts)}" fill="none" stroke="{colours[row % 3]}" '
                   f'stroke-width="2.2" stroke-linecap="round"/>')
        out.append(f'<text x="{S.f1(box.x - 12)}" y="{S.f1(box.y + lane * (row + 0.5) + 7)}" '
                   f'text-anchor="end" font-size="20" font-weight="700" '
                   f'fill="{colours[row % 3]}">{yr}</text>')
    for t in (-2, -1, 0, 1, 2):
        out.append(f'<text x="{S.f1(xr(t))}" y="{S.f1(box.bottom + 18)}" text-anchor="middle" '
                   f'font-size="14.4" font-family="{S.MONO}" fill="{S.SECONDARY}">{S.fr_pct(t, 0, True)}</text>')
    out.append(f'<text x="{S.f1(box.cx)}" y="{S.f1(box.bottom + 36)}" text-anchor="middle" '
               f'font-size="15" fill="{S.SECONDARY}">rendement net journalier (%)</text>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 7 — Rendements mensuels (carte de chaleur calendaire)                        #
# --------------------------------------------------------------------------- #
def _diverge(v: float, vmax: float) -> str:
    """Return a blue↔red diverging hex for ``v`` in ``[-vmax, vmax]`` (0 = white).

    Blue for negative, red for positive: the colour-vision-deficiency-safe
    diverging pair (never the red↔green traffic-light scheme).
    """
    from _svg import hex_to_rgb
    t = max(-1.0, min(1.0, v / (vmax or 1.0)))
    r0, g0, b0 = 255, 255, 255
    # Divergent BLEU (positif) ↔ ROUGE (négatif) : l'axe bleu-rouge reste
    # discriminable sous daltonisme rouge-vert (protanopie/deutéranopie), là où
    # le rouge-vert habituel s'effondre. Vérifié avec simulate_cvd.
    if t >= 0:
        r1, g1, b1 = hex_to_rgb(S.BLUE)
        k = t ** 0.85
    else:
        r1, g1, b1 = hex_to_rgb(S.RED)
        k = (-t) ** 0.85
    return f"#{round(r0 + (r1 - r0) * k):02X}{round(g0 + (g1 - g0) * k):02X}{round(b0 + (b1 - b0) * k):02X}"


def monthly_heatmap(g: Portfolio) -> str:
    """Grille (année × mois), teintée vert positif / rouge négatif."""
    W, H = 1300, 440
    ml, mt = 26, 24
    box = S.Box(ml, mt, W - 2 * ml, H - mt - 22)
    years = g.monthly["years"]
    grid = g.monthly["grid"]
    months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    finite = grid[np.isfinite(grid)]
    vmax = float(np.percentile(np.abs(finite), 92)) or 1.0
    gap = 6.0
    lab_left, lab_top = 46.0, 24.0
    cw = (box.w - lab_left - gap * 11) / 12
    ch = (box.h - lab_top - gap * (len(years) - 1)) / len(years)
    out = [S.svg_open(W, H, "Rendements mensuels, bleu positif rouge négatif", _HL)]
    for c in range(12):
        cx = box.x + lab_left + c * (cw + gap) + cw / 2
        out.append(f'<text x="{S.f1(cx)}" y="{S.f1(box.y + 14)}" text-anchor="middle" '
                   f'font-size="15" font-family="{S.MONO}" fill="{S.SECONDARY}">{months[c]}</text>')
    for rrow, yr in enumerate(years):
        ry = box.y + lab_top + rrow * (ch + gap)
        out.append(f'<text x="{S.f1(box.x + lab_left - 12)}" y="{S.f1(ry + ch / 2 + 5)}" '
                   f'text-anchor="end" font-size="16.2" font-weight="700" fill="{S.INK}">{yr}</text>')
        for c in range(12):
            v = grid[rrow, c]
            rx = box.x + lab_left + c * (cw + gap)
            if not np.isfinite(v):
                out.append(f'<rect x="{S.f1(rx)}" y="{S.f1(ry)}" width="{S.f1(cw)}" '
                           f'height="{S.f1(ch)}" rx="7" fill="{S.GRID}" fill-opacity=".5"/>')
                continue
            fill = _diverge(float(v), vmax)
            txt = "#FFFFFF" if abs(v) > vmax * 0.55 else S.INK
            out.append(
                f'<rect class="hit cell" x="{S.f1(rx)}" y="{S.f1(ry)}" '
                f'width="{S.f1(cw)}" height="{S.f1(ch)}" rx="7" fill="{fill}" '
                f'data-tip="{_tip([f"{S.month(c, long=True)} {yr}", f"Rendement : {S.fr_pct(float(v), 1, True)}"])}"/>')
            out.append(f'<text x="{S.f1(rx + cw / 2)}" y="{S.f1(ry + ch / 2 + 4.5)}" '
                       f'text-anchor="middle" font-size="15" font-family="{S.MONO}" '
                       f'fill="{txt}" pointer-events="none">{v:+.0f}</text>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 8 — Rotation aux réallocations (DOUBLE AXE, moyenne zoomée)                  #
# --------------------------------------------------------------------------- #
def turnover(g: Portfolio) -> str:
    """Double axe : rotation par réallocation (sucettes) et sa moyenne mobile zoomée."""
    W, H = 1300, 430
    ml, mr, mt, mb = 58, 250, 34, 54
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    turn = g.turnover * 100.0
    m = len(turn)
    xr = lambda j: box.x + (j + 0.5) / m * box.w  # noqa: E731
    lo_l, hi_l, ticks_l = S.nice_ticks(0, float(turn.max()) * 1.15 or 1, 4)
    yl = _ymap(box, lo_l, hi_l)
    # moyenne mobile (5 réallocations) sur un axe droit ZOOMÉ sur sa plage,
    # pour que ses ondulations soient lisibles et distinctes de l'axe gauche.
    ma = np.convolve(turn, np.ones(5) / 5, mode="same")
    lo_r = math.floor(float(ma.min()) / 20) * 20
    hi_r = math.ceil(float(ma.max()) / 20) * 20
    ticks_r = list(range(int(lo_r), int(hi_r) + 1, 20))
    yr = _ymap(box, lo_r, hi_r)
    out = [S.svg_open(W, H, "Rotation aux réallocations et sa moyenne mobile", _HL)]
    out.append(_grid(box, lo_l, hi_l, ticks_l))
    out.append(_yaxis(box, lo_l, hi_l, ticks_l, lambda t: S.fr_pct(t, 0),
                      side="left", colour=S.TEAL_INK))
    out.append(_yaxis(box, lo_r, hi_r, ticks_r, lambda t: S.fr_pct(t, 0),
                      side="right", colour=S.DEEPBLUE))
    for j, t in enumerate(turn):
        px = xr(j)
        out.append(f'<line x1="{S.f1(px)}" y1="{S.f1(box.bottom)}" x2="{S.f1(px)}" '
                   f'y2="{S.f1(yl(float(t)))}" stroke="{S.TEAL_INK}" stroke-width="2" stroke-opacity=".5"/>')
        out.append(
            f'<circle class="hit dot" cx="{S.f1(px)}" cy="{S.f1(yl(float(t)))}" r="5" fill="{S.TEAL_INK}" '
            f'data-tip="{_tip([_date_str(g, int(g.rebalance_idx[j])), f"Rotation : {S.fr_pct(float(t), 0)} du portefeuille", f"Coût : {g.fee_event[j] * 1e4:.0f} pb"])}"/>')
    pts = [(xr(j), yr(float(ma[j]))) for j in range(m)]
    out.append(f'<path d="{S.smooth_path(pts)}" fill="none" stroke="{S.DEEPBLUE}" '
               f'stroke-width="2.6" stroke-linecap="round"/>')
    out.append(_vlegend(box.right + 58, box.cy, [
        ("rotation (%)", S.TEAL_INK, "", ""), ("moyenne (%)", S.DEEPBLUE, "", "")]))
    out.append(f'<line x1="{S.f1(box.x)}" y1="{S.f1(box.bottom)}" x2="{S.f1(box.right)}" '
               f'y2="{S.f1(box.bottom)}" stroke="{S.AXIS}" stroke-width="1.4"/>')
    out.append(f'<text x="{S.f1(box.cx)}" y="{S.f1(box.bottom + 26)}" text-anchor="middle" '
               f'font-size="15" fill="{S.SECONDARY}">{m} réallocations, de la première à la dernière</text>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 9 — Pertes en ligne (drawdown)                                              #
# --------------------------------------------------------------------------- #
def drawdown(g: Portfolio) -> str:
    """La courbe immergée : l'écart sous le plus-haut atteint, en pourcentage."""
    W, H = 1300, 460
    ml, mr, mt, mb = 60, 210, 32, 54
    box = S.Box(ml, mt, W - ml - mr, H - mt - mb)
    dd = g.dd
    lo, hi, ticks = S.nice_ticks(float(dd.min()) * 1.16, 0, 4)
    x = _xmap(box, len(dd))
    y = _ymap(box, lo, hi)
    y0 = y(0.0)
    out = [S.svg_open(W, H, "Pertes en ligne, écart sous le plus-haut", _HL)]
    out.append(_vgrid(box, g))
    out.append(_grid(box, lo, hi, ticks))
    out.append(_yaxis(box, lo, hi, ticks, lambda t: S.fr_pct(t, 0), title="écart (%)"))
    pts = [(x(i), y(float(dd[i]))) for i in range(len(dd))]
    area = (f"M{S.f1(box.x)},{S.f1(y0)} "
            + " ".join(f"L{S.f1(px)},{S.f1(py)}" for px, py in pts)
            + f" L{S.f1(box.right)},{S.f1(y0)} Z")
    out.append(f'<path d="{area}" fill="{S.RED}" fill-opacity=".15"/>')
    out.append(f'<path d="{S.polyline_path(pts)}" fill="none" stroke="{S.RED}" '
               f'stroke-width="2.2" stroke-linejoin="round"/>')
    it = int(np.argmin(dd))
    out.append(f'<circle class="hit dot" cx="{S.f1(x(it))}" cy="{S.f1(y(float(dd[it])))}" r="6.5" '
               f'fill="{S.PANEL_BG}" stroke="{S.RED_INK}" stroke-width="3.4" '
               f'data-tip="{_tip([_date_str(g, it), f"Pire perte : {S.fr_pct(float(dd[it]), 0)}"])}"/>')
    # Plus d'étiquette posée sur la courbe : la légende à droite nomme la série et
    # donne la pire perte. Le creux reste marqué par la pastille.
    out.append(_vlegend(box.right + 20, box.cy, [
        ("pertes en ligne", S.RED, "", ""),
        ("pire perte", S.RED_INK, "", S.fr_pct(float(dd[it]), 0), "dot")]))
    out.append(_hit_columns(box, g, lambda i: [_date_str(g, i), f"Drawdown : {S.fr_pct(float(dd[i]), 1)}"]))
    out.append(_date_axis(box, g))
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# 10 — Performance ajustée du risque (jauge de Sharpe + bullet)                #
# --------------------------------------------------------------------------- #
def risk(g: Portfolio, stats: dict) -> str:
    """Panneau large : jauge du ratio de Sharpe à gauche, bullet du rendement à droite."""
    W, H = 1300, 300
    out = [S.svg_open(W, H, "Performance ajustée du risque, ratio de Sharpe et rendement total", _HL)]
    gcx, gcy = 250.0, 176.0
    gr = 112.0
    smax = 3.0
    sharpe = stats["sharpe"]

    def gpt(val: float, radius: float) -> Tuple[float, float]:
        """Map a gauge value to an ``(x, y)`` point on the arc of given radius.

        The gauge sweeps 180° from left (``val == 0``) to right (``val ==
        smax``), so a value fraction becomes an angle and the point is placed
        on the semicircle of ``radius`` around the gauge centre.

        Parameters
        ----------
        val : float
            Gauge value in ``[0, smax]``.
        radius : float
            Distance from the gauge centre at which to place the point.

        Returns
        -------
        tuple of float
            The ``(x, y)`` screen coordinates on the gauge arc.
        """
        th = math.radians(180.0 * (1.0 - val / smax))
        return gcx + radius * math.cos(th), gcy - radius * math.sin(th)

    # Zones de la jauge : rouge (faible) → ambre (moyen) → bleu (fort). On évite
    # le rouge→vert du feu tricolore, illisible sous daltonisme ; rouge↔bleu tient.
    # Chaque zone porte son propre survol (ce que ce niveau de Sharpe signifie),
    # pas seulement la jauge entière : trois bulles au lieu d'une.
    zone_labels = {
        (0, 1): ("Zone faible (Sharpe < 1)", "Rendement excédentaire à peine supérieur au risque pris"),
        (1, 2): ("Zone correcte (1 ≤ Sharpe < 2)", "Rendement excédentaire raisonnable pour le risque pris"),
        (2, 3): ("Zone excellente (Sharpe ≥ 2)", "Rendement excédentaire élevé par unité de risque"),
    }
    for a0, a1, col in ((0, 1, S.RED), (1, 2, S.AMBER), (2, 3, S.BLUE)):
        p0, p1 = gpt(a0, gr), gpt(a1, gr)
        head, sub = zone_labels[(a0, a1)]
        out.append(f'<path class="hit" d="M{S.f1(p0[0])},{S.f1(p0[1])} A{S.f1(gr)},{S.f1(gr)} 0 0 1 '
                   f'{S.f1(p1[0])},{S.f1(p1[1])}" fill="none" stroke="{col}" stroke-width="18" '
                   f'stroke-linecap="round" stroke-opacity=".9" data-tip="{_tip([head, sub])}"/>')
    tip = gpt(max(0.0, min(sharpe, smax)), gr - 8)  # aiguille bornée (Sharpe négatif possible)
    out.append(f'<line x1="{S.f1(gcx)}" y1="{S.f1(gcy)}" x2="{S.f1(tip[0])}" y2="{S.f1(tip[1])}" '
               f'stroke="{S.DEEPBLUE}" stroke-width="4" stroke-linecap="round"/>')
    out.append(f'<circle cx="{S.f1(gcx)}" cy="{S.f1(gcy)}" r="7" fill="{S.DEEPBLUE}"/>')
    verdict = "excellent" if sharpe >= 2 else "correct" if sharpe >= 1 else "faible"
    out.append(f'<circle class="hit" cx="{S.f1(gcx)}" cy="{S.f1(gcy - gr / 2)}" r="{S.f1(gr)}" '
               f'fill="transparent" data-tip="{_tip(["Ratio de Sharpe : " + S.fr_num(sharpe, 2), f"Interprétation : {verdict}", "Rendement excédentaire par unité de risque"])}"/>')
    for a in (0.0, 1.5, 3.0):
        lbl = str(int(a)) if a == int(a) else S.fr_num(a, 1)  # locale : « 1,5 » / « 1.5 »
        pt = gpt(a, gr + 18)
        out.append(f'<text x="{S.f1(pt[0])}" y="{S.f1(pt[1] + 4)}" text-anchor="middle" '
                   f'font-size="14.4" font-family="{S.MONO}" fill="{S.MUTED}">{lbl}</text>')
    out.append(f'<text x="{S.f1(gcx)}" y="{S.f1(gcy + 50)}" text-anchor="middle" '
               f'font-size="46" font-weight="700" fill="{S.INK}">{S.fr_num(sharpe, 2)}</text>')
    out.append(f'<text x="{S.f1(gcx)}" y="{S.f1(gcy + 74)}" text-anchor="middle" '
               f'font-size="16.8" font-weight="700" fill="{S.SECONDARY}">Ratio de Sharpe</text>')
    out.append(f'<text x="{S.f1(gcx)}" y="{S.f1(gcy + 94)}" text-anchor="middle" '
               f'font-size="13.8" fill="{S.MUTED}">(Rp − Rf) / σ · taux sans risque supposé nul · annualisé</text>')

    out.append(f'<line x1="510" y1="46" x2="510" y2="{H - 40}" stroke="{S.GRID}" stroke-width="1.4"/>')

    by = 150.0
    bx0, bw, bh = 600.0, 640.0, 26.0
    ret, bench = stats["total_return"], stats["buyhold_return"]
    # Axe SIGNÉ : il doit contenir zéro, la référence et le rendement (qui peut
    # être négatif dans le cas défavorable). La barre part de zéro (bleu vers la
    # droite si gain, rouge vers la gauche si perte).
    lo = min(ret, bench, 0.0)
    hi = max(ret, bench, 0.0)
    pad = (hi - lo) * 0.10 or 0.05
    lo_p, hi_p = lo - pad, hi + pad
    xr = lambda v: bx0 + (v - lo_p) / (hi_p - lo_p) * bw  # noqa: E731
    out.append(f'<text x="{S.f1(bx0)}" y="{S.f1(by - bh / 2 - 16)}" font-size="18" '
               f'font-weight="700" fill="{S.INK}">Rendement net total contre la référence</text>')
    # piste neutre + ligne du zéro
    out.append(f'<rect x="{S.f1(bx0)}" y="{S.f1(by - bh / 2)}" width="{S.f1(bw)}" '
               f'height="{S.f1(bh)}" rx="7" fill="#EEF1F4"/>')
    zx = xr(0.0)
    out.append(f'<line x1="{S.f1(zx)}" y1="{S.f1(by - bh / 2 - 8)}" x2="{S.f1(zx)}" '
               f'y2="{S.f1(by + bh / 2 + 8)}" stroke="{S.MUTED}" stroke-width="1.4"/>')
    # barre de mesure depuis zéro
    xret = xr(ret)
    mcol = S.BLUE if ret >= 0 else S.RED
    out.append(f'<rect class="hit bar" x="{S.f1(min(zx, xret))}" y="{S.f1(by - bh / 2 + 4)}" '
               f'width="{S.f1(abs(xret - zx))}" height="{S.f1(bh - 8)}" rx="6" fill="{mcol}" '
               f'data-tip="{_tip(["Rendement net total : " + S.fr_pct(ret * 100, 0, True), f"Référence (achat-conservation) : {S.fr_pct(bench * 100, 0, True)}", f"Surperformance : {(ret - bench) * 100:+.0f} pts"])}"/>')
    # repère de la référence
    out.append(f'<line x1="{S.f1(xr(bench))}" y1="{S.f1(by - bh / 2 - 8)}" x2="{S.f1(xr(bench))}" '
               f'y2="{S.f1(by + bh / 2 + 8)}" stroke="{S.INK}" stroke-width="3.5"/>')
    va = "start" if ret >= 0 else "end"
    vdx = 10 if ret >= 0 else -10
    vcol = S.DEEPBLUE if ret >= 0 else S.RED_INK
    out.append(f'<text x="{S.f1(xret + vdx)}" y="{S.f1(by + 6)}" text-anchor="{va}" font-size="20" '
               f'font-weight="700" fill="{vcol}">{S.fr_pct(ret * 100, 0, True)}</text>')
    out.append(f'<text x="{S.f1(xr(bench))}" y="{S.f1(by + bh / 2 + 24)}" text-anchor="middle" '
               f'font-size="15" fill="{S.SECONDARY}">achat-conservation {S.fr_pct(bench * 100, 0, True)}</text>')
    out.append("</svg>")
    return "".join(out)
