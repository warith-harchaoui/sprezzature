# Site indexes — `site_indexes.py`

Generate the standard set of site-index files for a project's web output, respecting the canonical specs for each. One Python script, stdlib only.

## What it emits

| File | Spec | When |
|---|---|---|
| `robots.txt` | [Google Search Central — robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt) | Always |
<!-- For the rules each of these files enforces in the larger SEO context (Google's three Search Essentials pillars + the AI Optimization Guide's foundations), see `seo-essentials.md` in this folder. -->

| `sitemap.xml` | [sitemaps.org 0.9](https://www.sitemaps.org/protocol.html) | Always |
| `llms.txt` | [llmstxt.org](https://llmstxt.org/) | Always |
| `llms-full.txt` | [llmstxt.org](https://llmstxt.org/) full-text convention | Always (skip with `--no-llms-full`) |
| `feed.atom` | [Atom 1.0 (RFC 4287)](https://datatracker.ietf.org/doc/html/rfc4287) | When a blog directory is detected (`posts/`, `blog/`, `articles/`) |
| `rss.xml` | [RSS 2.0](https://www.rssboard.org/rss-specification) | Same as Atom, but emitted instead when `--rss` is passed |
| `humans.txt` | [humanstxt.org](https://humanstxt.org/Standard.html) | When `--humans` is passed OR an `AUTHORS` / `CREDITS` file exists at the root |

## Run

```bash
# Bare minimum: a project root + the public origin
python scripts/site_indexes.py --root . --base-url https://example.com

# Project with a blog folder under posts/
python scripts/site_indexes.py --root . --base-url https://example.com --feed-from posts

# Force RSS 2.0 for clients that haven't moved past 2002
python scripts/site_indexes.py --root . --base-url https://example.com --feed-from posts --rss

# Ship a humans.txt explicitly
python scripts/site_indexes.py --root . --base-url https://example.com --humans

# Override the output directory (default: --root)
python scripts/site_indexes.py --root . --base-url https://example.com --out public
```

The script walks the project root looking for `.html` files at the root and inside the conventional output directories (`public/`, `dist/`, `site/`, `_site/`, `build/`, `out/`) plus `.md` files at the root and under `docs/`. Each becomes a sitemap entry and an `llms.txt` bullet.

### `llms-full.txt` — the full-text companion

`llms.txt` is an *index* (H1 + blockquote + linked bullets); `llms-full.txt` is the *corpus* — the complete text of those pages concatenated so an agent ingests the whole site in one request instead of following each link. It is emitted by default; opt out with `--no-llms-full`.

Three rules keep it from bloating (the failure mode where a full-text file drags in raw HTML, nav, and duplicated pages until it blows past a model's context):

- **Markdown sources only.** Rendered HTML is generated *from* the `.md` pages, so concatenating it would duplicate every page and pull in tag / nav / footer boilerplate. Only `.md` bodies go in; YAML front matter is stripped (we emit a `Source:` line per page instead).
- **Priority order.** Pages are ordered README / `index.md` first, then other root `.md`, then `docs/` — so any truncation keeps what matters.
- **Visible size, no silent truncation.** The run prints the page count and KB. Past ~200 KB with no cap it prints a soft advisory. With `--llms-full-max-kb N` it fills the budget in priority order and **names every page it dropped** — a bounded file never silently hides content.

```bash
# Default: emit llms-full.txt alongside llms.txt
python scripts/site_indexes.py --root . --base-url https://example.com

# Cap the corpus at 128 KB (drops lowest-priority pages, names them)
python scripts/site_indexes.py --root . --base-url https://example.com --llms-full-max-kb 128

# Skip it entirely
python scripts/site_indexes.py --root . --base-url https://example.com --no-llms-full
```

A generated `llms-full.txt` is only as fresh as its last run — regenerate it in the same CI step as the rest of the site, since a stale full-text corpus feeds an agent confidently wrong content.

## What the skill does automatically

When Claude emits a website (the **Markdown → website workflow** in SKILL.md, or any other surface that produces an HTML tree), it runs `site_indexes.py` as the final step:

1. Picks `--base-url` from the user's stated origin, or a sensible placeholder marked as TODO.
2. Auto-detects a blog folder (`posts/`, `blog/`, `articles/`) and emits the Atom feed when found.
3. Reads `AUTHORS` / `CREDITS` at the root if present, and emits `humans.txt` automatically.
4. Writes everything next to `index.html` (or under `public/` if that's the chosen output directory).
5. Surfaces the resulting URLs in the page's `<head>` via the meta-tags reference (`references/meta-tags.md`):

```html
<link rel="sitemap" type="application/xml" href="/sitemap.xml">
<link rel="alternate" type="application/atom+xml" href="/feed.atom" title="Site feed">
<!-- RSS variant: -->
<link rel="alternate" type="application/rss+xml" href="/rss.xml" title="Site feed">
```

The robots.txt's `Sitemap:` line is set automatically too.

## Why Atom is the default (not RSS 2.0)

- Atom 1.0 is an IETF standard with strict semantics; RSS 2.0 is a vendor format with ambiguous fields.
- Modern aggregators (NetNewsWire, Inoreader, FreshRSS, Feedbin, Bluesky's feed reader, Mastodon) all read Atom.
- Apple Podcasts still requires RSS 2.0 with `<itunes:*>` extensions; for podcasts specifically, the user should run with `--rss` and post-process the file to add the iTunes block.

## Composition with other helpers

`site_indexes.py` is one node in the skill's emission pipeline:

```text
.md sources ──► HTML pages ──► favicons.py ──► meta_from_ollama.py ──► site_indexes.py
                                  (icons + manifest)   (per-page meta)     (whole-site indexes)
```

For pages with embedded images or video, alt text and captions are produced by `alt_from_ollama.py` and `captions_from_whisper.py` in the same pass.

## Checklist (before publishing the site)

- [ ] `robots.txt`, `sitemap.xml`, `llms.txt`, `llms-full.txt` present at the site root.
- [ ] `llms-full.txt` size is sane for the target model; long tail left to `llms.txt` (or `--llms-full-max-kb` set).
- [ ] `<link rel="sitemap">` and `<link rel="alternate" type="application/atom+xml">` in every page's `<head>` (handled by `meta-tags.md`).
- [ ] `robots.txt`'s `Sitemap:` line points at the absolute URL.
- [ ] Atom feed validates via <https://validator.w3.org/feed/>.
- [ ] `llms.txt` follows the llmstxt.org shape: H1, blockquote, `## Optional` for non-essential links.
- [ ] If a podcast, RSS 2.0 emitted (`--rss`) and iTunes block added.
- [ ] `humans.txt` shipped if there's an AUTHORS file or `--humans` was passed.
