"""
sprezzature_cli_gui.schema
===================

The canonical action / parser-tree schema and its framework dispatch.

Every supported source framework normalises into one dict shape
(``prog`` / ``description`` / ``actions`` / ``sub_commands``). This
module owns the sentinel and default-serialisation helper shared by
all adapters, plus :func:`walk` — the single, framework-agnostic entry
point the HTML renderer calls. ``walk`` imports the concrete adapters
lazily (function-locally) so this module has no import-time dependency
on :mod:`sprezzature_cli_gui.adapters`, keeping the import graph acyclic.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from typing import Any


#: Sentinel returned by :func:`_safe_default` for defaults we cannot
#: safely serialise to JSON. The HTML treats it as "no default
#: published" and leaves the form field empty.
NO_DEFAULT: object = object()


def _safe_default(default: Any) -> Any:
    """Return a JSON-serialisable representation of an argparse default."""
    if default is argparse.SUPPRESS or default is None:
        return None
    if isinstance(default, (str, int, float, bool)):
        return default
    if isinstance(default, (list, tuple)):
        return [_safe_default(d) for d in default]
    return str(default)


def walk(obj: Any) -> dict[str, Any]:
    """
    Walk a CLI object (argparse or Click) into the canonical tree.

    Single entry point for the HTML renderer — it does not need to
    know which framework produced the input.

    Parameters
    ----------
    obj : argparse.ArgumentParser or click.Command
        The CLI to introspect.

    Returns
    -------
    dict
        Canonical parser tree (``prog``, ``description``, ``actions``,
        ``sub_commands``).

    Raises
    ------
    TypeError
        If ``obj`` is neither an argparse parser nor a Click command.
    """
    if isinstance(obj, argparse.ArgumentParser):
        # Lazy import keeps this module free of a top-level dependency
        # on the adapters package (which imports back from here).
        from sprezzature_cli_gui.adapters.argparse import walk_parser

        return walk_parser(obj)
    # Click is optional; only attempt the isinstance check after a
    # successful lazy import. Skipping the import on argparse-only
    # users keeps the script stdlib-only at run time.
    try:
        import click  # noqa: WPS433
    except ImportError:
        click = None  # type: ignore[assignment]
    if click is not None and isinstance(obj, click.Command):
        from sprezzature_cli_gui.adapters.click import walk_click

        return walk_click(obj)
    raise TypeError(
        f"walk() expected argparse.ArgumentParser or click.Command, "
        f"got {type(obj).__name__}"
    )
