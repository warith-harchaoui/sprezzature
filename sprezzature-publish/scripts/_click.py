"""
_click — shared Click decorators and helpers for a sprezzature-* skill's scripts.

Mirrors the ``_argparse.make_parser`` factory in shape and intent: every
Click-based script in this skill is registered through
:func:`sprezzature_command` so the surface stays uniform.

Why a custom ``Command`` subclass
---------------------------------
Click's default usage line reads ``Usage: prog [OPTIONS] ARGS``. The
sprezzature test suite checks for the literal ``[-h]`` or ``[--help]`` token
to confirm a help flag is wired up. The subclass below injects
``[--help]`` into the usage line so the same assertions that covered
the argparse era keep passing under Click.

Duplicated (intentionally) across sprezzature-ui/scripts/, sprezzature-publish/
scripts/, sprezzature-accessibility/scripts/ so each skill stays self-contained — same
policy as ``_argparse.py``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

import click


SKILL_VERSION = "1.0.0"


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
    epilog: Optional[str] = None,
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
        Text shown below the options table — usually usage examples.

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
            SKILL_VERSION, "-V", "--version", prog_name=name,
        )(cmd)
        # Stash the canonical prog name so :func:`run_command` can pass it
        # to Click's ``main(prog_name=...)`` — otherwise the usage line
        # shows the raw script filename (``meta_from_ollama.py``) instead
        # of the kebab-cased name the user sees in docs.
        cmd._sprezzature_prog_name = name  # type: ignore[attr-defined]
        return cmd

    return decorator


def run_command(cmd: click.Command, argv: Optional[Sequence[str]] = None) -> int:
    """Invoke a sprezzature Click command and return its integer exit code.

    Bridges the argparse-era contract — ``main(argv=None) -> int`` — to
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
    prog_name: Optional[str] = getattr(cmd, "_sprezzature_prog_name", None)
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
