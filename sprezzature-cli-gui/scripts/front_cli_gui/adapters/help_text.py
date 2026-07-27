"""
sprezzature_cli_gui.adapters.help_text
===============================

The framework-agnostic ``--from-help`` adapter.

Runs ``<command> --help`` and parses its output into the canonical
parser-tree dict. Works on any CLI that emits a conventional help
block — argparse, Click, Typer, clap (Rust), cobra (Go), commander
(Node), even hand-rolled shell scripts — at lower fidelity than native
introspection (everything maps to ``"text"`` unless a ``[default: …]``,
``[choices]`` or recognised METAVAR is visible). The regexes below
recognise the section headers and line shapes those frameworks
converge on.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


#: Subprocess timeout (seconds) for the ``--help`` invocation. Long
#: enough for a slow JIT-warm CLI, short enough that a hanging
#: subprocess does not freeze the GUI generator.
HELP_TIMEOUT_S: float = 10.0


#: Section headers we recognise. Most CLI conventions converge on
#: these — argparse, Click, clap (Rust), cobra (Go), commander (Node)
#: all use some variation. We match case-insensitively + tolerate the
#: trailing-colon-and-optional-newline shape.
RE_OPTIONS_HEADER: re.Pattern[str] = re.compile(
    r"^\s*(options|optional arguments|flags):\s*$",
    re.IGNORECASE | re.MULTILINE,
)
RE_COMMANDS_HEADER: re.Pattern[str] = re.compile(
    r"^\s*(commands|sub-?commands|available commands):\s*$",
    re.IGNORECASE | re.MULTILINE,
)
RE_USAGE_HEADER: re.Pattern[str] = re.compile(
    r"^\s*usage:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
RE_POSITIONAL_HEADER: re.Pattern[str] = re.compile(
    r"^\s*(positional arguments|arguments):\s*$",
    re.IGNORECASE | re.MULTILINE,
)

#: Line shape for one option entry: leading whitespace, one or more
#: ``-flag`` tokens (optionally with a comma-list and an inline
#: METAVAR), then 2+ whitespace and the help text.
#:
#: Permissive on purpose — argparse, Click, clap, cobra, commander
#: each format option lines slightly differently and we want all of
#: them to land in the same parse. The flag-token split happens
#: after the match, in :func:`_parse_option_line`.
#:
#: Captures:
#:   1. flags-and-metavar fragment (e.g. ``"-V, --version"``,
#:      ``"--input PATH"``, ``"--format [mp3|ogg|flac]"``)
#:   2. inline help text (may be empty when help is on the next line)
RE_OPTION_LINE: re.Pattern[str] = re.compile(
    r"^\s{2,}(-{1,2}[^\s,]+(?:,\s*-{1,2}[^\s,]+)*"
    r"(?:\s[^\s]+)?)"
    r"(?:\s{2,}(.*))?$"
)

#: One sub-command row: leading whitespace, the slug, two-or-more
#: spaces, the help fragment.
RE_COMMAND_LINE: re.Pattern[str] = re.compile(
    r"^\s{2,}([a-z0-9][a-z0-9_-]*)(?:\s{2,}(.*))?$",
    re.IGNORECASE,
)

#: ``[default: 128]`` / ``[default=128]`` / ``(default: 128)`` —
#: extracts the literal default the help text advertised.
RE_DEFAULT_HINT: re.Pattern[str] = re.compile(
    r"[\[\(]default[:= ]\s*([^\]\)]+)[\]\)]",
    re.IGNORECASE,
)
RE_REQUIRED_HINT: re.Pattern[str] = re.compile(
    r"\[required\]|\(required\)",
    re.IGNORECASE,
)
#: ``[mp3|ogg|flac]`` or ``{mp3,ogg,flac}`` — Click vs argparse styles.
RE_CHOICE_HINT: re.Pattern[str] = re.compile(
    r"\[([^\[\]]+\|[^\[\]]+)\]|\{([^{}]+,[^{}]+)\}"
)


def _run_help(cmdline: str) -> str:
    """
    Run ``<cmdline> --help`` and return its stdout.

    Parameters
    ----------
    cmdline : str
        The command to introspect, as a shell string. Split on
        whitespace; we never invoke the shell itself to keep
        injection surface narrow.

    Returns
    -------
    str
        Captured stdout. Stderr is folded in too because some CLIs
        (notably older argparse) write help to stderr.

    Raises
    ------
    FileNotFoundError
        If the command does not resolve on ``$PATH``.
    subprocess.TimeoutExpired
        If ``--help`` does not return within
        :data:`HELP_TIMEOUT_S` seconds.
    """
    import shlex
    import subprocess as sp

    parts: list[str] = shlex.split(cmdline) + ["--help"]
    proc = sp.run(
        parts,
        capture_output=True,
        text=True,
        timeout=HELP_TIMEOUT_S,
        check=False,
    )
    # Many CLIs exit non-zero on ``--help`` (notably tools that
    # treat help as "no real command was named"). Trust the output,
    # not the exit code.
    return proc.stdout + ("\n" + proc.stderr if proc.stderr else "")


def _extract_prog(cmdline: str, help_text: str = "") -> str:
    """
    Best-effort program name.

    Prefers the ``usage: <prog> …`` line in the help output (the CLI's
    own opinion of its prog name); falls back to the basename of the
    first shell token. Shell wrappers like ``python3 myscript.py`` get
    correctly identified by the usage line as ``myscript``, not
    ``python3``.
    """
    if help_text:
        m = RE_USAGE_HEADER.search(help_text)
        if m:
            usage_line: str = m.group(1).strip()
            first_token: str = usage_line.split()[0] if usage_line else ""
            if first_token:
                return first_token
    import shlex
    parts: list[str] = shlex.split(cmdline) if cmdline else []
    # Skip leading interpreter / wrapper tokens to land on the real
    # script name when invoked as ``python3 path/to/script.py``.
    for token in parts:
        name: str = Path(token).name
        if name and not name.startswith("-") and name not in {
            "python", "python3", "python2", "uvx", "uv", "npx", "node",
            "ruby", "perl", "bash", "sh",
        }:
            # Strip a ``.py`` / ``.js`` / ``.rb`` extension so the GUI
            # title is the conventional command name.
            return Path(name).stem or name
    return (parts[0] if parts else "cli")


#: argparse-style sub-command list: ``{cmd1,cmd2,cmd3}`` on a single
#: indented line under ``positional arguments:``.
RE_ARGPARSE_SUBS: re.Pattern[str] = re.compile(
    r"^\s{2,}\{([a-z0-9][a-z0-9_,-]*)\}\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _section(text: str, header_re: re.Pattern[str]) -> str | None:
    """
    Return the lines between ``header_re`` and the next blank line.

    Returns ``None`` if the section is not present in ``text``.
    The slice ends at the first line that does not start with two
    or more spaces — that is how argparse / Click visually delimit
    one section from the next.
    """
    m = header_re.search(text)
    if not m:
        return None
    start: int = m.end()
    # Walk forward line by line until we hit a non-indented line.
    lines: list[str] = text[start:].splitlines()
    out: list[str] = []
    for line in lines:
        if not line.strip():
            # A blank line is permitted *between* entries; we keep
            # going until two consecutive blanks OR an outdented line.
            out.append(line)
            continue
        if not line.startswith(" "):
            break
        out.append(line)
    return "\n".join(out)


def _parse_option_line(
    line: str, help_continuation: str = ""
) -> dict[str, Any] | None:
    """Project one help-text option line into the canonical action dict."""
    m = RE_OPTION_LINE.match(line)
    if not m:
        return None
    flags_fragment: str = m.group(1).strip()
    inline_help: str = (m.group(2) or "").strip()
    full_help: str = (inline_help + " " + help_continuation).strip()

    # Split ``"-V, --version"`` → ``["-V", "--version"]``.
    flag_tokens: list[str] = []
    for piece in flags_fragment.split(","):
        token: str = piece.strip().split()[0] if piece.strip() else ""
        if token.startswith("-"):
            flag_tokens.append(token)
    if not flag_tokens:
        return None
    if any(t in ("-h", "--help") for t in flag_tokens):
        return None  # filter the omnipresent help line

    # ``--input PATH`` → metavar = "PATH". Lower-cased becomes our
    # candidate dest. If no metavar is present, fall back to the
    # longest flag with its leading dashes stripped.
    metavar: str | None = None
    after_flags: str = flags_fragment.split()[-1] if " " in flags_fragment else ""
    if (
        after_flags
        and not after_flags.startswith("-")
        and after_flags not in flag_tokens
    ):
        metavar = after_flags.rstrip("]").lstrip("[<(")

    longest: str = max(flag_tokens, key=len)
    dest: str = longest.lstrip("-").replace("-", "_")

    # Heuristic kind detection from help text + metavar.
    kind: str = "text"
    if metavar and metavar.upper() in ("INTEGER", "INT", "N"):
        kind = "int"
    elif metavar and metavar.upper() in ("FLOAT", "NUMBER"):
        kind = "float"
    elif metavar and metavar.upper() in ("PATH", "FILE", "FILENAME", "DIR"):
        kind = "file"
    elif not metavar:
        # No metavar usually means a boolean flag.
        kind = "bool"

    # Choices: ``[mp3|ogg|flac]`` or ``{mp3,ogg,flac}``.
    choices: list[str] | None = None
    cm = RE_CHOICE_HINT.search(flags_fragment + " " + full_help)
    if cm:
        raw: str = cm.group(1) or cm.group(2) or ""
        sep: str = "|" if "|" in raw else ","
        choices = [c.strip() for c in raw.split(sep) if c.strip()]
        if choices:
            kind = "choice"

    # Default: ``[default: 128]`` (Click) or ``(default: 128)`` (argparse).
    default: Any = None
    dm = RE_DEFAULT_HINT.search(full_help)
    if dm:
        raw_default: str = dm.group(1).strip()
        # Try int / float, fall back to string.
        try:
            default = int(raw_default)
        except ValueError:
            try:
                default = float(raw_default)
            except ValueError:
                default = raw_default

    required: bool = bool(RE_REQUIRED_HINT.search(full_help))

    return {
        "dest": dest,
        "flags": flag_tokens,
        "kind": kind,
        "choices": choices,
        "required": required,
        "default": default,
        "help": full_help,
        "nargs": None,
        "metavar": metavar,
    }


def _parse_options_section(section: str | None) -> list[dict[str, Any]]:
    """Walk an options section and produce one action dict per entry."""
    if not section:
        return []
    out: list[dict[str, Any]] = []
    pending_line: str | None = None
    for line in section.splitlines():
        if not line.strip():
            if pending_line is not None:
                parsed = _parse_option_line(pending_line)
                if parsed:
                    out.append(parsed)
                pending_line = None
            continue
        # An indented line that does NOT start with ``-`` (under deep
        # indent) is a help-text continuation for the previous option.
        stripped: str = line.lstrip()
        if pending_line is not None and not stripped.startswith("-"):
            # Fold continuation into the previous parse.
            parsed_prev = _parse_option_line(pending_line, stripped)
            if parsed_prev:
                out.append(parsed_prev)
            pending_line = None
            continue
        if pending_line is not None:
            parsed = _parse_option_line(pending_line)
            if parsed:
                out.append(parsed)
        pending_line = line
    if pending_line is not None:
        parsed = _parse_option_line(pending_line)
        if parsed:
            out.append(parsed)
    return out


def _parse_commands_section(section: str | None) -> list[tuple[str, str]]:
    """Yield (sub_command_name, short_help) from a Commands section."""
    if not section:
        return []
    out: list[tuple[str, str]] = []
    for line in section.splitlines():
        m = RE_COMMAND_LINE.match(line)
        if not m:
            continue
        name: str = m.group(1)
        help_text: str = (m.group(2) or "").strip()
        # Reject false matches that look like option lines.
        if name.startswith("-"):
            continue
        out.append((name, help_text))
    return out


def walk_from_help(
    cmdline: str,
    *,
    _depth: int = 0,
    _max_depth: int = 3,
) -> dict[str, Any]:
    """
    Parse ``<cmdline> --help`` into the canonical parser tree.

    Works on any CLI that emits a conventional help block:
    argparse, Click, Typer, clap (Rust), cobra (Go), commander
    (Node), even hand-rolled shell scripts that follow the
    standard sections. Lower fidelity than native introspection
    (everything maps to ``"text"`` unless a ``[default: …]``,
    ``[choices]`` or recognised METAVAR is visible).

    Parameters
    ----------
    cmdline : str
        The command to introspect (passed through :mod:`shlex.split`
        — never via the shell, to keep the injection surface narrow).
    _depth : int, default 0
        Internal — current recursion depth into sub-commands.
    _max_depth : int, default 3
        Internal — stop recursing into sub-commands past this many
        levels. Defends against pathological CLIs whose sub-command
        list includes itself.

    Returns
    -------
    dict
        Canonical parser tree.
    """
    help_text: str = _run_help(cmdline)
    description: str = ""
    usage_match = RE_USAGE_HEADER.search(help_text)
    if usage_match:
        # Treat any prose between the Usage block and the first
        # ``Options:`` / ``Commands:`` header as the description.
        after_usage: int = usage_match.end()
        next_header = min(
            (m.start() for m in [
                RE_OPTIONS_HEADER.search(help_text, after_usage),
                RE_COMMANDS_HEADER.search(help_text, after_usage),
                RE_POSITIONAL_HEADER.search(help_text, after_usage),
            ] if m is not None),
            default=len(help_text),
        )
        description = help_text[after_usage:next_header].strip()

    options: list[dict[str, Any]] = _parse_options_section(
        _section(help_text, RE_OPTIONS_HEADER)
    )
    positionals: list[dict[str, Any]] = _parse_options_section(
        _section(help_text, RE_POSITIONAL_HEADER)
    )
    commands_raw: list[tuple[str, str]] = _parse_commands_section(
        _section(help_text, RE_COMMANDS_HEADER)
    )
    # argparse uses ``positional arguments:`` + a ``{cmd1,cmd2}`` line
    # to list sub-commands. Detect that shape and fold its entries
    # into the same sub_commands recursion.
    for m in RE_ARGPARSE_SUBS.finditer(help_text):
        for name in m.group(1).split(","):
            name = name.strip()
            if name and not any(c[0] == name for c in commands_raw):
                commands_raw.append((name, ""))

    sub_commands: dict[str, dict[str, Any]] = {}
    if _depth < _max_depth:
        for name, _ in commands_raw:
            try:
                sub_commands[name] = walk_from_help(
                    f"{cmdline} {name}",
                    _depth=_depth + 1,
                    _max_depth=_max_depth,
                )
            except (FileNotFoundError, OSError):
                # The sub-command exists in the help text but cannot
                # be invoked. Skip rather than abort the whole walk.
                continue
            except Exception:  # noqa: BLE001 — best-effort.
                continue

    return {
        "prog": _extract_prog(cmdline, help_text),
        "description": description,
        "actions": options + positionals,
        "sub_commands": sub_commands,
    }
