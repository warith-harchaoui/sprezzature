"""
sprezzature_cli_gui.adapters
=====================

One adapter per supported source CLI framework. Each adapter walks its
framework's native parser object into the canonical parser-tree dict
(``prog`` / ``description`` / ``actions`` / ``sub_commands``) that the
renderer consumes, so the renderer never branches on framework:

- :mod:`sprezzature_cli_gui.adapters.argparse` — stdlib
  :class:`argparse.ArgumentParser`.
- :mod:`sprezzature_cli_gui.adapters.click` — optional :class:`click.Command`
  (also serves Typer via its underlying Click group).
- :mod:`sprezzature_cli_gui.adapters.help_text` — the framework-agnostic
  ``--from-help`` fallback that parses a CLI's ``--help`` output.
"""

from __future__ import annotations
