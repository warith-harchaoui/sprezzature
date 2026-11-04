# Command-line interface (CLI) → web graphical user interface (GUI) — `sprezzature-cli-gui`

Wrap an existing command-line tool in a single-page vanilla-JavaScript (JS) + Tailwind GUI. It walks the parser of a Python CLI (argparse, Click or Typer) and, with `--from-help`, reads the printed `--help` of any other CLI (clap, cobra, commander). Sub-commands become collapsible forms; flags become checkboxes, dropdowns, number and text fields. The page builds the exact command line and never runs it. `sprezzature-cli-gui-audit` checks that a page generated earlier still covers the CLI.

One install, `pip install sprezzature-cli-gui`, brings the five surfaces: the library (`walk`, `render_html`, `audit`), the CLI (`sprezzature-cli-gui`, `sprezzature-cli-gui-audit`), the FastAPI app (with Docker and compose), the MCP (Model Context Protocol) server `sprezzature-cli-gui-mcp` with the tools `health`, `get_example_schema`, `render_gui` and `audit_gui`, and the skill.

This is the human landing page. It points to the places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-cli-gui/SKILL.md`](../sprezzature-cli-gui/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, flags, surfaces).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-cli-gui`; the package's own
  [README](https://github.com/warith-harchaoui/sprezzature-cli-gui#readme) documents every command, route and tool.
- **Go deeper:** [`sprezzature-cli-gui/references/`](../sprezzature-cli-gui/references/): the trigger catalogue and the hardening checklist for a host that runs the built command.
