# Lint Markdown: static + AI-assisted

Static + AI-assisted linter for Markdown content shipped by `sprezzature-publish`
sites and by anyone consuming the sprezzature skills. Three jobs:

1. Catch the static markdown errors a reader will notice (heading skips,
   trailing whitespace, code blocks without a language hint, missing
   alt text, dead local links).
2. Validate **LaTeX display blocks** for delimiter balance and multi-line
   hygiene. A missing `\\` inside an `align` environment silently
   collapses every formula on most renderers.
3. Report every **Mermaid block** (`MMD001`). Nothing here draws one: redraw
   the diagram with `sprezzature-figures render flowchart` and embed the SVG.

The static rules never reach the network, and `--ai` talks to a local Ollama
only.

## Quick start

```bash
pip install sprezzature-publish
sprezzature-publish-lint docs/

# Add AI suggestions (LaTeX captions):
sprezzature-publish-lint --ai --ai-lang en docs/intro.md
```

Via the front door: `make-site lint docs/` (or
`sprezzature-publish lint …`, the same command under its other name).

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
| `MMD001` | warning | A fenced Mermaid block: redraw it with `sprezzature-figures`. |
| `MD000` | warning | The file is not valid UTF-8, so it was skipped. |

`MD001`, `MD050`, `MDX001`, `MDX003` flip the exit code to `1`.
The rest are informational.

## Mermaid blocks (`MMD001`)

`lint` and `html` draw no diagram and load no diagram library. `MMD001` is a
warning, the exit code stays `0`, and `html` leaves the block on the page as
code and says so in its result for that file. To get the diagram, write its
arrows as rows and let `sprezzature-figures` lay them out:

```bash
printf 'source,target\nDraft,Review\nReview,Publish\n' > flow.csv
sprezzature-figures render flowchart --data flow.csv --out docs/flow.svg
```

Then embed the SVG with a Markdown image and an alt text that says what the
diagram shows, and delete the block.

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

- Drafts a **plain-language caption** for each LaTeX display block (one
  sentence, ≤ 30 words, screen-reader-friendly). The caption is printed
  for you to paste into a sibling `<figcaption>` or `aria-describedby`
  block.

The AI step is **read-only**. Under `--fix` the static half rewrites
trailing whitespace (`MD009`); nothing else is repaired. The AI step prints
suggestions you apply by hand.

### Prompts

The script ships one prompt. It is intentionally:

1. One concrete role line at the top ("You are a senior technical-documentation reviewer").
2. Numbered hard rules: the model gets specific constraints, not vague guidance.
3. An explicit output contract: one sentence, no quotes, no prefix.
4. Zero-shot. No in-context examples; the task is common enough in the model's training distribution that examples cost tokens without lifting quality.

See `scripts/prompts/latex_caption.yaml` for the verbatim prompt, loaded by
`scripts/_prompts.py`.

## CI integration

```yaml
- name: Lint Markdown
  run: |
    pip install sprezzature-publish
    sprezzature-publish-lint docs/
```

## Honest framing

This is a **fast pre-commit Markdown gate**, not a full Markdown
specification validator. For everything that depends on a real
Markdown→HTML render (math after KaTeX, GFM tables with inline HTML,
GitHub-specific footnote rendering), use the renderer itself and audit
the output. Pair this script with a renderer in CI for full coverage.
