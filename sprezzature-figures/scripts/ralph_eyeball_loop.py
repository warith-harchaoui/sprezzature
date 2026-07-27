#!/usr/bin/env python3
"""
ralph_eyeball_loop
==================

The **Ralph Eyeball Loop** — the universal visual-quality technique for the
``front-*`` repo. Render any visual-from-code artifact to a PNG, critique it
honestly, edit the source, and loop until satisfied.

The loop applies to every surface that produces a visual from code:

* **Web pages and GUI screens** — ``.html``, ``.htm`` (Chrome headless)
* **Data figures** — ``.vl.json``, ``.vg.json`` (Vega-Lite / Vega via vl-convert)
* **Mathematical figures** — ``.tex``, ``.tikz`` (TikZ via tectonic / pdflatex)
* **Flow and architecture diagrams** — ``.mmd``, ``.mermaid`` (Mermaid via mmdc)
* **Hand-authored graphics** — ``.svg`` (rsvg-convert or ImageMagick)

Data viz is *one* application. A webpage, a UI component, a Mermaid
architecture diagram — all go through the same four-step cycle.

Two modes
---------
**Agent mode (default)**
    The Claude Code / OpenCode agent reads the rendered PNG with its own
    vision and fills in the assessment template.  No Ollama call.  This is
    the primary, recommended workflow when running inside Claude Code.

**Local mode** (``--local``)
    A fully offline alternative.  After rendering the PNG, the script calls
    ``qwen3-vl:8b`` via Ollama (a vision-language model) to generate the
    critique automatically and pre-fill the assessment file.  No cloud API,
    no Claude Code session required — works in any terminal once Ollama is
    running and the model is pulled.

    Pull the model once::

        ollama pull qwen3-vl:8b

The loop (both modes)
---------------------
1. **Render** — PNG at the deployment-context size / background.
2. **Look**   — agent or Ollama vision reads the PNG.
3. **Assess** — critique written to ``.private/ralph-loop/assessment-<hash>.md``
   (gitignored, never committed; extended each iteration).
4. **Edit**   — improve the *source* (never the PNG).
5. **Repeat** — re-run; a new iteration section is appended.  Stop when the
   Verdict box is checked.

Rendering toolchain per surface
---------------------------------
+--------------------+----------------------------------------------+-----------------------------+
| Surface            | Tool                                         | Install                     |
+====================+==============================================+=============================+
| HTML / JS page     | Headless Chrome (Google Chrome or Chromium)  | https://google.com/chrome   |
+--------------------+----------------------------------------------+-----------------------------+
| Vega-Lite / Vega   | vl-convert-python (pure-Python wheel)        | pip install vl-convert-python|
+--------------------+----------------------------------------------+-----------------------------+
| Mermaid diagram    | mmdc (mermaid-cli)                           | npm install -g @mermaid-js/mermaid-cli |
+--------------------+----------------------------------------------+-----------------------------+
| TikZ figure        | tectonic (preferred) or pdflatex + pdftoppm  | brew install tectonic       |
+--------------------+----------------------------------------------+-----------------------------+
| SVG graphic        | rsvg-convert (preferred) or magick           | brew install librsvg        |
+--------------------+----------------------------------------------+-----------------------------+
| Local critique     | qwen3-vl:8b via Ollama                      | ollama pull qwen3-vl:8b    |
+--------------------+----------------------------------------------+-----------------------------+

Run ``python ralph_eyeball_loop.py --install-tools`` to check what is
installed and pip/npm-install what can be done automatically.

Usage
-----
::

    # Agent mode — desktop (default 1440 × 900)
    python sprezzature-figures/scripts/ralph_eyeball_loop.py web/index.html

    # Agent mode — mobile
    python sprezzature-figures/scripts/ralph_eyeball_loop.py web/index.html --width 375 --height 812

    # Local mode — Vega spec, critique filled in by Ollama vision
    python sprezzature-figures/scripts/ralph_eyeball_loop.py figs/histogram.vl.json --local

    # Local mode — Mermaid diagram, transparent canvas
    python sprezzature-figures/scripts/ralph_eyeball_loop.py docs/flow.mmd --bg transparent --local

    # Local mode — TikZ figure, dark canvas
    python sprezzature-figures/scripts/ralph_eyeball_loop.py figs/dag.tex --bg dark --dark --local

    # Local mode — SVG
    python sprezzature-figures/scripts/ralph_eyeball_loop.py figs/icon.svg --local

    # Check / install the rendering toolchain
    python sprezzature-figures/scripts/ralph_eyeball_loop.py --install-tools

Notes
-----
* Assessment files are keyed by a stable 8-char MD5 of the *resolved* source
  path — the same source always maps to the same assessment slot.
* ``.private/`` is in the top-level ``.gitignore``; assessment files and
  rendered PNGs are never committed.
* For diagram surfaces (Vega / TikZ / Mermaid / SVG), rendering is delegated
  to ``render_diagram.py`` in the same directory.
* Python 3.10+.  No extra stdlib-beyond dependencies; rendering tools are
  checked and surfaced as loud errors when absent.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths — resolved at import time so the script works from any cwd
# ---------------------------------------------------------------------------
_SCRIPT_DIR: Path = Path(__file__).resolve().parent      # sprezzature-figures/scripts/
_FIGURES_ROOT: Path = _SCRIPT_DIR.parent                 # sprezzature-figures/
_REPO_ROOT: Path = _FIGURES_ROOT.parent                  # sprezzature/ (project root)
_RENDER_DIAGRAM: Path = _SCRIPT_DIR / "render_diagram.py"

# Gitignored output directory (covered by .private/ in the top-level .gitignore).
_PRIVATE_LOOP_DIR: Path = _REPO_ROOT / ".private" / "ralph-loop"

# ---------------------------------------------------------------------------
# Ollama — the one authorized VLM for the whole front-* repo
# qwen3-vl:8b is a vision-language model (VLM): handles both text generation
# (used by other skills) and image understanding (--local critique mode here).
# ---------------------------------------------------------------------------
_VISION_MODEL: str = "qwen3-vl:8b"
_OLLAMA_URL: str = "http://localhost:11434/api/generate"
#: Generous ceiling: a cold model load (~6 GB) plus a tall full-page screenshot
#: on Apple Silicon can take minutes on the first call. Warm calls are seconds.
_OLLAMA_TIMEOUT: int = 600

#: Headless Chrome refuses to make its window narrower than this (~500 px on
#: macOS/Linux). Below it, the page lays out at ~485 px and the screenshot
#: crops — a false-overflow trap. HTML renders clamp to this floor and warn.
_CHROME_MIN_VIEWPORT: int = 500

# ---------------------------------------------------------------------------
# Surface kinds
# ---------------------------------------------------------------------------
_KIND_HTML: str = "html"
_KIND_VEGA: str = "vega"
_KIND_TIKZ: str = "tikz"
_KIND_MERMAID: str = "mermaid"
_KIND_SVG: str = "svg"

# Kinds delegated to render_diagram.py.
_DIAGRAM_KINDS: frozenset[str] = frozenset({_KIND_VEGA, _KIND_TIKZ, _KIND_MERMAID, _KIND_SVG})

# Suffix → kind (sorted longest-first so ".vl.json" matches before ".json").
_SUFFIX_KIND: dict[str, str] = {
    ".vl.json":  _KIND_VEGA,
    ".vg.json":  _KIND_VEGA,
    ".json":     _KIND_VEGA,
    ".tex":      _KIND_TIKZ,
    ".tikz":     _KIND_TIKZ,
    ".mmd":      _KIND_MERMAID,
    ".mermaid":  _KIND_MERMAID,
    ".svg":      _KIND_SVG,
    ".html":     _KIND_HTML,
    ".htm":      _KIND_HTML,
}

# ---------------------------------------------------------------------------
# Tool definitions — one record per surface / dependency
# ---------------------------------------------------------------------------
# Each entry: (display_name, check_fn_name_or_None, pip_pkg, npm_pkg,
#              brew_pkg, manual_url, description)
# check_fn returns True when the tool is usable.
_TOOLS: list[dict] = [
    {
        "name": "Chrome / Chromium",
        "kind": _KIND_HTML,
        "description": "Headless browser for HTML/JS page screenshots.",
        "pip": None,
        "npm": None,
        "brew": "google-chrome",
        "manual": "https://www.google.com/chrome/",
        "check": lambda: _chrome_path() is not None,
    },
    {
        "name": "vl-convert-python",
        "kind": _KIND_VEGA,
        "description": "Pure-Python wheel that rasterises Vega-Lite / Vega specs.",
        "pip": "vl-convert-python",
        "npm": None,
        "brew": None,
        "manual": None,
        "check": lambda: _importable("vl_convert"),
    },
    {
        "name": "mmdc (mermaid-cli)",
        "kind": _KIND_MERMAID,
        "description": "Node.js CLI that renders Mermaid diagrams.",
        "pip": None,
        "npm": "@mermaid-js/mermaid-cli",
        "brew": None,
        "manual": "https://github.com/mermaid-js/mermaid-cli",
        "check": lambda: bool(shutil.which("mmdc")),
    },
    {
        "name": "tectonic",
        "kind": _KIND_TIKZ,
        "description": "Self-contained TeX engine for TikZ figures (preferred).",
        "pip": None,
        "npm": None,
        "brew": "tectonic",
        "manual": "https://tectonic-typesetting.github.io/",
        "check": lambda: bool(shutil.which("tectonic")),
    },
    {
        "name": "pdftoppm (poppler)",
        "kind": _KIND_TIKZ,
        "description": "PDF → PNG rasteriser used after pdflatex/tectonic.",
        "pip": None,
        "npm": None,
        "brew": "poppler",
        "manual": "https://poppler.freedesktop.org/",
        "check": lambda: bool(shutil.which("pdftoppm")),
    },
    {
        "name": "rsvg-convert (librsvg)",
        "kind": _KIND_SVG,
        "description": "High-fidelity SVG → PNG rasteriser.",
        "pip": None,
        "npm": None,
        "brew": "librsvg",
        "manual": "https://wiki.gnome.org/Projects/LibRsvg",
        "check": lambda: bool(shutil.which("rsvg-convert")),
    },
    {
        "name": "ImageMagick",
        "kind": "fallback",
        "description": "Fallback rasteriser for SVG and TikZ when preferred tools are absent.",
        "pip": None,
        "npm": None,
        "brew": "imagemagick",
        "manual": "https://imagemagick.org/",
        "check": lambda: bool(shutil.which("magick") or shutil.which("convert")),
    },
    {
        "name": f"Ollama + {_VISION_MODEL}",
        "kind": "local-critique",
        "description": "Vision-language model for --local mode automated critique.",
        "pip": None,
        "npm": None,
        "brew": None,
        "manual": "https://ollama.com/",
        "check": lambda: _ollama_model_available(),
    },
]


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------
def _importable(module: str) -> bool:
    """Return True when *module* can be imported."""
    import importlib.util
    return importlib.util.find_spec(module) is not None


def _chrome_path() -> Optional[str]:
    """Return the path to Chrome / Chromium, or None."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ]
    for c in candidates:
        p = Path(c)
        if p.is_file() and p.stat().st_mode & 0o111:
            return str(p)
        if shutil.which(c):
            return c
    return None


def _find_chrome() -> str:
    """Return the Chrome path, or raise SystemExit."""
    path = _chrome_path()
    if path is None:
        raise SystemExit(
            "ralph_eyeball_loop: Chrome / Chromium not found.\n"
            "  macOS : install Google Chrome — https://www.google.com/chrome/\n"
            "  Linux : apt install chromium-browser  |  snap install chromium"
        )
    return path


def _ollama_model_available() -> bool:
    """Return True when Ollama is reachable and the vision model is pulled."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        model_names = [m.get("name", "") for m in data.get("models", [])]
        # Accept exact match or tag-prefix match (e.g. "qwen3-vl:8b" or
        # "qwen3-vl:8b-instruct-q4_K_M").
        prefix = _VISION_MODEL.split(":")[0]
        return any(_VISION_MODEL in n or n.startswith(prefix + ":") for n in model_names)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tool check / install
# ---------------------------------------------------------------------------
def check_tools(verbose: bool = True) -> dict[str, bool]:
    """Print a table of tool installation status and return a name → bool dict.

    Parameters
    ----------
    verbose : bool
        Print the status table when True.

    Returns
    -------
    dict[str, bool]
        Tool display name → installed.
    """
    status: dict[str, bool] = {}
    col = 34
    if verbose:
        print(f"{'Tool':<{col}}  {'Surface':<16}  Status")
        print("-" * (col + 36))
    for tool in _TOOLS:
        try:
            ok = tool["check"]()
        except Exception:
            ok = False
        status[tool["name"]] = ok
        if verbose:
            mark = "✓" if ok else "✗"
            print(f"{tool['name']:<{col}}  {tool['kind']:<16}  {mark}  {tool['description']}")
    if verbose:
        print()
        missing = [t for t in _TOOLS if not status[t["name"]]]
        if missing:
            print("Missing tools:")
            for t in missing:
                if t["pip"]:
                    print(f"  pip install {t['pip']}")
                if t["npm"]:
                    print(f"  npm install -g {t['npm']}")
                if t["brew"]:
                    print(f"  brew install {t['brew']}   # or see: {t['manual'] or ''}")
                if t["name"].startswith("Ollama"):
                    print("  ollama serve   # start Ollama daemon")
                    print(f"  ollama pull {_VISION_MODEL}")
        else:
            print("All tools installed.")
    return status


def install_tools() -> None:
    """Auto-install pip and npm tools; print manual steps for the rest."""
    status = check_tools(verbose=False)
    for tool in _TOOLS:
        if status[tool["name"]]:
            print(f"  ✓ {tool['name']} — already installed")
            continue
        if tool["pip"]:
            print(f"  pip install {tool['pip']} …")
            subprocess.run([sys.executable, "-m", "pip", "install", tool["pip"]], check=True)
            print(f"  ✓ {tool['name']} installed")
        elif tool["npm"]:
            print(f"  npm install -g {tool['npm']} …")
            npm = shutil.which("npm")
            if npm is None:
                print("    (npm not found — install Node.js from https://nodejs.org/ first)")
                continue
            subprocess.run([npm, "install", "-g", tool["npm"]], check=True)
            print(f"  ✓ {tool['name']} installed")
        else:
            hints: list[str] = []
            if tool["brew"]:
                hints.append(f"brew install {tool['brew']}")
            if tool["manual"]:
                hints.append(tool["manual"])
            if tool["name"].startswith("Ollama"):
                hints = ["ollama serve", f"ollama pull {_VISION_MODEL}"]
            print(f"  ✗ {tool['name']} — manual install: {' | '.join(hints)}")
    print()
    print("Re-run with --check-tools to verify the updated status.")


# ---------------------------------------------------------------------------
# Kind detection
# ---------------------------------------------------------------------------
def _detect_kind(path: Path) -> str:
    """Return the surface kind for *path* from its suffix.

    Parameters
    ----------
    path : Path
        Source file. Lowercased and matched against :data:`_SUFFIX_KIND`,
        longest suffix first.

    Returns
    -------
    str
        One of the ``_KIND_*`` constants.

    Raises
    ------
    SystemExit
        When no known suffix matches.
    """
    name = path.name.lower()
    for suffix in sorted(_SUFFIX_KIND, key=len, reverse=True):
        if name.endswith(suffix):
            return _SUFFIX_KIND[suffix]
    known = ", ".join(sorted(_SUFFIX_KIND))
    raise SystemExit(
        f"ralph_eyeball_loop: cannot detect surface kind for {path.name!r}.\n"
        f"Known suffixes: {known}"
    )


# ---------------------------------------------------------------------------
# Stable per-source hash
# ---------------------------------------------------------------------------
def _source_hash(path: Path) -> str:
    """Return an 8-char MD5 of the *resolved* absolute source path.

    Parameters
    ----------
    path : Path
        Source file.

    Returns
    -------
    str
        8 lowercase hex characters.
    """
    return hashlib.md5(str(path.resolve()).encode()).hexdigest()[:8]


def _rel(path: Path) -> str:
    """Return *path* relative to cwd when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path.resolve())


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------
def _render_html(src: Path, out: Path, width: int, height: int) -> None:
    """Screenshot an HTML page via headless Chrome.

    Parameters
    ----------
    src : Path
        HTML source file (resolved to absolute for the ``file://`` URL).
    out : Path
        PNG output path.
    width, height : int
        Viewport size in CSS pixels.

    Raises
    ------
    SystemExit
        When Chrome is not found or the screenshot fails.
    """
    chrome = _find_chrome()

    # Headless Chrome enforces a *minimum window width* (~500 px on macOS/Linux
    # builds): request a narrower window and Chrome silently lays the page out
    # at ~485 px, then the screenshot crops it to the requested width. That crop
    # looks exactly like a horizontal-overflow bug that isn't there. So a width
    # below the floor is a false-mobile trap — clamp it and say so out loud. For
    # a pixel-true phone viewport (375 px), use a real browser's device-mode;
    # the flag-only path cannot emulate it.
    effective_width = width
    if width < _CHROME_MIN_VIEWPORT:
        effective_width = _CHROME_MIN_VIEWPORT
        print(
            f"ralph_eyeball_loop: requested width {width} px is below Chrome's "
            f"headless minimum (~{_CHROME_MIN_VIEWPORT} px). Rendering at "
            f"{effective_width} px (a large-phone viewport) to avoid a "
            "misleading crop. For a true 375 px phone view, use a browser's "
            "device-mode.",
            file=sys.stderr,
        )

    url = f"file://{src.resolve()}"
    proc = subprocess.run(
        [
            chrome,
            "--headless=new",
            f"--screenshot={out}",
            f"--window-size={effective_width},{height}",
            # Without this the 15 px scrollbar makes the CSS viewport 15 px
            # narrower than the window, so the render never matches the width
            # you asked for. Hiding it makes viewport == window width.
            "--hide-scrollbars",
            "--no-sandbox",
            url,
        ],
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode(errors="replace")[-1000:]
        raise SystemExit(f"ralph_eyeball_loop: Chrome exited {proc.returncode}:\n{detail}")


def _render_diagram(src: Path, out: Path, bg: str, dark: bool) -> None:
    """Delegate diagram rendering to ``render_diagram.py``.

    Parameters
    ----------
    src : Path
        Vega / TikZ / Mermaid / SVG source file.
    out : Path
        PNG output path.
    bg : str
        Background token: ``"white"`` | ``"transparent"`` | ``"dark"`` | ``#RRGGBB``.
    dark : bool
        Activate the dark-mode house canvas.

    Raises
    ------
    SystemExit
        When ``render_diagram.py`` is missing or exits non-zero.
    """
    if not _RENDER_DIAGRAM.is_file():
        raise SystemExit(
            f"ralph_eyeball_loop: render_diagram.py not found at {_RENDER_DIAGRAM}.\n"
            "Ensure sprezzature-figures is installed and this script lives in "
            "sprezzature-figures/scripts/."
        )
    cmd = [
        sys.executable, str(_RENDER_DIAGRAM),
        str(src),
        "--background", bg,
        "--out", str(out),
    ]
    if dark:
        cmd.append("--dark")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"ralph_eyeball_loop: render_diagram.py exited {result.returncode}")


# ---------------------------------------------------------------------------
# Local-mode Ollama vision critique
# ---------------------------------------------------------------------------
_CRITIQUE_PROMPT_BASE = """\
You are a senior UI and data-visualization reviewer performing a Ralph Eyeball Loop pass.
Study this rendered image carefully and write a structured critique.
Be specific, honest, and actionable — describe what you actually *see*, not what you expect.
Name concrete problems and propose concrete fixes.

Format your response using exactly these bold labels (one paragraph per label):

**Layout** — overall composition, alignment, and use of white-space.

**Contrast** — legibility of text and marks against the background; any elements that are hard to read.

**Hierarchy** — does the eye land on the most important element first? Is visual weight correctly placed?

**Spacing** — padding, margins, and gaps between elements. Too tight, too loose, or inconsistent?

**Accessibility** — color-vision deficiency (CVD) safety, contrast ratios, missing alt-text or ARIA concerns.

**Colors** — purposeful vs decorative; on-brand; any hue that clashes, misleads, or is CVD-unsafe.

**OCR / text readability** — can every label, tick value, axis title, and caption be read at this rendered size?

**Overall verdict** — one or two sentences: what are the most important changes needed before shipping?
"""

_CRITIQUE_PROMPT_HTML_EXTRA = """
**First-fold content** — is the primary message, headline, or call-to-action (CTA) visible without scrolling at this viewport size?

**Responsiveness** — does the layout look intentional at this viewport, or are there overflow, clipping, or overflow-hidden artefacts?
"""


def _build_critique_prompt(kind: str) -> str:
    """Build the Ollama vision critique prompt for the given surface kind.

    Parameters
    ----------
    kind : str
        Surface kind (``"html"``, ``"vega"``, etc.).

    Returns
    -------
    str
        The complete prompt string to send to the vision model.
    """
    prompt = _CRITIQUE_PROMPT_BASE
    if kind == _KIND_HTML:
        prompt += _CRITIQUE_PROMPT_HTML_EXTRA
    return prompt.strip()


def _ollama_critique(png_path: Path, kind: str) -> str:
    """Call ``qwen3-vl:8b`` via the Ollama REST API to critique a PNG.

    Parameters
    ----------
    png_path : Path
        Rendered PNG to critique.
    kind : str
        Surface kind (used to extend the prompt for web pages).

    Returns
    -------
    str
        The model's critique text.

    Raises
    ------
    SystemExit
        When Ollama is unreachable or the model is not pulled.
    """
    image_b64 = base64.b64encode(png_path.read_bytes()).decode()
    prompt = _build_critique_prompt(kind)
    payload = json.dumps({
        "model": _VISION_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        _OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    print(f"ralph_eyeball_loop: calling {_VISION_MODEL} for visual critique "
          "(first call loads the model, ~30 s cold) …", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip()
    except TimeoutError:
        raise SystemExit(
            f"ralph_eyeball_loop: {_VISION_MODEL} did not respond within "
            f"{_OLLAMA_TIMEOUT} s. A large full-page screenshot on a cold model "
            "can be slow; warm it first with a tiny request, then re-run:\n"
            f"  ollama run {_VISION_MODEL} 'ok'"
        )
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"ralph_eyeball_loop: Ollama is not reachable at {_OLLAMA_URL}.\n"
            "  Start it with:  ollama serve\n"
            f"  Pull the model: ollama pull {_VISION_MODEL}\n"
            f"  Error: {exc}"
        )


# ---------------------------------------------------------------------------
# Assessment file
# ---------------------------------------------------------------------------
_HEADER_TMPL = """\
# Ralph Eyeball Loop — {rel_src}

| Field | Value |
|---|---|
| **Source** | `{rel_src}` |
| **Kind** | {kind} |
| **Hash** | `{h}` |
| **Started** | {ts} |

The loop: **render → look → fill in the critique → edit the source →
re-run → repeat** until the Verdict box is checked.

*The thing you edit is always the source, never the PNG.*

---

"""

# Template used in agent mode — the agent fills in the blank fields.
_ITERATION_AGENT_TMPL = """\
## Iteration {n} — {ts} [agent mode]

**PNG:** `{rel_png}`

### Critique

*Read the PNG with the `Read` tool, then fill in each section.*

**Layout** — overall composition, alignment, white-space:

**Contrast** — legibility of text and marks against the background:

**Hierarchy** — does the eye land on the most important element first?

**Spacing** — padding, margins, gaps between elements:

**Accessibility** — CVD safety, contrast ratios, ARIA/alt-text:

**Colors** — purposeful vs decorative; on-brand; CVD-safe?

**OCR / text readability** — can every label, tick, and caption be read?

**First-fold** *(web pages only)* — key message visible without scrolling?

**Overall verdict:**

### Planned changes

-

### Verdict

- [ ] Satisfied — stop the loop
- [ ] Not yet — edit the source and re-run

---

"""

# Template used in local mode — the vision model fills in the critique block.
_ITERATION_LOCAL_TMPL = """\
## Iteration {n} — {ts} [local mode — {vision_model}]

**PNG:** `{rel_png}`

### Critique (auto-generated — review and edit before acting)

{critique}

### Planned changes

-

### Verdict

- [ ] Satisfied — stop the loop
- [ ] Not yet — edit the source and re-run

---

"""


def _write_assessment(
    assess_path: Path,
    src: Path,
    png_path: Path,
    kind: str,
    h: str,
    auto_critique: Optional[str] = None,
) -> int:
    """Create or extend the assessment Markdown file.

    First call: writes the file header and iteration 1.
    Subsequent calls: appends the next numbered iteration section.

    Parameters
    ----------
    assess_path : Path
        ``.private/ralph-loop/assessment-<hash>.md``.
    src : Path
        Source file being looped on.
    png_path : Path
        The PNG just rendered.
    kind : str
        Surface kind.
    h : str
        8-char source hash.
    auto_critique : str, optional
        Auto-generated critique from Ollama (local mode).  When ``None``,
        agent-mode template blanks are written instead.

    Returns
    -------
    int
        The iteration number just written.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    rel_src = _rel(src)
    rel_png = _rel(png_path)

    if not assess_path.exists():
        header = _HEADER_TMPL.format(rel_src=rel_src, kind=kind, h=h, ts=ts)
        n = 1
        existing = ""
    else:
        existing = assess_path.read_text(encoding="utf-8")
        n = existing.count("\n## Iteration ") + 1
        header = ""

    if auto_critique is not None:
        body = _ITERATION_LOCAL_TMPL.format(
            n=n, ts=ts, rel_png=rel_png,
            vision_model=_VISION_MODEL,
            critique=auto_critique,
        )
    else:
        body = _ITERATION_AGENT_TMPL.format(n=n, ts=ts, rel_png=rel_png)

    assess_path.write_text(header + existing + body, encoding="utf-8")
    return n


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ralph_eyeball_loop",
        description=(
            "Ralph Eyeball Loop: render a visual-from-code artifact (web page, "
            "Vega spec, TikZ figure, Mermaid diagram, SVG) to PNG and write a "
            "gitignored assessment file. "
            "Two modes: agent (Claude Code reads the PNG) or --local (Ollama vision)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Assessment files: .private/ralph-loop/assessment-<hash>.md\n"
            "Rendered PNGs:    .private/ralph-loop/<stem>-<hash>.png\n"
            "(both gitignored — never committed)\n\n"
            "Each re-run appends a new iteration section.\n\n"
            "See sprezzature-figures/references/ralph-eyeball-loop.md for the full protocol."
        ),
    )
    p.add_argument(
        "source",
        nargs="?",
        help=(
            "Visual source file: "
            ".html/.htm (web page), "
            ".vl.json/.vg.json/.json (Vega), "
            ".tex/.tikz (TikZ), "
            ".mmd/.mermaid (Mermaid), "
            ".svg (SVG). "
            "Omit when using --install-tools or --check-tools."
        ),
    )
    p.add_argument(
        "--local",
        action="store_true",
        help=(
            f"Local mode: call {_VISION_MODEL} via Ollama to auto-generate "
            "the critique and pre-fill the assessment file. "
            "Requires: ollama serve && ollama pull " + _VISION_MODEL
        ),
    )
    p.add_argument(
        "--width", type=int, default=1440,
        help="Viewport width for HTML renders in CSS pixels (default: 1440). "
             "Values below ~500 are clamped up (Chrome's headless minimum); "
             "a true 375 px phone view needs a browser's device-mode.",
    )
    p.add_argument(
        "--height", type=int, default=900,
        help="Viewport height for HTML renders in CSS pixels (default: 900).",
    )
    p.add_argument(
        "--bg", default="white",
        help=(
            "Background for diagram renders: "
            "white | transparent | dark | #RRGGBB (default: white). "
            "Ignored for HTML — the page sets its own background."
        ),
    )
    p.add_argument(
        "--dark", action="store_true",
        help="Use the dark-mode house canvas for diagram renders.",
    )
    p.add_argument(
        "--out",
        help="Override the PNG output path.",
    )
    p.add_argument(
        "--install-tools",
        action="store_true",
        help=(
            "Auto-install pip and npm rendering tools; print manual steps "
            "for Chrome, system libs, and the Ollama vision model."
        ),
    )
    p.add_argument(
        "--check-tools",
        action="store_true",
        help="Print a table showing which rendering tools are installed.",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point.

    Parameters
    ----------
    argv : list[str], optional
        Argument list (uses ``sys.argv`` when *None*).

    Returns
    -------
    int
        Exit code: 0 on success, 2 on usage / IO error.
    """
    args = _build_parser().parse_args(argv)

    # ---- Tool management sub-commands ----
    if args.install_tools:
        install_tools()
        return 0
    if args.check_tools:
        check_tools(verbose=True)
        return 0

    if not args.source:
        _build_parser().print_help()
        return 2

    src = Path(args.source)
    if not src.exists():
        print(f"ralph_eyeball_loop: {src} — file not found", file=sys.stderr)
        return 2

    kind = _detect_kind(src)
    h = _source_hash(src)

    _PRIVATE_LOOP_DIR.mkdir(parents=True, exist_ok=True)

    # Derive PNG stem — strip compound suffixes (.vl.json → "fig").
    stem = src.name
    for suffix in sorted(_SUFFIX_KIND, key=len, reverse=True):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    png_path = Path(args.out) if args.out else _PRIVATE_LOOP_DIR / f"{stem}-{h}.png"
    assess_path = _PRIVATE_LOOP_DIR / f"assessment-{h}.md"

    mode = "local" if args.local else "agent"
    print(f"ralph_eyeball_loop: rendering {src.name!r}  [{kind}]  mode={mode} …", file=sys.stderr)

    if kind == _KIND_HTML:
        _render_html(src, png_path, width=args.width, height=args.height)
    else:
        _render_diagram(src, png_path, bg=args.bg, dark=args.dark)

    # ---- Critique ----
    auto_critique: Optional[str] = None
    if args.local:
        auto_critique = _ollama_critique(png_path, kind)

    iteration = _write_assessment(assess_path, src, png_path, kind, h, auto_critique)

    # ---- Summary ----
    rel_png = _rel(png_path)
    rel_assess = _rel(assess_path)
    print(f"\nralph_eyeball_loop: iteration {iteration}", file=sys.stderr)
    print(f"  PNG    → {rel_png}", file=sys.stderr)
    print(f"  assess → {rel_assess}", file=sys.stderr)
    print(file=sys.stderr)

    if args.local:
        print("Next steps:", file=sys.stderr)
        print(f"  1. Review the auto-critique in {Path(rel_assess).name}", file=sys.stderr)
        print(f"  2. Edit {src.name}  (never the PNG)", file=sys.stderr)
        print("  3. Re-run to loop", file=sys.stderr)
    else:
        print("Next steps (agent mode):", file=sys.stderr)
        print(f"  1. Read {png_path.name}  (use the Read tool to view it)", file=sys.stderr)
        print(f"  2. Fill in {Path(rel_assess).name} with your honest critique", file=sys.stderr)
        print(f"  3. Edit {src.name}  (never the PNG)", file=sys.stderr)
        print("  4. Re-run to loop", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
