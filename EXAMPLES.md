# EXAMPLES

A runnable cookbook for the `sprezzature-*` skill suite: one section per skill,
each with a copy-paste command and the output you should expect. Commands are
written to run from the **repository root** and use the checked-in fixtures
under `tests/fixtures/`, so every deterministic recipe here runs with no setup
beyond the skill's own dependencies.

See also: [`README.md`](README.md) for the skill map, [`GALLERY.md`](GALLERY.md)
for real projects shipped with the suite, and each skill's `SKILL.md` for the
full flag surface.

## Two kinds of recipe

- **Deterministic** (`[det]`): pure Python, no model, no network. Runs anywhere;
  output is byte-stable. These are the audit gates and the make-from-data
  generators. Safe in CI and `pre-commit`.
- **Local-AI** (`[ai]`): calls a **local** model (Ollama for vision/text, a local
  whisper.cpp build for audio). Never a SaaS. Requires a one-time `install_*`
  step; output varies by model. Draft-quality: verify before shipping.

Exit codes follow the usual convention: `0` = clean / success, non-zero =
findings or error (so the audits gate a commit).

---

## sprezzature-accessibility `[det]`: static accessibility (a11y) lint

Lint a static HyperText Markup Language (HTML) file for the 14 source-decidable accessibility rules
(missing `alt`, unlabelled inputs, `<div onclick>`, heading order, …):

```bash
sprezzature-accessibility-lint tests/fixtures/html/landing.html
```

Expected output (a clean fixture):

```text

0 findings.
```

Exit code `0`. A file with problems prints one line per finding (`file:line:
RULE message`) and exits non-zero. Add `--fix` to apply the safe repairs
(lang attribute, redundant Accessible Rich Internet Applications (ARIA), positive tabindex, aria-hidden-interactive,
motion-reduce guard) in place, and `--json` for machine-readable output.

## sprezzature-ux-laws `[det]`: Laws-of-user-experience (UX) audit

Audit HTML for the mechanically-detectable Laws of UX (Hick, Miller, Fitts,
Jakob, Tesler, Aesthetic-Usability, …), as JavaScript Object Notation (JSON):

```bash
python3 -m sprezzature_ux_laws_scripts.audit_laws_of_ux tests/fixtures/html/landing.html --json
```

Expected output (shape):

```json
[
  {
    "law": "aesthetic-usability",
    "severity": "warning",
    "path": "tests/fixtures/html/landing.html",
    "line": 24,
    "message": "<a> has no focus-visible:ring-* class. Add the house focus token.",
    "snippet": ""
  }
]
```

`--fix` applies the four mechanical fixers (Fitts / Aesthetic-Usability /
Miller / Jakob) with an idempotent convergence loop; `--only hick,jakob` and
`--ignore tesler,miller` scope the run; `--strict` upgrades warnings to errors.

## sprezzature-colors `[det]`: Web Content Accessibility Guidelines (WCAG) contrast, color-vision deficiency (CVD), palette → Tailwind

Audit a palette for WCAG contrast (suggests OKLCH (the perceptual OKLCH color space)-neighbour fixes):

```bash
python3 -m sprezzature_colors_scripts.audit_contrast --palette palette.json --target 4.5
```

Turn the canonical palette comma-separated-values (CSV) file into a drop-in `tailwind.config.js`:

```bash
python3 -m sprezzature_colors_scripts.palette_to_tailwind --emit theme > tailwind.theme.js
```

Simulate colour-vision deficiency on a screenshot (writes protanopia /
deuteranopia / tritanopia variants next to the input):

```bash
python3 -m sprezzature_colors_scripts.simulate_cvd tests/fixtures/images/chart-bar.png
```

All three are deterministic: no model, no network.

## sprezzature-figures `[det]`: figures, diagrams, and the Ralph Eyeball Loop

**Known bug:** `make-figure` (below) currently fails on a normally
pip-installed `sprezzature-figures` with "Registered module ... not
found"; the chart-kind registry resolves generator paths against a
development checkout layout, not the installed package layout. The
other recipes in this section (`render_diagram`, `audit_figure`,
`explain_model`, `causal_estimate`) are unaffected.

Prefer Vega-Lite over matplotlib / seaborn / pyplot / plotly: a house-styled
spec carries its own data, looks better by default, and covers nearly their
whole plotting application-programming-interface (API). The rendered proof is in
[`docs/FIGURES.md`](docs/FIGURES.md).

**The Ralph Eyeball Loop**: render a source to an image, *look* at it, refine
the source, repeat. The kind (Vega / TikZ / Mermaid / SVG) is auto-detected. A
runnable Vega spec ships in the repo, so this recipe needs no data of your own:

```bash
python3 -m sprezzature_figures_scripts.render_diagram \
  sprezzature-figures/assets/vega-examples/hexbin.vl.json --background white --out /tmp/hexbin.png
# → wrote /tmp/hexbin.png   (now open it, critique, edit the spec, re-render)
```

Never draw diagrams in ASCII; write colored Mermaid and render it the same way:

```bash
printf 'flowchart LR\n  A[Browser] --> B[FastAPI] --> C[(DB)]\n' > /tmp/flow.mmd
python3 -m sprezzature_figures_scripts.render_diagram /tmp/flow.mmd --background transparent --out /tmp/flow.png
```

Audit a Vega-Lite spec for data-viz sins (truncated baselines, dual y-axes,
rainbow palettes, missing labels), again against a committed spec:

```bash
python3 -m sprezzature_figures_scripts.audit_figure sprezzature-figures/assets/vega-examples/bar.vl.json
```

Make a figure straight from a data file (a catalogue kind, not a free
`--x/--y/--kind` combination: `sprezzature-figures list` shows what exists),
or run the explainability / causal recipes (these use *your* files and need
the tiers via `install_figures.py --tier dataviz+explain+causal`):

```bash
# `bar`'s roles are `region` (categorical) and `value` (numeric).
make-figure bar --data data.csv --map region=category_col --map value=value_col --out chart.svg
python3 -m sprezzature_figures_scripts.explain_model --model model.pkl --data X.csv --engine shapash --report shapash --out ./explain/
python3 -m sprezzature_figures_scripts.causal_estimate --data d.csv --treatment T --outcome Y --confounders "X1,X2,X3" --dag dag.gml
```

**Situation maps are currently unavailable.** `make_situation_map.py` and
`build_situation_examples.py` (the areas-of-control plate generator this
recipe used to show) have been removed from the standalone `sprezzature-figures`
package; only stale compiled bytecode remains. Do not run the commands this
recipe used to list here until the generator ships again.

## sprezzature-publish `[det]`: Markdown → site, meta, favicons, indexes

Lint a Markdown file (heading sentinel, trailing whitespace, fenced-code
language); `--fix` applies the safe rewrites:

```bash
python3 sprezzature-publish/scripts/lint_markdown.py tests/fixtures/public/gettysburg.md
```

A clean file prints nothing and exits `0`. Generate a full favicon / app-icon /
progressive-web-app (PWA) icon set from one logo (needs Pillow):

```bash
python3 sprezzature-publish/scripts/favicons.py logo.png --out public --name "My Project"
```

Emit `robots.txt` + `sitemap.xml` + `llms.txt` + optional Atom feed for a docs
tree:

```bash
python3 sprezzature-publish/scripts/site_indexes.py --root . --base-url https://example.com --feed-from posts
```

Narration (`narrate_post.py`) and meta-tag drafting (`meta_from_ollama.py`) are
`[ai]` local-AI (see below).

## sprezzature-cli-gui `[det]`: wrap a command-line interface (CLI) in a graphical user interface (GUI)

Introspect a Python CLI's argument parser (argparse **or** Click, auto-detected)
and emit a single-page vanilla-JavaScript (JS) + Tailwind GUI. Point `spec` at a zero-arg
factory that returns the parser/command:

```bash
# demo_cli.py exposes `def make_parser() -> argparse.ArgumentParser`
sprezzature-cli-gui demo_cli.py:make_parser --out gui.html
```

Expected output:

```text
cli_to_gui: wrote gui.html
```

For any CLI whose factory can't be imported, or a non-Python binary
(clap / cobra / commander), parse its `--help` text instead:

```bash
sprezzature-cli-gui --from-help "python3 -m json.tool" --out gui.html
```

The emitted HTML passes both the `sprezzature-ux-laws` and `sprezzature-accessibility`
audits with zero findings (the emitter is its own customer). A runnable worked
example ships in `sprezzature-cli-gui/assets/examples/cli-gui-demo/`.

## sprezzature-vision `[ai]`: alt text via a local vision model

One-time install (pulls a local Ollama vision model):

```bash
python3 sprezzature-vision/scripts/install_alt_ai.py
```

Draft World Wide Web Consortium (W3C)-compliant alt text for an image (bilingual EN/FR by default):

```bash
python3 sprezzature-vision/scripts/alt_from_ollama.py tests/fixtures/images/portrait.jpg
```

Prints the drafted alt text to stdout. `--kind informative|decorative|functional|
text|complex|group` forces the purpose; results are cached on disk so the same
image + parameters never hit the model twice. Draft-quality: verify before
committing.

## sprezzature-audio `[ai]`: captions, diarization, speaker naming

One-time install (pip-installs `vocal-helper` / whisper.cpp and pre-downloads a
GGML model so it runs offline):

```bash
python3 -m sprezzature_audio_scripts.install_captions
```

Transcribe audio/video to WebVTT / SubRip subtitle format (SRT) / plain text (local, never a SaaS):

```bash
sprezzature-audio-captions interview.mp4 --format vtt
```

Add "who spoke when" and "who is who" (needs `install_diarize.py` for the NeMo
Sortformer + TitaNet weights):

```bash
sprezzature-audio-diarize interview.wav --out interview.diarization.json
sprezzature-audio-pipeline --captions interview.vtt --diarization interview.diarization.json
```

Add a **second, translated subtitle track** in the language of the page that
embeds the video (native `captions` + translated `subtitles`). Runs on the
`.vtt` only (no audio) via the local `qwen3-vl:8b` model:

```bash
sprezzature-audio-translate interview.vtt --in article.html --media interview.mp4
# → writes interview.<lang>.vtt and prints:
#   <video controls>
#     <source src="interview.mp4" />
#     <track kind="captions" srclang="en" label="English" src="interview.vtt" default />
#     <track kind="subtitles" srclang="fr" label="Français" src="interview.fr.vtt" />
#   </video>
```

## sprezzature-ui `[det]`: the stack rules + component assets

`sprezzature-ui` is reference-first: it sets the vanilla-JS + Tailwind house style
(three-Roboto default, dark-mode peers, focus rings, reduced-motion guards) that
every other skill's output follows. Its make-side assets ship ready to copy:

```bash
# Starter page and law-keyed component snippets
ls sprezzature-ui/assets/starter-page.html sprezzature-ui/assets/snippets/
```

Validate that a skill folder is spec-compliant (used in CI via
`scripts/validate_all.py`):

```bash
python3 sprezzature-ui/scripts/validate.py sprezzature-ui
```

**i18n: one `locales/i18n.yaml` for GUI strings AND prompts** (make + audit):

```bash
# make: scaffold locales/i18n.yaml (gui: + prompts:), compile to i18n.json,
# emit the vanilla-JS loader (initI18n / t)
python3 sprezzature-ui/scripts/i18n_make.py --dir .
# -> created ./locales/i18n.yaml  |  compiled ./locales/i18n.json  |  emitted ./locales/i18n.js

# audit: flag translations embedded in JS/HTML (I18N001) or prompts inlined
# in Python (I18N002); they belong in the catalog. 0 = clean, 1 = findings.
python3 sprezzature-ui/scripts/audit_i18n.py src/
```

In the browser: `import { initI18n, t } from "./locales/i18n.js";
await initI18n(); el.textContent = t("action.save");`.

---

## Running the whole audit sweep

The deterministic audits are wired as `pre-commit` hooks (see
`.pre-commit-hooks.yaml`) so they gate commits. To run the repo's own checks:

```bash
python3 scripts/validate_all.py     # spec + content gate on all 9 skills
python3 -m pytest -q                 # full test suite (incl. tests/eval/ AI-eval layer)
```
