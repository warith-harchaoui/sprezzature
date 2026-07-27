"""
sprezzature_cli_gui.adapters.click
===========================

The Click adapter (optional dependency).

Walks a :class:`click.Command` — leaf ``Command`` or nested ``Group`` —
into the canonical parser-tree dict, mirroring the argparse adapter's
output schema exactly so the renderer never branches on framework.
Typer apps work through their underlying Click group (``app.cli``).
Click is only touched by callers who already produced a Click object,
so argparse-only users keep their stdlib-only run.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

from typing import Any

from sprezzature_cli_gui.schema import _safe_default


def _click_param_kind(param: Any) -> str:
    """
    Map a :class:`click.Parameter` to a form-field kind string.

    Mirrors :func:`_action_kind` but reads from Click's structured
    ``param.type`` / ``param.is_flag`` / ``param.multiple`` attributes
    instead of argparse's heuristic ``type=`` callable.

    Parameters
    ----------
    param : click.Parameter
        The Click parameter (an ``Option`` or ``Argument``).

    Returns
    -------
    str
        One of ``"bool"``, ``"int"``, ``"float"``, ``"choice"``,
        ``"file"``, ``"text"``.
    """
    # ``is_flag=True`` is Click's idiomatic boolean switch (parallel
    # to argparse's ``store_true`` / ``store_false``).
    if getattr(param, "is_flag", False):
        return "bool"
    # ``count=True`` increments an int per repetition (``-vvv``). We
    # render it as an integer field — the GUI cannot reasonably ask
    # the user to "click v three times".
    if getattr(param, "count", False):
        return "int"
    # ``click.types.*`` are concrete instances on ``param.type``. We
    # inspect the type's ``name`` so we do not need to import the
    # ``click.types`` symbols at module load (Click is optional).
    type_name: str = getattr(param.type, "name", "") or ""
    if type_name == "boolean":
        return "bool"
    if type_name in ("integer", "integer range"):
        return "int"
    if type_name in ("float", "float range"):
        return "float"
    if type_name == "choice":
        return "choice"
    if type_name in ("path", "filename", "file"):
        return "file"
    return "text"


def _click_param_choices(param: Any) -> list[str] | None:
    """Extract the choices list from a ``click.Choice`` param if present."""
    type_name: str = getattr(param.type, "name", "") or ""
    if type_name != "choice":
        return None
    choices: Any = getattr(param.type, "choices", None)
    if choices is None:
        return None
    return [str(c) for c in choices]


def _serialize_click_param(param: Any) -> dict[str, Any]:
    """
    Project one :class:`click.Parameter` into the canonical action dict.

    The output schema is identical to :func:`serialize_action` —
    ``dest``, ``flags``, ``kind``, ``choices``, ``required``,
    ``default``, ``help``, ``nargs``, ``metavar`` — so the HTML
    renderer never has to branch on the source framework.
    """
    # ``opts`` is the list of ``--flag`` strings for Options;
    # Arguments have no opts (positional).
    flags: list[str] = list(getattr(param, "opts", []) or [])
    # ``default`` is sometimes a callable (Click resolves it lazily).
    # We materialise + safe-serialise so the HTML emitter sees a
    # value it can write into ``value="…"``.
    default: Any = getattr(param, "default", None)
    if callable(default):
        try:
            default = default()
        except Exception:  # noqa: BLE001 — best-effort; fall back to None.
            default = None
    # Click 8.2+ uses a sentinel value (``click.core.Sentinel.UNSET``
    # or similar) for parameters with no explicit default; treat it
    # as "no default" so the HTML emitter does not stamp a literal
    # ``Sentinel.UNSET`` into the form's ``value="…"`` attribute.
    if default is not None and "Sentinel" in type(default).__name__:
        default = None
    return {
        "dest": param.name,
        "flags": flags,
        "kind": _click_param_kind(param),
        "choices": _click_param_choices(param),
        "required": bool(getattr(param, "required", False)),
        "default": _safe_default(default),
        "help": (getattr(param, "help", "") or "").strip(),
        # Click uses ``nargs=-1`` for "any number"; argparse uses "*".
        # We surface Click's int directly so the HTML side can decide.
        "nargs": getattr(param, "nargs", None),
        "metavar": getattr(param, "metavar", None),
    }


def walk_click(cmd: Any, prog: str | None = None) -> dict[str, Any]:
    """
    Walk a :class:`click.Command` into the canonical parser tree.

    Mirrors :func:`walk_parser` exactly — same dict shape — so the
    HTML renderer never branches on the source framework. Handles
    both leaf ``Command`` and nested ``Group`` trees; ``--help`` is
    filtered (Click adds it automatically and it has no GUI value).

    Parameters
    ----------
    cmd : click.Command
        A Click command or group. Typer apps expose their underlying
        Click group via ``app.cli`` — pass that.
    prog : str or None, optional
        Override the ``prog`` field. Defaults to the command's own
        ``name`` (Click sets this from the function name).

    Returns
    -------
    dict
        The canonical parser tree.
    """
    actions: list[dict[str, Any]] = []
    sub_commands: dict[str, dict[str, Any]] = {}
    # ``cmd.params`` are the leaf options / arguments.
    for param in getattr(cmd, "params", []) or []:
        # Click sometimes emits an ``HelpOption`` automatically; we
        # detect it via ``param.is_eager`` + an empty ``name``-shape.
        name: str | None = getattr(param, "name", None)
        if not name or name == "help":
            continue
        actions.append(_serialize_click_param(param))
    # ``Group.commands`` is a dict of sub-commands. Leaf ``Command``
    # objects do not have ``commands``.
    subs: dict[str, Any] = getattr(cmd, "commands", {}) or {}
    for name, sub in subs.items():
        sub_commands[name] = walk_click(sub, prog=name)
    return {
        "prog": prog or getattr(cmd, "name", "cli") or "cli",
        "description": (getattr(cmd, "help", "") or "").strip(),
        "actions": actions,
        "sub_commands": sub_commands,
    }
