# Sprezzature

[🇫🇷](https://github.com/warith-harchaoui/sprezzature/blob/main/LISEZMOI.md) · [🇬🇧](https://github.com/warith-harchaoui/sprezzature/blob/main/README.md)

<p align="center"><a href="https://sprezzature.ai/">
  <img src="https://sprezzature.ai/img/logo.png" alt="Sprezzature: ten Claude / OpenCode skills for vanilla JS + Tailwind frontends"></a>
</p>

[🌍 Documentation](https://sprezzature.ai/)

[💻 Examples](https://github.com/warith-harchaoui/sprezzature/blob/main/EXAMPLES.md)

## What this is

`sprezzature` is a set of **Claude / OpenCode skills** with a curated design system for a front-end stack. It covers colors, accessibility (alt text included), the user interface (UI), user experience (UX), audio both ways, figures and maps, publishing, the videos that describe a project, and the path from the command-line interface (CLI) to the graphical user interface (GUI).

The skills:

| Skill | When to install | Trigger phrases |
|---|---|---|
| **sprezzature-ui** | Always: it owns the stack rules and tokens. | "build a UI", "create a component", "design a page", "make a form / modal / button / nav", "dashboard", "audit this UI". |
| **sprezzature-cli-gui** | You wrap CLI tools in web user interfaces (UIs). | "wrap this CLI in a GUI", "build a UI for my Python script", "argparse to web UI". |
| **sprezzature-publish** | You ship docs sites, landing pages, meta-tags, favicons, or a site whose readers should book, buy or install. | "turn these markdown files into a website", "meta tags", "SEO", "GEO", "AEO", "write a FAQ", "favicons", "robots.txt", "sitemap", "llms.txt", "Atom feed", "plain language", "rewrite at grade 8". |
| **sprezzature-accessibility** | You need static HyperText Markup Language (HTML) accessibility (a11y) lint, or World Wide Web Consortium (W3C)-compliant alt text drafted from images locally (no SaaS). | "a11y lint", "check this HTML for accessibility", "WCAG compliance", "missing alt", "write alt text", "describe this image", "unlabelled input". |
| **sprezzature-colors** | You audit contrast, simulate color blindness, or want a curated palette with perceptual lighten / darken. | "WCAG check", "contrast audit", "is my palette accessible", "colorblind preview", "deuteranope", "CVD", "OKLCH", "lighten this color". |
| **sprezzature-audio** | You draft WebVTT / SubRip subtitle format (SRT) captions for `<video>` / `<audio>` locally, or narrate text with a local voice (no SaaS). | "captions", "transcribe video", "WebVTT", "SRT", "subtitles", "who spoke when", "text to speech", "narrate", "read this aloud". |
| **sprezzature-ux-laws** | You want a shared vocabulary for UI decisions AND a pre-commit auditor that fails on detectable Laws-of-UX violations (Hick, Fitts, Miller, Jakob, Tesler, Aesthetic-Usability, Selective Attention, Choice Overload). | "Laws of UX", "Hick / Fitts / Miller / Jakob / Tesler / Peak-End / Postel / Paradox of the Active User", "audit my nav / form / pricing page", "is this onboarding fighting the active user". |
| **sprezzature-figures** | You emit data-science figures (168 hand-authored Scalable Vector Graphics (SVG) chart types, the model-explainability plots (SHapley Additive exPlanations (SHAP) / Shapash / TimeSHAP / Local Interpretable Model-agnostic Explanations (LIME)) included), causal-effect estimates (DoWhy / EconML), or flow diagrams and TikZ figures, refined through the **Ralph Eyeball Loop** (render → look → refine the source), with a pre-commit auditor for data-viz sins and colour-vision accessibility levels on every figure. | "make a figure", "hand-authored SVG", "render this diagram", "mermaid diagram", "ralph eyeball loop", "no ascii art", "SHAP plot", "DoWhy", "DAG", "audit this figure". |
| **sprezzature-maps** | You have numbers attached to places and the shape of the land matters: a choropleth on a real basemap, or an areas-of-control situation plate for any region. Schematic place-shaped charts (hex map, dot density, spike map, binned grid) stay in **sprezzature-figures**. | "map this by country", "colour the regions by score", "which country is worst affected", "where is this happening", "world map", "choropleth", "areas of control", "front line", "situation map", « une carte par département ». |
| **sprezzature-video** | A video states facts about a project (counts, commands, versions) and the project keeps changing under it. | "the demo video is out of date", "verify the claims in this video", "is this number still right", "can we rebuild this video", "poster frame". |

The companion skills inherit the sprezzature-ui stack rules. Install only the
ones you need.

## How it works

![Flow diagram. At the top, a sentence typed to an agent feeds two lanes. The left lane is the agent layer, this repository: it matches the sentence to a skill through a declared vocabulary and reads that skill's reference documents rather than a memory, handing back one contract. The right lane is the tool layer, ten standalone packages: each is installed on its own and published through five surfaces, a library, a command line, an HTTP API, an agent tool surface and a skill. Both meet in one outcome, an artifact that was made and then audited by a gate that exits non-zero.](https://raw.githubusercontent.com/warith-harchaoui/sprezzature/main/assets/how-it-works.svg)

## Two-layer architecture

As of 2026-07-29, sprezzature is organised in two layers with distinct release cycles.

**Layer 1: pip-installable tool packages.** Each skill's Python scripts live in a standalone repo, published on PyPI. Install only the tools you need (`pip install <package>`), and each one arrives whole: the library, the command line (Click), the FastAPI server and the MCP tool surface are all in the base install. Each brick's Docker image runs its `<brick>-mcp` server, which serves the HTTP API and `/mcp` on the same port. There are no feature extras anywhere in the suite since 2026-11-01 — six of the bricks had a base of one dependency, so `pip install <brick>` installed almost nothing and knowing the right extra was a prerequisite for the package being useful:

| Package | What it does |
|---|---|
| `sprezzature-figures` | 168 chart types, SHAP, causal estimates, the Ralph Eyeball Loop |
| `sprezzature-colors` | WCAG contrast auditing, CVD simulation, Tailwind palette export |
| `sprezzature-accessibility` | Static a11y lint (20 rules, no browser) and W3C alt text drafted by a local vision model |
| `sprezzature-cli-gui` | CLI argument parser to single-page GUI emitter |
| `sprezzature-ux-laws` | Laws-of-UX audit (Hick, Fitts, Miller, Jakob, Tesler, …) |
| `sprezzature-audio` | Speech-to-text, diarization, speaker identification, caption translation; narration (Kokoro by default, OpenVoice, Chatterbox) |
| `sprezzature-maps` | Choropleths and situation maps, in five modes, at newsroom quality |
| `sprezzature-publish` | Markdown to site, meta tags, icons, indexes, plain language, narration and read-along, SEO / GEO / AEO |
| `sprezzature-ui` | i18n catalogue make and audit (`locales/i18n.yaml`) beside the UI generation playbook |
| `sprezzature-video` | Checks what a film says against the code, and whether it can be rendered again |

`pip install sprezzature` installs all ten, and the skills with them.

All repos live under [github.com/warith-harchaoui/](https://github.com/warith-harchaoui/).

**Layer 2: the agentic layer (this repo).** `SKILL.md` files, `references/`, and `web/` stay in the `sprezzature` monorepo. They define the contracts between the Claude / OpenCode agent and the tool packages. They ship on PyPI as the `sprezzature` package, whose `sprezzature-skills` command copies them where an agent reads them.

> **What prompt activates what?** See [`TRIGGERS.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/TRIGGERS.md),
> generated from every `SKILL.md` description, lists every guaranteed
> trigger phrase against the skill it invokes.

## Getting started

Sprezzature is a set of skills for **Claude Code** or **OpenCode**. Install the ones you
want, then ask in plain English. The skill both **makes** the artifact and **audits** it.

The shortest path installs the ten tool packages and the ten skills in one go:

```bash
pip install sprezzature
sprezzature-skills             # reports which installed skills differ from the shipped ones
sprezzature-skills --install   # copies them into ~/.claude/skills (--agent opencode for ~/.opencode/skills)
```

`--install` moves any previous copy aside rather than deleting it, and says where.
To take only the skill folders, without the tools:

```bash
# 1. Grab the latest release (resolved, so this never goes stale)
VERSION=$(curl -fsSL https://api.github.com/repos/warith-harchaoui/sprezzature/releases/latest \
  | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p')
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

Human-facing guides live in [`docs/`](https://github.com/warith-harchaoui/sprezzature/tree/main/docs), one landing page per skill
([UI](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/UI.md) · [CLI](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/CLI.md) · [publish](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/PUBLISH.md) ·
[accessibility](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/ACCESSIBILITY.md) · [colors](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/COLORS.md) ·
[vision](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/VISION.md) · [audio](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/AUDIO.md) · [UX-laws](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/UX-LAWS.md) ·
[figures](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/FIGURES.md) · [maps](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/MAPS.md) · [video](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/VIDEO.md)), each a thin pointer to that skill's
`SKILL.md`, its `references/`, and its `EXAMPLES.md` recipe (no duplication).
`SKILL.md` is the agent-facing spec; `docs/` is for humans.

For the *why* behind the stack (the design convictions that run through
every skill) see [`PHILOSOPHY.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/PHILOSOPHY.md) (français :
[`PHILOSOPHIE.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/PHILOSOPHIE.md)).

A deployable, multi-page static site, built with the `sprezzature-*` skills themselves
(sprezzature-ui house style, sprezzature-publish meta / favicons / sitemap / llms.txt,
sprezzature-colors palette, sprezzature-accessibility clean, a working 🌞/🌛 toggle), lives
in [`web/`](https://github.com/warith-harchaoui/sprezzature/tree/main/web) and publishes to <https://sprezzature.ai/>. It has
a detail page per skill (make / audit / triggers / reference library) plus a
dedicated **figures gallery** rendering the whole `sprezzature-figures` catalog. The
gallery carries a **"See it for…" colour-vision viewer** that applies a live
colour-vision-deficiency simulation over the default figures (it simulates what
a colour-blind reader sees, it does not swap in a different figure), and a shared
**figure-fullscreen** control so any chart can open full-screen.

## Features: what's unusual for a Claude skill

Most Claude skills, including Anthropic's own `document-skills` (docx, pdf,
pptx, xlsx) and `example-skills` (artifacts, GIFs, MCP servers, design), are
**make-only**: the model produces an artifact. `sprezzature` is built differently, and
these traits set it apart:

- **Make *and* audit.** Every skill pairs generation with a **deterministic
  auditor** that exits non-zero on findings: `sprezzature-accessibility-lint`,
  `sprezzature-colors-contrast`, `sprezzature-ux-laws`, `sprezzature-figures check`,
  `sprezzature-ui-i18n-audit`, `sprezzature-publish-lint` and `-audit`,
  `sprezzature-cli-gui-audit`, `make-map audit`, `make-film verify`. No official Anthropic skill ships a static lint gate as its
  purpose; here it's half the design.
- **Continuous integration (CI) / pre-commit gates, not vibes.** The auditors emit JavaScript Object Notation (JSON) + exit codes, so
  a pre-commit hook or a CI step blocks the commit whoever (or whatever) wrote
  the code; see [Pre-commit hooks](#pre-commit-hooks).
- **AI that runs on your machine, zero SaaS egress.** Alt text runs on a local Ollama vision
  model; captions / diarization on a local whisper.cpp build and NeMo; narration on Kokoro. Nothing leaves the
  machine; the official skills are cloud-Claude-first.
- **Deterministic generators.** palette → Tailwind config, CLI → GUI, favicon /
  progressive-web-app (PWA) icon sets, sitemaps / feeds, and `locales/i18n.yaml`: reproducible
  artifacts a model would not derive byte-for-byte.
- **Hardened like a product, not a demo.** A real pytest suite in every
  repository, an AI-eval layer (DeepEval) in the bricks that call a model, CI on
  Python 3.12 with an install-and-import check on the 3.10 floor,
  checksum-verified per-skill release tarballs, and a spec-conformance
  validator, vs demonstration-grade examples.
- **Runtime-portable.** One skill folder serves both **Claude Code** and
  **OpenCode**; the AI paths target local models so a smaller OpenCode model
  follows a script instead of inventing one.
- **Unified i18n.** GUI strings *and* large-language-model (LLM) prompts live in a single
  `locales/i18n.yaml`, enforced on both the make and audit sides.

## Two modes: make and audit

Every sprezzature-* skill belongs to one or both halves of a single loop:
**make** the artifact, **audit** the artifact. The matrix tells you
when to load each skill and what is still on the roadmap.

| Skill | Make (generate) | Audit (gate) |
|---|---|---|
| **sprezzature-ui** | `references/` + `assets/components/`, generation playbook for HTML / Tailwind / dataviz; `sprezzature-ui-i18n-make` (scaffolds and compiles `locales/i18n.yaml`) | `sprezzature-ui-i18n-audit` (I18N001, I18N002), `references/checklist.md`, `anti-patterns.md`, `ergonomics-criteria.md` |
| **sprezzature-cli-gui** | `sprezzature-cli-gui` (argparse, Click or Typer parser → one self-contained HTML form; `--from-help` reads a help text instead) + `assets/examples/cli-gui-demo/` (worked scaffold) | `sprezzature-cli-gui-audit` (five rules: does an earlier page still cover the CLI?); pair with `sprezzature-accessibility` + `sprezzature-ux-laws` on the emitted HTML |
| **sprezzature-publish** | `sprezzature-publish-html`, `-icons`, `-indexes` (`--offer`, `--cta`), `-meta`, `-plain`, `-changelog`, `-narrate`, `-readalong`; `-cta` (asks which call to action the site is for, writes `ctas.yaml`), `-faq` (builds the FAQ a site lacks from its own pages) | `sprezzature-publish-lint` (the Markdown), `-audit` (an emitted site or a live URL), `-cta` and `-faq --audit` (pages against the declared CTAs, `FAQPage` against the visible FAQ), `-findable` (one SEO + GEO + AEO report, money pages first) |
| **sprezzature-accessibility** | `--fix-alt` and `sprezzature-accessibility-alt` (W3C alt text drafted by a local vision model, in the page's language) | `sprezzature-accessibility-lint` (20 rules from the source, six with a safe `--fix`), `sprezzature-accessibility-text-spacing` |
| **sprezzature-colors** | `sprezzature-colors-palette-to-tailwind` (palette → tailwind.config.js), `sprezzature-colors-levels` (project the palette to `universal` / `high-contrast` / `monochrome` / a colour-vision-deficiency variant) | `sprezzature-colors-contrast` (every co-occurring pair against WCAG, nearest OKLCH fix; exit 2 when nothing matched a role), `sprezzature-colors-cvd` (simulation, mosaic, `--grayscale`) |
| **sprezzature-audio** | captions (local whisper.cpp), diarization, speaker naming, translation; narration through Kokoro, OpenVoice or Chatterbox, the engine chosen by speaker-helper's router | `sprezzature-audio-audit` (caption tracks), `-benchmark` (word error rate) |
| **sprezzature-ux-laws** | `references/laws-of-ux.md` (30-law Markdown playbook) | `sprezzature-ux-laws` (eight laws checked from the source: Hick, Fitts, Miller, Jakob, Tesler, Aesthetic-Usability, Selective Attention, Choice Overload; `--fix` repairs four) |
| **sprezzature-figures** | `sprezzature-figures render <kind>` (data → hand-authored SVG, 168 chart types), `explain_model.py` (SHAP / Shapash / TimeSHAP / LIME), `causal_estimate.py` (DoWhy + EconML + directed acyclic graph (DAG)), `render_diagram.py` (TikZ / SVG → PNG), `ralph_eyeball_loop.py` (render → look → refine, agent mode or `--local`). Every generator takes an `--accessibility` level | `sprezzature-figures check`, `audit_figure.py` (pie-3d, rainbow-palette, chartjunk, radius-over-cap, unformatted-tick, iso-date-tick, role-img-missing, alt-missing) |
| **sprezzature-maps** | `make-map choropleth` (rows keyed by territory → shaded real basemap, Equal Earth; diverging scale when values change sign), `make-map density` (points → accumulation map), `make-map situation_map` (one YAML config → areas-of-control plate; fifteen worked plates) | `make-map audit` (eleven static rules on a finished plate), `make-map improve` |
| **sprezzature-video** | `make-film captions` (narration script + **measured** audio → WebVTT, not a transcript), `make-film poster` (the idle frame, baked as frame 0 where a feed regenerates its own thumbnail) | `make-film verify` (every declared claim against the code that decides it — exit 1 means the film is lying), `make-film scan` (every number on screen that no claim accounts for), `make-film assets` (tracked / derived / nowhere-else; a divergence is reported, never silently repaired) |

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
is the right pick, see [LANDSCAPE.md](https://github.com/warith-harchaoui/sprezzature/blob/main/LANDSCAPE.md) (French:
[PAYSAGE.md](https://github.com/warith-harchaoui/sprezzature/blob/main/PAYSAGE.md)). It opens with a single **competitive-positioning**
table (projects × criteria, rated 1–5 ⭐️) that feeds
[standpoint](https://github.com/warith-harchaoui/standpoint) to plot a 2-D map
of where `sprezzature` stands. For real sites
already shipped on the stack, see [GALLERY.md](https://github.com/warith-harchaoui/sprezzature/blob/main/GALLERY.md). For copy-paste
recipes per skill (with expected output), see [`EXAMPLES.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/EXAMPLES.md).

## What the skills enforce

- Output uses vanilla JavaScript (JS) (ES modules, native `<dialog>`, custom elements when justified). No React, Vue, Svelte, Next.js, Nuxt, Angular, Solid.
- Output uses Tailwind utility classes with semantic tokens (`bg-brand-blue`, `text-label-primary`). No raw hex literals in markup.
- Output enforces the **three-Roboto rule**: exactly three downloaded webfonts, all from the Roboto super-family: **Roboto** (sans / UI / body), **Roboto Serif** (editorial / longform / prose-heavy landings), **Roboto Mono** (`<code>`, `<pre>`, terminal panels, log output). No other downloaded family is allowed (no Inter, no Montserrat, no IBM Plex, no JetBrains Mono). The three siblings share metrics and x-height by design; prose-heavy and code-heavy surfaces stay typographically coherent. All three are self-hosted (no Google Fonts content-delivery network (CDN) in production); Web Open Font Format 2 (WOFF2) + SIL Open Font License (OFL) live under `sprezzature-ui/assets/fonts/roboto/`, `…/roboto-serif/`, `…/roboto-mono/`.
- Output sets a `dark:` peer on every styled element, uses `<button>`/`<a>`/`<label>`/`<dialog>`/`<form>` first, exposes a visible focus ring, honors `prefers-reduced-motion` and meets a 44×44 px hit area.
- Output exposes a **🌞 Light / 🌚 Dark / 🌗 Auto toggle** (canonical placement: top-right of sticky header → footer far-right → fixed bottom-right anchor when there is no header). **Auto is the default** so a fresh visitor inherits their operating-system (OS) choice and is never surprised by a hard-coded scheme. Component: `sprezzature-ui/assets/components/theme-toggle.html`. Wiring: `sprezzature-ui/references/stack-vanilla-js.md` § "Theme switching".
- Color choices map to the palettes in `sprezzature-ui/references/color-psychology.md` (source: <https://deraison.ai/colors/>).
- Skill output is **prototype-grade single-file HTML** by default, suitable for demos, mockups, internal tools and small landing pages. The starter page uses the Tailwind Play CDN, which Tailwind itself warns is for prototyping only. For production sites at scale, run **Tailwind CLI** or **Vite + Tailwind** over the emitted HTML before shipping; the class names are stable, so the same files survive the swap. See `sprezzature-ui/references/stack-tailwind.md`.
- Bilingual-ready copy (EN/FR by default). The output language of the AI-backed scripts is **auto-detected from the input/context text** via `langdetect`: no configured default language; pass `--lang` to force one. For translatable UI strings and prompts, use one `locales/i18n.yaml` catalog (see `sprezzature-ui-i18n-make` and `sprezzature-publish/references/i18n.md`).
- **i18n lives in YAML (the YAML configuration format), never in JS.** Translatable strings, GUI labels **and** LLM prompts, belong in a single per-project catalog, **`locales/i18n.yaml`** (message id → per-locale text), loaded at runtime; never a translation dict baked into JavaScript, never a prompt inlined in Python. GUI strings and prompts share `locales/i18n.yaml` because they share one concern: *language*. Prompts already ship this way (`prompts/*.yaml`, loaded via `_prompts.load_prompt`); the same rule governs generated GUIs, on both the **make** (scaffold + read `locales/i18n.yaml`) and **audit** (flag any GUI string or prompt living outside it: hardcoded in JS or inlined in Python) sides.

## Status

A snapshot of where each surface stands. The ten skill folders are stable; the only WiP area is **audio captions** (sprezzature-audio, video → text). **Narration** (text → audio: sprezzature-audio makes the voice, sprezzature-publish wires it into the page with a read-along) is stable and clearly framed as optional editorial enhancement, not Web Content Accessibility Guidelines (WCAG) compliance.

| Area | Status | Notes |
|---|---|---|
| `sprezzature-ui` (stack rules, tokens, components, dataviz, checklist, i18n) | Stable | Stack rules documented; `scripts/validate_content.py` gates framework imports; the package ships `sprezzature-ui-i18n-audit` (I18N001, I18N002) and `-i18n-make`. |
| `sprezzature-cli` (unified `sprezzature` driver, shell completion) | Stable | Click-based; routes to the ten bricks' own commands, and forwards `--help` to them. |
| `sprezzature-cli-gui` (CLI → GUI flagship) | Stable (skill + runnable demo) | `assets/examples/cli-gui-demo/` runs end-to-end. Production hardening (auth, rate-limit, sandbox) deliberately left to the host. |
| `sprezzature-publish` (Markdown site, meta tags, favicons, indexes, plain language, narration, SEO + GEO + AEO) | Stable | Thirteen tools: the site artifacts, the Markdown lint and site audit, narration and read-along, and since 1.4.0 `cta`, `faq` and `findable`, which order search, generative and answer engine work by the site's declared call to action. |
| `sprezzature-accessibility`: lint | Stable | 20-rule static a11y lint from the source, six rules with a safe `--fix`. |
| `sprezzature-colors`: contrast audit, color-vision-deficiency (CVD) simulation, curated palette, perceptual lighten / darken | Stable | OKLCH (the perceptual OKLCH color space)-neighbour contrast fixer, Machado CVD matrices, unified palette CSV (Apple base + emotion / concept / psychology projections), stdlib-only `_colors` module, `Color` class. Split out of `sprezzature-accessibility` for clearer scope. |
| `sprezzature-accessibility`: W3C alt text via local Ollama vision | Stable | Model `qwen3-vl:8b` via Ollama (the one authorized LLM). Per-purpose decision tree, surrounding-text + vocabulary biasing, on-disk cache; `--fix-alt` writes it into the page. Was `sprezzature-vision` until it merged into `sprezzature-accessibility`. Wikipedia-fixture alt-text eval. |
| `sprezzature-audio`: **WebVTT / SRT captions via local whisper.cpp** | **WiP / TODO** | `sprezzature-audio-captions` is functional; what's missing is per-language word-error-rate (WER) baselines (`en` / `fr` / `es` extractor wired but baselines not yet published), the user-supplied `vocab-biasing-clip.wav`, and a planned `pdbms`-based revision of the whisper.cpp integration. See [Roadmap](https://github.com/warith-harchaoui/sprezzature/blob/main/CHANGELOG.md#roadmap). |
| `sprezzature-figures`, `-maps`, `-ux-laws` | Stable | figures draws 168 chart types; maps classes its choropleths and names the method; ux-laws audits a page against the Laws of UX. |
| `sprezzature-video` (claims, scan, asset ledger, captions, poster) | Stable, pre-1.0 | The surface may still move between minor versions. |
| `LISEZMOI.md` (French README) | Stable | At structural parity with this README, same section ordering, content kept in lock-step on every release. |

For the per-release detail (and what's planned next), see [`CHANGELOG.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/CHANGELOG.md).

## Inputs → outputs

What you give the agent and what comes back. Each row is a self-contained flow; pick one, ignore the rest.

| You provide | Phrase | Skill | Output |
|---|---|---|---|
| A working CLI (a Python `argparse` / Click / Typer parser, or any tool's `--help` text) | "Wrap this CLI in a GUI" + the project path | `sprezzature-cli-gui` | One self-contained `index.html`, Tailwind config and script inline, sub-commands mapped to forms / file inputs / choice lists. The form builds the exact command line; you wire it to your host (Tauri / Electron / FastAPI / Express / browser stub). An audit command checks the page still covers the parser. |
| A folder of Markdown files (README, `docs/**`, blog posts) | "Turn these markdown files into a website" | `sprezzature-publish` | Static site: one HTML page per `.md`, sticky top bar, sidebar TOC for `docs/`, dark-mode peer, favicons, `<meta>` tags, `robots.txt` + `sitemap.xml` + `llms.txt` + Atom feed. |
| A free-form ask ("primary button", "confirm dialog", "settings page") | "Build a `<component>`" | `sprezzature-ui` | Semantic HTML + Tailwind + minimal vanilla JS, focus ring, `dark:` peer, 44×44 hit area, `Escape` close on dialogs, reduced-motion guard. |
| A data shape (CSV, JSON, a few rows) | "Chart this" / "Dashboard for X" | `sprezzature-ui` | Inline SVG + `<figure>` wrapper. House style, palette from `color-psychology.md`, polarity-tagged axes, `role="img"`. |
| An existing HTML page or screenshot | "Audit this" / "WCAG check" / "Make it look less AI" | `sprezzature-ui` (anti-patterns, ergonomics) + `sprezzature-accessibility` (lint) + `sprezzature-colors` (contrast, CVD) | Findings against the 8 ergonomic criteria + anti-patterns catalogue; concrete diffs; pre-ship checklist run; `sprezzature-accessibility-lint` + `sprezzature-colors-contrast` + `sprezzature-colors-cvd` output. |
| An image file (`*.png`, `*.jpg`, …) | "Alt text for this image" | `sprezzature-accessibility` | W3C-compliant alt text for the right purpose category (informative / decorative / functional / text / complex / group), in the page's language, tagged `data-alt-source="ai"`. |
| An audio or video file (`.mp4`, `.wav`, `.mp3`, …), **WiP** | "Captions / transcript" | `sprezzature-audio` *(work in progress)* | WebVTT / SRT / plain-text captions from local whisper.cpp, with project-vocab biasing. `<video>` + `<track kind="captions">` snippet. Script + tests ship today; per-language WER baselines and the vocab-biasing reference clip are still being collected; see [Status](#status). |
| A logo (`logo.png` / `.svg`) | "Favicon set" / "PWA icons" | `sprezzature-publish` | `favicon.svg` + `.ico` + PNG set + `apple-touch-icon.png` + maskable PWA icon + `site.webmanifest` + a `head.html` snippet. |
| A goal description or an HTML page | "Meta tags" / "SEO" / "OG card" / "GEO" / "llms.txt" / "AI Overview" | `sprezzature-publish` | **For search-engine optimization (SEO):** title + description + Open Graph (OG) + Twitter Card + Schema.org JSON for Linking Data (JSON-LD) (JSON on stdout): see [Google's three Search Essentials pillars](https://developers.google.com/search/docs/essentials) applied in `sprezzature-publish/references/seo-essentials.md`. **For generative-engine optimization (GEO)** (Generative Engine Optimization, AI Overview / Gemini / ChatGPT answer surfaces): `llms.txt` is emitted by `sprezzature-publish-indexes` alongside `robots.txt` + `sitemap.xml` + Atom/really-simple-syndication (RSS), so the site ships an LLM-readable Markdown summary the moment any "turn this into a website" run completes. Same crawlers, same `robots.txt` permissions; no separate "AI" meta tag exists; anything claiming one is wrong. |
| An existing site (HTML, PHP, Markdown, JSON, YAML) | "My site doesn't sell" / "Write me a FAQ" / "AEO" | `sprezzature-publish` | First a question: which call to action is the site for (detection offers what it already links to). Then the FAQ the site is missing, every answer drawn from its own pages and the unanswerable questions listed apart; and one SEO + GEO + AEO report, money pages first. |
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
VERSION=$(curl -fsSL https://api.github.com/repos/warith-harchaoui/sprezzature/releases/latest \
  | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p')
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
cp -r sprezzature-accessibility ~/.${RUNTIME}/skills/   # only if you need static a11y lint or AI alt text
cp -r sprezzature-colors        ~/.${RUNTIME}/skills/   # only if you need WCAG contrast / CVD / palette
cp -r sprezzature-audio         ~/.${RUNTIME}/skills/   # only if you need captions or narration (local)
cp -r sprezzature-ux-laws       ~/.${RUNTIME}/skills/   # only if you want the Laws-of-UX audit + reference
cp -r sprezzature-figures       ~/.${RUNTIME}/skills/   # only if you emit dataviz / SHAP / DoWhy figures
cp -r sprezzature-maps          ~/.${RUNTIME}/skills/   # only if your numbers are attached to places
cp -r sprezzature-video         ~/.${RUNTIME}/skills/   # only if a video states facts about your project
```

Install in **both** runtimes if you switch between them, the same
folder copied to two paths.

### 3. Verify

```bash
# A skill is installed and its SKILL.md is on disk:
ls ~/.${RUNTIME}/skills/sprezzature-ui/SKILL.md

# Optional: if you cloned the repo too, verify every installed skill
# against the Anthropic spec (stdlib + PyYAML, no network):
python3 scripts/validate_all.py
```

The runtime reads each skill's `SKILL.md` frontmatter description at
conversation start; matching prompts auto-trigger the skill. See
[`TRIGGERS.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/TRIGGERS.md) for the per-phrase index.

### Cleanup: remove stale or renamed skills

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
that no longer ships from this repo. Read [`SKILLS.txt`](https://github.com/warith-harchaoui/sprezzature/blob/main/SKILLS.txt)
for the canonical list.

### Upgrade

Repeat steps 1–3 with the new `VERSION`. The on-disk skill folder
name is stable so each `cp -r` overwrites in place: no manual
removal between versions, except when a skill is **renamed** (use
the cleanup helper above for those). Skill renames are listed in
[`CHANGELOG.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/CHANGELOG.md).

### Install from source (contributor / developer path)

To iterate on the skills, or pin to a commit that has not been
tagged, clone and copy from the working tree. No checksum step:
you are responsible for verifying you cloned the commit you intended.

```bash
git clone https://github.com/warith-harchaoui/sprezzature.git
cd sprezzature
python3 -m pip install -r requirements-dev.txt   # PyYAML + pytest
python3 -m pytest                                # full deterministic suite
python3 scripts/validate_all.py                  # all 10 skills, YAML + content

# Mirrors step 2 above:
RUNTIME=claude   # or opencode
mkdir -p ~/.${RUNTIME}/skills
for skill in $(grep -v '^[[:space:]]*#' SKILLS.txt | grep -v '^[[:space:]]*$'); do
    cp -r "$skill" ~/.${RUNTIME}/skills/
done
```

`CONTRIBUTING.md` walks the same flow at the contributor level.

### OpenCode + local Ollama: the zero-token path

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

The fit with this repo is direct: **three sprezzature-* bricks already
talk to a local Ollama daemon** for their AI surfaces: `sprezzature-accessibility`
(alt text, `make-alt`), `sprezzature-publish` (`-meta`, `-plain`, `-faq`,
`-lint --ai`, `-narrate --ai-hints`) and `sprezzature-audio` (`-name`,
`-translate`). When you
run OpenCode against the same Ollama daemon, the whole loop,
agent + skill-driven scripts, uses one local model. Zero
external calls.

```bash
# Quick start. Assumes Ollama + an OpenCode binary on PATH.
ollama serve &         # start the daemon
ollama pull qwen3-vl:8b  # the one model, used by the agent loop AND every skill script
```

One model handles the whole stack: it drives the OpenCode agent
loop AND backs every sprezzature-* Ollama-backed script
(`make-alt`, `sprezzature-publish-meta`, `-plain`, `-faq`,
`sprezzature-audio-translate`, …). Same daemon, same tag, same answer for "which
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
# → The sprezzature-accessibility / sprezzature-publish Ollama-backed scripts hit the
#   same daemon for their per-script work.
# → Cost: 0 tokens; nothing leaves the machine.
```

One model, `qwen3-vl:8b`, backs both the agent loop and every
skill script, same daemon, same tag. `qwen3-vl:8b` is multimodal, so
the vision script (alt text) works on the same model as the text
scripts. There is nothing else to pick.

#### LLM choice: why Qwen3-VL 8B (Q4_K_M)

The single model is **Qwen3-VL 8B**, Q4_K_M quantization, pulled with
`ollama pull qwen3-vl:8b` (~6.1 GB). It was chosen against four criteria for a
bilingual, image-heavy, Mac-local toolkit: **vision**, **French**,
**OCR / charts**, and **Apple-Silicon fit**. It is the only ≈8B model that is
top-tier on vision, OCR/charts, and Mac-fit at once while being strong on
French (DocVQA 96.1%, OCRBench ~896, ScreenSpot 94.4%, OCR across 32 languages).
The full rationale, the scored comparison against Gemma 3, Pixtral, InternVL,
MiniCPM, and the specialist OCR models, and all research sources are in
[`docs/LLM_CHOICE.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/docs/LLM_CHOICE.md). The rule is machine-enforced by
`tests/test_single_llm.py`.

#### Configure the skill scripts (same daemon, separate env vars)

OpenCode drives the agent; the skill scripts that *also* talk to
Ollama (alt text, meta tags, plain-language rewrites, FAQ, caption
translation) read their own env vars. There is **no overlap with
`OPENCODE_MODEL`**; set both, both should agree on the daemon
web address (URL), but the model tag can differ. Every model call goes
through [best-engine-ai-helper](https://github.com/warith-harchaoui/best-engine-ai-helper),
which reads the daemon address itself:

| Env var | Read by | What it does | Default |
|---|---|---|---|
| `BEST_LLM_BASE_URL` | best-engine-ai-helper, so `make-alt`, `sprezzature-publish-meta`, `-plain`, `-faq` | Daemon endpoint. Must match the URL OpenCode talks to. | `http://localhost:11434` |
| `OLLAMA_URL` | `sprezzature-audio-translate` and `-name` (as their `--url` default), `sprezzature-publish-lint --ai` | Daemon endpoint for these three. `make-alt`, `-meta` and `-plain` read it too, but only to name it in their error message. | `http://localhost:11434` |
| `OLLAMA_MODEL` | every Ollama-backed script | Bare escape hatch (mainly for tests). The one authorized model is `qwen3-vl:8b`. | `qwen3-vl:8b` |
| `OPENCODE_MODEL` | OpenCode itself | Agent-side model tag; set it to `qwen3-vl:8b`. | `qwen3-vl:8b` |

The pattern is deliberately boring: `qwen3-vl:8b` on the same daemon
for both the agent and the scripts. `qwen3-vl:8b` is multimodal, so the
vision script and the text scripts share it: no per-concern model
juggling, no MLX.

```bash
# One daemon, one model, for everything.
export BEST_LLM_BASE_URL=http://localhost:11434
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
locally. See [`SECURITY.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/SECURITY.md) for the full supply-chain
note.

### Shell completion

The `sprezzature` driver, `sprezzature-skills`, and every command the ten
bricks install are Click, so they ship `bash` / `zsh` / `fish` completion for
free via Click's `_<TOOL>_COMPLETE=<shell>_source` trick. See
[`sprezzature-cli/README.md`](https://github.com/warith-harchaoui/sprezzature/blob/main/sprezzature-cli/README.md#shell-completion) for the
one-line setup per shell. The same env-var pattern works for any brick
command invoked directly (e.g.
`_SPREZZATURE_AUDIO_CAPTIONS_COMPLETE=zsh_source sprezzature-audio-captions`).

## Pre-commit hooks

Three repositories ship a `.pre-commit-hooks.yaml` manifest, so a project wires
those gates into [pre-commit](https://pre-commit.com/) with one `repo:` block
each. The other auditors run as `repo: local` hooks over the installed command.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/warith-harchaoui/sprezzature-publish
    rev: v1.5.0          # pin a tag; bump with renovate / dependabot
    hooks:
      - id: sprezzature-publish-lint        # the Markdown
  - repo: https://github.com/warith-harchaoui/sprezzature-ui
    rev: v1.2.2
    hooks:
      - id: sprezzature-ui-i18n-audit       # strings outside locales/i18n.yaml
  - repo: https://github.com/warith-harchaoui/sprezzature
    rev: v1.8.1
    hooks:
      - id: sprezzature-ui-validate-skill   # only if you ship skills yourself
      - id: sprezzature-triggers-sync
  - repo: local
    hooks:
      - id: sprezzature-accessibility-lint
        name: a11y lint
        entry: sprezzature-accessibility-lint
        language: system
        files: '\.html?$'
      - id: sprezzature-ux-laws
        name: Laws of UX
        entry: sprezzature-ux-laws
        language: system
        files: '\.html?$'
        # args: [--fix] enables the four mechanical repairs
```

A `repo: local` hook runs the command from your own environment, so
`pip install sprezzature-accessibility sprezzature-ux-laws` there first.

## CLI → GUI flagship

The `sprezzature-cli-gui` skill takes an existing CLI and produces a single-page vanilla-JS + Tailwind GUI for it. It reads the argument parser, categorizes each command (one-shot / form / streaming / list), maps flags to form controls, and wires execution to the project's host (Tauri, Electron, FastAPI, Express, or a stdlib HyperText Transfer Protocol (HTTP)+server-sent events (SSE) proxy).

A runnable worked example ships in `sprezzature-cli-gui/assets/examples/cli-gui-demo/`. Launch:

```bash
cd sprezzature-cli-gui/assets/examples/cli-gui-demo
python server.py  # stdlib only, opens http://localhost:8787
```

For an honest comparison against Gradio / Streamlit / Tauri / Taipy, see `sprezzature-cli-gui/SKILL.md` → "Why this skill, not Gradio / Streamlit / Tauri / Taipy" and [LANDSCAPE.md](https://github.com/warith-harchaoui/sprezzature/blob/main/LANDSCAPE.md) § 7.

## Author

[Warith HARCHAOUI, Ph.D.](https://www.linkedin.com/in/warith-harchaoui/)

Ten Claude / OpenCode **skills** for a single frontend stack: vanilla JavaScript, Tailwind CSS, and the three-Roboto typography rule (Roboto / Roboto Serif / Roboto Mono). Built to the [Anthropic skill specification](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf).

Special thanks to:

  + [Audrey DEJOUX](https://www.behance.net/dreyadesign/projects),

  + [Laurent PANTANACCE](https://www.linkedin.com/in/pantanacce/),

  + [Auguste BAUM](https://www.linkedin.com/in/auguste-baum/),

  + [Julien BOYER](https://www.linkedin.com/in/julien-boyer-2a76878/) and

  + [Jérôme GOMBERT](https://www.linkedin.com/in/j%C3%A9r%C3%B4me-gombert-84675b1b/)

for fruitful discussions.

Color palettes from <https://deraison.ai/colors/>.

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
