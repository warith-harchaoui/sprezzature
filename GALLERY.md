# Gallery

Sites and tools shipped with the `sprezzature-*` skill suite. Each entry is
a real, public surface, not a mock or a screenshot of the demo
component library. Light and dark variants are captured headlessly so
the dark-mode peer rule is visibly enforced.

Markdown-based by design: every entry lives in this file, every
screenshot lives under `assets/gallery/<slug>/`, every link points to
the live URL. No content management system (CMS), no separate showcase site, no build step.

To submit a new entry, see [Adding to the gallery](#adding-to-the-gallery)
at the bottom of this file.



## [md2star — Markdown → branded `.docx` / `.pptx` / `.pdf`](https://github.com/warith-harchaoui/md2star)

<img src="assets/gallery/md2star/logo.png" alt="md2star logo">

> *Convert Markdown into branded `.docx`, `.pptx`, and `.pdf`, end to end.*

A cross-platform command-line interface (CLI) + local web graphical user interface (GUI) that wraps **Pandoc** with a
curated styling layer: a single `.md` file becomes a polished Office
document. The CLI (`md2docx`, `md2pptx`, `md2pdf`) does the
non-interactive case; the live editor shown below is the
**Overleaf-style split pane** (Markdown source on the left, Portable Document Format (PDF)
preview on the right), debounced 500 ms after typing with `⌘ Enter` /
`Ctrl Enter` to force, `⌘ S` to download. The render pipeline is the
same one the CLI uses: `md2docx` produces the .docx, headless
LibreOffice (`soffice --convert-to pdf`) renders the PDF, then
**pdf.js paints each page into a `<canvas>`**, so the preview shows
up identically in real Chrome/Firefox/Safari *and* in headless Chrome
(the previous `<iframe src=blob:pdf>` approach silently broke under
headless because the browser PDF viewer plugin is absent there).

The split adds a **draggable divider** with keyboard resize
(`←` / `→` on the focused separator, ratio persisted to
`localStorage`), a **cycling theme toggle** (`light → dark → auto`,
also selectable via `?theme=…` web-address (URL) param; how the gallery captures
below were shot headlessly), and a **Download PDF** button (and
Markdown source autosave) so the editor state survives a reload.
A header **Word document (DOCX) / PowerPoint (PPTX) toggle** switches the output format on the
fly; each format keeps its own autosave buffer, and on first launch
the editor loads the canonical example bundled with the CLI:
`md2star/data/example.md` (Musk's five-step engineering algorithm)
for DOCX, `md2star/data/example_pptx.md` (Guy Kawasaki's 10/20/30
pitch-deck template) for PPTX, via a `GET /example?kind=…`
endpoint, so the very first render of either mode exercises the
pipeline against real content.

Why this entry matters for the gallery: md2star is the concrete
**CLI → GUI** target the `sprezzature-cli-gui` skill was designed for:
real CLI surface, real local web GUI, dark-mode peer on every panel,
no framework runtime. The backend is stdlib-only (Python's
`http.server`); the sprezzature end is a single vanilla ECMAScript (ES) module,
Tailwind Play CDN, and pdf.js from jsDelivr. The emitted HTML passes
both `sprezzature-ux-laws` and `sprezzature-accessibility` audits with zero
findings. The Tauri shell that will wrap it as a desktop application
is on the [roadmap](CHANGELOG.md#roadmap); the local-web GUI shown
below is what's live today.

*DOCX mode — Musk's five-step engineering algorithm rendered live:*

| Light | Dark |
|---|---|
| ![md2star DOCX — light](assets/gallery/md2star/light.png) | ![md2star DOCX — dark](assets/gallery/md2star/dark.png) |

*PPTX mode — Kawasaki's 10/20/30 pitch deck rendered live:*

| Light | Dark |
|---|---|
| ![md2star PPTX — light](assets/gallery/md2star/pptx-light.png) | ![md2star PPTX — dark](assets/gallery/md2star/pptx-dark.png) |

**Author:** [Warith Harchaoui](https://linkedin.com/in/warith-harchaoui)  ·  **Stack:** Python stdlib HyperText Transfer Protocol (HTTP) server + vanilla JavaScript (JS) + Tailwind + pdf.js + `md2docx` / `md2pptx` + headless LibreOffice



## [roitelet — local-first lab for large-language-model (LLM) / retrieval-augmented-generation (RAG) / agentic systems](https://github.com/warith-harchaoui/roitelet)

<img src="assets/gallery/roitelet/logo.png" alt="roitelet logo">

> *Several artificial-intelligence (AI) models answer your question at the same time, and a local model picks the best parts of each answer for you.*

A local-first workbench for designing and comparing LLM, RAG, and
agentic setups before they become client architectures. The chat user-interface (UI)
fans one prompt out to several models at once, then a local Ollama
"judge" synthesizes a single answer; slash-commands (`/image`,
`/personal`, `/help`) switch modes, and a companion Markdown editor
handles longer drafts. It runs entirely on the machine, bound to
`127.0.0.1` by default, and is used at deraison.ai to prototype
architectures with clients.

Why it earns its place: one **Web Content Accessibility Guidelines (WCAG)-tuned semantic token set** (surface /
label tiers, each with a `-dark` peer) is shared across every surface,
so the `dark:` peer rule holds on the chat pane, the sidebar, and the
editor alike, no framework runtime, vanilla ES modules, Tailwind just-in-time compilation (JIT),
self-hosted Roboto. Captures show the fresh-install empty state.

| Light | Dark |
|---|---|
| ![roitelet — light](assets/gallery/roitelet/light.png) | ![roitelet — dark](assets/gallery/roitelet/dark.png) |

**Author:** [Warith Harchaoui](https://linkedin.com/in/warith-harchaoui)  ·  **Stack:** Python (FastAPI + uvicorn) + vanilla JS (no build, Tailwind JIT) + self-hosted Roboto + local Ollama



## [intentions — Déraison Assurances intent router](https://github.com/warith-harchaoui/intentions)

<img src="assets/gallery/intentions/logo.png" alt="intentions logo">

> *Route a caller's request to the right department by comparing three intent engines side by side: term frequency-inverse document frequency (TF-IDF), Bidirectional Encoder Representations from Transformers (BERT), and a local LLM.*

A teaching demo for intent detection: the same request runs through
TF-IDF (instant, offline), BERT embeddings (semantic), and a local LLM
(Ollama, zero-shot with strict JSON), shown with confidence bars and
latencies so the trade-offs are visible. Intents live in Markdown:
one `# h1` per intent in `knowledge_base/`, so a domain expert adds
one without touching code.

Why it earns its place: the sprezzature cites the sprezzature-ui house style in its
own source comments (`web/app.js`: "règle sprezzature-ui n°1"): vanilla ES
modules, vendored Tailwind for an offline page, three-Roboto, and a
`dark:` peer on every surface (dark capture shows the live LLM badge and
the 21-intent knowledge base).

| Light | Dark |
|---|---|
| ![intentions — light](assets/gallery/intentions/light.png) | ![intentions — dark](assets/gallery/intentions/dark.png) |

**Author:** [Warith Harchaoui](https://linkedin.com/in/warith-harchaoui)  ·  **Stack:** Python (FastAPI) + vanilla JS + Tailwind (vendored) + scikit-learn / sentence-transformers / local Ollama



## [sql — Text2SQL teaching demo](https://github.com/warith-harchaoui/sql)

<img src="assets/gallery/sql/logo.png" alt="sql logo">

> *French natural-language questions become Structured Query Language (SQL) through three approaches: raw QwenCoder, LangChain, and Vanna RAG, 100% local via Ollama.*

A side-by-side text-to-SQL demo over a synthetic hospital database
(30 tables, fictional data). The same question is answered by three
approaches; the generated SQL is shown, run read-only (`mode=ro`,
single `SELECT`), and, when a chart fits, a local Gemma model picks a
visualization that is rendered as **Vega-Lite** (generated code is
never executed).

Why it earns its place: the sprezzature cites the sprezzature-ui house style in its
source comments and vendors Tailwind for a fully local page; the
`sprezzature-figures` philosophy shows up literally: the model chooses the
chart, the page renders it as Vega-Lite. Both color schemes carry the
full `dark:` peer set.

| Light | Dark |
|---|---|
| ![sql — light](assets/gallery/sql/light.png) | ![sql — dark](assets/gallery/sql/dark.png) |

**Author:** [Warith Harchaoui](https://linkedin.com/in/warith-harchaoui)  ·  **Stack:** Python (FastAPI) + vanilla JS + Tailwind (vendored) + Vega-Lite + local Ollama (qwen2.5-coder / Gemma) + SQLite



## [Standpoint — a comparison table becomes a 2-D positioning map](https://github.com/warith-harchaoui/standingpoint)

<img src="assets/gallery/standingpoint/logo.png" alt="Standpoint logo">

> *Know where each option actually stands: feed a ratings table, get a positioning map, a written analysis, and every coordinate.*

A local-first tool that reads an ordinary comparison table (options as
rows, criteria as columns, numbers in the cells) and returns a 2-D
positioning map, a plain-language analysis, and a settings file listing
every coordinate. The method is ordinary Principal Component Analysis
(PCA), the same maths behind decades of perceptual maps; what Standpoint
adds is the hand-work around it: it orients the map on a reference option,
names each axis at both ends in plain words drawn from your own column
headers, and colours and labels every point. There is a one-command
command-line interface (CLI) for scripting, and a local web GUI
(`standpoint-gui`, a working proof-of-concept) for people who would rather
type a table and press a button.

Why it earns its place: it is a four-skill showcase in one small app.
**`sprezzature-figures`**: the quadrant is a house-style Vega-Lite chart, emitted
as Portable Network Graphics (PNG), Scalable Vector Graphics (SVG), and the
raw Vega-Lite JavaScript Object Notation (JSON) spec, and rendered live in
the browser with `vega-embed`. **`sprezzature-colors`**: the "Good Colors"
palette is reserved for *data only* (the dots on the map and the role-tinted
option names in the analysis), while the chrome (buttons, headings, grid)
stays neutral slate and ink, so a colour in the app always means "data",
never decoration. **`sprezzature-ui`**: one HTML page, vanilla ECMAScript modules,
Tailwind with no build step, self-hosted Roboto, a `dark:`-free but
carefully neutral surface. **`sprezzature-accessibility`**: visible keyboard focus
rings and labelled controls throughout. Standpoint is also the engine that
renders `sprezzature`'s own competitive-positioning map (the *Related work* panel
on the homepage, fed from `LANDSCAPE.md`), so the gallery and the tool point
back at each other. Everything runs on the machine through `vl-convert`; the
only optional reach-out is a `localhost` Ollama model that names the axes
and writes the analysis, and `--no-llm` drops even that.

*The local web app: edit or upload a table, generate the quadrant, read the
colour-coded analysis. The proof-of-concept is light-only today.*

![Standpoint local web GUI — table editor, live quadrant, colour-coded analysis](assets/gallery/standingpoint/gui.png)

*And the figure on its own, the `sprezzature-figures` deliverable: a dozen
programming languages rated on eight criteria, points on the house palette,
axes named from the columns:*

![Standpoint positioning map — programming languages on the house palette](assets/gallery/standingpoint/positioning-map.png)

**Author:** [Warith Harchaoui](https://linkedin.com/in/warith-harchaoui)  ·  **Stack:** Python (numpy + pandas + scikit-learn PCA) + Vega-Lite via `vl-convert` / `vega-embed` + FastAPI local GUI + vanilla JS + Tailwind + optional local Ollama
