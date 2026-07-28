# Writing Standards

How the project enforces consistent prose quality on all auto-generated text: meta tags,
plain-language rewrites, LaTeX captions, Mermaid label suggestions, and narration copy.

Use this file when adding a new LLM prompt, authoring a charter for a new language, or
diagnosing why generated text violated a style rule.

## Why this exists

A site built with `sprezzature-publish` may produce hundreds of meta descriptions, alt
texts, and plain-language rewrites through LLM calls. Without an explicit constraint,
models default to a template register full of hollow openers, bolted-on transitions, and
reflexive see-saw constructions that are immediately recognizable as machine output.
Google's Helpful Content guidance penalizes scaled auto-text that adds no value. The GEO
research (arXiv 2311.09735, Princeton 2023) shows that preserving citations, statistics,
and fluent self-contained prose lifts citation rates in AI-generated answers by 27 to
41%. The charter is both a house style and a GEO lever.

## The three layers

### 1. Language charters (source of truth)

Six native charters live in `scripts/charters/`:

| File | Language | Scope |
|---|---|---|
| `en.md` | English | All English prose output |
| `fr.md` | French | All French prose output |
| `de.md` | German | All German prose output |
| `es.md` | Spanish | All Spanish prose output |
| `it.md` | Italian | All Italian prose output |
| `pt.md` | Portuguese | All Portuguese prose output |

Each charter is authored natively in its own language, not translated from English. It
covers: punctuation rules (no punctuation dashes), machine-tell lists (language-specific
banned phrases), acronym glossing conventions, idiomatic register, and the Ralph Loop
paragraph-pair seam check (section 10 of the English charter, section "Révision par
paires de paragraphes" in the French one).

These files are the canonic sources. Keep them in sync with the upstream gists referenced
in `BEST_AI.md` before each major release.

### 2. Distilled block: `writing_rules.yaml`

`scripts/prompts/writing_rules.yaml` holds a 9-rule distillation of the charters in
language-neutral English. It covers the rules that apply across all output languages:
reconstructibility, gloss-on-first-use, invent-nothing, no punctuation dashes, no machine
tells, sober register, match the document language, and short sentences.

This block travels inside every prompt so the constraint is present at inference time, not
just at review time.

### 3. Prompt injection via `_prompts.load_prompt()`

`scripts/_prompts.py` is the single loading point for all prompt YAML files. When a
script calls `load_prompt("meta_tags_json")`, the loader:

1. Reads the prompt YAML (`scripts/prompts/meta_tags_json.yaml`).
2. Calls `writing_rules_block()` to load `writing_rules.yaml` from the same directory.
3. Exposes the result as `{writing_rules}` inside the template string.

The `render()` helper substitutes both the static charter block and the runtime fields
(page content, language line, etc.) in one call, so every script that uses `render()`
automatically enforces the charter.

## Which prompts enforce the charter

| Prompt file | Script | Output type |
|---|---|---|
| `meta_tags_json.yaml` | `meta_from_ollama.py` | Title, description, Open Graph, Schema.org type, keywords |
| `plain_language_rewrite.yaml` | `plain_language.py` | Plain-language rewrites at a target grade level |
| `latex_caption.yaml` | `lint_markdown.py` | One-sentence screen-reader captions for LaTeX blocks |
| `mermaid_labels.yaml` | `lint_markdown.py` | Label improvement suggestions for Mermaid diagrams |

The `narration_emotion.yaml` prompt is a TTS annotation classifier, not a prose generator;
it produces structured JSON, not human-readable text, so charter injection does not apply.

## Adding a new language charter

1. Copy `scripts/charters/en.md` as a starting point.
2. Rewrite it natively in the target language. Do not translate sentence by sentence;
   adapt idiom, punctuation conventions, and the banned-phrase list to native usage.
3. Add the file as `scripts/charters/<lang>.md` where `<lang>` is the BCP 47 primary
   language subtag (`de`, `es`, `it`, `pt`, `ja`, etc.).
4. Test that `plain_language.py --lang <lang>` produces output that reads like a literate
   native speaker wrote it, without any of the banned phrases from the charter.

The distilled `writing_rules.yaml` does not need updating for new languages: it is
intentionally language-neutral and applies to all output.

## Adding a new LLM prompt

1. Create `scripts/prompts/<name>.yaml` with the standard shape:
   ```yaml
   name: <name>
   version: 1
   role: |
     ...
   task: |
     ...
   rules:
     - ...
   output_contract: |
     ...
   template: |
     ...
     {writing_rules}
     ...
   ```
2. Include `{writing_rules}` in the template wherever the model produces human-readable
   text. Omit it only for prompts that produce pure structured output (JSON arrays, YAML)
   with no prose fields.
3. Load it with `_prompts.render("name", **runtime_fields)` in the calling script.
4. Test that a representative output passes the checklist in the next section.

## Manual audit checklist

Run this checklist on a sample of generated text before publishing a new site:

- [ ] No em dash or en dash used as a punctuation aside.
- [ ] No hollow openers ("In today's world", "It is important to note that", "In an era where").
- [ ] No bolted-on transitions with no real link ("Moreover", "Furthermore", "Additionally").
- [ ] No restatement tics ("In other words", "Simply put").
- [ ] No empty intensifiers ("truly", "deeply", "crucial", "vital", "cutting-edge").
- [ ] No reflexive see-saw ("not only X but also Y").
- [ ] No hollow closers ("In conclusion", "All in all").
- [ ] No inflated abstractions ("the landscape of", "delve into", "a game-changer").
- [ ] Every acronym glossed on first use.
- [ ] No invented facts (numbers, names, claims not in the source).
- [ ] Reads like the document's native language, not a translation.

## Automated audit (not yet built)

The planned audit gate (see `todo.md` §Side-workstream) will apply a RAGAS-style
claim-decompose pass to every generated field: each factual claim in the output is
verified against the source document with forced-quote grounding. A claim the model
cannot quote from the source is flagged as NOT_SUPPORTED.

Traffic-light routing:
- Green: all claims supported and no charter violations. Emit as-is.
- Amber: charter violations only (no invented facts). Flag the field; offer a rewrite.
- Red: unsupported factual claims. Strip the field and regenerate from source.

This gate will run as a post-processing step in `build_site.py` and as a standalone
`best-engine-ai-helper validate` subcommand once the prose Ralph loop is implemented.
