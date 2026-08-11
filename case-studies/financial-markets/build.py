#!/usr/bin/env python3
"""
build — génère le tableau de bord financial-markets, intégré au site ``web/``.

Chaque panneau est rendu en SVG dans la langue courante (les nombres, les
pourcentages et les dates sont déjà localisés par ``market_style``). Les
**libellés statiques** français des SVG sont ensuite traduits en anglais
idiomatique de la finance par un dictionnaire — jamais du mot-à-mot « llmesque ».
Le gabarit reprend le **chrome du site** (Tailwind, en-tête, pied, thème) : on
écrit les pages sous ``web/`` (anglais) et ``web/fr/`` (français), deux tirages
(favorable / défavorable) au menu déroulant, avec sélecteur de langue 🇬🇧/🇫🇷.

Usage
-----
    python build.py

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import market_data as D
import market_style as S
import panels as P

_HERE = Path(__file__).resolve().parent
_OUT = _HERE / "panels"

# Traductions FR -> EN (anglais idiomatique de la finance). Appliquées de la
# plus longue à la plus courte pour éviter qu'un fragment court n'abîme une
# phrase plus longue (« Rendements mensuels » avant « Rendement »).
_TR: List[Tuple[str, str]] = [
    # étiquettes aria des panneaux
    ("Richesse nette comparée, base 100", "Net wealth compared, base 100"),
    ("Taille automatique du portefeuille, nombre de titres Kt", "Automatic portfolio size, number of holdings Kt"),
    ("Profils des 100 actions, indice base 100, échelle log", "The 100 stocks, indexed to 100, log scale"),
    ("Gains nets journaliers, rendement par séance", "Daily net P&L, return per session"),
    ("Frais ponctuels en points de base et frais cumulés en pourcentage", "Per-rebalance cost in basis points and cumulative cost in percent"),
    ("Distribution des rendements nets journaliers, par année", "Distribution of daily net returns, by year"),
    ("Rendements mensuels, bleu positif rouge négatif", "Monthly returns, blue positive red negative"),
    ("Rotation aux réallocations et sa moyenne mobile", "Turnover at rebalances and its moving average"),
    ("Pertes en ligne, écart sous le plus-haut", "Drawdown, distance below the running peak"),
    ("Performance ajustée du risque, ratio de Sharpe et rendement total", "Risk-adjusted performance, Sharpe ratio and total return"),
    # méta + hero + disclaimer (HTML)
    ("Tableau de bord d'un portefeuille systématique à taille automatique Kₜ, tout en SVG interactif, aux couleurs de la finance de marché.",
     "Dashboard of a systematic portfolio with automatic size Kₜ, all in interactive SVG, in market-finance colours."),
    ("tableau de bord d'un portefeuille à taille automatique", "dashboard of an automatically-sized portfolio"),
    ("Marchés financiers — tableau de bord", "Financial markets — dashboard"),
    ("Marchés financiers", "Financial markets"),
    ("Étude de cas : les marchés financiers", "Case study: financial markets"),
    ("sprezzature · finance de marché", "sprezzature · financial markets"),
    ("Données illustratives, aucune valeur réelle, aucun conseil d'investissement.", "Illustrative data, no real value, no investment advice."),
    # sous-titres des cartes
    ("Indice base 100 · nous (Kₜ auto), achat-conservation et K fixe", "Base 100 index · us (auto Kₜ), buy & hold and fixed K"),
    ("Nombre de titres détenus dans le temps", "Number of holdings over time"),
    ("Cours indexés base 100 · échelle logarithmique", "Prices indexed to 100 · logarithmic scale"),
    ("Rendement net (%) par séance · bleu en hausse, rouge en baisse", "Net return (%) per session · blue up, red down"),
    ("Double axe · points de base et pourcentage", "Dual axis · basis points and percent"),
    ("Densité du rendement net journalier (%), par année", "Density of daily net return (%), by year"),
    ("Bleu positif, rouge négatif (%)", "Blue positive, red negative (%)"),
    ("Double axe · part du portefeuille échangée (%)", "Dual axis · share of the book traded (%)"),
    ("Écart (%) sous le plus-haut atteint (drawdown)", "Distance (%) below the running peak (drawdown)"),
    ("Ratio de Sharpe et rendement total contre la référence", "Sharpe ratio and total return vs benchmark"),
    # titres des cartes
    ("Taille automatique Kₜ", "Automatic size Kₜ"),
    ("Profils des 100 actions", "The 100 stocks"),
    ("Gains nets journaliers", "Daily net P&L"),
    ("Frais ponctuels et cumulés", "Per-rebalance and cumulative cost"),
    ("Distribution des rendements", "Return distribution"),
    ("Rotation aux réallocations", "Turnover at rebalances"),
    ("Performance ajustée du risque", "Risk-adjusted performance"),
    ("Richesse nette comparée", "Net wealth compared"),
    ("Rendements mensuels", "Monthly returns"),
    ("Pertes en ligne", "Drawdown"),
    # infobulles + libellés dans les SVG
    ("Rendement excédentaire par unité de risque", "Excess return per unit of risk"),
    ("Rendement net total contre la référence", "Total net return vs benchmark"),
    ("(Rp − Rf) / σ · taux sans risque supposé nul · annualisé", "(Rp − Rf) / σ · risk-free rate assumed nil · annualised"),
    ("réallocations, de la première à la dernière", "rebalances, first to last"),
    ("Référence (achat-conservation)", "Benchmark (buy & hold)"),
    ("Hors marché (période de chauffe)", "Out of market (warm-up)"),
    ("hors marché (chauffe)", "out of market (warm-up)"),
    ("indice (base 100)", "index (base 100)"),
    ("rendement net journalier (%)", "daily net return (%)"),
    ("rendement net (%)", "net return (%)"),
    ("écart (%)", "distance (%)"),
    ("les 100 actions", "the 100 stocks"),
    ("pertes en ligne", "drawdown"),
    ("moyenne 20 j", "20-day avg"),
    ("hausse", "up"),
    ("baisse", "down"),
    ("médiane des 100", "median of the 100"),
    ("3 futurs gagnants", "3 eventual winners"),
    ("moyenne sur 20 jours", "20-day average"),
    ("Frais de réallocation", "Rebalance cost"),
    ("Rendement net total", "Total net return"),
    ("Frais cumulés", "Cumulative cost"),
    ("Rendement moyen", "Mean return"),
    ("rendement net journalier", "daily net return"),
    ("Titres détenus", "Holdings"),
    ("Poids par ligne", "Weight per name"),
    ("Indice médian", "Median index"),
    ("Surperformance", "Outperformance"),
    ("Écart", "Spread"),
    ("Réallocation", "Rebalance"),
    ("Interprétation", "Reading"),
    ("Volatilité", "Volatility"),
    ("Fourchette", "Range"),
    ("Moyenne 20 j", "20-day avg"),
    ("Gain net", "Net return"),
    ("Pire perte", "Max drawdown"),
    ("pire perte", "max drawdown"),
    ("Ratio de Sharpe", "Sharpe ratio"),
    ("du portefeuille", "of book"),
    ("de l'actif", "of NAV"),
    ("ponctuels (pb)", "per rebalance (bps)"),
    ("annualisée", "annualised"),
    ("Rotation", "Turnover"),
    ("rotation", "turnover"),
    ("Achat-conservation", "Buy & hold"),
    ("achat-conservation", "buy & hold"),
    ("Coût", "Cost"),
    ("cumulés", "cumulative"),
    # KPI (HTML) — libellés, notes, valeurs, suffixes
    ("vs achat-conservation", "vs buy & hold"),
    ("Séances gagnantes", "Winning sessions"),
    ("référence", "benchmark"),
    ("frais cumulés", "cumulative cost"),
    ("Ratio de Sharpe", "Sharpe ratio"),
    ("Rendement net", "Net return"),
    ("net de frais", "net of fees"),
    ("référence +63 %", "benchmark +63%"),
    ("net, annualisé", "net, annualised"),
    ("sous le plus-haut", "below the peak"),
    ("frais cumulés 1,7 %", "cumulative cost 1.7%"),
    ('data-suffix=" %"', 'data-suffix="%"'),
    ("+119 %", "+119%"),
    ("-18 %", "-18%"),
    ("48 %", "48%"),
    ("1,98", "1.98"),
    # navigation + accessibilité (HTML)
    ("Mettre une étoile sur GitHub", "Star on GitHub"),
    ("Aller au contenu", "Skip to content"),
    ("Changer de thème", "Switch theme"),
    ("Indicateurs clés", "Key figures"),
    ("Plein écran", "Fullscreen"),
    ("Principale", "Primary"),
    ("Galerie", "Gallery"),
    ("sprezzature/fr/figures.html", "sprezzature/figures.html"),
    ("sprezzature/fr/", "sprezzature/"),
    # fragments génériques — EN DERNIER
    ("Rendement", "Return"),
    ("indice", "index"),
    ("moyenne", "average"),
    ("titres", "holdings"),
    ("Nous", "us"),
    (" pb", " bps"),
    (" / jour", " / day"),
    (" à ", " to "),
    (" : ", ": "),
]
_TR.sort(key=lambda p: len(p[0]), reverse=True)


def translate(text: str) -> str:
    """Traduit ``text`` en anglais si la langue courante est ``en`` ; sinon inchangé."""
    if S.LANG != "en":
        return text
    for fr, en in _TR:
        text = text.replace(fr, en)
    return text


def compute_stats(g: D.Portfolio) -> Dict[str, float]:
    """Indicateurs de performance (rendement, Sharpe, drawdown, etc.)."""
    n = len(g.days)
    net_total = g.wealth_net[-1] / 100.0 - 1.0
    bh_total = g.buyhold[-1] / 100.0 - 1.0
    ann_vol = float(np.std(g.net_ret)) * np.sqrt(252.0)
    sharpe = float(np.mean(g.net_ret)) * 252.0 / (ann_vol or 1.0)
    return {
        "total_return": net_total, "buyhold_return": bh_total, "sharpe": sharpe,
        "max_dd": float(g.dd.min()), "win_rate": float(np.mean(g.net_ret > 0)),
        "fees_pct": float(g.fee_cum[-1]) * 100.0, "n": n,
    }


# Deux régimes : le beau cas (graine 48) et le cas défavorable (graine 4), pour
# répondre à la relecture — « le programme a affiché le cas le plus favorable ».
SCENARIOS = (("favorable", 48), ("adverse", 4))

_SCEN_LABEL = {"favorable": ("Cas favorable", "Favourable case"),
               "adverse": ("Cas défavorable", "Adverse case")}

# Où sont publiées les pages : dans le site ``web/`` (EN à la racine, FR sous fr/).
_WEB = _HERE.parent.parent / "web"

# Métadonnées bilingues des dix panneaux : (clé, générateur, titre, sous-titre).
# fr d'abord, en ensuite. Les titres des SVG eux-mêmes passent par translate().
_PANELS: List[Tuple[str, object, Tuple[str, str], Tuple[str, str]]] = [
    ("p1", P.equity, ("Richesse nette comparée", "Net wealth compared"),
     ("Indice base 100 · nous (Kₜ auto), achat-conservation et K fixe",
      "Base 100 index · us (auto Kₜ), buy & hold and fixed K")),
    ("p2", P.k_step, ("Taille automatique Kₜ", "Automatic size Kₜ"),
     ("Nombre de titres détenus dans le temps", "Number of holdings over time")),
    ("p3", P.profiles, ("Profils des 100 actions", "The 100 stocks"),
     ("Cours indexés base 100 · échelle logarithmique", "Prices indexed to 100 · logarithmic scale")),
    ("p4", P.daily_pnl, ("Gains nets journaliers", "Daily net P&L"),
     ("Rendement net (%) par séance · bleu en hausse, rouge en baisse",
      "Net return (%) per session · blue up, red down")),
    ("p5", P.fees, ("Frais ponctuels et cumulés", "Per-rebalance and cumulative cost"),
     ("Double axe · points de base et pourcentage", "Dual axis · basis points and percent")),
    ("p6", P.ridgeline, ("Distribution des rendements", "Return distribution"),
     ("Densité du rendement net journalier (%), par année", "Density of daily net return (%), by year")),
    ("p7", P.monthly_heatmap, ("Rendements mensuels", "Monthly returns"),
     ("Bleu positif, rouge négatif (%)", "Blue positive, red negative (%)")),
    ("p8", P.turnover, ("Rotation aux réallocations", "Turnover at rebalances"),
     ("Double axe · part du portefeuille échangée (%)", "Dual axis · share of the book traded (%)")),
    ("p9", P.drawdown, ("Pertes en ligne", "Drawdown"),
     ("Écart (%) sous le plus-haut atteint (drawdown)", "Distance (%) below the running peak (drawdown)")),
    ("p10", P.risk, ("Performance ajustée du risque", "Risk-adjusted performance"),
     ("Ratio de Sharpe et rendement total contre la référence", "Sharpe ratio and total return vs benchmark")),
]

# Chrome du site, par langue. On reprend au mot près les libellés de ``web/`` :
# « Skills » reste en anglais mais en italique côté français (règle maison).
_CHROME = {
    "en": {
        "skip": "Skip to content", "navlabel": "Primary", "skills": "Skills",
        "gallery": "Gallery", "cases": "Case studies", "gh": "⭐️ on Github", "theme": "Switch theme", "scen_label": "Scenario",
        "eyebrow": "sprezzature · financial markets", "h1": "Case study: financial markets",
        "hint": "On a phone, each chart fits the width. Tap ⤢ on any panel "
                "for fullscreen, then pinch to zoom into the detail.",
        "disclaimer": "Illustrative data, no real value, no investment advice.",
        "title": "Financial markets — Sprezzature",
        "desc": "A systematic portfolio with automatic size Kₜ, told in ten interactive SVG "
                "panels, colour-blind-safe, in market-finance colours. Favourable and adverse draws.",
        "footer": ('<a class="underline hover:text-brand-blue" href="index.html">&larr; All skills</a> '
                   '· Claude / OpenCode skills by <a class="underline hover:text-brand-blue" '
                   'href="https://www.linkedin.com/in/warith-harchaoui/">Warith Harchaoui</a>.'),
        "fs": "Fullscreen",
    },
    "fr": {
        "skip": "Aller au contenu", "navlabel": "Principale", "skills": "<em>Skills</em>",
        "gallery": "Galerie", "cases": "Études de cas", "gh": "⭐️ sur Github", "theme": "Changer de thème", "scen_label": "Scénario",
        "eyebrow": "sprezzature · finance de marché", "h1": "Étude de cas : les marchés financiers",
        "hint": "Sur téléphone, chaque graphique tient dans la largeur. Touchez ⤢ "
                "sur un panneau pour le plein écran, puis pincez pour zoomer sur le détail.",
        "disclaimer": "Données illustratives, aucune valeur réelle, aucun conseil d'investissement.",
        "title": "Marchés financiers — Sprezzature",
        "desc": "Un portefeuille systématique à taille automatique Kₜ, raconté en dix panneaux "
                "SVG interactifs, lisibles sous daltonisme, aux couleurs de la finance de marché. "
                "Tirages favorable et défavorable.",
        "footer": ('<a class="underline hover:text-brand-blue" href="index.html">&larr; Tous les skills</a> '
                   '· Skills Claude / OpenCode par <a class="underline hover:text-brand-blue" '
                   'href="https://www.linkedin.com/in/warith-harchaoui/">Warith Harchaoui</a>.'),
        "fs": "Plein écran",
    },
}

_SITE = "https://sprezzature.ai"


def _filename(scenario: str) -> str:
    """Nom de fichier d'une page (le dossier porte la langue : web/ ou web/fr/)."""
    return "financial-markets" + ("-adverse" if scenario == "adverse" else "") + ".html"


def _tile(label: str, value_txt: str, colour: str, count: str, foot: str,
          *, prefix: str = "", suffix: str = "", decimals: int = 0, span: str = "") -> str:
    """Une tuile KPI Tailwind, avec les attributs de comptage animé.

    ``span`` ajoute des classes de grille (ex. la 5ᵉ tuile occupe les deux
    colonnes en mobile pour éviter une cellule vide en fin de grille)."""
    attrs = f'data-count="{count}"'
    if prefix:
        attrs += f' data-prefix="{prefix}"'
    if suffix:
        attrs += f' data-suffix="{suffix}"'
    if decimals:
        attrs += f' data-decimals="{decimals}"'
    cls = f"bg-white p-5{(' ' + span) if span else ''}"
    return (
        f'<div class="{cls}" role="listitem">'
        f'<div class="text-xs font-medium uppercase tracking-wide text-neutral-400">{label}</div>'
        f'<div class="mt-1 text-4xl font-bold tabular-nums {colour}" {attrs}>{value_txt}</div>'
        f'<div class="mt-0.5 text-sm text-neutral-500">{foot}</div></div>')


def _kpi_html(st: Dict[str, float], lang: str) -> str:
    """Bande d'indicateurs (grille Tailwind) construite à partir des stats."""
    psuf = "%" if lang == "en" else " %"
    rn = st["total_return"] * 100.0
    bh = st["buyhold_return"] * 100.0
    vs = rn - bh
    sh, dd, wr, fees = st["sharpe"], st["max_dd"], st["win_rate"] * 100.0, st["fees_pct"]

    def colour(v: float) -> str:
        return "text-brand-blue" if v >= 0 else "text-red-500"

    sh_col = "text-brand-blue" if sh >= 1 else ("text-red-500" if sh < 0 else "text-neutral-900")
    tiles = [
        _tile(translate("Rendement net"), S.fr_pct(rn, 0, True), colour(rn), f"{rn:.0f}",
              translate("net de frais"), prefix="+", suffix=psuf),
        _tile(translate("vs achat-conservation"), f"{vs:+.0f} pts", colour(vs), f"{vs:.0f}",
              translate("référence") + " " + S.fr_pct(bh, 0, True), prefix="+", suffix=" pts"),
        _tile(translate("Ratio de Sharpe"), S.fr_num(sh, 2), sh_col, f"{sh:.2f}",
              translate("net, annualisé"), decimals=2),
        _tile(translate("Pire perte"), S.fr_pct(dd, 0), "text-red-500", f"{dd:.0f}",
              translate("sous le plus-haut"), suffix=psuf),
        _tile(translate("Séances gagnantes"), S.fr_pct(wr, 0), "text-purple-500", f"{wr:.0f}",
              translate("frais cumulés") + " " + S.fr_pct(fees, 1), suffix=psuf,
              span="col-span-2 sm:col-span-1"),
    ]
    return ('<div class="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border '
            'border-neutral-200 bg-neutral-200 sm:grid-cols-5 dark:border-neutral-800 '
            'dark:bg-neutral-800" role="list" aria-label="'
            + translate("Indicateurs clés") + '">' + "".join(tiles) + "</div>")


def _card(num: int, title: str, sub: str, svg: str, fs_label: str) -> str:
    """Une carte de panneau : titre, bouton plein écran, SVG inline (papier blanc)."""
    return (
        '<figure data-fs-target class="fm-card overflow-hidden rounded-xl border '
        'border-neutral-200 bg-white text-neutral-900 shadow-sm">'
        '<figcaption class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 pt-4 pb-1">'
        f'<span class="font-mono text-sm font-bold text-brand-blue">{num}</span>'
        f'<span class="text-lg font-bold tracking-tight">{title}</span>'
        f'<button data-fs type="button" aria-label="{fs_label}" title="{fs_label}" '
        'class="ml-auto self-center rounded-lg border border-neutral-200 bg-neutral-50 px-2 '
        'py-1 text-neutral-500 hover:border-brand-blue hover:text-brand-blue '
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue">⤢</button>'
        f'<span class="basis-full text-sm text-neutral-500">{sub}</span>'
        '</figcaption>'
        f'<div class="fm-embed block px-4 pb-4">{svg}</div></figure>')


def _dashboard(g: D.Portfolio, st: Dict[str, float], lang: str) -> str:
    """Assemble les dix cartes, deux fois (🏫 academic / 🏭 corporate).

    Chaque passe appelle :func:`market_style.set_theme` puis rend les dix
    panneaux avec les tokens de couleur du thème courant. Les deux jeux de
    cartes sont écrits dans la page ; ``[data-color-mode]`` (même attribut que
    le reste du site, ``web/js/color-mode.js``) bascule instantanément entre
    les deux via CSS (``template.html``), sans re-fetch ni re-render côté
    client.
    """
    i = 1 if lang == "en" else 0
    fs_label = _CHROME[lang]["fs"]
    blocks = []
    for theme, cls in (("academic", "fm-theme-academic"), ("corporate", "fm-theme-corporate")):
        S.set_theme(theme)
        cards = []
        for num, (_, fn, title, sub) in enumerate(_PANELS, start=1):
            svg = fn(g, st) if fn is P.risk else fn(g)
            cards.append(_card(num, title[i], sub[i], translate(svg), fs_label))
        blocks.append(f'<div class="{cls} space-y-6">' + "\n        ".join(cards) + "</div>")
    S.set_theme("corporate")  # remis à la valeur par défaut du module pour tout appelant ultérieur
    return "\n        ".join(blocks)


def _scenario_select(scenario: str, lang: str) -> str:
    """Menu déroulant favorable / défavorable, au style du site (pilule bordée)."""
    opts = ""
    for scen, _ in SCENARIOS:
        sel = " selected" if scen == scenario else ""
        lab = _SCEN_LABEL[scen][1 if lang == "en" else 0]
        opts += f'<option value="{_filename(scen)}"{sel}>{lab}</option>'
    lbl = _CHROME[lang]["scen_label"]
    return (f'<select aria-label="{lbl}" onchange="location=this.value" '
            'class="min-w-0 max-w-[10.5rem] truncate rounded-full border border-neutral-300 '
            'bg-white px-3 py-1 text-sm font-semibold hover:border-brand-blue '
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue '
            'dark:border-neutral-600 dark:bg-neutral-900 sm:max-w-none">'
            f'{opts}</select>')


def _lang_flag(scenario: str, lang: str) -> str:
    """Drapeau vers la même page dans l'autre langue (chemin inter-dossier)."""
    cls = ('rounded-full px-2 py-1 text-lg leading-none hover:bg-neutral-100 '
           'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue '
           'dark:hover:bg-neutral-800')
    if lang == "en":
        return (f'<a href="fr/{_filename(scenario)}" aria-label="Version française" '
                f'title="Version française" class="{cls}">🇫🇷</a>')
    return (f'<a href="../{_filename(scenario)}" aria-label="English version" '
            f'title="English version" class="{cls}">🇬🇧</a>')


def _page(g: D.Portfolio, st: Dict[str, float], lang: str, scenario: str) -> str:
    """Rend une page complète (chrome du site + dashboard) pour un scénario."""
    S.set_lang(lang)
    c = _CHROME[lang]
    base = "../" if lang == "fr" else ""
    canonical = f"{_SITE}/{'fr/' if lang == 'fr' else ''}{_filename(scenario)}"
    alt_en = f"{_SITE}/{_filename(scenario)}"
    alt_fr = f"{_SITE}/fr/{_filename(scenario)}"
    repl = {
        "__LANG__": lang, "__BASE__": base,
        "__TITLE__": c["title"], "__DESC__": c["desc"],
        "__CANONICAL__": canonical, "__ALTEN__": alt_en, "__ALTFR__": alt_fr,
        "__SKIP__": c["skip"], "__NAVLABEL__": c["navlabel"],
        "__NAV_SKILLS__": c["skills"], "__NAV_GALLERY__": c["gallery"],
        "__NAV_CASES__": c["cases"], "__NAV_GH__": c["gh"],
        "__THEMELABEL__": c["theme"], "__SCENARIO__": _scenario_select(scenario, lang),
        "__LANGFLAG__": _lang_flag(scenario, lang),
        "__EYEBROW__": c["eyebrow"], "__H1__": c["h1"], "__HINT__": c["hint"],
        "__KPIS__": _kpi_html(st, lang), "__DASHBOARD__": _dashboard(g, st, lang),
        "__DISCLAIMER__": c["disclaimer"], "__FOOTER__": c["footer"],
    }
    html = (_HERE / "template.html").read_text(encoding="utf-8")
    for token, value in repl.items():
        html = html.replace(token, value)
    return html


def main() -> int:
    """Construit les 4 pages web : {favorable, défavorable} × {anglais, français}."""
    (_WEB / "fr").mkdir(parents=True, exist_ok=True)
    written = []
    for scenario, seed in SCENARIOS:
        g = D.build(seed=seed, regime=scenario)
        st = compute_stats(g)
        for lang in ("en", "fr"):
            out = _WEB / ("fr" if lang == "fr" else "") / _filename(scenario)
            out.write_text(_page(g, st, lang, scenario), encoding="utf-8")
            written.append(out.relative_to(_WEB.parent))
        S.set_lang("en")
        print(f"{scenario:10s} seed {seed}: rendement {S.fr_pct(st['total_return'] * 100, 0, True)}, "
              f"vs achat-cons. {(st['total_return'] - st['buyhold_return']) * 100:+.0f} pts, "
              f"Sharpe {S.fr_num(st['sharpe'], 2)}, drawdown {S.fr_pct(st['max_dd'], 0)}")
    print("wrote:", ", ".join(str(p) for p in written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
