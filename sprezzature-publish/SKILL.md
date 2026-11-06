---
name: sprezzature-publish
description: >-
  Turn a folder of Markdown into a static site: meta tags (Open Graph,
  Twitter Card, JSON-LD), a favicon / PWA set from one logo, robots.txt +
  sitemap.xml + llms.txt + Atom / RSS, plain-language rewrites, local TTS
  narration with a read-along. Audits a site that already exists (HTML, PHP,
  no Markdown needed). SEO, GEO and AEO ordered by the call to action: asks
  which CTA the site is for, builds the FAQ it lacks from its own pages, one
  report with money pages first. Use it when you are holding writing that
  has to become a findable site, or a site whose readers should book, buy or
  install. Trigger phrases: "markdown to website", "meta tags", "SEO",
  "GEO", "AEO", "write a FAQ", "favicons", "llms.txt", "audit my site",
  "narrate this post". Not this one when: the question is accessibility or
  alt text (sprezzature-accessibility), or the speech is recorded and needs
  transcribing (sprezzature-audio). The exhaustive trigger catalogue is in
  `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10 to 3.13. One
  ``pip install sprezzature-publish`` brings every tool (Pillow, PyYAML,
  markdown, click, FastAPI, fastapi-mcp, and sprezzature-audio for the voice:
  Chatterbox, Kokoro and OpenVoice, picked by speaker-helper's router); no
  feature extras. meta,
  plain, faq (unless ``--no-llm``), ``lint --ai`` and ``narrate --ai-hints``
  also need a running local Ollama daemon.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.1
---

# sprezzature-publish — Markdown → website, meta, icons, indexes, plain language

> The deterministic tools below now ship as the standalone package [`sprezzature-publish`](https://github.com/warith-harchaoui/sprezzature-publish) (`pip install sprezzature-publish`), invoked as `sprezzature-publish-lint`, `-html`, `-icons`, `-indexes` and the rest — or through the click front door, under two names that are one callable, `make-site <tool>` and `sprezzature-publish <tool>`. Importable as `from sprezzature_publish import lint_file`, and reachable over HTTP or MCP: `sprezzature-publish-mcp --port 8000` serves seven routes plus `GET /health` and, on the same port, `/mcp` with the same eight as tools (`lint_markdown`, `audit_site`, `render_markdown`, `rewrite_plainly`, `find_calls_to_action`, `build_faq`, `report_findability`, `health`); the Docker image runs that command. Icons, indexes, meta, narration, read-along and the changelog feed stay commands. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

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
| "turn these markdown files into a website" | Static HTML per `.md` + sticky header + dark-mode peer (a sidebar for `docs/` is built by hand, workflow step 4) + favicons + meta tags + robots / sitemap / llms.txt / llms-full.txt / Atom feed |
| "meta tags" / "SEO" / "OG card" / "Twitter card" / "JSON-LD" | Title + description + Open Graph + Twitter + Schema.org `@type`, JSON on stdout |
| "SEO" / "AI search" / "AI Overview" / "discoverability" / "is this advice true?" | Google's three pillars + AI Optimization foundations applied to the artifacts this skill emits; see `references/seo-essentials.md` |
| "GEO" / "Generative Engine Optimization" / "llms.txt" / "make my site readable by ChatGPT / Gemini / Perplexity" | `sprezzature-publish-indexes` already emits `llms.txt` (a Markdown index of the site) plus `llms-full.txt` (the full-text corpus, Markdown sources only) alongside `robots.txt` + `sitemap.xml`. GEO and SEO share crawlers; same `robots.txt` permits both. There is **no separate "AI" meta tag**: refuse to emit one and cite `references/seo-essentials.md`. |
| "favicons" / "app icons" / "PWA icons" | `favicon.svg` + `.ico` + PNG set + `apple-touch-icon.png` + maskable PWA icon + `site.webmanifest` + `head.html` snippet |
| "robots.txt" / "sitemap.xml" / "llms.txt" / "llms-full.txt" / "feed" / "Atom" / "RSS" / "humans.txt" | All from a single command; auto-detects a blog folder for the feed |
| "plain language" / "simplify this copy" / "rewrite at grade N" | Same meaning, marketing voice stripped, output length ≤ 1.1× original |

## CTA first: ask before you run (SEO, GEO, AEO)

When the request is about a site's readers doing something — "my site
doesn't sell", "nobody books a call", "SEO", "GEO", "AEO", "write me a FAQ",
"show up in ChatGPT answers" — the first step is a **question to the user**,
not a command:

1. Run `sprezzature-publish-cta <site> --no-ask --top 8` (or the MCP tool
   `find_calls_to_action` with the pages) to see what the site already
   links to. **Show the candidates and ask**: which one action is this site
   for (book, buy, contact = *decide*; install, download, sign up =
   *evaluate*; read = *learn*), which secondary ones, for whom, and the one
   name of the organisation. Never pick for the user from the detection.
2. Write the answer to `ctas.yaml` (`sprezzature-publish-cta <site> --write
   ctas.yaml`, or by hand: `offer`, `organization`, `primary`,
   `secondary`). Over MCP, send it as the `ctas` parameter.
3. `sprezzature-publish-faq <site>` drafts the FAQ the site is missing:
   every answer from a passage of the site, every number from that passage,
   the rest in a gap report. It is a **draft**: show it, do not publish it.
   `--audit --fix` rebuilds `FAQPage` markup from the visible FAQ.
4. `sprezzature-publish-findable <site> --base-url …` is the one report,
   money pages first, each finding tagged `seo` / `geo` / `aeo`.
5. `sprezzature-publish-indexes … --offer "…" --cta "Label=URL"` so
   `llms.txt` leads with the offer and the CTA's own URL.

Never claim `FAQPage` markup ranks: Google stopped showing FAQ rich results
on 2026-05-07. The FAQ is built for its visible text. How many CTAs compete
on one screen is sprezzature-ux-laws (Hick), not this skill.

## Two modes: make and audit

Make-side commands paired with two audit-side tools — one before the render,
one after it. The second is the one that serves a site that **already
exists**, which has no Markdown to go back to.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — generate site artifacts | `sprezzature-publish-icons`, `-meta`, `-indexes`, `-plain`, `-html`, `-narrate`, `-readalong`, `-changelog` | Favicons + PWA, meta tags, robots / sitemap / llms.txt / Atom, plain-language rewrite, Markdown → HTML, optional narration and read-along, and one Atom + RSS feed from sibling repositories' `CHANGELOG.md`. The **voices themselves** ship with `sprezzature-audio`: captions turn sound into timed text, narration turns text into timed sound, and one package owns that modality in both directions. This one owns the document and the page. |
| **Make + audit** — what the site is for | `sprezzature-publish-cta`, `-faq`, `-findable` | Declared CTAs (`ctas.yaml`), the FAQ built from the site's own pages and its `FAQPage` markup, and the joint SEO + GEO + AEO report ordered by money pages. Reads HTML, PHP, Markdown, JSON and YAML. |
| **Audit** — before the render, gate the source | `sprezzature-publish-lint` | Markdown lint with project-aware rules (heading order, fenced-code language, trailing whitespace, empty image alt, a local link whose target is not on disk). `--fix` strips trailing whitespace and, with `--render-mermaid`, inserts the rendered PNG references; nothing else. |
| **Audit** — after the render, read what was emitted and repair it | `sprezzature-publish-audit` | `sprezzature-publish-audit <dir\|page\|url>`. Head meta, Open Graph, Twitter Card, JSON-LD, icon and manifest links, `robots.txt`, `sitemap.xml`, `llms.txt`, feed, icon set on disk. **No Markdown source required** — this is the tool for a site somebody else built. `--fix` writes back only what is *derived*: canonical from `--base-url`, `og:*` / `twitter:*` mirrored from the page's own title and description, the icon links from the `head.html` `favicons` wrote, `robots.txt` / `sitemap.xml` regenerated through `site_indexes`, and `og:image` / `<html lang>` only when `--og-image` / `--lang` are given and the page has none. The wording of a title, the choice of an `og:image` without `--og-image`, a JSON-LD body: reported with the command that drafts them, never written. A URL is reported, never repaired. |

Pair the emitted HTML with `sprezzature-accessibility-lint` (a11y) and
`sprezzature-colors-contrast` (contrast) to complete the audit side
end-to-end.

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
5. **Convert Markdown to HTML**. `sprezzature-publish-html <file-or-dir> --out site/` does it at build time (python-markdown, Mermaid rendered, KaTeX for math); any other build-step tool (Pandoc, `markdown-it`) is fine as long as the output is plain HTML; do not import a Markdown runtime into the browser. Apply typography classes from `sprezzature-ui/references/stack-tailwind.md`. Code blocks get a server-side syntax highlighter (Pygments, `highlight.js` build step); never load a runtime highlighter.
6. **Wire meta tags per page** using `references/meta-tags.md` and (optional) `sprezzature-publish-meta path/to/page.html`.
7. **Generate the favicon set** from the project's logo: `sprezzature-publish-icons logo.png --out public --name "Project name"`. Drop the produced `head.html` snippet into the layout template.
8. **Emit indexes**: `sprezzature-publish-indexes --root . --base-url https://example.com [--feed-from posts]` — produces robots.txt + sitemap.xml + llms.txt + llms-full.txt + optional Atom feed.
9. **Emit pages + assets**. One `index.html` per page, one shared `app.js` (theme switcher, search if needed), one `styles.css` (Tailwind directives + the three Roboto families per the three-Roboto rule). Include the favicon set under `public/`. Add a small `README.md` to the output root explaining the build.

Output is static HTML + CSS + a small `app.js`. For a small project (≤ 30 pages, prototype-grade) the Tailwind Play CDN keeps the deliverable build-free and it drops into GitHub Pages / Netlify / S3 / Nginx as-is. For anything you treat as production, run the Tailwind CLI / Vite build step from `sprezzature-ui/references/stack-tailwind.md` over the emitted HTML before deploying; the class names are stable, so the same files survive the swap.

## Stack rules (inherited)

Output follows the sprezzature-ui stack rules: vanilla JS, Tailwind, and the three-Roboto rule (Roboto for sans / UI, Roboto Serif for editorial longform, Roboto Mono for code and log panels). If sprezzature-ui is not installed, see `sprezzature-ui/SKILL.md` for the full ruleset.

## Tool composition (take initiative)

When emitting a whole website, compose the scripts in this order:

```text
sprezzature-publish-icons    # icons + manifest
↓
sprezzature-publish-meta     # per page: title, description, OG, JSON-LD
↓
sprezzature-publish-indexes  # robots, sitemap, llms.txt, llms-full.txt, feed
↓
sprezzature-publish-plain    # optional: simplify draft copy
↓
sprezzature-publish-audit    # read what was emitted; --fix what is derived
```

Then run `sprezzature-accessibility-lint` over the output and `sprezzature-colors-contrast` over the palette before declaring "done".

**Optional editorial step** — audio narration per post:

```text
sprezzature-publish-narrate             # one WAV per post (--audio-format mp3 for MP3)
↓
sprezzature-publish-html --readalong    # page follows the audio, sentence by sentence
↓
sprezzature-publish-indexes             # re-run with --audio-manifest to inject
                                        # <enclosure> rows → RSS feed = podcast feed
```

The narration pipeline is **not WCAG-required** (screen readers cover
text accessibility); it's an editorial choice for multitasking
audience / podcast positioning / cognitive-accessibility alternative
formats. Triggered by "narrate this post", "audio version of the
blog", "podcast feed from posts", "TTS this article". See
`references/audio-narration.md` for the placement rules (player
top-of-article), engine matrix (ChatterboxTTS and OpenVoice v2 for cloning,
both MIT for code AND weights; Kokoro, Apache-2.0, the light one; left unset,
speaker-helper's router picks the engine, Chatterbox today in English and
French), voice cloning ethics, and Schema.org /
OpenGraph metadata.

`sprezzature-publish-html --readalong <narration-dir>` makes the page follow the
audio: a span per sentence, highlighted on the browser's own
`cuechange`, visual-only so it does not talk over a screen reader.
It compares the cues the narration wrote against the rendered HTML and
**fails the conversion** when they disagree, naming the sentence —
a highlight that is off by one points a reader confidently at the wrong
line. Same reference, section *Following the narration on the page*.

**A page that was never Markdown** — hand-written, exported from a design
tool, live for three years — takes `sprezzature-publish-readalong` instead. Both
`sprezzature-publish-narrate` and `sprezzature-publish-readalong` read the HTML directly, so the
structural hints come from the page's own elements: an `<h2>` earns the
pause a `##` earns, because it is the same thing.

```text
sprezzature-publish-narrate   page.html --scope article --out-dir audio/
sprezzature-publish-readalong page.html --narration audio/ --scope article --out built/
```

`--scope` (`article`, `#id`, `.class`) is what makes this usable on a real
page: a reader who asked to hear *this article* did not ask for the
navigation. Without it the whole document is read, header and footer
included. Anything already hidden from assistive technology — `hidden`,
`aria-hidden="true"` — is left unspoken, and the input page is never
modified in place.

## When NOT to use this skill

- Versioned docs (semantic versioning, side-by-side per-release docs) → Hugo / MkDocs Material / Docusaurus.
- 100+ Markdown pages → an SSG with incremental rebuilds is faster.
- Heavy templating (custom shortcodes, partials, theme inheritance) → use a real SSG; this skill emits flat HTML.

## References

- `references/audit-site.md` — **every `sprezzature-publish-audit` rule and the specification behind it**: WHATWG HTML, RFC 6596 (canonical), RFC 9309 (robots.txt), sitemaps.org 0.9, ogp.me, X Cards, JSON-LD 1.1, W3C Web App Manifest, Apple's web-app configuration guide, RFC 4287 / RSS 2.0, llmstxt.org. Also names the rules that have **no** spec behind them (three `SITE` rules, seven of the CTA-dependent ones) and why, and shows what `--fix` is allowed to write. Cite it when a finding is disputed.
- `references/faq-aeo.md` — one FAQ per money page, never the same question twice, the markup on the page it describes; the anatomy of an answer an engine can quote (`FAQ005`); the questions a services firm is asked.
- `references/meta-tags.md` — `<meta>` tags per W3C / WHATWG + Open Graph + Twitter Cards + Schema.org JSON-LD.
- `references/site-indexes.md` — robots.txt, sitemap.xml, llms.txt, llms-full.txt, Atom / RSS, humans.txt.
- `references/seo-essentials.md` — Google's three Search Essentials pillars + the AI Optimization Guide's foundations, applied concretely to the artifacts this skill emits. Use it when the user asks about SEO / AI search / "is this third-party advice true?".
- `references/plain-language.md` — rewrite copy at a target reading level; preserves meaning.
- `references/audio-narration.md` — *(optional editorial enhancement, not WCAG-required)* turn a Markdown post (or an existing HTML page) into a narrated WAV/MP3 via ChatterboxTTS (the router's answer today), OpenVoice v2 (both MIT for code AND weights) or Kokoro (Apache-2.0). Structural narration hints from headings / lists / blockquotes / emoji, optional LLM enrichment via the same local Ollama daemon already used for alt-text, voice cloning (OpenVoice, Chatterbox) from a 6-30 s designer-supplied sample, RSS enclosure injection turns the blog feed into a podcast feed.
- `references/lint-markdown.md` — every `sprezzature-publish-lint` rule (`MD000`–`MD050`, `MDX001`–`MDX003`, `MMD001`), `--fix`, `--render-mermaid` and the read-only `--ai` pass.
- `references/writing-standards.md` — the per-language writing charters and the prompt files that inject them.
- `references/i18n.md` — multilingual frontend (URL strategy, `Intl.*`, plurals, RTL, persisted choice). Default language pair is configurable per project (EN/FR, EN/DE, EN/ES, EN/JA, …).

## Commands

Every command below comes with the one `pip install sprezzature-publish`; there are no feature extras.

| Command | Needs | Purpose |
|---|---|---|
| `sprezzature-publish-lint` | — (`--ai`: Ollama) | Lints Markdown before it renders; `--fix` for trailing whitespace, `--render-mermaid` for the diagram PNGs |
| `sprezzature-publish-html` | — | Markdown → static HTML pages, Mermaid rendered; `--readalong <dir>` binds a narration |
| `sprezzature-publish-icons` | — | Full favicon / PWA icon set + manifest + head snippet from a single logo |
| `sprezzature-publish-meta` | Ollama | Drafts title / description / OG / Twitter / JSON-LD from a goal or HTML page |
| `sprezzature-publish-indexes` | — | robots.txt + sitemap.xml + llms.txt + llms-full.txt + an Atom feed (RSS 2.0 with `--rss`) + humans.txt (`--humans`) |
| `sprezzature-publish-audit` | — | Audits an **emitted** site — directory, single page or live URL — and repairs with `--fix` what can be derived. The entry point for "improve this existing site". |
| `sprezzature-publish-cta` | — | Detects the calls to action a site offers, asks which ones it is for, writes `ctas.yaml`, audits every page against it. Rules only. |
| `sprezzature-publish-faq` | Ollama, unless `--no-llm` | Builds the FAQ a site lacks from its pages, grounded and gap-reported; `--audit --fix` checks and rewrites `FAQPage` markup. |
| `sprezzature-publish-findable` | — | One SEO + GEO + AEO report, money pages first, `--fix` for the deterministic repairs. |
| `sprezzature-publish-plain` | Ollama | Rewrites copy at a target grade (`--target-grade`, default 8); strips marketing voice |
| `sprezzature-publish-changelog` | — | Every sibling repository's `CHANGELOG.md` → one dated Atom and RSS feed, a release per entry |
| `sprezzature-publish-narrate` *(optional)* | the engine's model files, once: `sprezzature-audio-install-voice --engine chatterbox` (the router's answer today) | Narrates a Markdown post or an HTML page via local OSS TTS, writing the timed track beside the audio. Engine left to speaker-helper's router unless `--engine` is given. Editorial enhancement, not WCAG-required. |
| `sprezzature-publish-readalong` *(optional)* | — | Adds the read-along to an **existing** HTML page, which has no Markdown to rebuild from. `--scope` picks the element to read; the input is never modified in place. |
| `sprezzature-publish-mcp` | — | The seven HTTP routes + `/health` and the `/mcp` endpoint (eight tools) on one port |
| _(the voices, from sprezzature-audio, a base dependency)_ | — | `sprezzature-audio-narrate-kokoro` / `-openvoice` / `-chatterbox`, invoked as subprocesses by the narration. They live in `sprezzature-audio` with the rest of the sound modality. |
| _(the read-along wiring, in the package)_ | — | Wires a narrated page to its audio: a span per sentence, the `<audio>` + `<track>` player, reading time beside measured listening time. Used by `sprezzature-publish-html --readalong` and `sprezzature-publish-readalong`; refuses rather than mis-align. |
| _(voice chooser)_ | — | `sprezzature-audio-voice` lists engine voices and generates per-voice demo clips, so the designer chooses by listening. |
| _(voice installer)_ | — | `sprezzature-audio-install-voice --engine kokoro\|openvoice\|chatterbox\|all` fetches the model files (Kokoro's ONNX model, OpenVoice v2 checkpoints) and sets up the ChatterboxTTS voice library. |
| _(internal helpers, in the package)_ | — | Language detection + Ollama client + narration segment extractor shared by other scripts |

`make-site <tool>` and `sprezzature-publish <tool>` reach the same thirteen tools (`make-site tools` lists them).

## Companion skills

| You also need… | Install |
|---|---|
| Full UI design tokens, components, dark mode, dataviz | `sprezzature-ui` |
| a11y lint (static HTML) | `sprezzature-accessibility` |
| WCAG contrast audit, CVD simulation, curated palette | `sprezzature-colors` |
| W3C alt text via local Ollama vision | `sprezzature-accessibility` |
| WebVTT / SRT captions via local whisper.cpp | `sprezzature-audio` |
| Wrap a CLI in a GUI | `sprezzature-cli-gui` |
