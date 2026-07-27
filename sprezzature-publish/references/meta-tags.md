# HTML `<meta>` Tags

Authoritative sources (no single standards body covers all of this):

- **W3C HTML / WHATWG HTML Living Standard** — `charset`, `description`, `viewport`, `theme-color`, `color-scheme`, `referrer`, `robots`. <https://html.spec.whatwg.org/multipage/semantics.html#meta>
- **Open Graph Protocol** (ogp.me) — social previews (Facebook, LinkedIn, Slack, iMessage, WhatsApp, Discord). <https://ogp.me/>
- **Twitter Cards** (developer.x.com) — Twitter / X specific previews. <https://developer.x.com/en/docs/twitter-for-websites/cards>
- **Schema.org** — structured data via JSON-LD for search engines. <https://schema.org/>
- **Google Search Central** — canonical, robots, alternate hreflang. <https://developers.google.com/search/docs>

For the larger "what makes a page indexable and helpful for AI search" picture (Google's three Search Essentials pillars, the AI Optimization Guide's foundations, and how to evaluate third-party SEO advice), see `seo-essentials.md` in this folder.

Use this file when emitting any new HTML page or when the user asks to "fill in the meta tags".

## The base every page must have

```html
<!doctype html>
<html lang="en" dir="auto">  <!-- lang per i18n.md -->
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">

  <title>Page-specific title — Site name</title>
  <meta name="description" content="One sentence, ~120–155 characters, describing this page's value.">

  <meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">

  <link rel="canonical" href="https://example.com/this-page">
</head>
```

### Title

- One sentence. Page-specific part first, brand last, separated by ` — `, `|`, or `·`.
- 50–60 characters before the brand. Search engines truncate around 600 px wide.
- Front-load the keyword the user is likely searching for.
- Each page has a unique title. Never re-use the same `<title>` across pages.

### Description

- 120–155 characters. Google rarely shows more than ~155.
- One sentence; verb-first when an action is implied.
- Concrete, no buzzwords. The same voice rules as `ui-guidelines/foundations/writing.md` apply here.
- Each page has a unique description.

### Viewport

- Always `width=device-width, initial-scale=1`.
- Add `viewport-fit=cover` when the page draws under the OS status bar / notch (most apps).
- Don't set `user-scalable=no` or `maximum-scale=1`; those break zoom for low-vision users.

### Canonical

- Always set, even when there's a single canonical URL.
- Absolute URL.
- Distinguishes the "real" URL from query-string or tracking-tag variants.

## Open Graph (social previews)

Open Graph is the de-facto standard read by every major social platform. Add it on every shareable page.

```html
<meta property="og:site_name" content="Site name">
<meta property="og:type"      content="website">              <!-- article | profile | book | … -->
<meta property="og:url"       content="https://example.com/this-page">
<meta property="og:title"     content="Page title (≤ 60 chars)">
<meta property="og:description" content="One sentence (≤ 155 chars).">
<meta property="og:image"     content="https://example.com/og.png">
<meta property="og:image:width"  content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Describe the image, not the file.">
<meta property="og:locale"    content="en_US">
```

- **`og:image`** — 1200 × 630 PNG/JPG, < 5 MB, served over HTTPS. Aspect ratio 1.91:1 renders consistently across platforms.
- **`og:image:alt`** — required by accessibility tools; describe the image content.
- **`og:locale`** — locale tag with underscore (`en_US`, `fr_FR`), not BCP-47 (`en-US`).
- For multilingual sites, add `og:locale:alternate` per available language.

## Twitter / X Cards

```html
<meta name="twitter:card"        content="summary_large_image">    <!-- or "summary" for small image -->
<meta name="twitter:site"        content="@yourhandle">
<meta name="twitter:title"       content="Same as og:title">
<meta name="twitter:description" content="Same as og:description">
<meta name="twitter:image"       content="Same as og:image">
<meta name="twitter:image:alt"   content="Same as og:image:alt">
```

Twitter falls back to OG if Twitter-specific tags are missing, so the bare minimum is OG + `twitter:card`.

## Structured data — JSON-LD via Schema.org

JSON-LD is what Google reads. It's a `<script type="application/ld+json">` block in `<head>`.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Site name",
  "url": "https://example.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://example.com/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
```

Common types to use, picked from the situation:

| Page kind | `@type` |
|---|---|
| Marketing landing | `WebSite` + `Organization` |
| Article / blog post | `Article` (or `NewsArticle` / `BlogPosting`) |
| Product | `Product` + `Offer` |
| Person profile | `Person` |
| Recipe | `Recipe` |
| Event | `Event` |
| FAQ page | `FAQPage` |
| Local business | `LocalBusiness` (sub-typed) |

Validate output with <https://search.google.com/test/rich-results>.

## Robots and indexing

```html
<meta name="robots" content="index, follow">          <!-- default for public pages -->
<meta name="robots" content="noindex, nofollow">      <!-- preview / staging / admin -->
<meta name="googlebot" content="max-image-preview:large">
```

For the whole site, prefer `/robots.txt` for crawl rules; reserve the `<meta>` tag for page-level overrides.

## Multilingual — `hreflang`

When the page exists in several languages, declare each variant. See `i18n.md` for the full URL strategy.

```html
<link rel="alternate" hreflang="en" href="https://example.com/en/page">
<link rel="alternate" hreflang="fr" href="https://example.com/fr/page">
<link rel="alternate" hreflang="x-default" href="https://example.com/en/page">
```

## PWA / app integration

```html
<link rel="manifest" href="/site.webmanifest">       <!-- generated by favicons.py -->
<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Short name">
<meta name="mobile-web-app-capable" content="yes">
```

The favicon set, theme-color, and manifest are produced by `scripts/favicons.py` (see `ui-guidelines/foundations/app-icons.md`).

## What NOT to set

- `<meta name="keywords">` — ignored by all major search engines since around 2009. Drop it.
- `<meta name="author">` — rarely useful at page level; use Schema.org `Article.author` instead.
- `<meta http-equiv="X-UA-Compatible" content="IE=edge">` — IE is end-of-life. Drop it.
- `<meta http-equiv="refresh">` — bad for accessibility and SEO. Use a 301 redirect server-side.
- `<meta name="copyright">` — has no standardized handling; put it in the page footer.

## Filling tags from context

When the user gives the skill a goal ("a marketing page for X") or actual page content, derive the meta tags this way:

1. **Title** — page topic + brand. 50–60 chars before the brand.
2. **Description** — pull the single most concrete sentence describing the page's value. Strip buzzwords (see `anti-patterns.md`).
3. **og:image** — if a hero exists, use it (1200×630); else generate or note the gap. `og:image:alt` describes it.
4. **og:type** — match the kind table above.
5. **JSON-LD** — pick the type that best fits; fill the required fields; leave optional ones empty rather than invent.
6. **Theme-color** — light and dark hex from the skill's color tokens, matching the page's primary surface.
7. **Canonical** — absolute URL of this page.

A local AI helper for the description and `og:image:alt` is `scripts/meta_from_ollama.py` (see `references/alt-text-ai.md` for the install path; same Ollama setup).

## Checklist (before any page ships)

- [ ] `<html lang>` and `dir`.
- [ ] `charset` = utf-8.
- [ ] Viewport tag, no `user-scalable=no`.
- [ ] Unique, page-specific `<title>` and `description`.
- [ ] `theme-color` for light and dark.
- [ ] `link rel="canonical"`.
- [ ] Open Graph: site_name, type, url, title, description, image, image:alt.
- [ ] `twitter:card` set (the rest can inherit from OG).
- [ ] JSON-LD with the right `@type`.
- [ ] `hreflang` per locale, including `x-default`.
- [ ] No deprecated meta (`keywords`, `X-UA-Compatible`, `refresh`, …).
- [ ] Favicon set linked (`/favicon.svg`, `.ico`, `apple-touch-icon.png`, manifest).
- [ ] `og:image` and `apple-touch-icon` rendered correctly at 200 × 200 thumbnail.
