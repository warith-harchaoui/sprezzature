"""
_click: the same command-line conveniences as `_argparse.py`, for scripts
built with Click instead of argparse.

Click is a third-party library for building command-line interfaces: instead
of assembling a parser object by hand, you decorate a plain function with
``@click.command()`` and ``@click.option(...)``, and Click turns the
function's arguments into command-line flags on its own. This module plays
the same role for Click-based scripts that `_argparse.py` plays for
argparse-based ones: every script registers its command through
:func:`sprezzature_command` so all of this project's command-line tools look
and behave the same way, whichever library built them.

Why a custom ``Command`` subclass
---------------------------------
Click's default usage line reads ``Usage: prog [OPTIONS] ARGS``, with no
mention of a help flag. This project's test suite checks for the literal
token ``[-h]`` or ``[--help]`` in that line to confirm a script actually
offers a help flag: a check written back when every script used argparse,
which does show it by default. The subclass below injects ``[--help]`` into
Click's usage line too, so that same check still passes now that some
scripts use Click.

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

from collections.abc import Callable, Sequence
from typing import Any

import click

SKILL_VERSION = "1.3.0"


#: Context settings shared by every sprezzature Click command. ``-h`` joins
#: ``--help`` so users get the short form they expect from argparse era
#: tools; ``max_content_width`` keeps long help paragraphs readable on
#: standard 80-column terminals without forcing a hard wrap on wide ones.
CONTEXT_SETTINGS: dict[str, Any] = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 100,
}


class SprezzatureCommand(click.Command):
    """A :class:`click.Command` that prints ``[--help]`` in the usage line.

    Click's default usage string omits the help flag because it is
    implicit. The sprezzature test suite asserts on its presence as a sanity
    check that every shipped script answers ``-h`` / ``--help``; the
    subclass restores that token without altering any other behaviour.
    """

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Write the usage line with an explicit ``[--help]`` token restored."""
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(ctx.command_path, " ".join(["[--help]"] + pieces))


def sprezzature_command(
    name: str,
    *,
    help: str,
    epilog: str | None = None,
) -> Callable[[Callable[..., Any]], click.Command]:
    """Return a decorator that builds a sprezzature-flavoured Click command.

    Parameters
    ----------
    name : str
        Program name shown in ``--help`` (e.g. ``"sprezzature-publish-meta"``).
        Mirrors the ``prog=`` kwarg the argparse factory took.
    help : str
        One-paragraph description shown above the options table.
    epilog : str or None, optional
        Text shown below the options table, usually usage examples.

    Returns
    -------
    Callable
        Decorator that wraps the target function as a :class:`SprezzatureCommand`
        with a ``-V`` / ``--version`` option emitting ``"<name> <SKILL_VERSION>"``.
    """

    def decorator(func: Callable[..., Any]) -> click.Command:
        """Wrap ``func`` as a :class:`SprezzatureCommand` with a ``-V`` / ``--version`` flag."""
        cmd = click.command(
            name=name,
            cls=SprezzatureCommand,
            help=help,
            epilog=epilog,
            context_settings=CONTEXT_SETTINGS,
        )(func)
        # Version flag mirrors the argparse-era ``-V`` / ``--version`` pair
        # and the ``%(prog)s 0.2.0`` payload so test_cli_help keeps passing.
        cmd = click.version_option(
            SKILL_VERSION,
            "-V",
            "--version",
            prog_name=name,
        )(cmd)
        # Stash the canonical prog name so :func:`run_command` can pass it
        # to Click's ``main(prog_name=...)``; otherwise the usage line
        # shows the raw script filename (``meta_from_ollama.py``) instead
        # of the kebab-cased name the user sees in docs.
        cmd._sprezzature_prog_name = name  # type: ignore[attr-defined]
        return cmd

    return decorator


def run_command(cmd: click.Command, argv: Sequence[str] | None = None) -> int:
    """Invoke a sprezzature Click command and return its integer exit code.

    Bridges the argparse-era contract (``main(argv=None) -> int``) to
    Click's standalone-mode default of exiting via :class:`SystemExit`.

    The helper:

    * lets the command body return an explicit ``int`` (success: ``0``,
      handled failure: ``1`` / ``2``) which is forwarded unchanged;
    * converts Click's :class:`~click.exceptions.UsageError` and the
      ``--help`` / ``--version`` ``Exit`` events into the conventional
      :class:`SystemExit` the argparse parsers used to raise, so the
      pre-existing tests that wrap ``main()`` in
      ``pytest.raises(SystemExit)`` keep working.

    Parameters
    ----------
    cmd : click.Command
        A command built via :func:`sprezzature_command`.
    argv : sequence of str or None, optional
        Argument vector excluding ``argv[0]``. ``None`` means
        ``sys.argv[1:]`` (Click's default).

    Returns
    -------
    int
        Process exit code returned by the command body, or ``0`` when the
        body returned ``None``.
    """
    prog_name: str | None = getattr(cmd, "_sprezzature_prog_name", None)
    try:
        result = cmd.main(args=argv, prog_name=prog_name, standalone_mode=False)
    except click.exceptions.UsageError as exc:
        # Mirror argparse's behaviour: print the usage error to stderr and
        # raise ``SystemExit(2)`` so callers (and tests) see a familiar
        # exit signal.
        exc.show()
        raise SystemExit(2)
    except click.exceptions.Abort:
        # Ctrl-C inside a prompt; map to the conventional 130 exit.
        raise SystemExit(130)
    except click.exceptions.Exit as exc:
        # --help and --version raise this with code 0 in non-standalone
        # mode. Propagate as SystemExit so the test harness sees it.
        raise SystemExit(exc.exit_code)
    if result is None:
        return 0
    if isinstance(result, int):
        return result
    # Defensive default: anything else is treated as success.
    return 0
