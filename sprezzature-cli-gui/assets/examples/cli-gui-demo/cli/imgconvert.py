#!/usr/bin/env python3
"""
imgconvert
==========

Mock image-processing CLI used by the cli-gui-demo example.

The CLI exposes three subcommands with a mix of argument types so the GUI
exercises every flag-to-control mapping in the skill's CLI → GUI workflow:

* ``resize``    — positional paths + two ints + one boolean.
* ``convert``   — positional paths + one enum + one bounded int.
* ``optimize``  — one positional path + two booleans + one int.

The implementation does **not** actually process images — it sleeps for a
moment, prints fake progress lines to stdout, and exits with a useful
status code so the GUI's success and failure paths can be exercised.

Usage
-----
::

    python imgconvert.py --help
    python imgconvert.py resize in.png out.png --width 800 --height 600 --keep-aspect
    python imgconvert.py convert in.png out.webp --to webp --quality 85
    python imgconvert.py optimize in.png --max-kb 200 --strip-metadata

Notes
-----
* Python 3.9+, stdlib only (``argparse``, ``sys``, ``time``, ``pathlib``).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def progress(step: int, total: int, label: str) -> None:
    """
    Print a single fake-progress line and flush stdout so the GUI sees it live.

    Parameters
    ----------
    step : int
        1-based progress step.
    total : int
        Total number of steps.
    label : str
        Human-readable description of the current step.
    """
    sys.stdout.write(f"[{step}/{total}] {label}\n")
    sys.stdout.flush()


def fake_run(steps: list[str], output: Path | None = None) -> int:
    """
    Run a fake pipeline: print each step with a small delay, then write a
    stub output file when ``output`` is supplied.

    Parameters
    ----------
    steps : list of str
        Step labels printed one per line.
    output : Path or None, optional
        When given, a stub file is created at that path on completion.

    Returns
    -------
    int
        Process exit code; always ``0`` on success.
    """
    for i, label in enumerate(steps, 1):
        progress(i, len(steps), label)
        time.sleep(0.15)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        # Stub output — real conversion would happen here.
        output.write_text("imgconvert demo stub\n", encoding="utf-8")
        sys.stdout.write(f"→ wrote {output}\n")
    return 0


def cmd_resize(args: argparse.Namespace) -> int:
    """
    ``imgconvert resize`` — pretend to resize an image.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    int
        Exit code. ``2`` when the input is missing on disk; ``0`` otherwise.
    """
    if not Path(args.input).exists():
        sys.stderr.write(f"error: input not found: {args.input}\n")
        return 2
    aspect = "keeping aspect ratio" if args.keep_aspect else "stretching to fit"
    return fake_run(
        [
            f"reading {args.input}",
            f"resizing to {args.width}×{args.height} px ({aspect})",
            "encoding",
        ],
        Path(args.output),
    )


def cmd_convert(args: argparse.Namespace) -> int:
    """
    ``imgconvert convert`` — pretend to convert an image to another format.
    """
    if not Path(args.input).exists():
        sys.stderr.write(f"error: input not found: {args.input}\n")
        return 2
    return fake_run(
        [
            f"reading {args.input}",
            "decoding pixels",
            f"encoding as {args.to.upper()} (quality {args.quality})",
        ],
        Path(args.output),
    )


def cmd_optimize(args: argparse.Namespace) -> int:
    """
    ``imgconvert optimize`` — pretend to optimize an image.
    """
    src = Path(args.input)
    if not src.exists():
        sys.stderr.write(f"error: input not found: {args.input}\n")
        return 2
    out = src if args.in_place else src.with_name(src.stem + ".opt" + src.suffix)
    steps = [f"reading {src}"]
    if args.strip_metadata:
        steps.append("stripping metadata")
    steps.append(f"compressing to ≤ {args.max_kb} KB")
    return fake_run(steps, out)


def build_parser() -> argparse.ArgumentParser:
    """
    Construct the top-level parser with three subcommands.

    Returns
    -------
    argparse.ArgumentParser
        Fully-populated parser ready to consume ``argv``.
    """
    p = argparse.ArgumentParser(
        prog="imgconvert",
        description="Demo CLI for the sprezzature-skill cli-gui-demo example.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # resize
    rs = sub.add_parser("resize", help="Resize an image.")
    rs.add_argument("input", help="Input file path.")
    rs.add_argument("output", help="Output file path.")
    rs.add_argument("--width", type=int, required=True, help="Target width in px.")
    rs.add_argument("--height", type=int, required=True, help="Target height in px.")
    rs.add_argument(
        "--keep-aspect", action="store_true",
        help="Preserve aspect ratio (default: stretch).",
    )
    rs.set_defaults(func=cmd_resize)

    # convert
    cv = sub.add_parser("convert", help="Convert to another format.")
    cv.add_argument("input", help="Input file path.")
    cv.add_argument("output", help="Output file path.")
    cv.add_argument(
        "--to", choices=["png", "jpg", "webp"], required=True,
        help="Target format.",
    )
    cv.add_argument(
        "--quality", type=int, default=85, choices=range(1, 101),
        metavar="1-100", help="Encoding quality 1–100.",
    )
    cv.set_defaults(func=cmd_convert)

    # optimize
    op = sub.add_parser("optimize", help="Optimize an image.")
    op.add_argument("input", help="Input file path.")
    op.add_argument(
        "--in-place", action="store_true",
        help="Overwrite the input file (default: write <stem>.opt.<ext>).",
    )
    op.add_argument(
        "--max-kb", type=int, default=200,
        help="Target maximum size in kilobytes.",
    )
    op.add_argument(
        "--strip-metadata", action="store_true",
        help="Strip EXIF and other metadata.",
    )
    op.set_defaults(func=cmd_optimize)

    return p


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point. Parses ``argv`` and dispatches to the matching subcommand.
    """
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
