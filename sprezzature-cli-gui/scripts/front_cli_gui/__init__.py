"""
sprezzature_cli_gui
=============

Package split of the ``cli_to_gui`` skill script. The single-file
``cli_to_gui.py`` remains in place as a thin facade re-exporting this
package's public API; the code itself lives here, one concern per
module:

- :mod:`sprezzature_cli_gui.loader` — load a parser factory from a
  ``module:callable`` spec.
- :mod:`sprezzature_cli_gui.schema` — the canonical action/tree schema
  helpers (``_safe_default``, ``NO_DEFAULT``) and the framework
  dispatch entry point :func:`~sprezzature_cli_gui.schema.walk`.
- :mod:`sprezzature_cli_gui.adapters` — one adapter per supported source
  framework (argparse, Click, ``--from-help``), each normalising into
  the canonical parser-tree dict.
- :mod:`sprezzature_cli_gui.renderer` — the HTML emitter.
- :mod:`sprezzature_cli_gui.cli` — the command-line driver.

Nothing here changes behaviour or emitted HTML relative to the
original single file — the split is purely structural.
"""

from __future__ import annotations
