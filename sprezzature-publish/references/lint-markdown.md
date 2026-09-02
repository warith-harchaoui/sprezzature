# Lint Markdown: static + AI-assisted

Static + AI-assisted linter for Markdown content shipped by `sprezzature-publish`
sites and by anyone consuming the sprezzature skills. Three jobs:

1. Catch the static markdown errors a reader will notice (heading skips,
   trailing whitespace, code blocks without a language hint, missing
   alt text, dead local links).
2. Validate **LaTeX display blocks** for delimiter balance and multi-line
   hygiene. A missing `\\` inside an `align` environment silently
   collapses every formula on most renderers.
3. Validate **Mermaid blocks** by rendering them to a local PNG so the
   diagram still works when JS is disabled or when the renderer is on a
   different version.

All rendering is **fully local**. No network, no SaaS, no GitHub Actions
hosted rendering. The pipeline is reproducible.

## Quick start

```bash
pip install -r scripts/requirements-lint-md.txt
python scripts/lint_markdown.py docs/

# Render every Mermaid block to a PNG sibling and insert a fallback <img>:
python scripts/lint_markdown.py --render-mermaid --fix docs/

# Add AI suggestions (Mermaid label improvements + LaTeX captions):
python scripts/lint_markdown.py --ai --ai-lang en docs/intro.md
```

Via the unified driver: `sprezzature publish lint-md docs/ --render-mermaid`.

## Rules implemented

| ID | Severity | What it catches |
|---|---|---|
| `MD001` | error | Heading level skipped (`#` → `###`). |
| `MD009` | warning | Trailing whitespace (except the intentional two-space line break). |
| `MD040` | warning | Fenced code block without a language hint. |
| `MD045` | info | Empty image alt: confirm the image is decorative. |
| `MD050` | error | Local link target does not exist on disk. |
| `MDX001` | error | `$$ … $$` delimiters not balanced. |
| `MDX002` | warning | Multi-line display math without `\\` or an `align/gather` environment. |
| `MDX003` | error | Inside `\begin{align}` / `aligned` / `gather`, a non-trailing line is missing `\\`. |
| `MMD001` | error | A Mermaid block failed to render locally. |

`MD001`, `MD050`, `MDX001`, `MDX003`, `MMD001` flip the exit code to `1`.
The rest are informational.

## Mermaid rendering (local)

Two backends, tried in order:

1. **Pure Python `mmdc`** (`pip install mmdc`). Embeds PhantomJS via
   `phasma` (no Node, no npm, no Chromium). This is the recommended
   path; install it from `scripts/requirements-lint-md.txt`.
2. **Node `@mermaid-js/mermaid-cli`** (`npm install -g
   @mermaid-js/mermaid-cli`). Fallback if the pure-Python backend fails
   or is not installed. Heavier; pulls Chromium via Puppeteer.

If neither is available the script flags the block as `MMD001` and prints
both install commands. **It never attempts a hosted render.**

Output: one PNG per Mermaid block, named
`<source-stem>.mermaid-<N>.png`, written alongside the source (or under
`--out-dir`). When `--fix` is set the script inserts an
`![Mermaid diagram (rendered for non-JS readers)](…)` line above each
block so the static HTML still shows the diagram if the page later
disables Mermaid.js.

### Why local rendering matters

- **Privacy.** Diagrams may contain internal architecture, customer
  names, in-progress code. Rendering through a hosted service leaks
  them.
- **Reproducibility.** Hosted Mermaid versions update; the diagram you
  rendered last year stops rendering or renders differently. A local
  PNG saved beside the source is permanent.
- **Offline.** CI in an air-gapped environment, a flight, a
  cafe-without-wifi: none of these break the rendering pipeline.
- **Accessibility.** The PNG sibling is the right surface for an
  alt-text helper. See `sprezzature-vision/scripts/alt_from_ollama.py`;
  the rendered PNG can be passed to it directly.

## LaTeX checks

The script does not render LaTeX (no headless TeX install required). It
validates structure only:

- **Delimiter balance.** Counts unescaped `$$` pairs; flags odd counts.
- **Multi-line hygiene.** A `$$ … $$` block with three lines but no
  `\\` and no `\begin{align}` will render as one long line on most
  KaTeX/MathJax setups; flagged as `MDX002`.
- **Align environments.** Inside `\begin{align*}`, `\begin{aligned}`,
  `\begin{gather*}`, every non-trailing line must end with `\\`. The
  classic "Friday-afternoon" bug.

## AI-assisted suggestions (optional)

When `--ai` is set and a local Ollama daemon is reachable, the script
also:

- Drafts up to three **Mermaid label edits** (verb-first, parallel
  structure, match the existing label language). Returned as JSON; never
  auto-applied.
- Drafts a **plain-language caption** for each LaTeX display block (one
  sentence, ≤ 30 words, screen-reader-friendly). The caption is printed
  for you to paste into a sibling `<figcaption>` or `aria-describedby`
  block.

The AI step is **read-only**. The static rules alone can rewrite
trailing whitespace and code-fence languages (under `--fix`); the AI
step prints suggestions you apply by hand.

### Prompts

The script ships two prompts. They are intentionally:

1. One concrete role line at the top ("You are a senior technical-documentation reviewer").
2. Numbered hard rules: the model gets specific constraints, not vague guidance.
3. An explicit output contract: JSON array for the Mermaid task; one sentence (no quotes, no prefix) for the LaTeX caption. Both are parsed strictly; a model that drifts off-contract returns an empty result and the script reports nothing for that block.
4. Zero-shot. No in-context examples; both tasks are common enough in the model's training distribution that examples cost tokens without lifting quality.

See `scripts/lint_markdown.py` → `PROMPT_MERMAID_LABELS` and
`PROMPT_LATEX_CAPTION` for the verbatim prompts.

## CI integration

```yaml
- name: Lint Markdown
  run: |
    pip install -r sprezzature-publish/scripts/requirements-lint-md.txt
    python sprezzature-publish/scripts/lint_markdown.py docs/
```

Add `--render-mermaid --fix` if you want CI to commit the rendered PNGs;
otherwise keep CI lint-only.

## Honest framing

This is a **fast pre-commit Markdown gate**, not a full Markdown
specification validator. For everything that depends on a real
Markdown→HTML render (math after KaTeX, GFM tables with inline HTML,
GitHub-specific footnote rendering), use the renderer itself and audit
the output. Pair this script with a renderer in CI for full coverage.
