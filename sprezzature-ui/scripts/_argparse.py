"""
_argparse — shared argparse parser factory for a sprezzature-* skill's scripts.

``make_parser(prog, description, epilog=None)`` returns an
``ArgumentParser`` pre-configured the way every script in this skill
expects:

- ``prog`` set explicitly so ``--help`` shows a clean name (no path).
- ``RawDescriptionHelpFormatter`` so multi-line descriptions and the
  optional ``epilog`` are not reflowed.
- A standard ``-V`` / ``--version`` option.

Duplicated (intentionally) across every sprezzature-* skill so each stays
self-contained; keep this file in sync with the copies in
sprezzature-colors/scripts/_argparse.py etc. Bump ``SKILL_VERSION`` in every
copy at release time (release.sh checks the drift).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from typing import Optional


SKILL_VERSION = "1.0.1"


def make_parser(
    prog: str,
    description: str,
    epilog: Optional[str] = None,
) -> argparse.ArgumentParser:
    """Build a pre-configured argparse parser.

    Parameters
    ----------
    prog : str
        Program name shown in ``--help`` (e.g. ``"sprezzature-figures-make"``).
    description : str
        One-paragraph description shown above the options table.
    epilog : str or None, optional
        Text shown below the options table — usually usage examples.

    Returns
    -------
    argparse.ArgumentParser
        Parser with ``-V``/``--version`` pre-attached.
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {SKILL_VERSION}",
    )
    return parser
