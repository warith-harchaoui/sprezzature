# `sprezzature-publish-audit`: every rule, and the specification behind it

## When to consult this file

- A finding is disputed — "says who?" — and the answer has to be a document,
  not an opinion.
- A rule is being added, changed or removed.
- Somebody pastes third-party SEO advice that contradicts a rule here.

**The standing rule of this package:** a check earns its place by citing a
specification or the search engine's own documentation. Where no such
document exists, the rule either says so out loud or does not exist. Three
rules below are deliberately *not* backed by a spec, and each one says which
and why.

For the wider "what makes a page indexable and helpful for AI search"
picture, see `seo-essentials.md`. For what to put in each tag, see
`meta-tags.md`. For the index files themselves, see `site-indexes.md`.

---

## Per-page rules

| Rule | Checks | Authority |
|---|---|---|
| `SITE000` | a `<head>` exists | [WHATWG HTML § 4.2 Document metadata](https://html.spec.whatwg.org/multipage/semantics.html#document-metadata) |
| `SITE001` | `<html lang>` | [WHATWG HTML § the `lang` attribute](https://html.spec.whatwg.org/multipage/dom.html#the-lang-and-xml:lang-attributes); values per [BCP 47 / RFC 5646](https://datatracker.ietf.org/doc/html/rfc5646) |
| `SITE002` | `<title>` present | [WHATWG HTML § the `title` element](https://html.spec.whatwg.org/multipage/semantics.html#the-title-element) |
| `SITE003` | `<meta name="description">` present | [WHATWG HTML § standard metadata names](https://html.spec.whatwg.org/multipage/semantics.html#standard-metadata-names) |
| `SITE004` | description length 120–155 | **No spec.** Google's own guidance on [titles and snippets](https://developers.google.com/search/docs/appearance/snippet) states the purpose; the character window is observed rendering behaviour, not a published limit. That is why this is a *warning* and never an error. |
| `SITE005` | `<meta name="viewport">` | [CSS Device Adaptation (W3C WD)](https://www.w3.org/TR/css-device-adapt-1/); registered in the [WHATWG MetaExtensions registry](https://wiki.whatwg.org/wiki/MetaExtensions), reached from [HTML § other metadata names](https://html.spec.whatwg.org/multipage/semantics.html#other-metadata-names) |
| `SITE006` | `<link rel="canonical">` | [RFC 6596 — The Canonical Link Relation](https://datatracker.ietf.org/doc/html/rfc6596) and [Google: canonicalization](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls) |
| `SITE007` | the four required Open Graph properties | [The Open Graph protocol](https://ogp.me/) — `og:title`, `og:type`, `og:url`, `og:image` are "required"; `og:description` is optional in the spec and required in practice by every consumer, which is why it is a warning here |
| `SITE008` | `og:image` | [ogp.me § basic metadata](https://ogp.me/#metadata) |
| `SITE009` | `og:image:alt` | [ogp.me § structured properties](https://ogp.me/#structured). This is the preview card's alt, **not** the page's — the images inside the page belong to `sprezzature-accessibility`. |
| `SITE010` | `twitter:card` | [X: Cards markup reference](https://developer.x.com/en/docs/twitter-for-websites/cards/overview/markup) |
| `SITE011` | a JSON-LD block | [JSON-LD 1.1 (W3C Rec)](https://www.w3.org/TR/json-ld11/), vocabulary from [schema.org](https://schema.org/), consumed per [Google: structured data general guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) |
| `SITE012` | `theme-color` | [WHATWG HTML § `theme-color`](https://html.spec.whatwg.org/multipage/semantics.html#meta-theme-color) |
| `SITE013` | any `rel="icon"` | [WHATWG HTML § `rel="icon"`](https://html.spec.whatwg.org/multipage/links.html#rel-icon) |
| `SITE014` | `apple-touch-icon` | [Apple: Configuring Web Applications](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html). Apple documents two fallbacks and one inversion: the root is searched for `apple-touch-icon.png` when no link names one, and **manifest icons take precedence only when no `apple-touch-icon` is declared in the head**. So the severity drops to a note when the page carries a manifest: that is a supported choice, not an omission. |
| `SITE015` | `rel="manifest"` | [W3C Web Application Manifest](https://www.w3.org/TR/appmanifest/) |
| `SITE016` | folk GEO tags | **Deliberately no spec — that is the finding.** `ai-content`, `ai-overview-priority`, `geo-ranking`, `ai-index`, `llm-content` appear in blog posts and in no specification. Google's own [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features) names no such tag. `--fix` removes them. |

## Per-site rules

| Rule | Checks | Authority |
|---|---|---|
| `SITE100` | `robots.txt` exists | [RFC 9309 — Robots Exclusion Protocol](https://datatracker.ietf.org/doc/html/rfc9309) (IETF Proposed Standard, September 2022), and [Google: robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt). RFC 9309 fixes the location (`/robots.txt`, lowercase, top-level), the encoding (UTF-8) and the media type (`text/plain`). |
| `SITE101` | `robots.txt` names the sitemap | [sitemaps.org § informing crawlers](https://www.sitemaps.org/protocol.html#informing) — the `Sitemap:` directive is the documented way to announce it without submitting it anywhere |
| `SITE102` | `sitemap.xml` exists | [Sitemaps XML format 0.9](https://www.sitemaps.org/protocol.html) |
| `SITE103` | every discovered page is listed | same; the sitemap is a *complete* index by design |
| `SITE104` | no listed URL is gone | same. RFC 9309 and the sitemap protocol are both advisory: a stale entry is a warning, not an error. |
| `SITE105` | `llms.txt` exists | [llmstxt.org](https://llmstxt.org/) — a proposal rather than a standards-body document, and said so here. It is the only artifact generative engines look for *by name*; nothing is lost by shipping it. |
| `SITE106` | a feed exists | [RFC 4287 — Atom 1.0](https://datatracker.ietf.org/doc/html/rfc4287) or [RSS 2.0](https://www.rssboard.org/rss-specification) |
| `SITE110`, `SITE111` | the icon set on disk | [W3C Web App Manifest § icons](https://www.w3.org/TR/appmanifest/#icons-member) and Apple, above |
| `SITE112` | `head.html` written and never pasted | **No spec — a house rule.** `sprezzature-publish-icons` writes a drop-in snippet; nothing made anyone paste it. This is the package's own commonest failure, so it gets its own rule. |

---

## The maskable icon, and a number that was wrong

The Web App Manifest defines the safe zone as

> a circle with center point in the center of the icon and with a radius of
> 2/5 (40%) of the icon size

and says the user agent

> MAY apply a mask of any size, making any pixels that are more than 2/5ths
> of the image size […] away from the center […] transparent

while it

> MUST NOT make any pixel within the safe zone transparent

— [W3C Web App Manifest § icon masks](https://www.w3.org/TR/appmanifest/#icon-masks).

`favicons.py` placed the artwork in a centred **square** covering 80 % of the
canvas, under a docstring promising the artwork would survive any mask. The
corners of that square sit 0.566 of the icon size from the centre — outside
the circle, and therefore maskable away. The two claims could not both hold.

`MASKABLE_SAFE` is now derived rather than chosen: the largest centred square
that fits *inside* the safe circle has its half-diagonal equal to the radius,
so its side is `sqrt(2) × 0.4 ≈ 0.5657` of the icon size. The logo is
visibly smaller than the 80 % convention most generators use. That convention
is not wrong about the common case — a round mask is the usual one — but it
leaves the corners at the user agent's discretion, and the spec is explicit
that they are. `tests/test_favicons.py::TestMaskableSafeZone` holds the
geometry.

---

## What `--fix` may write, and the rule behind the line

Repairs are **derived, never invented** — the same line `lint_markdown`
draws around its `--ai` suggestions.

| Written | Derived from |
|---|---|
| `canonical` | `--base-url` + the file's own path (RFC 6596 wants one URL per resource; it does not want a guessed one) |
| `viewport` | a fixed, documented value |
| `og:title`, `og:description` | the page's own `<title>` and `description` |
| `og:url` | the canonical URL |
| `og:type` | `website`, [ogp.me's own stated default](https://ogp.me/#types) when the property is absent |
| `twitter:card` | `summary_large_image` when an `og:image` exists, `summary` otherwise — [X's own two card types for this case](https://developer.x.com/en/docs/twitter-for-websites/cards/overview/markup) |
| `twitter:title`, `twitter:description` | mirrored from Open Graph, which X documents as its fallback |
| icon and manifest `<link>`s | the `head.html` `favicons` wrote, or the icon files present |
| `theme-color` | `--theme-color`, only when given |
| `robots.txt`, `sitemap.xml` | regenerated through `site_indexes`, so there is one implementation of each |
| folk GEO tags | **removed** |

| Never written | Why |
|---|---|
| the text of `<title>` | no document derives a sentence |
| the text of `description` | same; `sprezzature-publish-meta` drafts it for review |
| the choice of `og:image` | names a file nobody can infer |
| `og:image:alt` | a description of a picture — `sprezzature-publish-meta` drafts it |
| the JSON-LD `@type` and body | a modelling decision |
| the `llms.txt` summary | a paragraph a person writes |
| anything at all, on a remote URL | a URL is reported; `--fix` against one is a usage error |
