"""
sprezzature_cli_gui.cli
================

The command-line driver.

Parses the ``SPEC`` / ``--from-help`` / ``--out`` / ``--title`` /
``--json`` arguments, selects the introspection path (native adapter
via :func:`load_parser_from_spec` + :func:`walk`, or the ``--from-help``
subprocess fallback), and writes the emitted HTML (or JSON) to a file
or stdout.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _argparse import make_parser

from sprezzature_cli_gui.adapters.help_text import walk_from_help
from sprezzature_cli_gui.loader import load_parser_from_spec
from sprezzature_cli_gui.renderer import render_html
from sprezzature_cli_gui.schema import walk


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns
    -------
    int
        ``0`` on success, ``1`` on a load failure, ``2`` on an
        argparse usage error (delegated to the parser).
    """
    parser: argparse.ArgumentParser = make_parser(
        prog="sprezzature-cli-gui-to-html",
        description=(
            "Introspect a Python CLI (argparse OR Click — autodetected) "
            "and emit a single-page vanilla-JS + Tailwind GUI mapping "
            "every sub-command and flag to a form field. Make-side "
            "primary of the sprezzature-cli-gui skill — counterpart to the "
            "static scaffold in assets/examples/cli-gui-demo/."
        ),
    )
    parser.add_argument(
        "spec",
        help=(
            "Parser factory spec — 'path/to/cli.py:factory' OR "
            "'pkg.mod:factory'. The factory is a zero-argument "
            "callable returning EITHER an argparse.ArgumentParser "
            "OR a click.Command (Group or Command). Adapter is "
            "auto-selected from the returned type. With "
            "``--from-help``, this argument is a shell command line "
            "instead; its '--help' output is parsed. Works on any "
            "CLI — Python or not, framework-agnostic — at lower "
            "fidelity than native introspection."
        ),
    )
    parser.add_argument(
        "--from-help",
        action="store_true",
        dest="from_help",
        help=(
            "Treat 'spec' as a shell command line; run "
            "'<command> --help' via subprocess and parse the output "
            "into the canonical parser tree. Works on non-Python "
            "CLIs (clap / cobra / commander) and on Python CLIs "
            "whose factory cannot be imported. Lower fidelity — "
            "everything maps to 'text' unless [default: …], "
            "[choices] or a recognised METAVAR is visible."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Write the emitted HTML to this file instead of stdout. "
            "The parent directory must already exist."
        ),
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Page <title>. Defaults to the parser's prog name.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit the walked parser as JSON instead of HTML. Useful "
            "when debugging the introspection step or when piping "
            "into a different renderer (e.g. a Tauri app)."
        ),
    )
    args: argparse.Namespace = parser.parse_args(argv)

    tree: dict[str, Any]
    if args.from_help:
        # ``--from-help``: subprocess-based path. ``spec`` is a shell
        # command line, not a module:factory string.
        try:
            tree = walk_from_help(args.spec)
        except (FileNotFoundError, OSError) as exc:
            print(f"cli_to_gui: --from-help failed: {exc}", file=sys.stderr)
            return 1
    else:
        try:
            cli_obj: Any = load_parser_from_spec(args.spec)
        except (ValueError, FileNotFoundError, ImportError, AttributeError) as exc:
            print(f"cli_to_gui: {exc}", file=sys.stderr)
            return 1
        try:
            tree = walk(cli_obj)
        except TypeError as exc:
            print(f"cli_to_gui: {exc}", file=sys.stderr)
            return 1
    output: str = (
        json.dumps(tree, indent=2, ensure_ascii=False) + "\n"
        if args.json
        else render_html(tree, title=args.title or tree["prog"])
    )

    if args.out is None:
        sys.stdout.write(output)
        return 0
    try:
        args.out.write_text(output, encoding="utf-8")
    except OSError as exc:
        print(f"cli_to_gui: write failed: {exc}", file=sys.stderr)
        return 1
    print(f"cli_to_gui: wrote {args.out}", file=sys.stderr)
    return 0
