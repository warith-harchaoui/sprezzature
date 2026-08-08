#!/usr/bin/env python3
"""
cvd_check — run the repo's colour-vision check on a financial-markets render.

Thin wrapper that delegates to the canonical tool,
``sprezzature-colors/scripts/simulate_cvd.py`` (Machado matrices applied in linear
sRGB, plus a relative-luminance grayscale panel via ``--grayscale``). It writes
a ``<stem>-cvd-grid.png`` mosaic — original + protanopia + deuteranopia +
tritanopia + grayscale — to eyeball right after the Ralph-loop render.

Usage
-----
    python cvd_check.py out/page.png

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_TOOL = Path(__file__).resolve().parent.parent / "sprezzature-colors" / "scripts" / "simulate_cvd.py"


def main(argv: list | None = None) -> int:
    """Run the canonical simulator (grid + grayscale) on each PNG argument."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python cvd_check.py <render.png> [...]")
        return 1
    for a in args:
        subprocess.run([sys.executable, str(_TOOL), a, "--grid", "--grayscale"], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
