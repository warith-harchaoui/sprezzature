# Approach: the ideas behind `sprezzature`

This page gathers the design convictions that run through the whole
`sprezzature-*` stack. Each one is something the code actually does; nothing
here is aspiration. If you want the *what* (the skills, the install), read
[`README.md`](README.md). This is the *why*.

French mirror: [`PHILOSOPHIE.md`](PHILOSOPHIE.md).

Acronyms are spelled out on first use: scalable vector graphics (SVG),
portable network graphics (PNG), color-vision deficiency (CVD),
cascading style sheets (CSS), vision-language model (VLM).

---

## The figure is an SVG, not a picture of one

A `sprezzature-figures` figure ships as carefully authored scalable vector graphics
(SVG). The generators in `sprezzature-figures/scripts/make_*.py` write the SVG
markup directly; the shared `svg_open` helper in `_svg.py` opens every
document with an explicit width and height and a matching `viewBox`, so the
graphic scales fluidly to any size without a single blurry pixel. All 91
example figures carry that `viewBox`. Vega-Lite is a convenient way to
*describe* many of these charts, but the Vega JavaScript Object Notation
(JSON) is not what you ship, and the portable network graphics (PNG) file
is only an export for places that can't take vector art. The deliverable is
the SVG: text stays selectable, lines stay crisp at any zoom, and the file
is small.

## Interactivity that composes instead of duplicating

The reference component `sprezzature-ui/assets/components/figure-fullscreen.html`
lays out how an interactive figure behaves. It starts from a measured fact
rather than a guess: how you embed an SVG decides what it can do.

| Embedding | Responsive | CSS `:hover` | Internal `<script>` | Fullscreen |
|---|---|---|---|---|
| `<img src=".svg">` | yes | no | no | no |
| `<object data=".svg">` | yes | yes | yes | yes |
| inline `<svg>` in HTML | yes | yes | yes | yes |

So the baseline that has to survive every embedding, responsiveness and a
plain cascading style sheets (CSS) hover tooltip, lives *inside* the SVG,
next to a small internal fullscreen button. That is the default: a single
self-contained `.svg` that works opened on its own, served through
`<object>`, or inlined.

A dashboard often wants more: one cursor-following tooltip shared across
cards, a fullscreen button in the card chrome, an iOS fallback. That is an
optional page-level module. The two layers do not fight, because the
boundary is one selector. A figure inside a `[data-fs-target]` card is
externally managed, so its internal button and CSS tooltip stand down: no
two buttons, no two tooltips. You author one SVG; the context picks the
mode. (A detail worth stating because it is easy to get wrong: in
fullscreen the browser paints only the top-layer element, so a tooltip
parked on `<body>` disappears; the external module re-homes the tooltip
into the fullscreen element so it stays visible.)

## Look at the figure before you ship it: the Ralph Eyeball Loop

You can proofread a sentence by reading it back. You cannot do that with a
chart: whether it is right lives in the pixels, not the source. So
`sprezzature-figures/scripts/ralph_eyeball_loop.py` renders any visual-from-code
artifact to a PNG with a deterministic tool (a Vega chart, a TikZ figure,
a Mermaid diagram, a whole web page, a carefully drawn SVG), and then something
actually looks at it. By default that is the agent itself, the same one
that wrote the code; fully offline, an optional local VLM does the
critique. It catches what a code check never will: a label clipped at the
edge, a legend slid off the canvas, two nodes overlapping, colors that
vanish for a colorblind reader. Fix the source, render again, look again.
Data visualization is just one use; the same loop reviews UI screens and
diagrams too.

## Accessible and color-vision-deficiency-safe by construction

Color is never the only channel that carries meaning, so a figure still
reads in grayscale or for a colorblind viewer. Diverging data uses a
blue-to-red ramp, which survives red-green color-vision deficiency (CVD).
These are not claims taken on faith: `sprezzature-colors/scripts/simulate_cvd.py`
re-renders any image as a protanope, deuteranope, or tritanope sees it
(Machado et al. 2009 matrices) so you can check, and `sprezzature-accessibility`
lints the static HyperText Markup Language (HTML) for the accessibility
mistakes a parser can catch: missing alt text, unlabelled inputs,
color-only state, and more.

The default is built for the hardest case, a viewer who sees no color at
all, because a design that survives grayscale survives every color-vision
deficiency. Stronger and deficiency-specific levels can sit on top for
people who want them, never as the price of entry. The reasoning and the
sources are in `sprezzature-colors/references/accessibility-levels.md`.

## Runs on your machine, one model, no software-as-a-service

The artificial-intelligence work runs on your machine. A single
vision-language model, Qwen3-VL 8B served through Ollama, writes the alt
text, drafts the captions, and critiques the figures in the Ralph loop's
offline mode. One model for text and vision, and a test that keeps a second
one from slipping in. The reasoning and the sources are in
[`docs/LLM_CHOICE.md`](docs/LLM_CHOICE.md). Nothing has to leave the
machine.

## Shared code, byte-for-byte unchanged output

Around sixty figure generators once repeated the same boilerplate: the SVG
root tag, the write-and-report tail, a handful of geometry helpers. That is
now factored into `_svg.py` and `_render.py`. The rule for every such
refactor is strict: only code that was *identical* across generators moves,
and the move is verified by regenerating the figures and confirming the
bytes did not change. Deduplication that would alter a single rendered pixel
is rejected. The helpers stay stdlib-only so they import everywhere the
generators already run.

## Bilingual prose, written by hand in both languages

The documentation and the site exist in English and French, kept in strict
parity: the same claims in the same order. Each side is written natively in
its own language, so neither reads like a translation of the other.
Acronyms are spelled out on first use. The prose aims to read like a person
wrote it, with no hollow hype and no tics. This document is meant to be its
own example.
