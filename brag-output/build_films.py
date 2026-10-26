#!/usr/bin/env python3
"""Emit the twelve HyperFrames projects: four films, three canvases each.

One spec per film drives all three formats, so the series stays frame-synced:
the same beat lands at the same second in landscape, portrait and square.
Only the layout changes, never the timing.

Run from brag-output/:  python3 build_films.py
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
FILMS_DIR = ROOT / "films"
ASSETS = ROOT / "_assets"
MUSIC = "happy-beats-business-moves-vol-12-by-ende-dot-app.mp3"

# ---------------------------------------------------------------------------
# Design tokens, taken from web/css/app.css, [data-color-mode=academic].
# ---------------------------------------------------------------------------
INK, INK_SOFT, BLUE, LINE, PAPER = "#171717", "#525252", "#0072b2", "#e5e5e5", "#ffffff"
NAVY = "#003c5d"   # brand-navy: the eyebrow rides over the wash, blue does not clear AA there

# Per-canvas scale. Portrait is watched full-screen on a phone, so its type is
# relatively larger; square gives up the most room and shrinks the figure.
FORMATS = {
    "landscape": dict(w=1920, h=1080, pad=104, hero=104, h2=44, body=38, mono=29,
                      eyebrow=26, chip=32, split=True, fig=1010, grid6=3, shot=880,
                      view=0.62),
    "portrait":  dict(w=1080, h=1920, pad=72, hero=92, h2=52, body=44, mono=32,
                      eyebrow=28, chip=31, split=False, fig=884, grid6=2, shot=780,
                      view=1.05),
    "square":    dict(w=1080, h=1080, pad=64, hero=74, h2=40, body=34, mono=26,
                      eyebrow=23, chip=25, split=False, fig=600, grid6=3, shot=560,
                      view=0.80),
}

# Beat grid of the bundled track, 109.96 BPM.
#
# Extended from 42 beats (23 s) to 111 (60 s) on 2026-10-26, when the films
# grew to a minute. Not extrapolated: `npx hyperframes beats` detected 483
# onsets across the whole 117 s track -- at 243.9 BPM and flagged uncertain,
# because it found subdivisions rather than the musical pulse. So the pulse is
# walked at 60/109.96 and each step SNAPPED to the nearest detected onset
# within 120 ms. Every one of the 111 found one, and the result agrees with
# the original hand-measured 42 to a mean of 12 ms -- which is the check that
# matters: a new grid has to put the known-good beats where they already were.
BEATS = [0.549, 1.106, 1.637, 2.181, 2.736, 3.288, 3.819, 4.368,
         4.912, 5.471, 5.995, 6.549, 7.088, 7.653, 8.181, 8.731,
         9.28, 9.819, 10.368, 10.917, 11.461, 12.005, 12.549, 13.093,
         13.643, 14.187, 14.731, 15.28, 15.819, 16.368, 16.912, 17.467,
         18.005, 18.555, 19.099, 19.648, 20.187, 20.741, 21.28, 21.829,
         22.368, 22.923, 23.461, 24.005, 24.549, 25.104, 25.643, 26.192,
         26.741, 27.285, 27.824, 28.379, 28.923, 29.467, 30.005, 30.555,
         31.099, 31.643, 32.187, 32.741, 33.28, 33.824, 34.368, 34.923,
         35.461, 36.011, 36.555, 37.104, 37.643, 38.192, 38.736, 39.28,
         39.824, 40.373, 40.917, 41.461, 42.005, 42.549, 43.163, 43.648,
         44.187, 44.741, 45.285, 45.824, 46.368, 46.917, 47.467, 48.011,
         48.56, 49.104, 49.648, 50.187, 50.741, 51.28, 51.829, 52.373,
         52.943, 53.488, 54.034, 54.58, 55.125, 55.671, 56.217, 56.747,
         57.308, 57.957, 58.395, 58.928, 59.451, 60.036, 60.539]

OUTRO_LINE = "Make it. Audit it. Then look at it."


# ---------------------------------------------------------------------------
# Film specs. `at` values are global seconds and identical across formats.
# ---------------------------------------------------------------------------
def group_scenes(claim, s2, s3, mark, logo="logo-512.png", grid=None):
    """The shared four-beat shape. `grid` overrides it when a film needs more
    room, as the accessibility one does for its four simulations."""
    g = grid or [(0.0, 4.8, 4.0), (4.0, 7.4, 10.6), (10.4, 5.6, 15.4),
                 (15.2, 3.1, 18.3)]
    return [
        dict(type="claim", start=g[0][0], dur=g[0][1], end=g[0][2], line=claim),
        dict(s2, start=g[1][0], dur=g[1][1], end=g[1][2]),
        dict(s3, start=g[2][0], dur=g[2][1], end=g[2][2]),
        dict(type="outro", start=g[3][0], dur=g[3][1], end=g[3][2], logo=logo,
             mark=mark, line=OUTRO_LINE, url="sprezzature.ai"),
    ]


LOOP_STEPS = [("01", "render"), ("02", "look"), ("03", "fix the source"), ("04", "again")]

FILMS = {
    # ---------------------------------------------------------------- global
    "sprezzature": dict(
        duration=25.0,
        vo=[("global-1", 0.90), ("global-2", 4.60), ("global-3", 10.40),
            ("global-4", 16.80), ("global-5", 22.20)],
        sfx=[("drop", 4.10), ("wipe", 12.55), ("tile", 16.93), ("bell", 22.10)],
        # The arc, rewritten 2026-10-26. It used to open on "you can't proofread
        # a chart" and spend a scene naming the nine skills -- a catalogue, and
        # the least interesting thing about the suite. What every brick has in
        # common is design know-how: rules somebody already wrote down, turned
        # into something that runs. The film now says that, and builds to the
        # outro line it always had -- "Make it. Audit it. Then look at it." --
        # which was the thesis before the film was.
        scenes=[
            dict(type="claim", start=0.0, dur=4.8, end=4.0,
                 line="Design is know-how. Most of it is already written down."),
            # The know-how, named. Every chip is a source somebody can go and
            # read, which is the point: cited, not invented here.
            dict(type="chips", start=4.0, dur=6.3, end=9.9,
                 eyebrow="Written down, by somebody else",
                 items=["30 Laws of UX", "WCAG contrast", "Machado 2009",
                        "Gestalt", "Equal Earth", "W3C WebVTT", "Schema.org",
                        "OKLCH"],
                 at=[4.39, 4.91, 5.34, 6.00, 6.56, 7.09, 7.64, 8.19],
                 caption="Yablonski, the W3C, a 2009 IEEE paper, a 2018 "
                         "projection — read, then written into the tools"),
            # The other half, and the one a reference cannot supply: a model
            # that looks at the result. Kept from the old cut because it is the
            # strongest thing in the film and it now has a reason to be here.
            dict(type="loop", start=9.7, dur=7.2, end=16.5,
                 eyebrow="The part no reference can do", steps=LOOP_STEPS,
                 fig="figures/bar-grouped.svg", gray="figures/bar-grouped-gray.svg",
                 ratio=745 / 505, step_at=[10.37, 10.93, 11.46, 12.02],
                 wipe_at=12.55, wipe_dur=1.06, caption_at=14.20,
                 caption="If the story survives grey, it survives everyone."),
            # The payoff: one body of know-how, pointed both ways.
            dict(type="panel", start=16.3, dur=5.8, end=22.1,
                 eyebrow="The same rules, both directions",
                 rows=[("Make", "a page, a figure, a map, a caption"),
                       ("Audit", "the same rules, against what you made")],
                 at=[16.93, 17.47],
                 caption="167 chart kinds · 20 a11y rules · 30 laws of UX · "
                         "nothing has to leave the machine"),
            dict(type="outro", start=21.9, dur=3.1, end=25.0, logo="logo-512.png",
                 mark="Sprezzature", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # ------------------------------------------------------------------ colors
    "colors": dict(
        duration=60.0,
        vo=[("colors-1", 1.10), ("colors-2", 5.50), ("colors-3", 11.50),
            ("colors-4", 17.50), ("colors-5", 24.00), ("colors-6", 31.50),
            ("colors-7", 41.00), ("colors-8", 49.50), ("colors-9", 55.80)],
        sfx=[("drop", 5.46), ("wipe", 18.03), ("wipe", 21.85), ("tile", 31.46),
             ("tile", 41.46), ("bell", 55.63)],
        scenes=[
            dict(type="claim", start=0.0, dur=5.5, end=5.0,
                 line="Light grey on white reads fine. To you, indoors."),
            dict(type="panel", start=4.9, dur=6.6, end=11.4,
                 eyebrow="The same button, two readers",
                 rows=[("Low vision", "the text and the background are too close to separate"),
                       ("Bright sunlight", "a phone screen loses the difference entirely")],
                 at=[5.46, 6.00],
                 caption="It reads fine to whoever picked the colour. That is the problem."),
            dict(type="claim", start=11.3, dur=5.4, end=16.3,
                 line="About one man in twelve sees red and green as the same bar."),
            dict(type="cvd", start=16.2, dur=12.0, end=28.1,
                 eyebrow="So the simulator renders those eyes",
                 base="figures/cvd/00-original.png",
                 stages=[("01", "protanopia", "figures/cvd/01-protanopia.png", 18.03),
                         ("02", "deuteranopia", "figures/cvd/02-deuteranopia.png", 20.21),
                         ("03", "tritanopia", "figures/cvd/03-tritanopia.png", 22.39),
                         ("04", "grayscale", "figures/cvd/04-grayscale.png", 24.57)],
                 ratio=1490 / 1010, wipe_dur=0.80, caption_at=26.21,
                 caption="If the story survives grey, it survives everyone."),
            dict(type="chips", start=28.0, dur=11.5, end=39.4,
                 eyebrow="None of this was invented here",
                 items=["WCAG 2.x", "2.4-gamma luminance", "OKLab", "Ottosson 2020",
                        "Machado 2009", "IEEE TVCG", "OKLCH", "CVD_MATRICES"],
                 # Reveals end ~2.5 s before the scene does. The first cut put the
                 # last chip on screen 0.3 s before the cut -- read by nobody.
                 at=[29.28, 30.37, 31.46, 32.56, 33.64, 34.73, 35.81, 36.91],
                 caption="The thresholds are the standard's. The matrices are a "
                         "measured paper's. The lightness axis is Ottosson's."),
            dict(type="panel", start=39.3, dur=10.3, end=49.4,
                 eyebrow="The same know-how, both directions",
                 rows=[("Audit", "every text-on-background pair, and a fix that stays close"),
                       ("Make", "the approved palette, emitted as a Tailwind config")],
                 at=[41.46, 42.55],
                 caption="One source for the colours, instead of each project "
                         "copying hex codes."),
            dict(type="claim", start=49.3, dur=6.4, end=55.6,
                 line="Pure standard library. No network. No model."),
            dict(type="outro", start=55.5, dur=4.5, end=60.0, logo="logo-512.png",
                 mark="Sprezzature · colors", line=OUTRO_LINE, url="sprezzature.ai"),
        ],
    ),
    # --------------------------------------------------------------- figures
    "figures-et-cartes": dict(
        duration=18.3,
        vo=[("figures-1", 0.80), ("figures-2", 4.40), ("figures-3", 10.90)],
        sfx=[("drop", 4.30), ("tile", 9.29), ("bell", 15.25)],
        scenes=group_scenes(
            "167 kinds, every one hand‑authored.",
            dict(type="grid", eyebrow="sprezzature-figures",
                 images=["figures/sankey.svg", "figures/alluvial.svg",
                         "figures/chord.svg", "figures/calendar-heatmap.svg",
                         "figures/bellcurve.svg", "figures/circle-packing.svg"],
                 at=[4.39, 4.91, 5.34, 6.00, 6.56, 7.09],
                 caption="the SVG is the deliverable, never an export"),
            dict(type="grid", eyebrow="sprezzature-maps",
                 images=["maps/choropleth-sequential.svg", "maps/choropleth-diverging.svg",
                         "maps/situation-western-europe.png", "maps/situation-himalaya.png"],
                 at=[10.93, 11.46, 12.02, 12.55],
                 caption="choropleth · situation · density, on a real projection"),
            "Figures & Maps"),
    ),
    # ---------------------------------------------------------- accessibility
    "accessibilite": dict(
        duration=21.3,
        vo=[("access-1", 0.80), ("access-2", 4.40), ("access-3", 13.60)],
        sfx=[("drop", 4.10), ("wipe", 5.34), ("wipe", 8.74), ("bell", 18.25)],
        scenes=group_scenes(
            "Eyes you don’t have.",
            dict(type="cvd", eyebrow="Colour vision simulation",
                 # Rendered by the project's own simulate_cvd.py, Machado
                 # matrices, from the shipped bar-grouped.svg.
                 base="figures/cvd/00-original.png",
                 stages=[("01", "protanopia", "figures/cvd/01-protanopia.png", 5.34),
                         ("02", "deuteranopia", "figures/cvd/02-deuteranopia.png", 6.56),
                         ("03", "tritanopia", "figures/cvd/03-tritanopia.png", 7.64),
                         ("04", "grayscale", "figures/cvd/04-grayscale.png", 8.74)],
                 ratio=1490 / 1010, wipe_dur=0.80, caption_at=9.83,
                 caption="If the story survives grey, it survives everyone."),
            dict(type="chips", eyebrow="accessibility · colors · audio",
                 items=["20 a11y rules", "WCAG contrast", "CVD simulation",
                        "OKLCH lighten / darken", "Tailwind export", "alt text",
                        "WebVTT / SRT", "diarization"],
                 at=[13.64, 14.20, 14.73, 15.29, 15.84, 16.38, 16.93, 17.47],
                 caption="deterministic where it can be, local where it cannot"),
            "Accessibility", grid=[(0.0, 4.8, 4.0), (4.0, 9.8, 13.2),
                                   (13.0, 6.0, 18.4), (18.2, 3.1, 21.3)]),
    ),
    # ------------------------------------------------------------- interface
    "interface": dict(
        duration=18.3,
        vo=[("interface-1", 0.80), ("interface-2", 4.40), ("interface-3", 10.90)],
        sfx=[("drop", 4.20), ("tile", 12.55), ("bell", 15.25)],
        scenes=group_scenes(
            "A command line is a wall.",
            dict(type="shot", eyebrow="sprezzature-cli-gui",
                 src="shots/cli-gui-full.png", ratio=760 / 1040, at=4.39, scroll=True,
                 caption="argparse, Click or Typer in. One self-contained page out."),
            dict(type="chips", eyebrow="ui · publish · ux-laws",
                 items=["three Roboto", "dark mode", "focus rings", "reduced motion",
                        "meta tags", "favicons", "llms.txt", "30 Laws of UX"],
                 at=[10.93, 11.46, 12.02, 12.55, 13.11, 13.64, 14.20, 14.73],
                 caption="the same skill builds it and audits it"),
            "Interface"),
    ),
}


# ---------------------------------------------------------------------------
# HTML emission
# ---------------------------------------------------------------------------
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def css(f: dict) -> str:
    """Canvas-specific stylesheet. Everything else is shared."""
    pad, split = f["pad"], f["split"]
    fig = f["fig"]
    return f"""
    :root {{
      --ink: {INK}; --ink-soft: {INK_SOFT}; --blue: {BLUE};
      --line: {LINE}; --paper: {PAPER}; --navy: {NAVY};
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: {f['w']}px; height: {f['h']}px; overflow: hidden;
                  background: var(--paper); }}
    #root {{ position: relative; width: 100%; height: 100%; overflow: hidden;
             background: var(--paper); color: var(--ink);
             font-family: "Roboto", system-ui, sans-serif; }}

    /* Background: the site's own hero wash, raised to video intensity, over a
       faint brand-tinted grid so the light canvas is not a blank slide. */
    .bg {{ position: absolute; inset: 0; background: var(--paper); }}
    .bg-grid {{ position: absolute; inset: 0; opacity: .55;
      background-image: radial-gradient(rgba(0,114,178,.14) 1.6px, transparent 1.7px);
      background-size: 44px 44px; }}
    .bg-wash {{ position: absolute; top: {-int(f['h'] * .38)}px; left: 50%;
      width: {int(f['w'] * 1.25)}px; height: {int(f['h'] * 1.4)}px;
      margin-left: {-int(f['w'] * .625)}px;
      background: radial-gradient(closest-side, rgba(127,209,255,.55) 0%,
        rgba(127,209,255,.22) 45%, rgba(127,209,255,0) 78%); }}

    .inner {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    .stage {{ position: absolute; inset: 0; display: flex; align-items: center;
              justify-content: center; padding: {pad}px; }}
    .col {{ display: flex; flex-direction: column; align-items: center;
            justify-content: center; width: 100%; }}

    .eyebrow {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['eyebrow']}px; font-weight: 500; letter-spacing: .2em;
      color: var(--navy); text-transform: uppercase; text-align: center; }}
    .rule {{ height: 3px; background: var(--blue); transform-origin: center; }}
    .caption {{ font-size: {f['body']}px; font-weight: 400; line-height: 1.34;
      color: var(--ink-soft); text-align: center; max-width: {f['w'] - 2 * pad}px; }}

    /* Scene 1: the claim */
    .claim {{ font-family: "Roboto Serif"; font-size: {f['hero']}px; font-weight: 600;
      letter-spacing: -.02em; line-height: 1.08; text-align: center;
      max-width: {f['w'] - 2 * pad}px; color: var(--ink); }}

    /* The site's card, drawn at 2px for video instead of the web's 1px */
    .card {{ border: 2px solid var(--line); border-radius: 20px;
      background: var(--paper); padding: 22px;
      box-shadow: 0 26px 64px rgba(0,60,93,.14); }}

    .figbox {{ position: relative; width: {fig}px; overflow: hidden; }}
    .figbox img {{ position: absolute; top: 0; left: 0; display: block;
      width: {fig}px; height: 100%; }}
    .gray-wrap {{ position: absolute; inset: 0; clip-path: inset(0% 100% 0% 0%); }}
    .fig-gray {{ filter: grayscale(1) contrast(1.03); }}
    .wipe-edge {{ position: absolute; top: 0; left: 0; width: 4px; height: 100%;
      background: var(--blue); opacity: 0; }}

    .loop-wrap {{ display: flex; {'flex-direction: row; align-items: center; gap: 88px;'
                                 if split else 'flex-direction: column; align-items: center; gap: 46px;'}
      justify-content: center; width: 100%; }}
    .loop-text {{ display: flex; flex-direction: column;
      align-items: {'flex-start' if split else 'center'};
      text-align: {'left' if split else 'center'};
      {'width: ' + str(f['w'] - 2 * pad - fig - 132) + 'px;' if split
       else 'width: ' + str(f['w'] - 2 * pad) + 'px;'} }}
    .loop-text .eyebrow, .loop-text .caption {{ text-align: {'left' if split else 'center'}; }}
    .steps {{ display: inline-flex; flex-direction: column; align-items: flex-start; }}
    .step {{ display: flex; align-items: baseline; gap: 18px;
      font-family: "Roboto Mono", ui-monospace, monospace; font-size: {f['mono']}px;
      font-weight: 500; line-height: 1.55; color: var(--ink); }}
    .step-n {{ color: var(--blue); font-weight: 600; }}
    .step-dim {{ opacity: .32; }}

    .grid {{ display: grid; gap: 22px; justify-content: center; }}
    .tile {{ overflow: hidden; border: 2px solid var(--line); border-radius: 16px;
      background: var(--paper); padding: 9px; }}
    .tile img {{ display: block; width: 100%; height: 100%; object-fit: contain; }}

    .chips {{ display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;
      max-width: {f['w'] - 2 * pad}px; }}
    .chip {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['chip']}px; font-weight: 500; color: var(--ink);
      border: 2px solid var(--line); border-radius: 999px;
      padding: {int(f['chip'] * .42)}px {int(f['chip'] * .9)}px;
      background: var(--paper); white-space: nowrap; }}

    .panel {{ width: {min(f['w'] - 2 * pad, 1280)}px; }}
    .prow {{ display: flex; align-items: baseline;
      {'flex-direction: row; gap: 28px;' if split else 'flex-direction: column; gap: 6px;'}
      padding: {int(f['body'] * .62)}px 0; border-bottom: 2px solid var(--line); }}
    .prow:last-child {{ border-bottom: 0; }}
    .pk {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {f['mono']}px; font-weight: 600; color: var(--blue);
      {'min-width: 380px;' if split else ''} white-space: nowrap; }}
    .pv {{ font-size: {f['h2']}px; font-weight: 400; color: var(--ink);
      line-height: 1.3; }}

    .shotcard img {{ display: block; border-radius: 8px; }}
    .viewport {{ position: relative; overflow: hidden; border-radius: 8px; }}

    #logo {{ display: block; width: {int(f['hero'] * 2.0)}px;
      height: {int(f['hero'] * 2.0)}px; object-fit: contain; }}
    #mark {{ font-family: "Roboto Serif"; font-size: {int(f['hero'] * .84)}px;
      font-weight: 600; letter-spacing: -.02em; color: var(--ink);
      margin-top: {int(f['hero'] * .3)}px; text-align: center; }}
    #oline {{ font-size: {f['h2']}px; color: var(--ink-soft);
      margin-top: {int(f['hero'] * .22)}px; text-align: center; }}
    #ourl {{ font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * .96)}px; font-weight: 500; letter-spacing: .06em;
      color: var(--blue); margin-top: {int(f['hero'] * .3)}px; }}

    #rail-l, #rail-r {{ position: absolute; top: {int(pad * .48)}px;
      font-family: "Roboto Mono", ui-monospace, monospace;
      font-size: {int(f['eyebrow'] * .9)}px; font-weight: 500; letter-spacing: .22em; }}
    #rail-l {{ left: {pad}px; color: var(--blue); }}
    #rail-r {{ right: {pad}px; letter-spacing: .1em; color: var(--ink-soft); }}
    #rail-line {{ position: absolute; left: {pad}px; top: {f['h'] - int(pad * .52)}px;
      width: {f['w'] - 2 * pad}px; height: 2px; background: var(--line);
      transform-origin: left center; }}
    """


def scene_html(sc: dict, f: dict, i: int) -> str:
    """Body markup for one scene. Timing lives on the wrapper, not here."""
    t = sc["type"]
    head = (f'<p class="eyebrow" id="s{i}-eyebrow">{esc(sc["eyebrow"])}</p>'
            f'<div class="rule" id="s{i}-rule" style="width:132px;margin:18px 0 '
            f'{int(f["body"] * 1.0)}px"></div>') if sc.get("eyebrow") else ""
    cap = (f'<p class="caption" id="s{i}-caption" '
           f'style="margin-top:{int(f["body"] * 1.05)}px">{esc(sc["caption"])}</p>'
           ) if sc.get("caption") and t not in ("loop", "cvd") else ""

    if t == "claim":
        return (f'<div class="stage"><div class="col">'
                f'<h1 class="claim" id="s{i}-line">{esc(sc["line"])}</h1>'
                f'<div class="rule" id="s{i}-rule" '
                f'style="width:220px;margin-top:{int(f["hero"] * .42)}px"></div>'
                f'</div></div>')

    if t == "loop":
        h = int(f["fig"] / sc["ratio"])
        steps = '<div class="steps">' + "".join(
            f'<div class="step" id="s{i}-step{n}"><span class="step-n">{esc(k)}</span>'
            f'<span>{esc(v)}</span></div>'
            for n, (k, v) in enumerate(sc["steps"], 1)) + '</div>'
        return (f'<div class="stage"><div class="loop-wrap">'
                f'<div class="card" id="s{i}-card"><div class="figbox" '
                f'style="height:{h}px">'
                f'<img src="assets/{sc["fig"]}" alt="">'
                f'<div class="gray-wrap" id="s{i}-gray">'
                f'<img class="fig-gray" src="assets/{sc["gray"]}" alt=""></div>'
                f'<div class="wipe-edge" id="s{i}-wipe"></div>'
                f'</div></div>'
                f'<div class="loop-text">{head}{steps}'
                f'<p class="caption" id="s{i}-caption" '
                f'style="margin-top:{int(f["body"] * 1.2)}px">{esc(sc["caption"])}</p>'
                f'</div></div></div>')

    if t == "cvd":
        h = int(f["fig"] / sc["ratio"])
        # Every simulation sits on the one below it, so each wipe hands the
        # frame to the next pair of eyes without a cut.
        layers = "".join(
            f'<div class="gray-wrap" id="s{i}-w{k}">'
            f'<img src="assets/{src}" alt=""></div>'
            for k, (_, _, src, _) in enumerate(sc["stages"], 1))
        steps = '<div class="steps">' + "".join(
            f'<div class="step step-dim" id="s{i}-step{k}">'
            f'<span class="step-n">{esc(num)}</span><span>{esc(lbl)}</span></div>'
            for k, (num, lbl, _, _) in enumerate(sc["stages"], 1)) + '</div>'
        return (f'<div class="stage"><div class="loop-wrap">'
                f'<div class="card" id="s{i}-card"><div class="figbox" '
                f'style="height:{h}px">'
                f'<img src="assets/{sc["base"]}" alt="">'
                f'{layers}'
                f'<div class="wipe-edge" id="s{i}-wipe"></div>'
                f'</div></div>'
                f'<div class="loop-text">{head}{steps}'
                f'<p class="caption" id="s{i}-caption" '
                f'style="margin-top:{int(f["body"] * 1.2)}px">{esc(sc["caption"])}</p>'
                f'</div></div></div>')

    if t == "grid":
        n = len(sc["images"])
        cols = (4 if f["split"] else 2) if n == 4 else f["grid6"]
        rows = -(-n // cols)
        tw = min((f["w"] - 2 * f["pad"] - (cols - 1) * 22) // cols, 560)
        th = int(tw * 0.75)
        # Reserve the eyebrow, the rule and a two-line caption, then let the
        # remaining height cap the tile. Without this the caption slides under
        # the bottom rail in landscape.
        reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
        cap_h = (f["h"] - 2 * f["pad"] - reserve - (rows - 1) * 22) // rows
        if th > cap_h:
            th = max(150, cap_h)
            tw = int(th / 0.75)
        tiles = "".join(
            f'<div class="tile" id="s{i}-t{k}" style="width:{tw}px;height:{th}px">'
            f'<img src="assets/{src}" alt=""></div>'
            for k, src in enumerate(sc["images"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="grid" style="grid-template-columns:repeat({cols},{tw}px)">'
                f'{tiles}</div>{cap}</div></div>')

    if t == "chips":
        chips = "".join(f'<span class="chip" id="s{i}-c{k}">{esc(v)}</span>'
                        for k, v in enumerate(sc["items"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="chips">{chips}</div>{cap}</div></div>')

    if t == "panel":
        rows = "".join(
            f'<div class="prow" id="s{i}-r{k}"><span class="pk">{esc(a)}</span>'
            f'<span class="pv">{esc(b)}</span></div>'
            for k, (a, b) in enumerate(sc["rows"], 1))
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="card panel" id="s{i}-panel">{rows}</div>{cap}</div></div>')

    if t == "shot":
        reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
        max_h = f["h"] - 2 * f["pad"] - reserve - 44
        iw = f["shot"]
        ih = int(iw / sc["ratio"])
        if sc.get("scroll"):
            view = min(max_h, int(iw * f["view"]))
            return (f'<div class="stage"><div class="col">{head}'
                    f'<div class="card shotcard" id="s{i}-shot">'
                    f'<div class="viewport" style="width:{iw}px;height:{view}px">'
                    f'<img id="s{i}-page" src="assets/{sc["src"]}" alt="" '
                    f'style="width:{iw}px;height:{ih}px"></div></div>'
                    f'{cap}</div></div>')
        if ih > max_h:
            ih = max_h
            iw = int(ih * sc["ratio"])
        return (f'<div class="stage"><div class="col">{head}'
                f'<div class="card shotcard" id="s{i}-shot">'
                f'<img src="assets/{sc["src"]}" alt="" '
                f'style="width:{iw}px;height:{ih}px;object-fit:contain"></div>'
                f'{cap}</div></div>')

    if t == "outro":
        return (f'<div class="stage"><div class="col">'
                f'<img id="logo" src="assets/{sc["logo"]}" alt="">'
                f'<p id="mark">{esc(sc["mark"])}</p>'
                f'<p id="oline">{esc(sc["line"])}</p>'
                f'<p id="ourl">{esc(sc["url"])}</p></div></div>')

    raise ValueError(t)


def scene_js(sc: dict, i: int, f: dict) -> list[str]:
    """Tweens for one scene, in global time. Entrances vary by element type so
    a scene has choreography rather than one repeated slide-up."""
    t, s, out = sc["type"], sc["start"], []
    if sc.get("eyebrow"):
        out.append(f'tl.fromTo("#s{i}-eyebrow",{{x:-26,opacity:0}},'
                   f'{{x:0,opacity:1,duration:.55,ease:"power2.out"}},{s + .3:.2f});')
        out.append(f'tl.fromTo("#s{i}-rule",{{scaleX:0}},'
                   f'{{scaleX:1,duration:.6,ease:"expo.out"}},{s + .5:.2f});')
    if sc.get("caption") and t not in ("loop", "cvd"):
        out.append(f'tl.fromTo("#s{i}-caption",{{y:16,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.55,ease:"power2.out"}},{s + .7:.2f});')

    if t == "claim":
        out.append(f'tl.fromTo("#s{i}-line",{{y:30,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.55,ease:"power3.out"}},{s + .2:.2f});')
        out.append(f'tl.fromTo("#s{i}-rule",{{scaleX:0,opacity:0}},'
                   f'{{scaleX:1,opacity:1,duration:.7,ease:"expo.out"}},{s + .55:.2f});')

    elif t == "loop":
        w = f["fig"]
        out.append(f'tl.fromTo("#s{i}-card",{{y:44,scale:.975,opacity:0}},'
                   f'{{y:0,scale:1,opacity:1,duration:.75,ease:"power3.out"}},{s + .1:.2f});')
        for k, at in enumerate(sc["step_at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-step{k}",{{y:16,opacity:0}},'
                       f'{{y:0,opacity:1,duration:.45,ease:"power2.out"}},{at:.2f});')
        wa, wd = sc["wipe_at"], sc["wipe_dur"]  # beat-locked
        out.append(f'tl.fromTo("#s{i}-gray",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                   f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{wd},'
                   f'ease:"power2.inOut"}},{wa:.2f});')
        out.append(f'tl.fromTo("#s{i}-wipe",{{x:0,opacity:0}},'
                   f'{{opacity:.9,duration:.18,ease:"power1.out"}},{wa:.2f});')
        out.append(f'tl.to("#s{i}-wipe",{{x:{w - 4},duration:{wd},'
                   f'ease:"power2.inOut"}},{wa:.2f});')
        out.append(f'tl.to("#s{i}-wipe",{{opacity:0,duration:.22,ease:"power1.in"}},'
                   f'{wa + wd - .15:.2f});')
        out.append(f'tl.fromTo("#s{i}-caption",{{y:20,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},'
                   f'{sc["caption_at"]:.2f});')

    elif t == "cvd":
        w, wd = f["fig"], sc["wipe_dur"]
        out.append(f'tl.fromTo("#s{i}-card",{{y:44,scale:.975,opacity:0}},'
                   f'{{y:0,scale:1,opacity:1,duration:.75,ease:"power3.out"}},{s + .1:.2f});')
        for k, (_, _, _, at) in enumerate(sc["stages"], 1):
            # beat-grid; the grayscale stage is beat-locked to the 8.74s cue.
            out.append(f'tl.fromTo("#s{i}-w{k}",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                       f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{wd},'
                       f'ease:"power2.inOut"}},{at:.2f});')
            out.append(f'tl.to("#s{i}-step{k}",{{opacity:1,duration:.3,'
                       f'ease:"power1.out"}},{at:.2f});')
            out.append(f'tl.fromTo("#s{i}-wipe",{{x:0,opacity:0}},'
                       f'{{opacity:.9,duration:.14,ease:"power1.out"}},{at:.2f});')
            out.append(f'tl.to("#s{i}-wipe",{{x:{w - 4},duration:{wd},'
                       f'ease:"power2.inOut"}},{at:.2f});')
            out.append(f'tl.to("#s{i}-wipe",{{opacity:0,duration:.16,'
                       f'ease:"power1.in"}},{at + wd - .1:.2f});')
        out.append(f'tl.fromTo("#s{i}-caption",{{y:20,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},'
                   f'{sc["caption_at"]:.2f});')

    elif t == "grid":
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-t{k}",{{y:22,scale:.955,opacity:0}},'
                       f'{{y:0,scale:1,opacity:1,duration:.5,ease:"power3.out"}},{at:.2f});')

    elif t == "chips":
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-c{k}",{{y:14,scale:.94,opacity:0}},'
                       f'{{y:0,scale:1,opacity:1,duration:.42,ease:"back.out(1.3)"}},{at:.2f});')

    elif t == "panel":
        out.append(f'tl.fromTo("#s{i}-panel",{{y:34,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.7,ease:"power3.out"}},{s + .25:.2f});')
        for k, at in enumerate(sc["at"], 1):  # beat-grid
            out.append(f'tl.fromTo("#s{i}-r{k}",{{x:22,opacity:0}},'
                       f'{{x:0,opacity:1,duration:.5,ease:"power2.out"}},{at:.2f});')

    elif t == "shot":
        out.append(f'tl.fromTo("#s{i}-shot",{{y:48,scale:.97,opacity:0}},'
                   f'{{y:0,scale:1,opacity:1,duration:.8,ease:"power3.out"}},{sc["at"]:.2f});')
        if sc.get("scroll"):
            iw = f["shot"]
            ih = int(iw / sc["ratio"])
            reserve = int(f["eyebrow"] * 1.3 + f["body"] * 4.5 + 24)
            view = min(f["h"] - 2 * f["pad"] - reserve - 44, int(iw * f["view"]))
            travel = max(0, ih - view)
            begin = sc["at"] + 0.7
            span = round(sc["end"] - begin - 0.9, 2)
            if travel and span > 0.8:
                out.append(f'tl.fromTo("#s{i}-page",{{y:0}},{{y:{-travel},'
                           f'duration:{span},ease:"power1.inOut"}},{begin:.2f});')

    elif t == "outro":
        out.append(f'tl.fromTo("#logo",{{scale:.88,opacity:0}},'
                   f'{{scale:1,opacity:1,duration:.7,ease:"power3.out"}},{s + .2:.2f});')
        out.append(f'tl.fromTo("#mark",{{y:24,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power3.out"}},{s + .45:.2f});')
        out.append(f'tl.fromTo("#oline",{{y:18,opacity:0}},'
                   f'{{y:0,opacity:1,duration:.6,ease:"power2.out"}},{s + .75:.2f});')
        out.append(f'tl.fromTo("#ourl",{{opacity:0}},'
                   f'{{opacity:1,duration:.55,ease:"power1.out"}},{s + 1.05:.2f});')
    return out


SFX_FILES = {
    "drop": ("sfx/interface/drop_001.ogg", 0.11, 0.55),
    "wipe": ("sfx/impact/impactSoft_medium_001.ogg", 0.19, 0.50),
    "tile": ("sfx/interface/drop_001.ogg", 0.11, 0.50),
    "bell": ("sfx/impact/impactBell_heavy_000.ogg", 1.48, 0.62),
}


def vo_duration(name: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(ASSETS / f"vo-{name}.wav")],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 3)


def emit(film_key: str, spec: dict, fmt_key: str) -> pathlib.Path:
    f = FORMATS[fmt_key]
    scenes, dur = spec["scenes"], spec["duration"]

    body = "\n".join(
        f'<section id="s{i}" class="clip" data-start="{sc["start"]}" '
        f'data-duration="{sc["dur"]}" data-track-index="{i}">'
        f'<div class="inner" id="s{i}-inner">{scene_html(sc, f, i)}</div></section>'
        for i, sc in enumerate(scenes, 1))

    rails_start = scenes[0]["end"]
    rails = (f'<div id="rails" class="clip" data-start="{rails_start}" '
             f'data-duration="{round(dur - rails_start, 2)}" data-track-index="90">'
             f'<div class="inner" id="rails-inner">'
             f'<p id="rail-l">Sprezzature</p><p id="rail-r">sprezzature.ai</p>'
             f'<div id="rail-line"></div></div></div>')

    # Audio. Voice on its own lane; each overlapping SFX gets its own index.
    audio = [f'<audio id="bgm" data-start="0" data-duration="{dur}" '
             f'data-track-index="10" data-volume="1" src="assets/music/{MUSIC}"></audio>']
    duck = []
    for name, at in spec["vo"]:
        d = vo_duration(name)
        audio.append(f'<audio id="vo-{name}" data-start="{at}" data-duration="{d}" '
                     f'data-track-index="11" data-volume="1" '
                     f'src="assets/vo-{name}.wav"></audio>')
        duck.append((at, at + d))
    for n, (kind, at) in enumerate(spec["sfx"]):
        src, sd, vol = SFX_FILES[kind]
        audio.append(f'<audio id="sfx-{n}" data-start="{at}" data-duration="{sd}" '
                     f'data-track-index="{12 + n}" data-volume="{vol}" '
                     f'src="assets/{src}"></audio>')

    # Music: in, duck across the whole narrated stretch, lift once the voice is
    # done, fade out on the held frame.
    first_vo, last_vo = duck[0][0], duck[-1][1]
    js = ['tl.fromTo("#bgm",{volume:0},{volume:.3,duration:.8,ease:"power1.out"},0);',
          f'tl.to("#bgm",{{volume:.13,duration:.35,ease:"power1.inOut"}},{max(0.85, first_vo - .35):.2f});',
          f'tl.to("#bgm",{{volume:.27,duration:.6,ease:"power1.inOut"}},{last_vo + .15:.2f});',
          f'tl.to("#bgm",{{volume:0,duration:.9,ease:"power1.in"}},{dur - 1.0:.2f});']

    # Crossfades: clip windows overlap 0.6s and the incoming scene, later in the
    # DOM, fades up over the outgoing one.
    for i, sc in enumerate(scenes, 1):
        if i == 1:
            js.append(f'tl.to("#s1-inner",{{opacity:0,duration:.6,ease:"power1.inOut"}},'
                      f'{sc["end"]:.2f});')
        else:
            js.append(f'tl.fromTo("#s{i}-inner",{{opacity:0}},'
                      f'{{opacity:1,duration:.6,ease:"power1.inOut"}},{sc["start"]:.2f});')
            if i < len(scenes):
                js.append(f'tl.to("#s{i}-inner",{{opacity:0,duration:.6,'
                          f'ease:"power1.inOut"}},{sc["end"]:.2f});')
        js += scene_js(sc, i, f)

    js.append(f'tl.fromTo("#rails-inner",{{opacity:0}},{{opacity:1,duration:.6,'
              f'ease:"power1.inOut"}},{rails_start:.2f});')
    js.append(f'tl.fromTo("#rail-line",{{scaleX:0}},{{scaleX:1,duration:1.1,'
              f'ease:"expo.out"}},{rails_start + .2:.2f});')

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={f['w']}, height={f['h']}" />
<title>{esc(film_key)} — {fmt_key}</title>
<script src="assets/vendor/gsap.min.js"></script>
<script src="assets/music/audio-data.js"></script>
<style>
/* The project's three-Roboto rule, self-hosted, so the render stays offline. */
@font-face {{ font-family:"Roboto"; src:url("assets/fonts/Roboto-Variable.woff2") format("woff2");
  font-weight:100 900; font-style:normal; font-display:block; }}
@font-face {{ font-family:"Roboto Serif"; src:url("assets/fonts/Roboto-Serif-Variable.woff2") format("woff2");
  font-weight:100 900; font-style:normal; font-display:block; }}
@font-face {{ font-family:"Roboto Mono"; src:url("assets/fonts/Roboto-Mono-Variable.woff2") format("woff2");
  font-weight:100 700; font-style:normal; font-display:block; }}
{css(f)}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}"
     data-width="{f['w']}" data-height="{f['h']}" data-fps="30">
  <div class="bg"><div class="bg-grid"></div><div class="bg-wash" id="wash"></div></div>
{body}
{rails}
{chr(10).join(audio)}
</div>
<script>
(function () {{
  var tl = gsap.timeline({{ paused: true }});
{chr(10).join('  ' + line for line in js)}

  /* Audio-reactive: pre-extracted bands let the wash and the card breathe with
     the bed. Nothing here touches type size or position. */
  var AD = window.AUDIO_DATA;
  if (AD && AD.frames && AD.frames.length) {{
    var wash = document.getElementById("wash");
    var total = Math.min(AD.totalFrames, Math.floor({dur} * AD.fps));
    var cards = document.querySelectorAll(".card");
    var mark = document.getElementById("mark");
    var apply = function (fr) {{
      return function () {{
        var rms = fr.rms, bass = fr.b[0], treble = fr.b[2];
        wash.style.opacity = (0.72 + rms * 0.45).toFixed(3);
        wash.style.transform = "scale(" + (1 + bass * 0.05).toFixed(4) + ")";
        var sh = "0 " + (22 + bass * 16).toFixed(1) + "px " + (56 + bass * 26).toFixed(1) +
          "px rgba(0,60,93," + (0.12 + bass * 0.07).toFixed(3) + ")";
        for (var c = 0; c < cards.length; c++) {{ cards[c].style.boxShadow = sh; }}
        if (mark) {{
          mark.style.textShadow = "0 0 " + (10 + treble * 26).toFixed(1) +
            "px rgba(0,114,178," + (0.05 + treble * 0.16).toFixed(3) + ")";
        }}
      }};
    }};
    for (var fr = 0; fr < total; fr++) {{ tl.call(apply(AD.frames[fr]), [], fr / AD.fps); }}
  }}

  window.__timelines["main"] = tl;
  tl.seek(0);
}})();
</script>
</body>
</html>
"""
    d = FILMS_DIR / f"{film_key}-{fmt_key}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html, encoding="utf-8")
    (d / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components",
                  "assets": "assets"},
        "media": {"autoProxy": True},
    }, indent=2) + "\n", encoding="utf-8")
    (d / "package.json").write_text(json.dumps({
        "name": f"{film_key}-{fmt_key}", "private": True, "type": "module",
        "scripts": {"check": "npx --yes hyperframes@0.8.46 check",
                    "render": "npx --yes hyperframes@0.8.46 render"},
    }, indent=2) + "\n", encoding="utf-8")
    link = d / "assets"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to("../../_assets")
    return d


def main() -> None:
    if FILMS_DIR.exists():
        shutil.rmtree(FILMS_DIR)
    built = [emit(k, s, fmt) for k, s in FILMS.items() for fmt in FORMATS]
    for p in built:
        print(p.relative_to(ROOT))
    print(f"{len(built)} projects")


if __name__ == "__main__":
    main()
