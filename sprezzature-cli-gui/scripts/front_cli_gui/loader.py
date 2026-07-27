"""
sprezzature_cli_gui.loader
====================

Load a parser factory from a ``module:callable`` spec.

Given a ``"<module>:<factory>"`` string, resolve the module (either a
filesystem path or a dotted import path), call the zero-argument
factory, and hand back the CLI object it returns — an
:class:`argparse.ArgumentParser` or a :class:`click.Command`. The
loader consumes the parser by introspection only; it never calls
``parse_args``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_parser_from_spec(spec: str) -> Any:
    """
    Load a parser factory from a ``module:callable`` spec.

    Two forms are accepted, distinguished by whether the module part
    looks like a filesystem path:

    * ``"path/to/file.py:factory"`` — load the file as an anonymous
      module via :mod:`importlib.util`; works on any standalone
      script, no package install needed.
    * ``"dotted.module:factory"`` — :func:`importlib.import_module`;
      the module must be on ``sys.path`` (typically because the user
      ran from the repo root).

    Parameters
    ----------
    spec : str
        The ``"<module>:<factory>"`` string.

    Returns
    -------
    argparse.ArgumentParser
        The parser returned by ``factory()``. The function does *not*
        call ``parse_args`` — it consumes the parser by introspection
        only.

    Raises
    ------
    ValueError
        If ``spec`` does not contain a single ``:`` separator, or the
        factory returns something that is not an
        :class:`argparse.ArgumentParser`.
    """
    if ":" not in spec:
        raise ValueError(
            f"Spec '{spec}' must be of the form 'module:factory' "
            f"(e.g. 'path/to/cli.py:make_parser')."
        )
    mod_part, _, factory_name = spec.rpartition(":")
    # File-path form?
    if mod_part.endswith(".py") or "/" in mod_part or mod_part.startswith("./"):
        mod_path: Path = Path(mod_part).resolve()
        if not mod_path.is_file():
            raise FileNotFoundError(f"No such file: {mod_path}")
        spec_obj = importlib.util.spec_from_file_location(
            "_cli_to_gui_target", mod_path
        )
        if spec_obj is None or spec_obj.loader is None:
            raise ImportError(f"Could not load {mod_path} as a module")
        mod = importlib.util.module_from_spec(spec_obj)
        # Adding the file's parent dir to sys.path lets the target
        # script's own ``import`` statements resolve siblings.
        parent: str = str(mod_path.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        spec_obj.loader.exec_module(mod)
    else:
        mod = importlib.import_module(mod_part)
    factory = getattr(mod, factory_name, None)
    if factory is None:
        raise AttributeError(
            f"Module '{mod_part}' has no attribute '{factory_name}'."
        )
    parser_obj = factory()
    # Adapter dispatch (see :func:`walk`): an argparse.ArgumentParser
    # or any Click BaseCommand counts. Anything else is rejected with
    # an actionable error message — we name both frameworks the
    # adapter understands so the user knows what to return.
    if isinstance(parser_obj, argparse.ArgumentParser):
        return parser_obj
    # Click is an optional dependency. We import it lazily so the
    # ``language: python`` pre-commit hook + minimal CI runners that
    # only target argparse keep working without Click on the path.
    try:
        import click  # noqa: WPS433  (lazy by design)
    except ImportError:
        click = None  # type: ignore[assignment]
    if click is not None and isinstance(parser_obj, click.Command):
        return parser_obj
    raise ValueError(
        f"Factory '{spec}' returned a "
        f"{type(parser_obj).__name__}; expected argparse.ArgumentParser "
        f"or click.Command (install click if your factory returns "
        f"a Click app)."
    )
