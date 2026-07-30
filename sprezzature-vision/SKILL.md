---
name: sprezzature-vision
description: >-
  W3C-compliant alt-text drafting via a local Ollama vision model: per-image
  decision tree for informative / decorative / functional / text / complex /
  group purposes, output in any detected language (native-language phrasing
  for common ones), surrounding- text and project-vocabulary biasing,
  deterministic
  on-disk cache so the same image + parameters never hit the model twice.
  The one authorized model is ``qwen3-vl:8b`` (registry-standard, multimodal)
  via Ollama, no other model, no MLX. For solo developers and small teams who
  want accessibility content drafted locally with no SaaS cost or data
  exfiltration. Drafts are starting points; verify before committing. Trigger
  phrases: "alt text", "alt text for this image", "describe this image",
  "draft alt", "image description", "img has no alt", "decorative image",
  "functional image", "figure / chart description", "accessible images",
  "batch alt text". Output is plain text / JSON on stdout suitable for
  pre-commit and CI.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Needs Python 3.10+ stdlib +
  Pillow + requests (see ``scripts/requirements-alt-text.txt``) and a
  running local Ollama daemon with a vision-capable model. The
  ``install_alt_ai.py`` script installs Ollama (brew on macOS, official
  installer on Linux, winget on Windows) and pulls the default model on
  first run.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
---

# sprezzature-vision — local AI alt text for accessibility

## Audience and positioning

Solo developers and small teams who:

- Need **W3C-compliant alt text** drafted from images at commit time, not
  at runtime via a hosted service.
- Want **AI that runs locally**: no SaaS, no data exfiltration, no per-image
  cost. Runs on any box through Ollama.
- Want **output in the reader's language**, auto-detected from the
  surrounding text (via `langdetect`), any language, not a fixed pair; no
  flag, no configured default. Common languages get a native-language
  prompt; the rest are named to the model so they still come out right.
- Want **vocabulary biasing** so the model knows your product / brand /
  technical-term spellings before it hallucinates a near-miss.

This skill is **not** a substitute for a human review pass. Each draft is
tagged ``data-alt-source="ai"`` so a reviewer can find it later. Top-tier
hosted vision (Claude vision, GPT-4o vision, Gemini) is more accurate;
use this skill when local-only matters or when the volume makes hosted
costs unattractive.

## Two modes — make and audit

This skill is **make-only** in the sprezzature-* duality, by design:

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — draft accessible image text | `scripts/alt_from_ollama.py` + `scripts/install_alt_ai.py` | W3C-compliant alt text via local Ollama vision (the one authorized model, `qwen3-vl:8b`; no other model, no MLX). Per-purpose decision tree, surrounding-text + vocabulary biasing, on-disk cache. |
| **Audit** — gate the presence of `alt=` | _(see `sprezzature-accessibility/scripts/lint_a11y.py`)_ | Static lint catches `<img>` without `alt` and `<img alt="">` on non-decorative images. |

Pair with `sprezzature-accessibility` to close the loop: this skill drafts
the text; the a11y lint verifies it lands on every `<img>`.

## Status — WiP

Every draft this skill produces is a **draft requiring human review**, never a
finished alt text. The local vision model gives context-aware, W3C-guided
starting points; a person still confirms each one before it ships. Still being
built out: a `deepeval` evaluation layer that measures the "context-aware,
W3C-guided" claim (purpose classification, language match, review-honesty), and
worked examples. Treat the output as assistive, not authoritative.

## Honest framing of what each tool covers

| Tool | Catches | Misses |
|---|---|---|
| `scripts/alt_from_ollama.py` | W3C-compliant alt for informative / decorative / functional / text / complex / group purposes; per-purpose YAML prompt templates; surrounding-text + project-vocabulary biasing; on-disk cache | model-quality drafts; verify each draft before committing. Top-tier hosted vision (Claude vision, GPT-4o vision, Gemini) is more accurate. Decorative images get ``alt=""`` (no model call). |
| `scripts/install_alt_ai.py` | Installs the Ollama daemon on the host (brew / official installer / winget) and pulls the default vision model. Idempotent; safe to re-run. | does not auto-update an already-installed daemon or model; does not enforce GPU drivers; does not start the daemon as a service on Linux. |

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "alt text" / `<img>` with no `alt` / "describe this image" | `alt_from_ollama.py` | Match W3C image-purpose decision tree → `python scripts/alt_from_ollama.py [--kind informative\|decorative\|functional\|text\|complex\|group] [--lang fr] [--in DOC] [--vocab-from DIR] <src>`. Tag drafts with `data-alt-source="ai"`. |
| "Ollama not installed" / "first-time setup" | `install_alt_ai.py` | `python scripts/install_alt_ai.py` — installs the daemon, pulls `qwen3-vl:8b`. |

## W3C image-purpose mapping

| Purpose | What it is | What this skill emits |
|---|---|---|
| **informative** | Conveys content (photos, illustrations carrying meaning) | Short literal description biased by surrounding text. |
| **decorative** | Pure ornament, no information value | ``alt=""`` — no model call, instant. |
| **functional** | Image acts as a control or link | Describes the *action or destination*, not the picture. |
| **text** | Image of text | Verbatim transcription of the text only. |
| **complex** | Charts, diagrams, infographics | Short alt + a long-form Markdown description (separate `<figcaption>` or linked `aria-describedby` target). |
| **group** | Multiple images conveying one idea | One unified description across the set. |

When the caller does not pass ``--kind``, the script falls back to
``informative``, the safest non-zero default for a random ``<img>``.

## Model

The one authorized model is **``qwen3-vl:8b``**, an 8B-parameter multimodal
model served through Ollama, in the public registry so ``ollama pull``
works on any box. No other model, no MLX, and the model is **not selectable**
on the command line: there is no ``--model`` flag. (``OLLAMA_MODEL`` is honoured
only as a bare test seam so the suite can point the resolver at a stub.)

The endpoint defaults to ``http://localhost:11434`` and can be
overridden with ``OLLAMA_URL``.

## Caching

Successful generations are cached under
``~/.cache/sprezzature-skill/alt/`` by default. The cache key includes the
image bytes, the image-purpose kind, the output language, any context
hint, and the resolved model tag, so changing any of those produces a
fresh draft. Override the cache root with ``SPREZZATURE_CACHE_DIR``; disable
caching for one call with ``--no-cache``.

## Tool composition

When emitting an ``<img>`` whose source path appears in a Markdown or
HTML doc, pass the doc as context:

```bash
python scripts/alt_from_ollama.py --in <that-doc> <image>
```

The surrounding text becomes both ``--context`` and the vocabulary
seed.

For a UI deliverable end-to-end:

```bash
python sprezzature-accessibility/scripts/lint_a11y.py public/                       # static a11y gate
python sprezzature-colors/scripts/audit_contrast.py --palette palette.json # WCAG ratios
python sprezzature-vision/scripts/alt_from_ollama.py public/hero.jpg       # AI alt text
```

## When NOT to use this skill

- You need **top-quality alt text and don't care about local-only / cost**
  → use Claude vision or GPT-4o vision APIs.
- You need **real-time alt** (live captioning of camera feeds) → not the
  shape of this tool; the cache assumes static inputs.
- You need **multi-modal models that also reason about page layout / DOM
  context** → use a hosted multimodal model that accepts HTML + image
  inputs.

## References

- ``references/alt-text-ai.md`` — W3C-compliant alt text via local Ollama
  + Qwen3-VL vision (per-purpose decision tree, prompt templates, cache
  semantics).

## Scripts

| Script | Install | Purpose |
|---|---|---|
| ``scripts/alt_from_ollama.py`` | ``pip install -r scripts/requirements-alt-text.txt`` + Ollama | W3C-compliant alt text via local vision model. |
| ``scripts/install_alt_ai.py`` | stdlib only (shells out to brew / winget / official installer) | Installs Ollama + pulls the default vision model (``qwen3-vl:8b``). |
| ``scripts/prompts/*.yaml`` | (data) | Per-purpose prompt templates (short / long × informative / functional / text / complex / group). |
| ``scripts/_argparse.py``, ``scripts/_click.py``, ``scripts/_lang.py``, ``scripts/_prompts.py``, ``scripts/_vocab.py`` | (internal helpers) | Argparse / Click factory, language detection, YAML prompt loader, project-vocab biasing. Duplicated per-skill so each skill stays self-contained. |

## Companion skills

| You also need… | Install |
|---|---|
| Static HTML a11y lint | ``sprezzature-accessibility`` |
| WCAG contrast audit, CVD simulation, curated palette | ``sprezzature-colors`` |
| Local WebVTT / SRT captions via whisper.cpp | ``sprezzature-audio`` |
| Vanilla-JS + Tailwind UI generation | ``sprezzature-ui`` |
| Wrap a CLI in a GUI | ``sprezzature-cli-gui`` |
| Markdown → website + meta + favicons + indexes | ``sprezzature-publish`` |
| Data-viz / explainability / causality figures | ``sprezzature-figures`` |
| Laws-of-UX audit on the surrounding page | ``sprezzature-ux-laws`` |
