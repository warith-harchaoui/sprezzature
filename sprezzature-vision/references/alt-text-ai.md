# AI-assisted Alt Text

The skill emits `<img>` tags with meaningful `alt`, following the W3C / WAI decision tree (<https://www.w3.org/WAI/tutorials/images/decision-tree/>). When the author hasn't supplied `alt`, the skill drafts it with a **local vision model running on Ollama**: nothing leaves the machine.

- **Model (default):** `qwen3-vl:8b`
- **Override anywhere:** `OLLAMA_MODEL=<tag>` (for example `qwen3-vl:8b`).

Runtime: **Python 3.9+** (cross-platform, one helper per task).

## W3C decision tree

Every image has a *purpose* in the page. Match the purpose to the right alt strategy before invoking the AI helper.

| Purpose | Alt strategy |
|---|---|
| **Decorative** (no information) | `alt=""`: empty alt only. No `role="presentation"` or `aria-hidden` needed. Don't call the AI. |
| **Informative** (conveys meaning) | Short alt describing the meaning in page context. Call `alt_from_ollama.py` with `--kind informative` (default). |
| **Functional** (inside `<a>` / `<button>`) | Alt describes the *action or destination*, not the image. Call with `--kind functional --context "<what the control does>"`. |
| **Text image** (mostly text) | Alt = the readable text verbatim. Call with `--kind text`. |
| **Complex** (chart, diagram, infographic) | Short alt + long description elsewhere (`<figcaption>` or `aria-describedby`). Call with `--kind complex`; pair with a separate long description. |
| **Group** of related images | One alt describes the whole; the rest get `alt=""`. Call with `--kind group`. |

`alt=""` is the empty-alt signal. **Never omit the `alt` attribute**: that makes screen readers read the filename.

## Install Ollama + pull the model

One command on every platform (the installer is in Python):

```bash
pip install -r scripts/requirements-alt-text.txt
python scripts/install_alt_ai.py
```

The installer:

- Detects the OS and uses the right package manager:
  - Darwin (any chip): Homebrew (`brew install ollama`: [brew.sh](https://brew.sh)).
  - Linux: the official Ollama installer script.
  - Windows: `winget install Ollama.Ollama`.
- Starts the Ollama daemon if it isn't already running.
- Pulls the default model tag (`qwen3-vl:8b`).

## Generate alt text

```bash
# informative (default)
python scripts/alt_from_ollama.py ./public/hero.jpg

# language
python scripts/alt_from_ollama.py --lang fr ./public/hero.jpg

# functional — describe the destination/action, not the visual
python scripts/alt_from_ollama.py --kind functional --context "Submit signup form" ./public/icons/check.png

# text-in-image — return the readable text verbatim
python scripts/alt_from_ollama.py --kind text ./public/quote-card.png

# complex (chart) — returns a SHORT summary; pair with a long description
python scripts/alt_from_ollama.py --kind complex --context "Weekly active users" ./public/chart.png

# complex AND long description — writes the Markdown long desc to chart.png.longdesc.md
python scripts/alt_from_ollama.py --kind complex --longdesc --context "Weekly active users" ./public/chart.png

# Use the surrounding text of a Markdown / HTML document as BOTH context
# and vocabulary. Highest-signal source for an embedded image.
python scripts/alt_from_ollama.py --in blog/post.md ./blog/figures/hero.png

# Walk the project root for proper-noun vocabulary
python scripts/alt_from_ollama.py --auto-project ./figures/diagram.png

# decorative — no API call needed; the script returns empty
python scripts/alt_from_ollama.py --kind decorative ./public/divider.svg
```

Output: one line of alt text on stdout, hard-capped at 150 characters at a word boundary, **never** with a trailing `…`. Empty stdout for decorative.

Python API:

```python
from alt_from_ollama import describe
alt = describe("public/hero.jpg", kind="informative", lang="fr", context="Careers page hero")
```

## Use from the skill (server-side proxy)

Browser callers go through a small Python proxy: Ollama doesn't speak CORS to web pages.

```python
# pip install fastapi uvicorn requests Pillow
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "sprezzature" / "scripts"))
from alt_from_ollama import describe

app = FastAPI()

class Req(BaseModel):
    src: str
    kind: str = "informative"
    lang: str | None = None
    context: str = ""

@app.post("/alt")
def alt(req: Req) -> dict:
    text = describe(req.src, kind=req.kind, lang=req.lang, context=req.context)
    return {"alt": text, "decorative": req.kind == "decorative"}
```

Front-end:

```js
async function altFor(src, opts = {}) {
  const r = await fetch("/alt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ src, ...opts }),
  });
  return r.json();
}
```

## Rules the prompt enforces

1. **Image purpose decides the prompt** (per W3C). No generic one-size prompt.
2. **Hard cap 150 characters**: no `…` truncation; the script regenerates or cuts at a word boundary.
3. **Match meaning, not pixels.** A photo of a smiling teacher in a classroom is "Teacher leading a class", not "An adult standing in front of children with a chalkboard behind".
4. **No banned prefixes**: "image of", "photo of", "picture of", "illustration of", and their equivalents in 9 other languages. The script strips them if the model ignores the instruction.
5. **Be specific where relevant to meaning.** For news photos, name visible people, setting, action; don't sanitize to "a person".
6. **Functional alt describes the action**, not the visual. A magnifying-glass icon in a search button → `alt="Search"`, not `alt="Magnifying glass"`.
7. **Text-as-image is extracted verbatim.**
8. **Complex returns short alt only**; the long description belongs in `<figcaption>` or `aria-describedby`.

## Review workflow

AI-generated alt is a draft, not a final answer. Tag every AI-drafted attribute so a review tool can flag it:

```html
<img src="…" alt="Teacher leading a class" data-alt-source="ai">
```

Strip `data-alt-source="ai"` once a human has reviewed and approved.

## Cache

Both `alt_from_ollama.py` and `meta_from_ollama.py` cache results on disk so the same input never hits the model twice. Stdlib-only, no extra dependency.

- **Location:** `~/.cache/sprezzature-skill/alt/` (override with `SPREZZATURE_CACHE_DIR=<path>`).
- **Key:** SHA-256 of (image bytes + `kind` + `lang` + `context` + `model`). Truncated to 32 hex chars for filenames.
- **Bypass once:** `--no-cache` on the CLI.
- **Bypass globally:** `SPREZZATURE_NO_CACHE=1` in the environment.
- **Clear:** delete the directory.

Cache writes fail silently (`try/except OSError`): caching is opportunistic and never fatal.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `Cannot reach Ollama at http://localhost:11434` | Daemon not running | `python scripts/install_alt_ai.py` (idempotent) or `ollama serve`. |
| `Error: model not found` | Tag mistyped or installer skipped | Re-run installer, or `ollama pull qwen3-vl:8b` directly. |
| Garbled or hallucinated text | Image very small / very large | The script downscales to 1024 px by default; raise quality of source or set `--resize 768`. |
| Very slow first call | First inference loads weights | Subsequent calls are fast; keep the daemon up. |

## Related script: meta tags

The same Ollama setup powers `python sprezzature-publish/scripts/meta_from_ollama.py`, which drafts the page-level `<title>`, `<meta name="description">`, Open Graph, Twitter, and JSON-LD `@type` from a goal description or an HTML page. See `references/meta-tags.md`.

## Checklist

- [ ] `python scripts/install_alt_ai.py` ran and the model is in `ollama list`.
- [ ] `python scripts/alt_from_ollama.py <test image>` returns a non-empty string.
- [ ] Decorative images use `alt=""` alone (no `role="presentation"`, no `aria-hidden`).
- [ ] Every AI-drafted `alt` carries `data-alt-source="ai"` until a human reviews it.
- [ ] Complex images pair a short alt with a long description in `<figcaption>` / `aria-describedby`.
- [ ] Functional `alt` describes the action/destination, not the icon.
- [ ] No `alt` ever ends in `…`.
