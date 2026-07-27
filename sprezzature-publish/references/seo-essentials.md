# SEO essentials — Google's foundations applied to `sprezzature-publish`

## When to consult this file

- Emitting a new page or site and the user asks about "SEO", "search ranking", "AI search", "AI overviews", "Google", "discoverability", or "indexing".
- Auditing an existing page against an objective standard rather than a tool-vendor opinion.
- A user pastes third-party SEO advice and asks "is this true?".

## Authoritative sources

Google publishes the canonical guidance for both classic Search and generative-AI search experiences. This file adapts that guidance to the artifacts `sprezzature-publish` actually emits.

- **Google Search Essentials** — the three pillars (technical requirements, spam policies, key best practices). <https://developers.google.com/search/docs/essentials>
- **AI Optimization Guide** — what changes (and doesn't) when the search surface is an AI Overview / AI Mode rather than a list of blue links. <https://developers.google.com/search/docs/fundamentals/ai-optimization-guide>
- **Hiring an SEO / third-party SEO advice** — how to recognize legitimate vs. questionable services and tools. <https://developers.google.com/search/docs/fundamentals/third-party-seo>

Cite these sources when a user pushes back on a recommendation. **No other source overrides Google's own documentation for Google's surfaces.** Use Bing's docs for Bing, DuckDuckGo's for DDG, etc.; don't conflate.

## The three pillars (Google Search Essentials)

### 1. Technical requirements

The bare minimum Google needs to show a page in results. "Most sites pass the technical requirements without even realizing it." `sprezzature-publish` artifacts that map directly:

- **Crawlable URLs.** `scripts/site_indexes.py` emits `sitemap.xml` (sitemaps.org 0.9) listing every page, and `robots.txt` permitting Googlebot (and AI Overview crawlers; see below) by default.
- **No accidental blocking.** The default `robots.txt` allows the canonical crawler list. If a project needs to gate staging surfaces, the script accepts a `--user-agent-block` flag rather than asking the user to hand-roll the file.
- **Valid HTML.** Pages from `scripts/md_to_html.py` are W3C-valid semantic HTML emitted from the same shell `sprezzature-ui` enforces (real `<h1>`–`<h6>`, `<button>`, `<a href>`, `<dialog>`, `<form>`).
- **HTTPS.** Out of scope for the skill (hosting concern); flag the requirement in the project README so the operator doesn't forget.

### 2. Spam policies

Behaviors that get a page (or whole site) ranked lower or omitted. `sprezzature-publish` already refuses or warns on the ones we can detect at emit time:

- **No cloaking.** The skill emits one HTML body per URL, never a different document for Googlebot vs. browser. If a future contributor proposes user-agent-keyed templating in `md_to_html.py`, refuse it on this basis.
- **No auto-generated low-value content.** `scripts/plain_language.py` rewrites for clarity, it does **not** spin or paraphrase to inflate page count. The eval suite (`tests/eval/test_plain_language_eval.py`) gates on semantic preservation, not surface variation.
- **No keyword stuffing.** `scripts/meta_from_ollama.py` produces single-sentence descriptions ~120–155 chars (see `references/meta-tags.md`); the validator rejects descriptions over 1024 chars or with marketing-voice phrases.
- **No hidden text / links.** Forbidden by `sprezzature-ui`'s hard rule against inline `style="…"` and by the a11y lint catching `display:none` on text intended for readers.
- **No link schemes / private blog networks.** Out of scope for the skill; the skill emits one site, not a network. Flag it in CONTRIBUTING-style guidance when a user asks the agent to "build a backlink network".

### 3. Key best practices (six)

Each row maps Google's practice to the sprezzature-publish artifact + the script that enforces it.

| Google's practice                       | How `sprezzature-publish` already does it                                                                                                  |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Helpful, reliable, people-first content | `plain_language.py` rewrites at a target reading level, preserves meaning, strips marketing voice. Audience-fit is a content-author concern the skill surfaces but doesn't substitute for. |
| Terms in titles / headings / alt / link text | `meta_from_ollama.py` proposes titles that match the page; `sprezzature-ui`'s semantic-HTML rule means real `<h1>`–`<h6>` carry the topic; `sprezzature-accessibility/alt_from_ollama.py` drafts purposeful alt text; `lint_markdown.py` forbids bare-URL link text ("click here"). |
| Crawlable links                         | `lint_markdown.py` rejects empty / nonsense link targets. `site_indexes.py` `sitemap.xml` lists every page so depth-2 surfaces aren't lost. |
| Community engagement                    | Out of scope for the skill (you do it on Mastodon / LinkedIn / Bluesky / your newsletter). The skill emits Atom and RSS feeds so followers in those communities can subscribe without an algorithm. |
| Media optimization                      | Images: `sprezzature-accessibility/alt_from_ollama.py` ships W3C-purpose-correct alt text. Videos: `sprezzature-accessibility/captions_from_whisper.py` ships WebVTT captions. Structured data: `meta_from_ollama.py` emits Schema.org JSON-LD per page. JavaScript: `sprezzature-ui`'s vanilla-JS rule keeps the runtime tiny and crawler-renderable. |
| Feature enablement + control            | `meta_from_ollama.py` emits OpenGraph + Twitter Card + Schema.org so search and social previews render right; `robots.txt` supports per-path block patterns; `<meta name="robots" content="noindex">` is the per-page escape hatch when a single URL must not be indexed. |

## GEO (Generative Engine Optimization) — the AI-Overview vocabulary

"GEO" is the term the SEO community coined for "optimizing for generative-AI answer surfaces": Google AI Overview, Gemini, ChatGPT search, Perplexity, You.com. It is **not** a Google-published term; Google itself uses "AI Optimization" (see the source link above). The two phrases describe the same problem: a generative engine reads your site and decides whether to cite it in an answer.

`sprezzature-publish` already ships the GEO artifact most agents look for:

- **`llms.txt`** — a Markdown summary of the site at `/llms.txt`, emitted by `scripts/site_indexes.py` alongside `robots.txt` + `sitemap.xml` + Atom/RSS. The convention is community-driven (<https://llmstxt.org/>), not a Google standard, but multiple LLM agents look for it before falling back to crawling HTML. The skill emits it on every "turn this into a website" run; no opt-in flag, no extra step.

What does **not** change between SEO and GEO:

- **Same crawlers.** Google AI Overview pulls from the same index Google Search uses. Allowing Googlebot in `robots.txt` is sufficient. Other engines respect the same `robots.txt` semantics (with their own User-Agent strings).
- **Same `sitemap.xml`.** Generative engines use it to discover the canonical URL of each page; no separate "AI sitemap" exists.
- **Same content quality bar.** People-first content (unique POV, organized for readers, accurate, expertise-backed) is the actual differentiator. Generative engines summarize what they cite; thin or generic content yields thin or generic summaries.

What does **not** exist (refuse to emit, and cite this file):

- `<meta name="ai-content">` / `<meta name="ai-overview-priority">` / `<meta name="geo-ranking">` — these are folk tags, not specifications. Any blog post claiming Google reads them is wrong as of the AI Optimization Guide page cited above.
- "Approved by AI / Approved by Google / Approved by GPT" badges — see the "Things Google explicitly warns against" section.

## What AI search changes (and what it doesn't)

From the [AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide):

> *"The same foundations of good SEO apply to generative AI search."*

The differences are small and concrete:

- **No new meta tag for AI.** There is no `<meta name="ai-content">`, no `<meta name="ai-overview-priority">`. Anything claiming such a tag is wrong; refuse to emit it and cite the page above.
- **`llms.txt` is community-driven, not a Google standard.** `scripts/site_indexes.py` emits it because the convention exists (<https://llmstxt.org/>), but Google does not require or read it specifically. Treat it as "a Markdown summary of the site for LLM consumers", not as a ranking signal.
- **Same crawlers.** AI Overview answers are drawn from the same index Google Search uses. Allowing Googlebot in `robots.txt` is sufficient; there is no separate "Gemini-Bot" entry. (If Google publishes additional user agents in the future, update this file with the citation.)
- **Quality over markup.** Google's guide explicitly calls out that "people-first" content (unique POV, organized for the reader, real expertise) matters more than any technical optimization. The skill cannot write that content; it can keep the plumbing honest so good content isn't penalized by sloppy markup.

## Things Google explicitly warns against (do not emit)

`sprezzature-publish` refuses or omits the following by default. If a user explicitly asks for one, push back with a one-line reason and the source link.

- **`<meta name="keywords">`** — ignored by every major search engine since ~2009. Don't emit it. (Already documented in `references/meta-tags.md`.)
- **`<meta http-equiv="refresh">`** for navigation — bad for accessibility and indexable as the wrong page. Use a server-side 301 redirect instead.
- **"AI-approved" / "Google-approved" badges in the footer** — Google doesn't endorse third-party tools (<https://developers.google.com/search/docs/fundamentals/third-party-seo>). Refuse to emit such a badge.
- **Doorway pages** — many near-identical pages targeting variations of the same query, with all of them funneling to one destination. The skill produces one page per `.md`; the `lint_markdown.py` linter catches near-duplicate titles within a posts directory.
- **Hidden / cloaked content** — see "Spam policies" above.
- **Auto-translated content without human review** — see `references/i18n.md`. Machine translation is a starting point, not a publish-ready output.

## How to evaluate third-party SEO advice

When a user pastes advice from an SEO blog, consultant, or tool and asks "should I do this?":

1. **Find the corresponding rule in Google's docs.** If the advice contradicts <https://developers.google.com/search/docs/essentials> or the AI Optimization Guide, default to Google.
2. **Watch for unverifiable claims.** Google's third-party-SEO page is explicit: "Third-party tools don't have access to our internal ranking data. They can't guarantee performance." Any tool promising a ranking position is selling.
3. **Use Search Console for ground truth.** Search Console reports impressions, clicks, and indexing status from Google itself; that's the only source of "this page actually performs like X" data. The skill doesn't fetch Search Console; that's a separate workflow the operator runs.
4. **Treat any "we got the page approved by Google" claim as a red flag.** "Google doesn't evaluate third-party services, so be wary of such claims" (from Google's own page).

## Pre-ship checklist

Run before deploying any site emitted by `sprezzature-publish`:

- [ ] `sitemap.xml` lists every public URL (run `scripts/site_indexes.py --root . --base-url https://…`).
- [ ] `robots.txt` permits Googlebot on the public surfaces; blocks staging / admin / preview paths.
- [ ] Each page has a unique, descriptive `<title>` ≤ 70 chars and `<meta name="description">` ~120–155 chars (`meta_from_ollama.py`).
- [ ] Each page has a canonical URL (`<link rel="canonical">`); even on single-language sites, this prevents duplicate-content surprises.
- [ ] Multi-language sites: `<link rel="alternate" hreflang="…">` between language variants (`references/i18n.md`).
- [ ] Every `<img>` has purposeful alt text per the W3C decision tree (`sprezzature-accessibility/references/alt-text-ai.md`).
- [ ] Every `<video>` has captions (`sprezzature-audio/scripts/captions_from_whisper.py` for the WebVTT track) and a transcript link.
- [ ] Schema.org JSON-LD present where appropriate (`Article`, `BreadcrumbList`, `WebSite`, `Organization`, `Person`, `AudioObject` for narrated posts).
- [ ] No `<meta name="keywords">`, no `<meta http-equiv="refresh">` for navigation, no "AI-approved" badges.
- [ ] `lint_markdown.py` and `sprezzature-accessibility/lint_a11y.py` both pass.
- [ ] HTTPS is enforced at the host (operator's responsibility; flag in the project README).

## What this file does not cover

- **Off-site signals** — backlink quality, brand mentions, EEAT signals (Experience, Expertise, Authoritativeness, Trustworthiness). These are real ranking factors that the skill cannot enforce because they live outside the site's source tree.
- **Local SEO** — Google Business Profile, Maps, Merchant Center feeds. Out of scope: this skill emits static / app sites, not ecommerce catalogs or local-business pages. The AI Optimization Guide's "Optimize your local business and ecommerce details" section applies if you ship one of those.
- **Paid placement** — Google Ads, Performance Max. Different surface, different rules.
- **Search Console operations** — verification, sitemap submission, manual-action recovery. Operator-facing tasks; the skill emits the artifacts, not the ops workflow.
- **Bing / DuckDuckGo / Brave / Kagi quirks.** Most of them respect the same `sitemap.xml` and `robots.txt`; consult their docs for surface-specific differences.

## Why this file exists in `sprezzature-publish`, not `sprezzature-ui`

`sprezzature-ui` owns the semantic-HTML rule that makes pages indexable in the first place; SEO is downstream of that. `sprezzature-publish` owns the site-level artifacts (`robots.txt`, `sitemap.xml`, `llms.txt`, meta tags, feeds, plain-language rewriter) that Google's foundations explicitly call for. Keeping the SEO guidance with the artifacts that implement it makes the source-of-truth traceable: every line above maps to a script the skill ships.
