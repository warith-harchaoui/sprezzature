# Sprezzature

[🇫🇷](LISEZMOI.md) · [🇬🇧](README.md)

<p align="center"><a href="https://harchaoui.org/warith/sprezzature/">
  <img src="https://harchaoui.org/warith/sprezzature/img/logo.png" alt="Sprezzature — nine Claude / OpenCode skills for vanilla JS + Tailwind frontends" width="240"></a>
</p>

[🌍 Documentation](https://harchaoui.org/warith/sprezzature/)

[💻 Examples](EXAMPLES.md)

## What this is

`sprezzature` is a set of **Claude / OpenCode skills** with a curated design system for a front-end stack. It covers colors, accessibility, the user interface (UI), user experience (UX), audio, vision, and the path from the command-line interface (CLI) to the graphical user interface (GUI).

The skills:

| Skill | When to install | Trigger phrases |
|---|---|---|
| **sprezzature-ui** | Always: it owns the stack rules and tokens. | "build a UI", "create a component", "design a page", "make a form / modal / button / nav", "dashboard", "audit this UI". |
| **sprezzature-cli-gui** | You wrap CLI tools in web user interfaces (UIs). | "wrap this CLI in a GUI", "build a UI for my Python script", "argparse to web UI". |
| **sprezzature-publish** | You ship docs sites, landing pages, meta-tags, favicons. | "turn these markdown files into a website", "meta tags", "favicons", "robots.txt", "sitemap", "llms.txt", "Atom feed", "plain language", "rewrite at grade 8". |
| **sprezzature-accessibility** | You need static HyperText Markup Language (HTML) accessibility (a11y) lint. | "a11y lint", "check this HTML for accessibility", "static a11y check", "WCAG-friendly lint", "a11y pre-commit". |
| **sprezzature-colors** | You audit contrast, simulate color blindness, or want a curated palette with perceptual lighten / darken. | "WCAG check", "contrast audit", "is my palette accessible", "colorblind preview", "deuteranope", "CVD", "OKLCH", "lighten this color". |
| **sprezzature-vision** | You draft World Wide Web Consortium (W3C)-compliant alt text from images locally (no SaaS). | "alt text", "alt text for this image", "describe this image", "draft alt", "image description", "img has no alt". |
| **sprezzature-audio** | You draft WebVTT / SubRip subtitle format (SRT) captions for `<video>` / `<audio>` locally (no SaaS). | "captions", "transcribe video", "transcribe audio", "WebVTT", "SRT", "subtitle file", "VTT", "caption track". |
| **sprezzature-ux-laws** | You want a shared vocabulary for UI decisions AND a pre-commit auditor that fails on detectable Laws-of-UX violations (Hick, Fitts, Miller, Jakob, Tesler, Aesthetic-Usability, Selective Attention, Doherty, Choice Overload). | "Laws of UX", "Hick / Fitts / Miller / Jakob / Tesler / Peak-End / Postel / Paradox of the Active User", "audit my nav / form / pricing page", "is this onboarding fighting the active user". |
| **sprezzature-figures** | You emit data-science figures (**Vega-Lite first**, hand-authored Scalable Vector Graphics (SVG) when the grammar can't reach, matplotlib only as a last resort), model-explainability plots (SHapley Additive exPlanations (SHAP) / Shapash / TimeSHAP / Local Interpretable Model-agnostic Explanations (LIME)), causal-effect estimates (DoWhy / EconML), TikZ / Mermaid diagrams, thematic maps, or areas-of-control situation maps for any region, refined through the **Ralph Eyeball Loop** (render → look → refine the source), with a pre-commit auditor for data-viz sins and colour-vision accessibility levels on every figure. | "make a figure", "prefer vega", "render this diagram", "mermaid diagram", "ralph eyeball loop", "no ascii art", "SHAP plot", "choropleth", "world map", "situation map", "areas of control", "DoWhy", "DAG", "audit this figure". |

The companion skills inherit the sprezzature-ui stack rules. Install only the
ones you need.

> **What prompt activates what?** See [`TRIGGERS.md`](TRIGGERS.md),
> generated from every `SKILL.md` description, lists every guaranteed
> trigger phrase against the skill it invokes.

## Getting started

Sprezzature is a set of skills for **Claude Code** or **OpenCode**. Install the ones you
want, then ask in plain English. The skill both **makes** the artifact and **audits** it.

```bash
# 1. Grab the latest release (set VERSION to the latest tag on the releases page)
VERSION=1.0.0
curl -L https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/sprezzature-skills-${VERSION}.tar.gz | tar xz

# 2. Copy the skills you want into your runtime
#    Claude Code → ~/.claude/skills   ·   OpenCode → ~/.opencode/skills
mkdir -p ~/.claude/skills
cp -r sprezzature-ui sprezzature-figures ~/.claude/skills/
```

Then, in a session, just ask:

- *"make this page accessible"* → **sprezzature-accessibility** lints the HTML and reports what to fix.
- *"make a figure of this CSV"* → **sprezzature-figures** draws it, then audits the chart.
- *"wrap this CLI in a GUI"* → **sprezzature-cli-gui** scaffolds a usable interface.

The full options (checksum verification, per-skill tarballs, the OpenCode + local-Ollama
zero-token path, upgrades, cleanup) are in [Install](#install) below.

## Docs & website

Human-facing guides live in [`docs/`](docs/), one landing page per skill
([UI](docs/UI.md) · [CLI](docs/CLI.md) · [publish](docs/PUBLISH.md) ·
[accessibility](docs/ACCESSIBILITY.md) · [colors](docs/COLORS.md) ·
[vision](docs/VISION.md) · [audio](docs/AUDIO.md) · [UX-laws](docs/UX-LAWS.md) ·
[figures & maps](docs/FIGURES.md)), each a thin pointer to that skill's
`SKILL.md`, its `references/`, and its `EXAMPLES.md` recipe (no duplication).
`SKILL.md` is the agent-facing spec; `docs/` is for humans.

For the *why* behind the stack (the design convictions that run through
every skill) see [`PHILOSOPHY.md`](PHILOSOPHY.md) (français :
[`PHILOSOPHIE.md`](PHILOSOPHIE.md)).

A deployable, multi-page static site, built with the `sprezzature-*` skills themselves
(sprezzature-ui house style, sprezzature-publish meta / favicons / sitemap / llms.txt,
sprezzature-colors palette, sprezzature-accessibility clean, a working 🌞/🌛 toggle), lives
in [`web/`](web/) and publishes to <https://harchaoui.org/warith/sprezzature/>. It has
a detail page per skill (make / audit / triggers / reference library) plus a
dedicated **figures gallery** rendering the whole `sprezzature-figures` catalog. The
gallery carries a **"See it for…" colour-vision viewer** that applies a live
colour-vision-deficiency simulation over the default figures (it simulates what
a colour-blind reader sees, it does not swap in a different figure), and a shared
**figure-fullscreen** control so any chart can open full-screen.

## Features — what's unusual for a Claude skill

Most Claude skills, including Anthropic's own `document-skills` (docx, pdf,
pptx, xlsx) and `example-skills` (artifacts, GIFs, MCP servers, design), are
**make-only**: the model produces an artifact. `sprezzature` is built differently, and
these traits set it apart:

- **Make *and* audit.** Every skill pairs generation with a **deterministic
  auditor** that exits non-zero on findings: six of them (`lint_a11y`,
  `audit_contrast`, `audit_laws_of_ux`, `audit_figure`, `audit_i18n`,
  `lint_markdown`). No official Anthropic skill ships a static lint gate as its
  purpose; here it's half the design.
- **Continuous integration (CI) / pre-commit gates, not vibes.** The auditors emit JavaScript Object Notation (JSON) + exit codes and
  ship as a [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) manifest; one
  `repo:` block and they block commits, whoever (or whatever) wrote the code.
- **AI that runs on your machine, zero SaaS egress.** Alt text runs on a local Ollama vision
  model; captions / diarization on a local whisper.cpp build. Nothing leaves the
  machine; the official skills are cloud-Claude-first.
- **Deterministic generators.** palette → Tailwind config, CLI → GUI, favicon /
  progressive-web-app (PWA) icon sets, sitemaps / feeds, and `locales/i18n.yaml`: reproducible
  artifacts a model would not derive byte-for-byte.
- **Hardened like a product, not a demo.** A real pytest suite + an AI-eval
  layer (DeepEval), CI across Python 3.10–3.12, checksum-verified per-skill
  release tarballs, and a spec-conformance validator, vs demonstration-grade
  examples.
- **Runtime-portable.** One skill folder serves both **Claude Code** and
  **OpenCode**; the AI paths target local models so a smaller OpenCode model
  follows a script instead of inventing one.
- **Unified i18n.** GUI strings *and* large-language-model (LLM) prompts live in a single
  `locales/i18n.yaml`, enforced on both the make and audit sides.

## Two modes — make and audit

Every sprezzature-* skill belongs to one or both halves of a single loop:
**make** the artifact, **audit** the artifact. The matrix tells you
when to load each skill and what is still on the roadmap.

| Skill | Make (generate) | Audit (gate) |
|---|---|---|
| **sprezzature-ui** | `references/` + `assets/components/`, generation playbook for HTML / Tailwind / dataviz | `scripts/validate.py`, `references/checklist.md`, `anti-patterns.md`, `ergonomics-criteria.md` |
| **sprezzature-cli-gui** | `scripts/cli_to_gui.py` (CLI → HTML emitter: argparse + Click + `--from-help` adapters) + `assets/examples/cli-gui-demo/` (worked scaffold) | Pair with `sprezzature-accessibility` + `sprezzature-ux-laws` on the emitted HTML (the emitter is its own customer; its output passes both gates with zero findings). |
| **sprezzature-publish** | `favicons.py`, `meta_from_ollama.py`, `site_indexes.py`, `plain_language.py`, `md_to_html.py`, `narrate.py` | `lint_markdown.py` |
| **sprezzature-accessibility** | _(none, see `sprezzature-ui` templates, `sprezzature-vision` for alt text, `sprezzature-audio` for captions)_ | `lint_a11y.py` (14 rules, stdlib only) |
| **sprezzature-colors** | `palette_to_tailwind.py` (comma-separated values (CSV) → tailwind.config.js), `accessibility_levels.py` (project the palette to `universal` / `high-contrast` / `monochrome` / a colour-vision-deficiency variant) | `audit_contrast.py`, `simulate_cvd.py` (mosaic + `--grayscale` luminance panel) |
| **sprezzature-vision** | `alt_from_ollama.py` (W3C alt text via local Ollama) | _(presence of `alt=` checked by `sprezzature-accessibility`)_ |
| **sprezzature-audio** | `captions_from_whisper.py` (WebVTT / SRT via local whisper.cpp) | _(presence of `<track>` checked by `sprezzature-accessibility`)_ |
| **sprezzature-ux-laws** | `references/laws-of-ux.md` (30-law Markdown playbook) | `audit_laws_of_ux.py` (Hick / Miller / Fitts / Jakob / Tesler / …) |
| **sprezzature-figures** | `make_figure.py` (CSV → Vega / matplotlib), `explain_model.py` (SHAP / Shapash / TimeSHAP / LIME dispatcher), `causal_estimate.py` (DoWhy loop + EconML backends + directed acyclic graph (DAG) render), `make_situation_map.py` (YAML config → layered areas-of-control plate for any region, SVG + PNG), `render_diagram.py` (auto-routed Vega / TikZ / Mermaid / SVG → Portable Network Graphics (PNG) / SVG / Portable Document Format (PDF) for the Ralph Eyeball Loop; rendered catalog in `docs/FIGURES.md`), `ralph_eyeball_loop.py` (render → look → refine any visual from code, agent mode or `--local` offline vision), `install_figures.py` (tier installer). Every generator takes an `--accessibility` level (`universal` default is byte-for-byte identical) | `audit_figure.py` (missing-axis-title, dual-y-axis, truncated-baseline, pie-3d, rainbow-palette, cvd-unsafe, missing-polarity, chartjunk, role-img-missing) |

The matrix is honest about gaps. Empty cells mark genuine roadmap
items, not omissions; see `.private/todo.md` (gitignored) for the
ranking.

## Who this is for

`sprezzature` is targeted at four concrete audiences. Each row is a stand-alone
pitch; if any one of them matches you, the matching skill earns its
keep on its own.

1. **Solo devs without a designer.** Opinionated defaults so you stop
   bikeshedding tokens; install `sprezzature-ui` and ship a usable UI from
   the first commit. Tailwind tokens, dark-mode peers, focus rings, hit
   areas, the lot.
2. **Pentesters writing internal dashboards.** Single-file HTML output
   that drops onto an internal box with no build chain. The a11y gates
   (`sprezzature-accessibility`) run in CI without a browser, so even one-off recon
   tooling stays legible to teammates with assistive tech.
3. **Data scientists wrapping CLIs.** Point `sprezzature-cli-gui` at your
   `--help` (argparse, Click, Typer, clap, commander, cobra all
   introspect cleanly) and get a working GUI mock-up. No Gradio
   runtime, no React lock-in.
4. **Bilingual docs sites (EN/FR by default; pair is configurable).**
   `sprezzature-publish` keeps typography and tone in lock-step across two
   languages, drafts meta tags + favicons + sitemap in one pass. Change
   the pair (EN/DE, EN/JA, EN/ES, …) by editing one config token; see
   each `SKILL.md` → "Changing the language pair".

This is **not** the right pick for:

- Consumer-app brand work that needs a custom visual identity.
- Marketing landing pages where a tool like Webflow or Framer is faster.
- Apps where the team has chosen React / Vue / Svelte: use shadcn / Headless UI / Mantine instead.
- Versioned docs sites with hundreds of pages: pick MkDocs Material, Hugo, or Astro.

For alternatives in every category, and how to decide whether `sprezzature`
is the right pick, see [LANDSCAPE.md](LANDSCAPE.md) (French:
[PAYSAGE.md](PAYSAGE.md)). It opens with a single **competitive-positioning**
table (projects × criteria, rated 1–5 ⭐️) that feeds
[standpoint](https://github.com/warith-harchaoui/standingpoint) to plot a 2-D map
of where `sprezzature` stands. For real sites
already shipped on the stack, see [GALLERY.md](GALLERY.md). For copy-paste
recipes per skill (with expected output), see [`EXAMPLES.md`](EXAMPLES.md).

## What the skills enforce

- Output uses vanilla JavaScript (JS) (ES modules, native `<dialog>`, custom elements when justified). No React, Vue, Svelte, Next.js, Nuxt, Angular, Solid.
- Output uses Tailwind utility classes with semantic tokens (`bg-brand-blue`, `text-label-primary`). No raw hex literals in markup.
- Output enforces the **three-Roboto rule**: exactly three downloaded webfonts, all from the Roboto super-family: **Roboto** (sans / UI / body), **Roboto Serif** (editorial / longform / prose-heavy landings), **Roboto Mono** (`<code>`, `<pre>`, terminal panels, log output). No other downloaded family is allowed (no Inter, no Montserrat, no IBM Plex, no JetBrains Mono). The three siblings share metrics and x-height by design; prose-heavy and code-heavy surfaces stay typographically coherent. All three are self-hosted (no Google Fonts content-delivery network (CDN) in production); Web Open Font Format 2 (WOFF2) + SIL Open Font License (OFL) live under `sprezzature-ui/assets/fonts/roboto/`, `…/roboto-serif/`, `…/roboto-mono/`.
- Output sets a `dark:` peer on every styled element, uses `<button>`/`<a>`/`<label>`/`<dialog>`/`<form>` first, exposes a visible focus ring, honors `prefers-reduced-motion` and meets a 44×44 px hit area.
- Output exposes a **🌞 Light / 🌚 Dark / 🌗 Auto toggle** (canonical placement: top-right of sticky header → footer far-right → fixed bottom-right anchor when there is no header). **Auto is the default** so a fresh visitor inherits their operating-system (OS) choice and is never surprised by a hard-coded scheme. Component: `sprezzature-ui/assets/components/theme-toggle.html`. Wiring: `sprezzature-ui/references/stack-vanilla-js.md` § "Theme switching".
- Color choices map to the palettes in `sprezzature-ui/references/color-psychology.md` (source: <https://harchaoui.org/warith/colors/>).
- Skill output is **prototype-grade single-file HTML** by default, suitable for demos, mockups, internal tools and small landing pages. The starter page uses the Tailwind Play CDN, which Tailwind itself warns is for prototyping only. For production sites at scale, run **Tailwind CLI** or **Vite + Tailwind** over the emitted HTML before shipping; the class names are stable, so the same files survive the swap. See `sprezzature-ui/references/stack-tailwind.md`.
- Bilingual-ready copy (EN/FR by default). The output language of the AI-backed scripts is **auto-detected from the input/context text** via `langdetect`: no configured default language; pass `--lang` to force one. For translatable UI strings and prompts, use one `locales/i18n.yaml` catalog (see `sprezzature-ui/scripts/i18n_make.py` and `sprezzature-publish/references/i18n.md`).
- **i18n lives in YAML (the YAML configuration format), never in JS.** Translatable strings, GUI labels **and** LLM prompts, belong in a single per-project catalog, **`locales/i18n.yaml`** (message id → per-locale text), loaded at runtime; never a translation dict baked into JavaScript, never a prompt inlined in Python. GUI strings and prompts share `locales/i18n.yaml` because they share one concern: *language*. Prompts already ship this way (`prompts/*.yaml`, loaded via `_prompts.load_prompt`); the same rule governs generated GUIs, on both the **make** (scaffold + read `locales/i18n.yaml`) and **audit** (flag any GUI string or prompt living outside it: hardcoded in JS or inlined in Python) sides.

## Status

A snapshot of where each surface stands. The nine skill folders are stable; the only WiP area is **audio captions** (sprezzature-audio, video → text). The **audio narration** feature (sprezzature-publish, text → audio) is stable and clearly framed as optional editorial enhancement, not Web Content Accessibility Guidelines (WCAG) compliance.

| Area | Status | Notes |
|---|---|---|
| `sprezzature-ui` (stack rules, tokens, components, dataviz, checklist) | Stable | All 9 hard rules documented; `validate.py` stdlib-only; covered by `tests/test_validate.py`. |
| `sprezzature-cli` (unified `sprezzature` driver, shell completion) | Stable | Click-based; leaf-command `--help` forwarding fixed in 0.3.0 (regression test in 0.3.1). |
| `sprezzature-cli-gui` (CLI → GUI flagship) | Stable (skill + runnable demo) | `assets/examples/cli-gui-demo/` runs end-to-end. Production hardening (auth, rate-limit, sandbox) deliberately left to the host. |
| `sprezzature-publish` (Markdown site, meta tags, favicons, indexes, plain language, audio narration) | Stable | 11 public scripts spanning the four core artifacts (favicons, meta, indexes, plain-language) + Markdown → HTML + Markdown linter + the audio-narration pipeline (narrate orchestrator, OpenVoice and Chatterbox engine wrappers, voice picker, install helper). Broad deterministic test coverage (favicons, site-indexes, meta, plain-language, lint, narrate); eval suite for meta + plain-language. |
| `sprezzature-accessibility` — lint | Stable (renamed from `sprezzature-a11y` in 0.9.0) | 14-rule static a11y lint, stdlib only. Now narrowed to lint after the color / vision / audio splits. |
| `sprezzature-colors` — contrast audit, color-vision-deficiency (CVD) simulation, curated palette, perceptual lighten / darken | Stable (new in 0.7.0) | OKLCH (the perceptual OKLCH color space)-neighbour contrast fixer, Machado CVD matrices, unified palette CSV (Apple base + emotion / concept / psychology projections), stdlib-only `_colors` module, `Color` class. Split out of `sprezzature-accessibility` for clearer scope. |
| `sprezzature-vision` — W3C alt text via local Ollama vision | Stable (new in 0.8.0) | Model `qwen3-vl:8b` via Ollama (the one authorized LLM). Per-purpose decision tree, surrounding-text + vocabulary biasing, on-disk cache. Split out of `sprezzature-accessibility` for clearer scope. Wikipedia-fixture alt-text eval. |
| `sprezzature-audio` — **WebVTT / SRT captions via local whisper.cpp** | **WiP / TODO** (split out in 0.9.0) | `captions_from_whisper.py` is functional; what's missing is per-language word-error-rate (WER) baselines (`en` / `fr` / `es` extractor wired but baselines not yet published), the user-supplied `vocab-biasing-clip.wav`, and a planned `pdbms`-based revision of the whisper.cpp integration. See [Roadmap](CHANGELOG.md#roadmap). |
| `LISEZMOI.md` (French README) | Stable | At structural parity with this README, same section ordering, content kept in lock-step on every release. |

For the per-release detail (and what's planned next), see [`CHANGELOG.md`](CHANGELOG.md).

## Inputs → outputs

What you give the agent and what comes back. Each row is a self-contained flow; pick one, ignore the rest.

| You provide | Phrase | Skill | Output |
|---|---|---|---|
| A working CLI (`tool --help`, source with `argparse` / `click` / `clap` / `commander` / `cobra`) | "Wrap this CLI in a GUI" + the project path | `sprezzature-cli-gui` | One-page `index.html` + `app.js` + Tailwind CSS, sub-commands mapped to forms / streams / tables, wired to your host (Tauri / Electron / FastAPI / Express / browser stub). Self-hosted Roboto / Roboto Mono. |
| A folder of Markdown files (README, `docs/**`, blog posts) | "Turn these markdown files into a website" | `sprezzature-publish` | Static site: one HTML page per `.md`, sticky top bar, sidebar TOC for `docs/`, dark-mode peer, favicons, `<meta>` tags, `robots.txt` + `sitemap.xml` + `llms.txt` + Atom feed. |
| A free-form ask ("primary button", "confirm dialog", "settings page") | "Build a `<component>`" | `sprezzature-ui` | Semantic HTML + Tailwind + minimal vanilla JS, focus ring, `dark:` peer, 44×44 hit area, `Escape` close on dialogs, reduced-motion guard. |
| A data shape (CSV, JSON, a few rows) | "Chart this" / "Dashboard for X" | `sprezzature-ui` | Vega-Lite v5 JSON spec + `<figure>` wrapper. House style, palette from `color-psychology.md`, polarity-tagged axes, `role="img"`. |
| An existing HTML page or screenshot | "Audit this" / "WCAG check" / "Make it look less AI" | `sprezzature-ui` (anti-patterns, ergonomics) + `sprezzature-accessibility` (lint) + `sprezzature-colors` (contrast, CVD) | Findings against the 8 ergonomic criteria + anti-patterns catalogue; concrete diffs; pre-ship checklist run; `lint_a11y` + `audit_contrast` + `simulate_cvd` output. |
| An image file (`*.png`, `*.jpg`, …) | "Alt text for this image" | `sprezzature-vision` | W3C-compliant alt text for the right purpose category (informative / decorative / functional / text / complex / group), in the page's language, tagged `data-alt-source="ai"`. |
| An audio or video file (`.mp4`, `.wav`, `.mp3`, …), **WiP** | "Captions / transcript" | `sprezzature-audio` *(work in progress)* | WebVTT / SRT / plain-text captions from local whisper.cpp, with project-vocab biasing. `<video>` + `<track kind="captions">` snippet. Script + tests ship today; per-language WER baselines and the vocab-biasing reference clip are still being collected; see [Status](#status). |
| A logo (`logo.png` / `.svg`) | "Favicon set" / "PWA icons" | `sprezzature-publish` | `favicon.svg` + `.ico` + PNG set + `apple-touch-icon.png` + maskable PWA icon + `site.webmanifest` + a `head.html` snippet. |
| A goal description or an HTML page | "Meta tags" / "SEO" / "OG card" / "GEO" / "llms.txt" / "AI Overview" | `sprezzature-publish` | **For search-engine optimization (SEO):** title + description + Open Graph (OG) + Twitter Card + Schema.org JSON for Linking Data (JSON-LD) (JSON on stdout): see [Google's three Search Essentials pillars](https://developers.google.com/search/docs/essentials) applied in `sprezzature-publish/references/seo-essentials.md`. **For generative-engine optimization (GEO)** (Generative Engine Optimization, AI Overview / Gemini / ChatGPT answer surfaces): `llms.txt` is emitted by `scripts/site_indexes.py` alongside `robots.txt` + `sitemap.xml` + Atom/really-simple-syndication (RSS), so the site ships an LLM-readable Markdown summary the moment any "turn this into a website" run completes. Same crawlers, same `robots.txt` permissions; no separate "AI" meta tag exists; anything claiming one is wrong. |
| Draft UI copy | "Plain language" / "Rewrite at grade 8" | `sprezzature-publish` | Same meaning, marketing voice stripped, output length ≤ 1.1× original. |
| A palette JSON | "Contrast audit" / "Is my palette accessible?" | `sprezzature-colors` | Every `(label, surface)` pair walked, failures listed with the nearest OKLCH-neighbour fix. Exit 1 on any failure. |
| A finished page / screenshot | "Pre-ship check" | `sprezzature-ui` + `sprezzature-accessibility` + `sprezzature-colors` | The `checklist.md` gate executed; lint + contrast + CVD passes; copy / motion / performance verified. |

> Not sure which row you're on? Describe the input in plain English. Each skill's `SKILL.md` decision tree maps phrasing → workflow.

## Install

The skills follow the [Anthropic skill specification](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) and are read natively by **Claude Code** and **OpenCode**. Install only the ones you need.

The Claude Code and OpenCode flows are **identical except for the
install directory**; both runtimes read SKILL.md files from a
per-skill folder, and the same tarballs serve both. The instructions
below show one path; the second runtime is a one-line substitution.

> **Shared variables.** Replace `<RUNTIME>` with `claude` or
> `opencode` below. Pin `VERSION` to the latest tag; see
> [releases](https://github.com/warith-harchaoui/sprezzature/releases).

### 1. Download a tagged release (checksum-verified)

```bash
VERSION=1.0.0
curl -L -o sprezzature-skills.tar.gz \
    https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/sprezzature-skills-${VERSION}.tar.gz
curl -L -o SHA256SUMS \
    https://github.com/warith-harchaoui/sprezzature/releases/download/v${VERSION}/SHA256SUMS

# macOS: shasum -a 256 -c SHA256SUMS
# Linux: sha256sum -c SHA256SUMS
shasum -a 256 -c SHA256SUMS

tar xzf sprezzature-skills.tar.gz
```

If you only need one skill, swap the bundle for a per-skill tarball
(e.g. `sprezzature-accessibility-${VERSION}.tar.gz`). The same `SHA256SUMS`
covers every artifact.

### 2. Copy into the runtime's skills directory

Pick **one** runtime block:

```bash
# Claude Code:
RUNTIME=claude   # → ~/.claude/skills/
# OpenCode:
RUNTIME=opencode # → ~/.opencode/skills/

mkdir -p ~/.${RUNTIME}/skills
cp -r sprezzature-ui            ~/.${RUNTIME}/skills/   # always
cp -r sprezzature-cli-gui       ~/.${RUNTIME}/skills/   # only if you wrap CLIs
cp -r sprezzature-publish       ~/.${RUNTIME}/skills/   # only if you ship docs sites
cp -r sprezzature-accessibility ~/.${RUNTIME}/skills/   # only if you need static a11y lint
cp -r sprezzature-colors        ~/.${RUNTIME}/skills/   # only if you need WCAG contrast / CVD / palette
cp -r sprezzature-vision        ~/.${RUNTIME}/skills/   # only if you need AI alt text (local Ollama)
cp -r sprezzature-audio         ~/.${RUNTIME}/skills/   # only if you need AI captions (local whisper.cpp)
cp -r sprezzature-ux-laws       ~/.${RUNTIME}/skills/   # only if you want the Laws-of-UX audit + reference
cp -r sprezzature-figures       ~/.${RUNTIME}/skills/   # only if you emit dataviz / SHAP / DoWhy figures
```

Install in **both** runtimes if you switch between them, the same
folder copied to two paths.

### 3. Verify

```bash
# A skill is installed and its SKILL.md is on disk:
ls ~/.${RUNTIME}/skills/sprezzature-ui/SKILL.md

# Optional — if you cloned the repo too, verify every installed skill
# against the Anthropic spec (stdlib + PyYAML, no network):
python3 scripts/validate_all.py
```

The runtime reads each skill's `SKILL.md` frontmatter description at
conversation start; matching prompts auto-trigger the skill. See
[`TRIGGERS.md`](TRIGGERS.md) for the per-phrase index.

### Cleanup — remove stale or renamed skills

If you installed an older version, your `~/.${RUNTIME}/skills/`
folder may carry orphan directories from past renames (e.g.
`sprezzature-a11y/` from before the v0.9.0 rename to `sprezzature-accessibility`).
Run the helper to detect + remove them:

```bash
# Audit only (lists orphan skill folders; never deletes):
python3 scripts/cleanup_local_skills.py

# Apply: prompts for confirmation per directory before removal.
python3 scripts/cleanup_local_skills.py --apply
```

It checks both `~/.claude/skills/` and `~/.opencode/skills/` against
the canonical `SKILLS.txt` manifest and flags any `sprezzature-*` folder
that no longer ships from this repo. Read [`SKILLS.txt`](SKILLS.txt)
for the canonical list.

### Upgrade

Repeat steps 1–3 with the new `VERSION`. The on-disk skill folder
name is stable so each `cp -r` overwrites in place: no manual
removal between versions, except when a skill is **renamed** (use
the cleanup helper above for those). Skill renames are listed in
[`CHANGELOG.md`](CHANGELOG.md).

### Install from source (contributor / developer path)

To iterate on the skills, or pin to a commit that has not been
tagged, clone and copy from the working tree. No checksum step:
you are responsible for verifying you cloned the commit you intended.

```bash
git clone https://github.com/warith-harchaoui/sprezzature.git
cd sprezzature
python3 -m pip install -r requirements-dev.txt   # PyYAML + pytest
python3 -m pytest                                # full deterministic suite
python3 scripts/validate_all.py                  # all 9 skills, YAML + content

# Mirrors step 2 above:
RUNTIME=claude   # or opencode
mkdir -p ~/.${RUNTIME}/skills
for skill in $(grep -v '^[[:space:]]*#' SKILLS.txt | grep -v '^[[:space:]]*$'); do
    cp -r "$skill" ~/.${RUNTIME}/skills/
done
```

`CONTRIBUTING.md` walks the same flow at the contributor level.

### OpenCode + local Ollama — the zero-token path

[OpenCode](https://opencode.ai) is the second supported runtime,
and the natural fit for an **all-local, no-tokens** workflow.
OpenCode is model-agnostic: point it at a local
[Ollama](https://ollama.com) daemon and you get the same skill
behaviour as Claude Code with two real differences:

- **No application-programming-interface (API) tokens.** Nothing leaves your machine; nothing bills.
- **No usage limits.** Run the loop overnight on a long batch
  without watching a meter.

The trade-off is model quality. A 7-13 B local model is below
Claude / GPT-4 (the generative pre-trained transformer) on hard reasoning; the sprezzature-* skills compensate
because they front-load the *opinion* (stack rules, audit checks,
trigger phrases); the model mostly has to follow a script, not
invent it. For UI work, alt text, captions, contrast audits,
Laws-of-UX checks, the local path is genuinely usable today.

The fit with this repo is direct: **three sprezzature-* skills already
talk to a local Ollama daemon** for their AI surfaces: `sprezzature-vision`
(alt text, `qwen3-vl:8b`), `sprezzature-publish/meta_from_ollama.py` (page
meta), `sprezzature-publish/plain_language.py` (copy rewrite). When you
run OpenCode against the same Ollama daemon, the whole loop,
agent + skill-driven scripts, uses one local model. Zero
external calls.

```bash
# Quick start. Assumes Ollama + an OpenCode binary on PATH.
ollama serve &         # start the daemon
ollama pull qwen3-vl:8b  # the one model — agent loop AND every skill script
```

One model handles the whole stack: it drives the OpenCode agent
loop AND backs every sprezzature-* Ollama-backed script
(`alt_from_ollama`, `meta_from_ollama`, `plain_language`,
`narrate_post`). Same daemon, same tag, same answer for "which
model is in play": `qwen3-vl:8b`.

#### Wire OpenCode to the local Ollama daemon (one-time config)

OpenCode's bundled `ollama` provider points at Ollama Cloud by
default. To target your **local** daemon, add a `local-ollama`
provider to `~/.config/opencode/opencode.jsonc` (the file already
exists; only the `provider` key is new):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "local-ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "qwen3-vl:8b": { "name": "qwen3-vl:8b (local)" }
      }
    }
  }
}
```

Ollama exposes an OpenAI-compatible endpoint at
`http://localhost:11434/v1`, which the `@ai-sdk/openai-compatible`
provider speaks natively; no plugin install needed beyond writing
the config. List exactly the model tags you have pulled (run
`ollama list` to see them); OpenCode will not auto-discover.

Then start OpenCode against the local provider:

```bash
opencode run "build me a primary CTA button" \
    -m local-ollama/qwen3-vl:8b

# → ~/.opencode/skills/sprezzature-* load automatically per their frontmatter.
# → The sprezzature-vision / sprezzature-publish Ollama-backed scripts hit the
#   same daemon for their per-script work.
# → Cost: 0 tokens; nothing leaves the machine.
```

One model, `qwen3-vl:8b`, backs both the agent loop and every
skill script, same daemon, same tag. `qwen3-vl:8b` is multimodal, so
the vision script (alt text) works on the same model as the text
scripts. There is nothing else to pick.

#### LLM choice — why Qwen3-VL 8B (Q4_K_M)

The single model is **Qwen3-VL 8B**, Q4_K_M quantization, pulled with
`ollama pull qwen3-vl:8b` (~6.1 GB). It was chosen against four criteria for a
bilingual, image-heavy, Mac-local toolkit: **vision**, **French**,
**OCR / charts**, and **Apple-Silicon fit**. It is the only ≈8B model that is
top-tier on vision, OCR/charts, and Mac-fit at once while being strong on
French (DocVQA 96.1%, OCRBench ~896, ScreenSpot 94.4%, OCR across 32 languages).
The full rationale, the scored comparison against Gemma 3, Pixtral, InternVL,
MiniCPM, and the specialist OCR models, and all research sources are in
[`docs/LLM_CHOICE.md`](docs/LLM_CHOICE.md). The rule is machine-enforced by
`tests/test_single_llm.py`.

#### Configure the skill scripts (same daemon, separate env vars)

OpenCode drives the agent; the skill scripts that *also* talk to
Ollama (alt text, meta tags, plain-language rewrites, audio
narration) read their own env vars. There is **no overlap with
`OPENCODE_MODEL`**; set both, both should agree on the daemon
web address (URL), but the model tag can differ:

| Env var | Read by | What it does | Default |
|---|---|---|---|
| `OLLAMA_URL` | every Ollama-backed script | Daemon endpoint. Must match the URL OpenCode talks to. | `http://localhost:11434` |
| `OLLAMA_MODEL` | every Ollama-backed script | Bare escape hatch (mainly for tests). The one authorized model is `qwen3-vl:8b`. | `qwen3-vl:8b` |
| `OPENCODE_MODEL` | OpenCode itself | Agent-side model tag; set it to `qwen3-vl:8b`. | `qwen3-vl:8b` |

The pattern is deliberately boring: `qwen3-vl:8b` on the same daemon
for both the agent and the scripts. `qwen3-vl:8b` is multimodal, so the
vision script and the text scripts share it: no per-concern model
juggling, no MLX.

```bash
# One daemon, one model, for everything.
export OLLAMA_URL=http://localhost:11434
export OPENCODE_MODEL=qwen3-vl:8b
```

Pick OpenCode when token costs matter, when the work is bulk /
repetitive (alt-text a 500-image library, regenerate meta tags on
every doc commit, audit a 50-page docs site), or when the data
must not leave the box. Pick Claude Code when the work needs
frontier-model judgement (novel design synthesis, ambiguous
refactors, code review of unfamiliar libraries).

### Trust model

Short version: the repo ships text and Python scripts you can read
top-to-bottom in under an hour. **Tagged releases carry Secure Hash Algorithm (SHA) SHA-256
checksums** (integrity-against-corruption); they are **not
GPG-signed** or Sigstore-attested today. If you need authenticity
beyond a transport-integrity check, build from a tagged commit you've
reviewed yourself; `scripts/release.sh` is in-tree and reproducible,
and the `release.yml` workflow does nothing the script can't do
locally. See [`SECURITY.md`](SECURITY.md) for the full supply-chain
note.

### Shell completion

The `sprezzature` driver (and the four Click-migrated per-script CLIs:
`alt_from_ollama.py`, `captions_from_whisper.py`, `meta_from_ollama.py`,
`plain_language.py`) ship `bash` / `zsh` / `fish` completion for free
via Click's `_<TOOL>_COMPLETE=<shell>_source` trick. See
[`sprezzature-cli/README.md`](sprezzature-cli/README.md#shell-completion) for the
one-line setup per shell. The same env-var pattern works for any of
the per-script CLIs invoked directly (e.g.
`_ALT_FROM_OLLAMA_COMPLETE=zsh_source alt_from_ollama.py`).

## Pre-commit hooks

The repo ships a `.pre-commit-hooks.yaml` manifest, so any project
can wire the sprezzature-* audit gates into [pre-commit](https://pre-commit.com/)
with a single `repo:` block: no manual script paths, no install
beyond `pre-commit install`.

```yaml
# .pre-commit-config.yaml — add the repo as one entry
repos:
  - repo: https://github.com/warith-harchaoui/sprezzature
    rev: v1.0.0          # pin a tag — bump with renovate / dependabot
    hooks:
      - id: sprezzature-accessibility-lint
      - id: sprezzature-ux-laws-audit
      - id: sprezzature-publish-lint-markdown
      - id: sprezzature-ui-validate-skill   # only if you ship skills yourself
      # Add --fix to any of the above as a hook arg to enable auto-repairs
      # e.g. - id: sprezzature-ux-laws-audit
      #        args: [--fix]
```

The hooks are stdlib-only on the Python side (pre-commit installs
each into its own isolated env). The two color hooks declare Pillow
via `additional_dependencies`. Each hook respects the file-type
filter pre-commit hands it (HTML for the a11y + Laws-of-UX hooks;
Markdown for the publish hook).

## CLI → GUI flagship

The `sprezzature-cli-gui` skill takes an existing CLI and produces a single-page vanilla-JS + Tailwind GUI for it. It reads the argument parser, categorizes each command (one-shot / form / streaming / list), maps flags to form controls, and wires execution to the project's host (Tauri, Electron, FastAPI, Express, or a stdlib HyperText Transfer Protocol (HTTP)+server-sent events (SSE) proxy).

A runnable worked example ships in `sprezzature-cli-gui/assets/examples/cli-gui-demo/`. Launch:

```bash
cd sprezzature-cli-gui/assets/examples/cli-gui-demo
python server.py  # stdlib only, opens http://localhost:8787
```

For an honest comparison against Gradio / Streamlit / Tauri / Taipy, see `sprezzature-cli-gui/SKILL.md` → "Why this skill, not Gradio / Streamlit / Tauri / Taipy" and [LANDSCAPE.md](LANDSCAPE.md) § 7.

## Author

[Warith Harchaoui, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)

Nine Claude / OpenCode **skills** for a single frontend stack: vanilla JavaScript, Tailwind CSS, and the three-Roboto typography rule (Roboto / Roboto Serif / Roboto Mono). Built to the [Anthropic skill specification](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf).

Special thanks to:

  + [Audrey Dejoux](https://www.behance.net/dreyadesign/projects),

  + [Laurent Pantanacce](https://www.linkedin.com/in/pantanacce/),

  + [Auguste Baum](https://www.linkedin.com/in/auguste-baum/),

  + [Julien Boyer](https://www.linkedin.com/in/julien-boyer-2a76878/) and

  + [Jérôme Gombert](https://www.linkedin.com/in/j%C3%A9r%C3%B4me-gombert-84675b1b/)

for fruitful discussions.

Color palettes from <https://harchaoui.org/warith/colors/>.

The three Roboto families are bundled in `sprezzature-ui/assets/fonts/roboto/`, `sprezzature-ui/assets/fonts/roboto-serif/`, and `sprezzature-ui/assets/fonts/roboto-mono/`, each under the SIL Open Font License; see the bundled `OFL.txt` in each folder.

We also drew on the [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/), [Google Material Design](https://material.io/design) and [Laws of UX](https://lawsofux.com/)

## License

**Berkeley Software Distribution (BSD)-3-Clause**, the same license used by **scikit-learn**.
Permissive: use, modify, redistribute, sell, ship in commercial
products. The three conditions are (1) keep the copyright notice in
source redistributions, (2) reproduce it in binary distributions'
documentation, (3) do not use the copyright holder's name to endorse
derived products without permission. See `LICENSE.md` for the canonical
text. The bundled Roboto / Roboto Serif / Roboto Mono fonts remain
under the SIL Open Font License (see the `OFL.txt` bundled in each
`sprezzature-ui/assets/fonts/roboto*/` folder); the BSD-3-Clause license
above applies to the source, not to the fonts.

**License vs. attribution.** Author credits in the docs are voluntary
acknowledgement (not part of the license condition #3). You are free
to remove or replace them in your fork; the BSD-3-Clause obligations
above are what travels with the code.
