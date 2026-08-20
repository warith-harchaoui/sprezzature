---
name: sprezzature-publish
description: >-
  Turn a folder of Markdown (README + docs/ + blog/) into a static site with
  per-page meta tags (Open Graph + Twitter Card + Schema.org JSON-LD), a full
  favicon / app-icon / PWA-icon set from one logo, robots.txt + sitemap.xml +
  llms.txt + llms-full.txt + Atom / RSS + humans.txt, plain-language rewrites, and MP3
  narration via local OSS TTS. Trigger phrases: "markdown to website", "meta
  tags", "OG card", "SEO", "AI Overview", "GEO", "favicons", "app icons",
  "robots.txt", "sitemap", "llms.txt", "llms-full.txt", "Atom feed", "RSS",
  "plain language", "rewrite at grade N", "simplify this copy",
  "narrate this post", "podcast my blog", "text to speech",
  "schema.org JSON-LD", "humans.txt", "lint markdown",
  "OpenVoice / Chatterbox TTS". Applies Google's SEO + GEO (AI
  Optimization) foundations to the emitted artifacts. For solo developers and
  small teams shipping a site without an SSG. Output follows the sprezzature-ui
  stack rules; install sprezzature-ui alongside for the full design tokens.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Core scripts (favicons,
  site_indexes, plain_language, meta_from_ollama, md_to_html, lint_markdown)
  need Python 3.10+ with stdlib + Pillow + PyYAML; meta_from_ollama and
  plain_language additionally need a running local Ollama daemon. Optional
  audio narration (narrate_post + OpenVoice v2 or ChatterboxTTS) pulls
  torch + torchaudio; installed only when explicitly opted into.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
---

# sprezzature-publish — Markdown → website, meta, icons, indexes, plain language

## Audience and positioning

Solo developers and small teams shipping:

- A docs site for a small project (≤ 30 pages).
- A project landing page from a single README.
- A research / portfolio site from a few Markdown files.
- An indie blog with ≤ 50 posts.

This skill is **not** the right pick for a docs site with hundreds of versioned pages; pick MkDocs Material, Hugo, or Astro instead. For React-driven content sites, pick Docusaurus.

## What it does

| Trigger phrase | Output |
|---|---|
| "turn these markdown files into a website" | Static HTML per `.md` + sticky top nav + sidebar TOC for `docs/` + dark-mode peer + favicons + meta tags + robots / sitemap / llms.txt / llms-full.txt / Atom feed |
| "meta tags" / "SEO" / "OG card" / "Twitter card" / "JSON-LD" | Title + description + Open Graph + Twitter + Schema.org `@type`, JSON on stdout |
| "SEO" / "AI search" / "AI Overview" / "discoverability" / "is this advice true?" | Google's three pillars + AI Optimization foundations applied to the artifacts this skill emits; see `references/seo-essentials.md` |
| "GEO" / "Generative Engine Optimization" / "llms.txt" / "make my site readable by ChatGPT / Gemini / Perplexity" | `scripts/site_indexes.py` already emits `llms.txt` (a Markdown index of the site) plus `llms-full.txt` (the full-text corpus, Markdown sources only) alongside `robots.txt` + `sitemap.xml`. GEO and SEO share crawlers; same `robots.txt` permits both. There is **no separate "AI" meta tag**: refuse to emit one and cite `references/seo-essentials.md`. |
| "favicons" / "app icons" / "PWA icons" | `favicon.svg` + `.ico` + PNG set + `apple-touch-icon.png` + maskable PWA icon + `site.webmanifest` + `head.html` snippet |
| "robots.txt" / "sitemap.xml" / "llms.txt" / "llms-full.txt" / "feed" / "Atom" / "RSS" / "humans.txt" | All from a single command; auto-detects a blog folder for the feed |
| "plain language" / "simplify this copy" / "rewrite at grade N" | Same meaning, marketing voice stripped, output length ≤ 1.1× original |

## Two modes: make and audit

Ten make-side scripts paired with one audit-side gate.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — generate site artifacts | `favicons.py`, `meta_from_ollama.py`, `site_indexes.py`, `plain_language.py`, `md_to_html.py`, `narrate.py`, `install_narrate.py` | Favicons + PWA, meta tags, robots / sitemap / llms.txt / Atom, plain-language rewrite, Markdown → HTML, optional MP3 narration. |
| **Audit** — gate the emitted Markdown | `lint_markdown.py` | Markdown lint with project-aware rules (heading order, fenced-code language, link freshness). |

Pair the emitted HTML with `sprezzature-accessibility/scripts/lint_a11y.py`
(a11y) and `sprezzature-colors/scripts/audit_contrast.py` (contrast) to
complete the audit side end-to-end.

## Markdown → website workflow

When the user points to a Markdown-only project and asks for a website:

1. **Inventory the Markdown.** Walk the tree. Group files by purpose: landing (`README.md`), documentation (`docs/**/*.md`), blog posts (`posts/**`, `blog/**`), references, changelogs. Note frontmatter conventions if present.
2. **Pick a site shape**:
   - One README → single landing page with anchored sections from the headings.
   - README + a `docs/` tree → two-pane docs site (sidebar TOC + content).
   - Blog directory → home with post list + per-post pages + tag pages.
3. **Build a route map**. Each Markdown file becomes one HTML page; preserve the directory shape under the output root. Landing at `/index.html`.
4. **Generate navigation**:
   - Sticky top bar with the project name on start, theme switcher on end.
   - Sidebar (lg:) with section tree on `docs/**` pages.
   - Bottom tab bar (mobile) when ≤ 5 top-level destinations.
5. **Convert Markdown to HTML**. Prefer a build-step tool (Pandoc, `markdown-it`, `python-markdown`) so the output is plain HTML; do not import a Markdown runtime into the browser. Apply typography classes from `sprezzature-ui/references/stack-tailwind.md`. Code blocks get a server-side syntax highlighter (Pygments, `highlight.js` build step); never load a runtime highlighter.
6. **Wire meta tags per page** using `references/meta-tags.md` and (optional) `python scripts/meta_from_ollama.py path/to/page.html`.
7. **Generate the favicon set** from the project's logo: `python scripts/favicons.py logo.png --out public --name "Project name"`. Drop the produced `head.html` snippet into the layout template.
8. **Emit indexes**: `python scripts/site_indexes.py --root . --base-url https://example.com [--feed-from posts]` — produces robots.txt + sitemap.xml + llms.txt + llms-full.txt + optional Atom feed.
9. **Emit pages + assets**. One `index.html` per page, one shared `app.js` (theme switcher, search if needed), one `styles.css` (Tailwind directives + the three Roboto families per the three-Roboto rule). Include the favicon set under `public/`. Add a small `README.md` to the output root explaining the build.

Output is static HTML + CSS + a small `app.js`. For a small project (≤ 30 pages, prototype-grade) the Tailwind Play CDN keeps the deliverable build-free and it drops into GitHub Pages / Netlify / S3 / Nginx as-is. For anything you treat as production, run the Tailwind CLI / Vite build step from `sprezzature-ui/references/stack-tailwind.md` over the emitted HTML before deploying; the class names are stable, so the same files survive the swap.

## Stack rules (inherited)

Output follows the sprezzature-ui stack rules: vanilla JS, Tailwind, and the three-Roboto rule (Roboto for sans / UI, Roboto Serif for editorial longform, Roboto Mono for code and log panels). If sprezzature-ui is not installed, see `sprezzature-ui/SKILL.md` for the full ruleset.

## Tool composition (take initiative)

When emitting a whole website, compose the scripts in this order:

```text
favicons.py        # icons + manifest
↓
meta_from_ollama.py  # per page: title, description, OG, JSON-LD
↓
site_indexes.py    # robots, sitemap, llms.txt, llms-full.txt, feed
↓
plain_language.py  # optional: simplify draft copy
```

Then run `sprezzature-accessibility/scripts/lint_a11y.py` over the output and `sprezzature-colors/scripts/audit_contrast.py` over the palette before declaring "done".

**Optional editorial step** — audio narration per post:

```text
narrate_post.py            # one MP3 per Markdown post (opt-in)
↓
site_indexes.py            # re-run with --audio-manifest to inject
                           # <enclosure> rows → RSS feed = podcast feed
```

The narration pipeline is **not WCAG-required** (screen readers cover
text accessibility); it's an editorial choice for multitasking
audience / podcast positioning / cognitive-accessibility alternative
formats. Triggered by "narrate this post", "audio version of the
blog", "podcast feed from posts", "TTS this article". See
`references/audio-narration.md` for the placement rules (player
top-of-article), engine matrix (OpenVoice v2 + ChatterboxTTS, both
MIT for code AND weights), voice cloning ethics, and Schema.org /
OpenGraph metadata.

## When NOT to use this skill

- Versioned docs (semantic versioning, side-by-side per-release docs) → Hugo / MkDocs Material / Docusaurus.
- 100+ Markdown pages → an SSG with incremental rebuilds is faster.
- Heavy templating (custom shortcodes, partials, theme inheritance) → use a real SSG; this skill emits flat HTML.

## References

- `references/meta-tags.md` — `<meta>` tags per W3C / WHATWG + Open Graph + Twitter Cards + Schema.org JSON-LD.
- `references/site-indexes.md` — robots.txt, sitemap.xml, llms.txt, llms-full.txt, Atom / RSS, humans.txt.
- `references/seo-essentials.md` — Google's three Search Essentials pillars + the AI Optimization Guide's foundations, applied concretely to the artifacts this skill emits. Use it when the user asks about SEO / AI search / "is this third-party advice true?".
- `references/plain-language.md` — rewrite copy at a target reading level; preserves meaning.
- `references/audio-narration.md` — *(optional editorial enhancement, not WCAG-required)* turn a Markdown post into a narrated WAV/MP3 via OpenVoice v2 or ChatterboxTTS (both MIT for code AND weights). Structural narration hints from headings / lists / blockquotes / emoji, optional LLM enrichment via the same local Ollama daemon already used for alt-text, voice cloning from a 6-30 s designer-supplied sample, RSS enclosure injection turns the blog feed into a podcast feed.
- `references/i18n.md` — multilingual frontend (URL strategy, `Intl.*`, plurals, RTL, persisted choice). Default language pair is configurable per project (EN/FR, EN/DE, EN/ES, EN/JA, …).

## Scripts

| Script | Install | Purpose |
|---|---|---|
| `scripts/favicons.py` | `pip install -r scripts/requirements-favicons.txt` | Full favicon / PWA icon set + manifest + head snippet from a single logo |
| `scripts/meta_from_ollama.py` | `pip install -r scripts/requirements-meta-tags.txt` + Ollama | Drafts title / description / OG / Twitter / JSON-LD from a goal or HTML page |
| `scripts/site_indexes.py` | stdlib only | robots.txt + sitemap.xml + llms.txt + llms-full.txt + Atom / RSS + humans.txt |
| `scripts/plain_language.py` | `pip install -r scripts/requirements-plain-language.txt` + Ollama | Rewrites copy at a target grade; strips marketing voice |
| `scripts/narrate_post.py` *(optional)* | `pip install -r scripts/requirements-narrate-{openvoice\|chatterbox}.txt` + `install_narrate.py` | Narrate a Markdown post via local OSS TTS. Engine-agnostic orchestrator; default off. Editorial enhancement, not WCAG-required. |
| `scripts/narrate_openvoice.py` / `narrate_chatterbox.py` *(optional)* | as above | Engine wrappers invoked as subprocesses by `narrate_post.py`. |
| `scripts/pick_voice.py` *(optional)* | as above | Lists engine voices + generates per-voice demo clips so the designer chooses by listening. |
| `scripts/install_narrate.py` *(optional)* | subprocess | Downloads OpenVoice v2 checkpoints + sets up the ChatterboxTTS voice library directory. |
| `scripts/_lang.py`, `scripts/_ollama.py`, `scripts/_narrate.py` | (internal helpers) | Language detection + Ollama client + narration segment extractor shared by other scripts |

## Companion skills

| You also need… | Install |
|---|---|
| Full UI design tokens, components, dark mode, dataviz | `sprezzature-ui` |
| a11y lint (static HTML) | `sprezzature-accessibility` |
| WCAG contrast audit, CVD simulation, curated palette | `sprezzature-colors` |
| W3C alt text via local Ollama vision | `sprezzature-vision` |
| WebVTT / SRT captions via local whisper.cpp | `sprezzature-audio` |
| Wrap a CLI in a GUI | `sprezzature-cli-gui` |
