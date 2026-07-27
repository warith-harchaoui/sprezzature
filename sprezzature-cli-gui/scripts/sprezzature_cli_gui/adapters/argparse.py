"""
sprezzature_cli_gui.adapters.argparse
==============================

The stdlib-argparse adapter.

Walks an :class:`argparse.ArgumentParser` into the canonical
parser-tree dict, filtering help / version actions (they exist only on
the CLI surface, not in a GUI). This is the always-available adapter —
argparse ships with Python — and the one :func:`walk` dispatches to
when the factory returns an argparse parser.

Note the module is named ``argparse.py`` but still reaches the stdlib
:mod:`argparse` via ``import argparse``: Python 3 absolute imports make
the name unambiguous, so there is no shadowing.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from typing import Any

from sprezzature_cli_gui.schema import NO_DEFAULT, _safe_default

# Re-exported for parity with the original single-module namespace, where
# the sentinel lived alongside these adapters.
__all__ = ["NO_DEFAULT", "_action_kind", "serialize_action", "walk_parser"]


def _action_kind(a: argparse.Action) -> str:
    """
    Map an :class:`argparse.Action` to an HTML form-field kind string.

    Returns one of: ``"bool"``, ``"int"``, ``"float"``, ``"choice"``,
    ``"text"``, ``"file"`` (for actions whose ``type`` looks like
    :func:`open` / :class:`argparse.FileType`).
    """
    if isinstance(a, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        return "bool"
    if a.choices:
        return "choice"
    if a.type is None:
        return "text"
    if a.type is int:
        return "int"
    if a.type is float:
        return "float"
    if isinstance(a.type, argparse.FileType):
        return "file"
    # ``type=open`` or callable — render as text and let the user paste a path.
    return "text"


def serialize_action(a: argparse.Action) -> dict[str, Any]:
    """Project one :class:`argparse.Action` into a JSON-friendly dict."""
    return {
        "dest": a.dest,
        "flags": list(a.option_strings),
        "kind": _action_kind(a),
        "choices": list(a.choices) if a.choices else None,
        "required": bool(a.required),
        "default": _safe_default(a.default),
        "help": (a.help or "").strip(),
        "nargs": a.nargs if isinstance(a.nargs, (str, int)) else None,
        "metavar": (
            a.metavar
            if isinstance(a.metavar, str)
            else (a.metavar[0] if isinstance(a.metavar, tuple) else None)
        ),
    }


def walk_parser(parser: argparse.ArgumentParser) -> dict[str, Any]:
    """
    Walk an :class:`argparse.ArgumentParser` into a serialisable tree.

    The shape mirrors ``argparse`` itself: a ``prog`` / ``description``
    pair, a list of leaf actions, and a (possibly empty)
    ``sub_commands`` dict for any nested sub-parsers.

    Help / version actions are filtered out — they exist only on the
    CLI surface, not in a GUI.

    See also :func:`walk` for the framework-agnostic entry point that
    dispatches between this and :func:`walk_click`.
    """
    actions: list[dict[str, Any]] = []
    sub_commands: dict[str, dict[str, Any]] = {}
    for a in parser._actions:
        if isinstance(a, argparse._SubParsersAction):
            for name, sub in a.choices.items():
                sub_commands[name] = walk_parser(sub)
        elif isinstance(a, (argparse._HelpAction,)) or a.dest == argparse.SUPPRESS:
            continue
        elif getattr(a, "version", None) is not None:
            # ``action="version"`` — version banner, not a user input.
            continue
        else:
            actions.append(serialize_action(a))
    return {
        "prog": parser.prog,
        "description": (parser.description or "").strip(),
        "actions": actions,
        "sub_commands": sub_commands,
    }
