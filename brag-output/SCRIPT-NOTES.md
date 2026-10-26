# Notes for the film scripts

Read 2026-10-26, from the hub and the nine brick repos. One film per brick plus
the suite film; target ~60s each. Everything below is sourced — a line that
cannot be traced to a file does not go on screen.

The only thing kept from the old cuts is the closing line:
**"Make it. Audit it. Then look at it."**

---

## sprezzature-colors

**The human problem, in the repo's own words:** a button with light-grey text
on white "reads fine" to most people and is unreadable to someone with low
vision, or on a phone in sunlight. A chart using red for down and green for up
is one bar to **about one man in twelve**, who has some form of colour-vision
deficiency.

**The know-how it encodes**
- WCAG 2.x contrast, including the **2.4-gamma relative-luminance transfer
  function** the standard specifies — not raw RGB.
- **OKLab / OKLCH**, designed by **Björn Ottosson (2020)** precisely so that
  "move lightness by X" matches how much brighter the colour actually looks.
- **Machado, Oliveira and Fernandes (2009, IEEE TVCG)**: they measured how each
  type of colour blindness transforms a colour and published the matrices.
  `CVD_MATRICES` is literally that table.

**Three tools:** contrast audit (with a fix that stays visually close), CVD
simulation on a real image, Tailwind palette export.

**The boast worth making:** pure standard library. No network, no model. The
contrast audit is cheap enough for a pre-commit hook.

---

## sprezzature-ux-laws

**30 laws documented** (`references/laws-of-ux.md`, Jon Yablonski's canonical
set from lawsofux.com and the O'Reilly book). **Eight are mechanically
detectable** and the auditor checks those:

| Law | What the auditor actually catches |
|---|---|
| Hick | too many choices at once — an over-long nav |
| Choice overload | a long option list with no grouping and no default |
| Miller | an unchunked digit run past ~7 — a phone number, a code |
| Jakob | a non-conventional pattern where a familiar one is expected |
| Fitts | a control with no 44-pixel hit area (`min-h-11`) |
| Aesthetic-Usability | an interactive element with no visible focus ring |
| Selective attention | real content styled like an advert |
| Tesler | irreducible complexity pushed onto the user |

**The honest line, and it is the repo's own:** "It does not judge whether a
screen answers the right question or whether a flow makes sense. That stays a
human call. It is a fast gate, not a substitute for design review."

---

## sprezzature-accessibility

**Twenty rules, decidable from the source — no browser, no DOM.** The vivid
ones, each with its WCAG reference:

- `media-autoplay-sound` — unmuted autoplay **masks a screen reader** (1.4.2)
- `video-missing-captions` — audio with no caption track (1.2.2)
- `media-missing-controls` — nothing to operate from a keyboard (2.1.1)
- `div-onclick` — a clickable div with no role and no tabindex
- `tabindex-positive` — `tabindex >= 1` breaks DOM order
- `heading-skip`, `input-missing-label`, `dialog-missing-close`,
  `color-only-state`, `motion-no-reduce-guard`

**Six of the twenty auto-fix**: lang detection and insertion, redundant aria
removal, tabindex demotion, aria-hidden strip, motion-reduce guard, tight
tracking.

**And the make side:** `text_spacing_preset` emits the comfortable-reading CSS
at the **WCAG 1.4.12** minimums — the same rule, pointed the other way.

**Stdlib only. Exit 1 on any finding.** Which is what makes it a pre-commit
gate rather than a report.

---

## sprezzature-figures

**167 chart types across 52 categories**, each `make_<kind>.py` self-contained
and writing the SVG markup directly — no charting library underneath. The
category list is the film's best visual: Comparison, Composition,
Distribution, Flow, Geospatial, Hierarchy, KPI, Matrix, **Meteorology**
(windbarb, windrose), **Model evaluation** (ROC, calibration, confusion
matrix, survival-KM), Network, Regression, Signal, Text, 3-D.

**The deliverable is the SVG, not a picture of one** (PHILOSOPHY.md): every
one of the 167 carries an explicit width, height and matching `viewBox`, so
text stays selectable and lines stay crisp at any zoom. The PNG is an export
for places that cannot take vector art.

**The Ralph Eyeball Loop** is the half no reference supplies: render → look →
fix the source → again, with a local vision model doing the looking. It reads
a figure, a Mermaid diagram, a TikZ drawing or a whole HTML page.

---

## sprezzature-maps

**Three generators, and the distinction from a chart is the point:** a map
here draws real coastlines on a real projection. The schematic place-shaped
charts (hexmap, dot density, spike map, binned grid) stayed in figures.

- `choropleth` — a world map on **Equal Earth**, one fill per country, no-data
  falling back to neutral grey rather than to the bottom of the scale.
- `situation_map` — a layered who-controls-what plate that **auto-centres
  itself** on its region using a **Lambert conformal conic** projection, draws
  national outlines from a bundled **Natural Earth** base map, shades the sea
  floor near the coast, and carries a scale bar **in kilometres and miles at
  once**.
- `density` — and this is the line worth speaking: no coastline, no border, no
  graticule. Events are binned into a luminous field, so **"the land appears
  because events fell on it, and the sea stays dark because none did"** — the
  reader recognises the shape without being shown it.

**Provenance is documented, not implied:** `doc/CARTOGRAPHY.tex` carries the
data licences — Natural Earth, the USGS/NGA **GMTED2010** elevation set, the
Census Bureau's **TIGER/Line** boundaries, France's **IGN ADMIN EXPRESS**.


### The maps film shows situation plates and nothing else

Warith's call, and the contact sheet agrees: of the three kinds the package
draws, the situation plate is the one worth a minute of attention. No
choropleth, no density field in this film.

**Six of the nine in the gallery**, chosen by putting all nine side by side
and looking:

| Plate | Why it is in |
|---|---|
| `himalaya` | eight kilometres of relief, and the rivers that leave it |
| `iberia` | relief, the great rivers, and the Meseta |
| `switzerland` | terrain, lakes and rivers, with no thematic layer at all |
| `western-europe` | the physical base the thematic maps are drawn on |
| `ukraine` | areas of control, wide enough to read at speed |
| `syria` | four actors, and a legend that has to carry them |

**Left out, with the reason:** `drc` is a 1300x2227 portrait plate that shrinks
to nothing in a landscape frame; `libya` reads flat beside the others; `sudan`
is good but says what `ukraine` already says better.

### Raising them to NYT standard, by looking

Ralph loop, agent mode, on the Ukraine plate. Three iterations, each one
finding what the previous had broken:

1. `legend_position: "right"` put the key in its own column and left **a
   quarter of the image white**. → `"top-right"`: the map fills the frame, but
   the subtitle ran under the card and cut mid-word.
2. → `"bottom-right"`: subtitle back, but the legend sat on Marioupol, the Sea
   of Azov and the land bridge — the corner the plate exists to show.
3. → `"top-right"` **with a deck written to fit beside it**. The quiet corner
   of this map is Russia and the Don; that is where a key belongs. The full
   provenance stays in the footer under the map, so nothing is lost by saying
   less in the deck.

The other five needed nothing: `syria` never set `legend_position`, so it
already took the inside default over empty desert, and the four reference
plates carry no legend at all.

**What still falls short of the NYT, and was left alone:** label tiering is
flatter than theirs (Kyiv is starred, but Kharkiv, Donetsk and Odesa all carry
the same weight), and the government-held green is desaturated enough to read
as terrain rather than as control. Both are generator-wide changes that would
touch every plate and every test that pins them; neither is a film blocker.

Four of the six are **reference plates** — no thematic layer, the geography
itself. Two carry areas of control, which is what the kind is for. Lead with
the beauty, close with the purpose.

---

## sprezzature-publish

**Nine tools, a document becoming a site.** `lint` (stdlib, milliseconds,
pre-commit shaped, `--fix` where there is one safe repair) · `html` ·
`icons` (one logo → favicon, app icons, PWA icons, and the `<head>` snippet
that references them) · `indexes` (`robots.txt`, `sitemap.xml`, **`llms.txt`,
`llms-full.txt`**, Atom, `humans.txt`) · `meta` (Open Graph, Twitter Card,
Schema.org JSON-LD, drafted locally) · `plain` (rewrite at a target reading
grade, **keeping the terms you name**) · `changelog` (a CHANGELOG becomes
dated posts and a feed) · `narrate` · **`readalong`**.

**The one to film is readalong:** it binds the narration to the page, so the
sentence being spoken is the sentence highlighted.

**And what it refuses to own:** the voices. Narration lives in
sprezzature-audio, invoked as a subprocess so its heavy imports never enter
this package's graph.

---

## sprezzature-audio

**One modality, read in both directions** — the repo's own framing. Captions
turn sound into timed text; narration turns text into timed sound, landing as
a WAV **plus a WebVTT, exactly like a transcript does**, which is what lets a
page follow the reading sentence by sentence.

**The models, named:** Whisper `large-v3-turbo` through whisper.cpp; NVIDIA
NeMo **Sortformer** for who-spoke-when (up to four speakers); NeMo
**TitaNet** to match a voice against a reference sample. Diarization lands as
**RTTM**, the format the speech-research world already uses.

**It audits its own output too:** `audit_captions` reports reading speed,
overlaps, line width and duration — a caption track can be present and still
be unreadable.

---

## sprezzature-cli-gui

A tool somebody will not type, wrapped in a page. **It reads the parser
object's own fields rather than guessing from printed text** — argparse,
Click, Typer — and falls back to parsing `--help` in a subprocess when no
parser object is reachable, which is how a Go or Rust CLI is covered.

`schema.py` is the normalised description every adapter produces, **so the
renderer never needs to know which framework it came from**.

---

## sprezzature-ui

The smallest brick, and deliberately so. Its own words: *"Its job is the
aesthetic judgement written in prose — the three-Roboto rule, the design
tokens, what an interface has to respect — plus the part of that judgement
which can be mechanised."*

**The mechanised part is i18n**, and the argument for it is the best cost
sentence in the suite: *"A hardcoded sentence in a template costs nothing on
the day it is written. It costs a week the day somebody needs a second
language"* — scattered through JavaScript literals, HTML attributes, and
prompt templates buried in Python.

Ships 9 components, 9 snippets, 12 font files, a starter page.

---

## The suite film

**The common ground, in one sentence:** design is know-how somebody already
wrote down, and these are the tools that run it — in both directions, to make
a thing and to audit it.

**The AI half, exactly:** one model. **Qwen3-VL 8B through Ollama** writes the
alt text, drafts the captions and critiques the figures in the Ralph loop's
offline mode — text and vision from a single model, with a test that keeps a
second one from slipping in (`docs/LLM_CHOICE.md`). **Nothing has to leave the
machine.**

**The engineering conviction worth one beat:** around sixty figure generators
repeated the same boilerplate; it moved into `_svg.py` and `_render.py` under a
strict rule — *only code that was identical moves, and the move is verified by
regenerating the figures and confirming the bytes did not change.*
**"Deduplication that would alter a single rendered pixel is rejected."**

**Five surfaces per brick:** library, command line, HTTP API, MCP tools, skill.
One implementation underneath.

---

## Staleness found while reading — to fix before the films quote anything

Three READMEs still describe the argparse front door removed on 2026-10-25:

- `sprezzature-ui/README.md` — "Two front doors over both: `make-ui <tool>`
  (argparse) and `sprezzature-ui <tool>` (click)"
- `sprezzature-publish/README.md` — the same sentence over its nine tools
- `sprezzature-figures/README.md` — architecture block calls `make_figure.py`
  the "argparse CLI" and `cli.py` the "Click entry point (optional, needs
  [cli] extra)"

The films must not repeat a claim the code no longer supports.
