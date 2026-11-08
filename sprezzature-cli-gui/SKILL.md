---
name: sprezzature-cli-gui
description: >-
  Wrap an existing command-line tool in a single-page vanilla-JS +
  Tailwind GUI. Walks the parser itself for Python CLIs — argparse, Click,
  Typer — and parses `--help` in a subprocess for anything else, covering
  a Go or Rust CLI (cobra, clap) at lower fidelity. Sub-commands become
  collapsible forms and flags become checkboxes, dropdowns, number and text
  fields, in one self-contained HTML file that builds the exact command
  line without running it. An audit says whether a page generated earlier
  still covers the CLI. Use it when you are
  holding a command-line tool somebody who will not type it needs to run.
  Trigger phrases: "wrap this CLI in a GUI", "build a UI for my CLI",
  "argparse to GUI", "click to web UI", "GUI for my Python script", "web
  form for my script", "Typer / clap / cobra to GUI", "GUI for my Go or
  Rust CLI", "streaming log panel for a CLI". Not this one when: the
  screen has no CLI behind it (sprezzature-ui). The exhaustive trigger
  catalogue is in `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10+, one install:
  `pip install sprezzature-cli-gui` (Click, Typer, FastAPI and the MCP
  server included). Output is one HTML page that runs in any modern browser;
  it loads Tailwind's Play build from cdn.tailwindcss.com for styling, and
  the form works unstyled offline. The worked demo in assets/ needs only the
  Python standard library.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.2
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
2. Carries the sprezzature-ui semantic tokens (color, dark-mode peers, focus rings) in the page it writes. They are fixed in `renderer.py`; the levers the command gives you are `--title` and `--prog`, and after that the page is yours to edit.
3. Builds the command line and stops there. Running it is the host's job (HTTP + SSE, Tauri `invoke()`, or a shell prompt where the line is pasted); the worked demo shows one such wiring.
4. Ships a worked example you can copy in `assets/examples/cli-gui-demo/`.

Honest limitation: this skill **scaffolds** the GUI. You still need to wire execution to your CLI through the host of your choice. We provide a Python SSE proxy reference implementation in the demo; for production you'll harden it (auth, rate-limit, sandbox).

## Two modes: make and audit

This skill is **make-heavy** in the sprezzature-* duality: one executable
make-side primary, plus a worked scaffold, plus referenced audit
gates on the emitted HTML.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — CLI → HTML (three adapters) | `sprezzature-cli-gui` | Introspects a Python CLI and emits a single-page vanilla-JS + Tailwind GUI: one `<details>` per sub-command, form fields mapped per action type (bool → checkbox, choice → dropdown, int / float → number input, file and str → text input; a counter such as `-v` is a number input that repeats the flag; an on/off pair such as `--color/--no-color` starts at its default and writes the other spelling when changed, and a `store_false` flag is passed only when it is ticked), required marker, default values pre-filled, and a "Build command" button per form that constructs the CLI line locally from that form's fields. **Three adapters**: argparse (stdlib, default), Click (`module:factory` returning a `click.Command` — or a `typer.Typer`, converted with typer's own `get_command` and walked as Click, since that is what it becomes), and `--from-help` (subprocess + regex on the help text, works on non-Python CLIs: clap / cobra / commander). |
| **Make** — worked scaffold | `assets/examples/cli-gui-demo/` | End-to-end runnable demo (HTML + ES module + Python SSE proxy) showing the host-wiring step the emitter leaves to the user. |
| **Audit** — gate the emitted HTML _(borrowed, not shipped here)_ | Pair with `sprezzature-accessibility-lint` and `sprezzature-ux-laws-audit` on the emitted output. | The emitter's HTML inherits sprezzature-ui stack rules; both auditors apply unmodified. Measured on 2026-11-08 on four generated pages (argparse, Click, Typer, `--from-help`) with `sprezzature-accessibility` 1.4.3 and `sprezzature-ux-laws` 1.4.2: 0 findings from each. No test in the package asserts either gate. |
| **Audit** — does the page still cover the CLI | `sprezzature-cli-gui-audit <spec> <page.html>` | This brick's own promise, checked by five rules: `flag-not-in-page` (an option with no field), `field-has-no-flag` (a field building an option the parser rejects), `choice-dropped`, `prog-missing` and `prog-mismatch` (the command line is not seeded with the installed name). A page that lost a flag renders and behaves perfectly — the option is simply unreachable — so the disagreement has to be looked for. `--format text|json`, `--prog`. Exit 1 on any finding, so it gates a build. |

## Five surfaces

| Surface | Entry point | Notes |
|---|---|---|
| Library | `from sprezzature_cli_gui import walk, render_html, audit, Finding` | `walk(obj, prog=None)` reads an argparse parser, a Click command or a Typer app in the caller's process. |
| CLI | `sprezzature-cli-gui`, `sprezzature-cli-gui-audit` | Click commands; shell completion through `_SPREZZATURE_CLI_GUI_COMPLETE`. |
| HTTP | `uvicorn sprezzature_cli_gui.api:app`, or `docker compose up` in the package repository (the image runs `sprezzature-cli-gui-mcp`, so one container answers the routes and `/mcp` on port 8000) | `GET /health`, `GET /v1/example`, `POST /v1/render` (tree in, HTML out), `POST /v1/audit` (`schema` + `page` in, findings out). |
| MCP | `sprezzature-cli-gui-mcp [--host H] [--port P]` | Endpoint `/mcp`. Tools = `operation_id`: `health`, `get_example_schema`, `render_gui`, `audit_gui`. |
| Skill | this file | Routing; the catalogue is in `references/triggers.md`. |

The HTTP and MCP surfaces take a schema tree, never a `module:factory` spec: importing a module named by a remote caller would be remote code execution. To render over MCP, walk the parser locally (`sprezzature-cli-gui SPEC --json`) or call `get_example_schema` and copy its shape.

## Quick recipe — the one command

Most CLI → GUI conversions are a single invocation of the make-side
script. Don't re-derive the workflow if the user just wants the HTML.

```bash
# Spec is "<file>.py:factory" or "pkg.mod:factory".
# Factory is a zero-arg callable returning argparse.ArgumentParser,
# click.Command or typer.Typer (auto-detected); the spec may also name
# such an object directly, which is then never called. `sprezzature-cli-gui`
# is the console script the package installs (pip install sprezzature-cli-gui).
# Options: --out PATH, --title TEXT, --prog TEXT (the installed command name,
# when Click or Typer reports a function name), --json (the tree, no HTML).
sprezzature-cli-gui <spec> --out path/to/index.html

# Examples:
sprezzature-cli-gui mycli/cli.py:make_parser --out dist/gui.html
sprezzature-cli-gui mypkg.cli:cli            --out dist/gui.html
sprezzature-cli-gui mypkg.cli:app --prog mytool --out dist/gui.html   # Typer app

# For a non-Python CLI (clap / cobra / commander), or a Python CLI
# whose factory cannot be imported: --from-help runs the command
# with --help appended and parses the output. Nothing falls back to
# it on its own; pass the flag.
sprezzature-cli-gui --from-help "mybin"        --out dist/gui.html
sprezzature-cli-gui --from-help "cargo run --" --out dist/gui.html
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

Check the output with both audit gates:

```bash
sprezzature-ux-laws-audit path/to/index.html
sprezzature-accessibility-lint                           path/to/index.html
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

**This skill works with any parser.** The package walks an argparse,
Click or Typer parser object directly; for everything else (docopt, fire,
clap, commander, cobra) `--from-help` reads the tool's printed `--help`
instead, at lower fidelity. The bespoke flow at step 1 reads the help
output and the README either way.

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
   fine when the team wants zero dependencies. The package walks the
   `argparse.ArgumentParser` object itself, so argparse works for
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

`assets/examples/cli-gui-demo/` is a runnable, ~1,000-line demo of the whole workflow:

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
| W3C alt text for the wrapping page's images (local Ollama vision) | `sprezzature-accessibility` |
| Captions for any embedded `<video>` / `<audio>` (local whisper.cpp) | `sprezzature-audio` |
| Favicon / meta / docs site for the wrapping page | `sprezzature-publish` |
| Screenshot the emitted GUI, look at it, and refine the markup (the Ralph Eyeball Loop) | `sprezzature-figures` (`sprezzature-figures/references/ralph-eyeball-loop.md`) |
