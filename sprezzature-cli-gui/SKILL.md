---
name: sprezzature-cli-gui
description: >-
  Wrap an existing command-line tool in a single-page vanilla-JavaScript +
  Tailwind GUI. Trigger phrases: "wrap this CLI in a GUI", "build a UI for my
  CLI", "argparse to GUI", "click to web UI", "GUI for my Python script",
  "wrap my command-line tool", "web form for my script", "Typer / clap / cobra
  to GUI", "GUI for my Go or Rust CLI", "frontend for a CLI", "streaming log
  panel for a CLI". Reads the CLI's argument parser (argparse, click, clap,
  commander, cobra), maps sub-commands and flags to forms / segmented controls
  / file inputs / streaming log panels, and emits one index.html + app.js +
  Tailwind config. For solo developers and small teams (Python / Node / Go /
  Rust CLI authors, ML researchers, data scientists, DevOps / SRE) who need a
  usable web UI without picking up React or learning Gradio's / Streamlit's
  look. Output follows the sprezzature-ui stack rules; install sprezzature-ui alongside
  for full design tokens.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Output is one-page HTML + ES
  modules + Tailwind that runs in any modern browser. Reads CLIs from any
  argparse / Click / Typer / clap / commander / cobra source. Runnable demo
  needs Python 3.10+ stdlib only; no third-party deps. Network access not
  required.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
---

> The deterministic tools below now ship as the standalone package [`sprezzature-cli-gui`](https://github.com/warith-harchaoui/sprezzature-cli-gui) (`pip install`), invoked as `sprezzature-cli-gui …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-cli-gui — CLI → web GUI

## Audience and positioning

Solo developers and small teams who have a working CLI (Python / Node / Go / Rust) and need a usable web UI for it. Common cases:

- ML researcher with a `train.py` / `eval.py` that teammates run with the wrong flags.
- Data scientist with a Click pipeline that stakeholders should be able to launch.
- DevOps engineer with internal `argparse` tools that should not require shell access.
- Indie hacker shipping a CLI tool whose first user-facing surface is a web page.

### Why this skill, not Gradio / Streamlit / Tauri / Taipy

The auto-form generators handle the common case well and get awkward at the last 20%. They produce a UI that looks like the tool's UI, not yours. The trade-offs:

- **Gradio / Streamlit / Taipy / Shiny.** Server-side runtimes that auto-generate widgets from your function signature. Fast for ML demos. The cost: every Gradio app looks like a Gradio app; every Streamlit app looks like a Streamlit app. The CSS surface to override is large and brittle across versions. You also ship the runtime: a minimum of ~50 MB of Python deps and a long-lived server process.
- **Tauri / Wails / Electron.** Native desktop wrappers. Real desktop integration, real binary you can hand to a non-technical user. They wrap a web view; `sprezzature-cli-gui` is what you'd put **inside** the web view. Pick Tauri when the deliverable must be a desktop app; pick `sprezzature-cli-gui` when the deliverable is a single HTML page that runs anywhere.
- **Gooey / dearpygui.** Native widgets, no web. Pick these when you specifically want OS-native chrome.

What `sprezzature-cli-gui` does instead:

1. Emits plain HTML + Tailwind + vanilla JS, the same files you'd write by hand. No runtime, no lock-in. You can edit it without learning a framework.
2. Uses your own design tokens (semantic color, typography, dark mode, focus rings) via the shared sprezzature-ui stack rules. The UI does not look like every other auto-generated tool UI.
3. Speaks to the CLI through a small adapter (HTTP + SSE, Tauri `invoke()`, or stub); you pick the host. The GUI is decoupled from the runtime.
4. Ships a worked example you can copy in `assets/examples/cli-gui-demo/`.

Honest limitation: this skill **scaffolds** the GUI. You still need to wire execution to your CLI through the host of your choice. We provide a Python SSE proxy reference implementation in the demo; for production you'll harden it (auth, rate-limit, sandbox).

## Two modes — make and audit

This skill is **make-heavy** in the sprezzature-* duality: one executable
make-side primary, plus a worked scaffold, plus referenced audit
gates on the emitted HTML.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — CLI → HTML (three adapters) | `cli_to_gui.py` | Introspects a Python CLI and emits a single-page vanilla-JS + Tailwind GUI: one `<details>` per sub-command, form fields mapped per action type (str / int / float / choice / bool / file), required marker, default values pre-filled, a "Build command" button that constructs the CLI line locally. Output passes both `sprezzature-ux-laws` audit and `sprezzature-accessibility` lint with zero findings. **Three adapters**: argparse (stdlib, default), Click (`module:factory` returning a `click.Command`), and `--from-help` (subprocess + regex on the help text, works on non-Python CLIs: clap / cobra / commander). |
| **Make** — worked scaffold | `assets/examples/cli-gui-demo/` | End-to-end runnable demo (HTML + ES module + Python SSE proxy) showing the host-wiring step the emitter leaves to the user. |
| **Audit** — gate the emitted HTML | Pair with `sprezzature-accessibility/scripts/lint_a11y.py` and `sprezzature-ux-laws/scripts/audit_laws_of_ux.py` on the emitted output. | The emitter's HTML inherits sprezzature-ui stack rules; both auditors apply unmodified. The test suite asserts the output passes both gates. |

## Quick recipe — the one command

Most CLI → GUI conversions are a single invocation of the make-side
script. Don't re-derive the workflow if the user just wants the HTML.

```bash
# Spec is "<file>.py:factory" or "pkg.mod:factory".
# Factory is a zero-arg callable returning argparse.ArgumentParser
# OR click.Command (auto-detected).
python3 scripts/cli_to_gui.py <spec> --out path/to/index.html

# Examples:
python3 scripts/cli_to_gui.py mycli/cli.py:make_parser --out dist/gui.html
python3 scripts/cli_to_gui.py mypkg.cli:cli            --out dist/gui.html

# For a non-Python CLI (clap / cobra / commander), or a Python CLI
# whose factory cannot be imported: --from-help runs the binary
# with --help and parses the output.
python3 scripts/cli_to_gui.py --from-help "mybin"        --out dist/gui.html
python3 scripts/cli_to_gui.py --from-help "cargo run --" --out dist/gui.html
```

If the user's CLI factory takes arguments (rare), write a tiny
zero-arg wrapper:

```python
# adapter.py
from mypkg.cli import _make_format_parser
def make_parser():
    return _make_format_parser("docx")
```

Then point the spec at `adapter.py:make_parser`.

Verify the output passes both audit gates (zero findings):

```bash
python3 sprezzature-ux-laws/scripts/audit_laws_of_ux.py path/to/index.html
python3 sprezzature-accessibility/scripts/lint_a11y.py   path/to/index.html
```

The longer design workflow below is for the bespoke cases the
one-command recipe can't reach (new CLI design choices, custom
streaming-output layouts, host wiring decisions).

## CLI → GUI workflow (the flagship)

When the user points to an existing CLI project and asks for a GUI:

1. **Inventory the CLI.** Read the help output (`tool --help`, `tool sub --help`), the README, the source's argument parser (`argparse`, `click`, `clap`, `commander`, `cobra`, …). Build a map: sub-commands → flags → input types → output shape.
2. **Categorize each command** by surface:
   - One-shot action (single button + result panel).
   - Form-driven (multiple inputs → run).
   - Long-running (streaming output → progress + log panel).
   - List-producing (table view with filters).
3. **Pick a layout**:
   - 2–4 commands → tab bar at the bottom (mobile) or sidebar (desktop).
   - 5–8 → sidebar with grouped sections.
   - 9+ → command palette (`⌘K`) + categorized sidebar.
4. **Map flags to form controls**:
   - boolean flag → toggle.
   - enum flag → segmented control (≤ 4 options) or `<select>`.
   - path → `<input type="file">` + drag-drop zone.
   - string → text field.
   - number → stepper or slider.
   - repeated flag → tag list.
5. **Wire execution.** Choose ONE depending on the project:
   - **Local-only**, packaged as Tauri / Electron / web view: invoke via the host's `invoke()` / IPC.
   - **HTTP-served**: emit a tiny `fetch` wrapper assuming the CLI is wrapped by `python -m http.server`, `express`, `fastapi`, or the demo's stdlib SSE proxy.
   - **Browser-only mock**: stub execution with `console.log` and clearly mark TODOs.
6. **Stream output** to a monospace `<pre>` panel; convert ANSI escapes to HTML if needed.
7. **Emit a single `index.html` + `app.js` + Tailwind** that runs out of the box. Ship the three Roboto families (Roboto / Roboto Serif / Roboto Mono) in `./fonts/roboto*/`.
8. **Document** in the project's README how to launch the GUI alongside the CLI.

## Stack rules (inherited)

Output follows the sprezzature-ui stack rules. If sprezzature-ui is not installed in the same agent, apply these directly:

- **Vanilla JS** (ES modules), no framework.
- **Tailwind utility classes**, semantic tokens, dark-mode peer on every styled element.
- **Three-Roboto rule**: Roboto (sans / UI), Roboto Serif (editorial / longform), Roboto Mono (`<code>` / `<pre>` / log panels / terminal). Self-hosted, no Google Fonts CDN. The CLI → GUI flagship leans on **Roboto Mono** for the streaming log panel and **Roboto** everywhere else.
- Semantic HTML, visible focus rings, 44 × 44 hit area, `prefers-reduced-motion` honored.
- Both color schemes.

For full rules, see `sprezzature-ui/SKILL.md` and `sprezzature-ui/references/`.

## Choosing a CLI parser (for new tools)

**This skill works with any parser.** The inventory step reads
`tool --help` and the README — not your source. argparse, Click, Typer,
docopt, fire (Python), clap (Rust), commander (Node), cobra (Go): all
of them produce a `--help` the skill consumes. The flow at step 1 does
not care which one you picked.

> **If you have an existing CLI, do not migrate parsers just to use this
> skill.** The pitch is "you have a working CLI; we wrap it." A forced
> migration breaks that pitch. Migrate only if a *different* benefit
> justifies it.

When the user is starting a **new** CLI that they know will be wrapped
in a GUI later, the parser choice does shape two things: the quality
of `--help` (the primary source at step 1) and how easily the skill
can introspect the command tree at step 4. **Soft default**, in order:

1. **[Click](https://click.palletsprojects.com/)** — the safe default.
   Decorator-based, BSD-3, stable since 2014. Generates a clean
   `--help`, supports nested sub-commands cleanly, ships
   `click.testing.CliRunner` for tests, and exposes a stable
   `click.Command` object the skill can walk programmatically.
2. **[Typer](https://typer.tiangolo.com)** — fine when the team already
   commits to type hints. Sits on top of Click; same model with
   nicer-looking help via Rich. Slightly heavier (pulls Click + Rich).
3. **[argparse](https://docs.python.org/3/library/argparse.html)** —
   fine when the team wants zero dependencies. The skill reads
   `tool --help` text as the source of truth, so argparse works for
   every CLI → GUI flow without an upgrade.
4. **Avoid [Fire](https://github.com/google/python-fire)** for CLIs
   you plan to wrap: the reflection model makes the schema implicit
   in the source class shape, which makes both `--help` parsing and
   programmatic introspection brittle.
5. **Avoid [docopt](http://docopt.org/)** — effectively unmaintained.

For non-Python projects, the equivalents that work cleanly with this
skill are **clap** (Rust), **commander** (Node), and **cobra** (Go);
all generate the introspectable `--help` the inventory step expects.

## When NOT to use this skill

- The user wants a **desktop app binary**, not a web page. → Use Tauri (this skill can supply Tauri's web view content).
- The user wants **ML model auto-demos** with sliders and audio playback wired automatically. → Use Gradio.
- The user wants **a data app with charts as the primary surface** and is fine with the runtime's look. → Use Streamlit.
- The CLI is **purely interactive** (REPL, prompt-heavy): a TUI like Textual / Bubble Tea is the better fit.

## Worked example

`assets/examples/cli-gui-demo/` is a runnable, ~700-LOC demo of the whole workflow:

- A mock CLI `imgconvert` with three sub-commands.
- A Python stdlib HTTP + SSE proxy (`server.py`).
- A single-page GUI (`public/index.html` + `public/app.js`).
- Per-flag-shape → control-shape table.

Launch:

```bash
cd sprezzature-cli-gui/assets/examples/cli-gui-demo
python server.py
# open http://localhost:8787
```

## References

- `references/hardening.md` — Production-readiness checklist for the host (auth, rate-limit, subprocess sandbox, CORS, TLS posture). Keep the demo demo; this is what you apply when the surface stops being loopback-only.

## Companion skills

| You also need… | Install |
|---|---|
| Full UI design tokens (color, typography, components, dark mode) | `sprezzature-ui` |
| a11y lint on the emitted HTML | `sprezzature-accessibility` |
| WCAG contrast audit + CVD simulation on the emitted HTML | `sprezzature-colors` |
| W3C alt text for the wrapping page's images (local Ollama vision) | `sprezzature-vision` |
| Captions for any embedded `<video>` / `<audio>` (local whisper.cpp) | `sprezzature-audio` |
| Favicon / meta / docs site for the wrapping page | `sprezzature-publish` |
| Screenshot the emitted GUI, look at it, and refine the markup (the Ralph Eyeball Loop) | `sprezzature-figures` (`sprezzature-figures/references/ralph-eyeball-loop.md`) |
