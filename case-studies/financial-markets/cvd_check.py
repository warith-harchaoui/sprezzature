#!/usr/bin/env python3
"""
cvd_check — run the suite's colour-vision check on a financial-markets render.

Thin wrapper that delegates to the canonical tool, ``sprezzature-colors-cvd``
(Machado matrices applied in linear sRGB, plus a relative-luminance grayscale
panel via ``--grayscale``). It writes a ``<stem>-cvd-grid.png`` mosaic —
original + protanopia + deuteranopia + tritanopia + grayscale — to eyeball
right after the Ralph-loop render.

What was wrong with the previous version
----------------------------------------
It built a path to the tool's file instead of calling the command::

    Path(__file__).resolve().parent.parent / "sprezzature-colors" / "scripts" / …

Two parents up from this file is ``case-studies/``, so the path it assembled
was ``case-studies/sprezzature-colors/scripts/simulate_cvd.py`` — a directory
that has never existed, before or after the brick moved to its own package.
And a file path is the wrong thing to hold either way: the tool ships as a pip
package now, and the command is the part that stays put.

So: the registered command first, then ``python -m`` against the module, which
works for an install with no console script on ``$PATH``. Neither resolving is
a clean message, not a traceback about a file nobody asked about.

Usage
-----
    python cvd_check.py out/page.png

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import shutil
import subprocess
import sys

#: The command `sprezzature-colors` registers for the simulator.
_COMMAND = "sprezzature-colors-cvd"

#: Its module, for the ``python -m`` fallback.
_MODULE = "sprezzature_colors_scripts.simulate_cvd"


def _invocation() -> list[str] | None:
    """How to call the simulator here, or None if it is not installed."""
    found = shutil.which(_COMMAND)
    if found is not None:
        return [found]
    try:
        import importlib.util

        if importlib.util.find_spec(_MODULE) is not None:
            return [sys.executable, "-m", _MODULE]
    except (ImportError, ValueError):
        pass
    return None


def main(argv: list | None = None) -> int:
    """Run the canonical simulator (grid + grayscale) on each PNG argument."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python cvd_check.py <render.png> [...]")
        return 1
    call = _invocation()
    if call is None:
        print(
            f"cvd_check: {_COMMAND} is not installed.\n"
            f"  pip install sprezzature-colors",
            file=sys.stderr,
        )
        return 2
    worst = 0
    for a in args:
        # Not check=True: the simulator already says what is wrong with a file
        # it cannot open, and raising CalledProcessError on top of that buries
        # its message under a traceback from this wrapper.
        completed = subprocess.run([*call, a, "--grid", "--grayscale"])
        worst = worst or completed.returncode
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
