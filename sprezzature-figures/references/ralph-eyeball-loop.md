# The Ralph Eyeball Loop: protocol, assessment format, per-surface critique

You can proofread a sentence by reading it back. You cannot proofread a
chart that way: code that draws a figure can be entirely correct and the
figure can still be wrong, a label sliding off the edge, a legend sitting
on top of the data, two points landing exactly on each other, a
red-and-green palette collapsing into one muddy color for a reader who
cannot tell them apart. None of that is visible in the source. It is only
visible once you look at the rendered result. The Ralph Eyeball Loop is
the discipline of actually looking: render the artifact, study the image,
fix the source, render again, until nothing is left to catch.

The name borrows from an older habit in software: "render, look, fix the
code, repeat." The loop implemented here is that same cycle applied to
anything that turns code into a picture, not only figures.

## Scope: one loop, five surfaces

`ralph_eyeball_loop.py` is repo-wide, not data-viz-specific. Data
visualization is one surface it happens to cover, not the reason it
exists. The kind is auto-detected from the source file's suffix:

| Surface | Suffixes | Renderer |
|---|---|---|
| Web page / GUI screen | `.html`, `.htm` | Headless Chrome, screenshotted directly by `ralph_eyeball_loop.py` |
| Vega-Lite / Vega spec | `.vl.json`, `.vg.json`, `.json` | `vl-convert-python`, via `render_diagram.py` |
| TikZ figure | `.tex`, `.tikz` | `tectonic` (preferred) or `pdflatex` + `pdftoppm`, via `render_diagram.py` |
| Mermaid diagram | `.mmd`, `.mermaid` | `mmdc` (mermaid-cli), via `render_diagram.py` |
| Hand-authored SVG | `.svg` | `rsvg-convert` (preferred) or ImageMagick, via `render_diagram.py` |

For the four diagram surfaces, `ralph_eyeball_loop.py` does not render
anything itself, it shells out to the sibling script `render_diagram.py`
in the same directory, passing through `--background` and `--dark`. Only
the HTML path is rendered in-process, via a direct headless-Chrome
subprocess call. Both renderers theme their output from the same
canonical `sprezzature-colors` palette by default: TikZ gets an injected
`\definecolor` preamble, Mermaid an injected `%%{init}%%` theme block,
Vega keeps whatever `config` the spec itself declares (the renderer never
authors Vega, only rasterizes a spec you already wrote).

## The loop, in four steps

1. **Render.** Turn the source into a PNG with a deterministic tool. No
   model, no guessing at this stage: the same source always produces the
   same image.
2. **Look.** Study the rendered PNG. Is the intended message the first
   thing the eye lands on? Is anything clipped, cramped, overlapping, or
   illegible at this size?
3. **Assess.** Write the critique into
   `.private/ralph-loop/assessment-<hash>.md`, a file gitignored by the
   repo's top-level `.gitignore` and never committed. Each re-run appends
   a new numbered iteration section rather than overwriting the last one,
   so the file accumulates a history of what was seen and fixed.
4. **Edit and repeat.** Change the source, never the PNG, the PNG is only
   ever the evidence you looked at, not the artifact you ship. Re-run the
   command; it renders again, appends a new iteration, and you look again.
   Stop when the Verdict checkbox in the latest iteration is checked
   "Satisfied."

## Two modes

**Agent mode** (the default, no flag needed) hands the looking to
whichever coding agent is already running the loop, Claude Code or
OpenCode reading the rendered PNG with its own vision and filling in the
assessment template by hand. No Ollama call happens in this mode; the
script writes a blank template with each critique dimension as a heading
and stops, expecting the agent to fill it in with the `Read` tool before
moving on.

**Local mode** (`--local`) is the fully offline alternative: after
rendering, the script calls a vision-language model, `qwen3-vl:8b`, and
uses its answer to pre-fill the same template automatically. This is not
a second, separate integration, every LLM or VLM call anywhere in the
`sprezzature-*` suite routes through one function,
`best_engine_ai_helper.llm.chat`, which resolves the actual backend
(Ollama by default, OpenAI-compatible or LangChain opt-in via an
environment variable) and shapes the request. `ralph_eyeball_loop.py`
itself never opens a connection to Ollama directly; it only builds the
prompt and hands over the PNG bytes. Local mode needs the model pulled
once (`ollama pull qwen3-vl:8b`) and Ollama running (`ollama serve`); the
auto-generated critique is meant to be reviewed and edited, not accepted
blindly, the template itself says so in a heading comment.

## The assessment file

Keyed by an 8-character MD5 hash of the *resolved absolute path* of the
source file, so the same source always maps to the same assessment slot
across runs, even from a different working directory:
`.private/ralph-loop/assessment-<hash>.md`, with rendered PNGs living
alongside it at `.private/ralph-loop/<stem>-<hash>.png` (or wherever
`--out` points). The first run writes a header (source path, surface
kind, hash, start timestamp) followed by iteration 1; every later run on
the same source appends the next numbered iteration, found by counting
existing `## Iteration ` headings in the file. Both the assessment
Markdown and the rendered PNGs are gitignored and never committed, they
are working notes for the loop, not shipped documentation.

Each iteration section asks for the same eight critique dimensions, in
agent mode as blank prompts to fill in, in local mode pre-filled by the
vision model:

- **Layout.** Overall composition, alignment, use of white space.
- **Contrast.** Legibility of text and marks against the background.
- **Hierarchy.** Does the eye land on the most important element first?
- **Spacing.** Padding, margins, gaps between elements, too tight, too
  loose, or inconsistent.
- **Accessibility.** Color-vision-deficiency safety, contrast ratios,
  missing alt text or ARIA concerns.
- **Colors.** Purposeful versus decorative; on-brand; any hue that
  clashes, misleads, or is CVD-unsafe.
- **OCR / text readability.** Can every label, tick value, axis title, and
  caption actually be read at the size it renders?
- **Overall verdict.** What are the most important changes needed before
  shipping, in one or two sentences?

HTML sources get two additional dimensions appended: **first-fold
content** (is the primary message or call-to-action visible without
scrolling at this viewport?) and **responsiveness** (does the layout look
intentional at this viewport, or is there overflow or clipping?).

Below the critique, every iteration has a **Planned changes** list (what
you are about to edit) and a **Verdict** checkbox pair, "Satisfied, stop
the loop" or "Not yet, edit the source and re-run." The loop is meant to
stop on the first box, not on a fixed iteration count.

## A note on the HTML viewport floor

Headless Chrome refuses to lay out a window narrower than roughly 500 CSS
pixels on macOS and Linux; asking for a narrower `--width` does not
produce a true narrow-phone render, it silently lays the page out around
485px and then crops the screenshot to the requested width, which looks
exactly like a horizontal-overflow bug that is not actually there. The
script clamps any requested width under that floor up to ~500px and warns
about it on stderr rather than producing that misleading crop silently.
For a genuinely accurate 375px phone viewport, use a real browser's
device-mode tools instead, the flag-only headless path cannot emulate it.

## Not to be confused with

`sprezzature_figures.studio.ralph`, a different module in the same
package, is the FigurePlan-editing engine behind Sprezzature Studio's
in-app copilot. It follows the same render-critique-edit idea but applies
it to a structured, in-app `FigurePlan` object, not to an arbitrary file
on disk. `ralph_eyeball_loop.py`, documented here, is the general-purpose,
any-file version.

## Toolchain setup

`python -m sprezzature_figures_scripts.ralph_eyeball_loop --check-tools`
prints a table of which per-surface renderer is installed. `--install-tools`
auto-installs whatever is pip- or npm-installable (`vl-convert-python`,
`@mermaid-js/mermaid-cli`) and prints manual install instructions for the
rest (Chrome, `tectonic`, `librsvg`, Ollama plus the vision model pull),
since those are not Python or Node packages.

## Usage

```bash
# Agent mode, desktop viewport (default 1440x900)
python -m sprezzature_figures_scripts.ralph_eyeball_loop web/index.html

# Agent mode, a different viewport
python -m sprezzature_figures_scripts.ralph_eyeball_loop web/index.html --width 375 --height 812

# Local mode, a Vega spec, transparent canvas
python -m sprezzature_figures_scripts.ralph_eyeball_loop fig.vl.json --bg transparent --local

# Local mode, a TikZ figure, dark canvas
python -m sprezzature_figures_scripts.ralph_eyeball_loop dag.tex --bg dark --dark --local

# Check the rendering toolchain
python -m sprezzature_figures_scripts.ralph_eyeball_loop --check-tools
```

## Why the loop is not scoped to data viz

Plenty of tools will screenshot a web page and lint it. The same
render-look-fix discipline is worth pointing at the harder cases people
usually ship without ever looking at the rendered result, because the
code ran and the file saved: statistical plots, causal DAGs, architecture
diagrams, maps. Whether any of them is actually right lives in the
pixels, not in whether the generating code raised an exception. Chart
generation is therefore one call site of this loop among several, not
its reason for existing, `SKILL.md`'s own two-mode table separates
**make** (produce the artifact) from **audit** (a static source check)
from this **loop** (look at the rendered result) as three distinct,
complementary passes, each catching what the other two let through.
