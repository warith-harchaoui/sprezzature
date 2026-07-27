"""
_argparse — shared argparse parser factory for the sprezzature-ui scripts.

``make_parser(prog, description, epilog=None)`` returns an
``ArgumentParser`` pre-configured the way every script in this skill
expects:

- ``prog`` set explicitly so ``--help`` shows a clean name (no path).
- ``RawDescriptionHelpFormatter`` so multi-line descriptions and the
  optional ``epilog`` are not reflowed.
- A standard ``-V`` / ``--version`` option.

Duplicated (intentionally) across sprezzature-ui/scripts/, sprezzature-publish/
scripts/, sprezzature-accessibility/scripts/ so each skill stays self-contained.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
from typing import Optional


SKILL_VERSION = "1.0.0"


def make_parser(
    prog: str,
    description: str,
    epilog: Optional[str] = None,
) -> argparse.ArgumentParser:
    """Build a pre-configured argparse parser.

    Parameters
    ----------
    prog : str
        Program name shown in ``--help`` (e.g. ``"sprezzature-ui-validate"``).
    description : str
        One-paragraph description shown above the options table.
    epilog : str or None, optional
        Text shown below the options table — usually usage examples.
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
