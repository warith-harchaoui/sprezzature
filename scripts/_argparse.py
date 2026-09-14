"""
_argparse: one factory function for every script's command-line parser.

Python's standard library builds a command-line interface around an
``argparse.ArgumentParser`` object: you create one, register each flag
(``--lang``, ``--out``, and so on) on it, then call ``.parse_args()`` to
turn the words the user typed into a plain object with one attribute per
flag. Every script in this project needs the same handful of small
conveniences on top of that (a clean program name in ``--help``, instead
of a long file path; multi-line help text kept exactly as written instead
of being auto-reflowed; a ``-V``/``--version`` flag). Rather than
repeating that setup in every script, ``make_parser(prog, description,
epilog=None)`` builds one parser already configured that way, and each
script starts from it.

This file is duplicated on purpose into every sprezzature-* repository,
one copy each, so a skill stays self-contained and runs on its own:
including from a downloaded zip, with nothing available but Python's
standard library. The copies are meant to stay byte-for-byte identical
apart from ``SKILL_VERSION``, which each repository sets to its own
released version. So edit the canonical copy rather than this one, unless
this is it: ``scripts/sync_helpers.py``, in the sprezzature monorepo,
names the canonical copy, reports the ones that have drifted, and
propagates the change with ``--apply``.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse

SKILL_VERSION = "1.3.4"


def make_parser(
    prog: str,
    description: str,
    epilog: str | None = None,
) -> argparse.ArgumentParser:
    """Build a pre-configured argparse parser.

    Parameters
    ----------
    prog : str
        Program name shown in ``--help`` (e.g. ``"sprezzature-figures-make"``).
    description : str
        One-paragraph description shown above the options table.
    epilog : str or None, optional
        Text shown below the options table, usually usage examples.

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
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {SKILL_VERSION}",
    )
    return parser
