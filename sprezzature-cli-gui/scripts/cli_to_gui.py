#!/usr/bin/env python3
"""
cli_to_gui
==========

Introspect an :mod:`argparse` parser belonging to a Python CLI and
emit a single-page vanilla-JS + Tailwind GUI that maps every
sub-command and flag to a form field. Output follows the
``sprezzature-ui`` stack rules so the emitted file drops onto an internal
box, into Tauri's web view, or into a static-asset bucket without
modification.

This is the make-side primary of the ``sprezzature-cli-gui`` skill — the
counterpart to ``audit_laws_of_ux.py`` / ``palette_to_tailwind.py``
elsewhere in the sprezzature-* ecosystem. It is **not** a runtime: the
emitted page builds the command string locally and shows it for the
user to copy / paste / submit through the host adapter of their
choice (FastAPI SSE, Tauri ``invoke()``, Express, plain shell).

Supported source frameworks
---------------------------

The emitter is **framework-agnostic** at the renderer boundary: a
small adapter protocol normalises every supported framework into a
canonical parser-tree dict (``prog`` / ``description`` / ``actions``
/ ``sub_commands``). Two adapters ship today:

- **argparse** (stdlib, always available). Walks
  :class:`argparse.ArgumentParser` via :func:`walk_parser`. Used
  when the factory returns an argparse parser.
- **Click** (optional dep). Walks :class:`click.Command` via
  :func:`walk_click`. Typer apps work via their underlying Click
  group (``app.cli``). Click is imported lazily so argparse-only
  users keep their stdlib-only run.

The renderer never branches on framework — :func:`walk` dispatches
by type and the HTML side sees a single shape. Adding a third
framework (Cobra via ``--from-help``, clap, …) is a new adapter +
the same dict; the renderer never moves.

Why introspect, not parse ``--help``?
-------------------------------------

``--help`` text is a presentation format — fragile under
formatter / line-wrap / locale variation. An in-memory parser
carries the **structured** truth (choice lists, ``type=`` callables,
``required`` flags, defaults). When the framework is reachable,
prefer introspection. For non-Python binaries (clap / cobra /
commander) or when the parser cannot be imported, the planned
``--from-help`` adapter parses the help text as a low-fidelity
fallback (everything maps to ``"text"`` unless ``[default: …]`` or
similar is visible).

Inputs
------

The caller names a parser factory as ``SPEC``:

- ``path/to/file.py:make_parser`` — load the file as an anonymous
  module, call ``make_parser()`` to obtain the parser.
- ``my_pkg.my_cli:build_parser`` — import the dotted module path,
  call the named factory.

The factory must be a zero-argument callable returning EITHER an
:class:`argparse.ArgumentParser` OR a :class:`click.Command`
(Click Group or Command). Adapter selection is automatic.

Outputs
-------

A single HTML file (stdout by default; ``--out PATH`` to write to
disk) containing:

- Tailwind Play CDN bootstrap + the three-Roboto webfont fallback.
- A sticky header with the parser's prog name + description.
- One collapsed ``<details>`` per sub-command (or a single form
  when no sub-command exists), with form fields mapped per action.
- A "Build command" button that constructs the CLI line and
  displays it in a ``<pre>`` block ready for copy / Tauri-invoke.
- Dark-mode peers on every styled element + focus rings + reduced
  motion guards (per the sprezzature-ui hard rules).

Stack rules respected
---------------------

- Vanilla JS only (ES module, no React / Vue / Svelte).
- Tailwind utility classes only; no raw hex in markup.
- Semantic HTML (``<form>``, ``<label for>``, ``<button>``,
  ``<details>``).
- Visible focus ring everywhere; ``prefers-reduced-motion`` honoured.
- No third-party CDN fonts — fallback to ``system-ui`` /
  ``ui-monospace`` when Roboto is not installed.

Usage
-----
::

    # Wrap a Python CLI exposing make_parser() in a single-file GUI
    python scripts/cli_to_gui.py path/to/cli.py:make_parser \\
        --out dist/index.html --title "My Tool"

    # Pipe to stdout for a quick preview
    python scripts/cli_to_gui.py mypkg.cli:build_parser

Refactor note
-------------

The implementation now lives in the :mod:`sprezzature_cli_gui` package
alongside this file; this module is a thin facade that re-exports the
full public API so every consumer — ``python scripts/cli_to_gui.py``
and ``from cli_to_gui import …`` alike — keeps working unchanged.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import os
import sys

# Ensure this file's own directory (``sprezzature-cli-gui/scripts``) is on
# ``sys.path`` so the ``sprezzature_cli_gui`` package and the shared
# ``_argparse`` helper resolve when this facade is imported directly
# (tests add ``scripts`` to ``sys.path`` already; running the script
# directly adds it via ``sys.path[0]`` — this covers the remaining
# import-as-module case without changing behaviour).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from sprezzature_cli_gui.adapters.argparse import (  # noqa: E402
    _action_kind,
    serialize_action,
    walk_parser,
)
from sprezzature_cli_gui.adapters.click import (  # noqa: E402
    _click_param_choices,
    _click_param_kind,
    _serialize_click_param,
    walk_click,
)
from sprezzature_cli_gui.adapters.help_text import (  # noqa: E402
    HELP_TIMEOUT_S,
    RE_ARGPARSE_SUBS,
    RE_CHOICE_HINT,
    RE_COMMAND_LINE,
    RE_COMMANDS_HEADER,
    RE_DEFAULT_HINT,
    RE_OPTION_LINE,
    RE_OPTIONS_HEADER,
    RE_POSITIONAL_HEADER,
    RE_REQUIRED_HINT,
    RE_USAGE_HEADER,
    _extract_prog,
    _parse_commands_section,
    _parse_option_line,
    _parse_options_section,
    _run_help,
    _section,
    walk_from_help,
)
from sprezzature_cli_gui.cli import main  # noqa: E402
from sprezzature_cli_gui.loader import load_parser_from_spec  # noqa: E402
from sprezzature_cli_gui.renderer import (  # noqa: E402
    _children_html,
    _e,
    _field_html,
    _form_html,
    render_html,
)
from sprezzature_cli_gui.schema import (  # noqa: E402
    NO_DEFAULT,
    _safe_default,
    walk,
)

# Re-export the full public API so ``from cli_to_gui import X`` keeps
# resolving for every consumer (tests, docstrings, the entry point).
__all__ = [
    "HELP_TIMEOUT_S",
    "NO_DEFAULT",
    "RE_ARGPARSE_SUBS",
    "RE_CHOICE_HINT",
    "RE_COMMAND_LINE",
    "RE_COMMANDS_HEADER",
    "RE_DEFAULT_HINT",
    "RE_OPTION_LINE",
    "RE_OPTIONS_HEADER",
    "RE_POSITIONAL_HEADER",
    "RE_REQUIRED_HINT",
    "RE_USAGE_HEADER",
    "_action_kind",
    "_children_html",
    "_click_param_choices",
    "_click_param_kind",
    "_e",
    "_extract_prog",
    "_field_html",
    "_form_html",
    "_parse_commands_section",
    "_parse_option_line",
    "_parse_options_section",
    "_run_help",
    "_safe_default",
    "_section",
    "_serialize_click_param",
    "load_parser_from_spec",
    "main",
    "render_html",
    "serialize_action",
    "walk",
    "walk_click",
    "walk_from_help",
    "walk_parser",
]


if __name__ == "__main__":
    raise SystemExit(main())
