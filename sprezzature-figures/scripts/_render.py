"""
_render — the write-and-report tail shared by every ``make_<id>.py`` generator.

Each ``make_<id>.py`` in this folder assembles a figure as an SVG string and
then runs the *same* three-part epilogue: resolve the canonical output path
under ``<skill>/assets/svg-examples/<id>.svg``, create the parent directory,
write the bytes as UTF-8, and echo ``wrote <path>`` so a human running the
script from a terminal sees where the artifact landed. That epilogue was
copy-pasted, verbatim, into roughly sixty generators; this module is the one
place it now lives.

Only the pieces that were *byte-for-byte identical* across generators are
factored here — the path expression, the ``mkdir``/``write_text``/``print``
sequence, and (for the handful of generators that expose a ``--out`` flag) the
tiny argparse wiring. The figure-specific ``build_svg`` bodies stay in their own
files; this module never touches the SVG string, so adopting it leaves every
rendered byte unchanged. Generators with a bespoke epilogue (animated variants
that render twice, or maps that also emit a PNG companion) still call
:func:`write_svg` and :func:`svg_example_path` for the parts they share and keep
their extra logic inline.

The module is **stdlib-only** (``argparse`` + ``pathlib``), so it imports
everywhere the generators already run — no dataviz tier required. The ``wrote
<path>`` line is a deliberate, user-facing CLI confirmation (these scripts are
run by hand), not diagnostic logging, so it stays a plain ``print``.

Consumers
---------
The ``make_<id>.py`` generators in this same ``scripts/`` directory, via
``from _render import svg_example_path, write_svg, render_cli``.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import inspect
from pathlib import Path
from typing import Callable


def svg_example_path(script_file: str, figure_id: str) -> Path:
    """Return the canonical ``assets/svg-examples/<figure_id>.svg`` for a generator.

    Every generator writes, by default, to a file named after its figure inside
    the skill's ``assets/svg-examples`` folder — a sibling of the ``scripts``
    directory the generator lives in. Passing ``__file__`` lets this helper
    locate that folder relative to the *calling* script, exactly as the inline
    ``Path(__file__).resolve().parent.parent / "assets" / "svg-examples" /
    f"{figure_id}.svg"`` expression did, so the resolved path is identical.

    Parameters
    ----------
    script_file : str
        The calling generator's ``__file__``. Resolved to an absolute path so
        the result does not depend on the current working directory.
    figure_id : str
        The figure's short identifier (e.g. ``"dumbbell"``, ``"hexbin-map"``).
        Becomes the output file's stem; ``.svg`` is appended here.

    Returns
    -------
    pathlib.Path
        The absolute path ``<skill>/assets/svg-examples/<figure_id>.svg``.

    Examples
    --------
    >>> p = svg_example_path("/repo/sprezzature-figures/scripts/make_venn.py", "venn")
    >>> p.as_posix().endswith("sprezzature-figures/assets/svg-examples/venn.svg")
    True
    """
    # ``.parent`` is the scripts/ dir; ``.parent.parent`` is the skill root that
    # holds assets/. Resolve first so a relative ``__file__`` still works.
    return (
        Path(script_file).resolve().parent.parent
        / "assets"
        / "svg-examples"
        / f"{figure_id}.svg"
    )


def write_svg(out: Path, svg: str) -> Path:
    """Write ``svg`` to ``out`` (creating parents) and echo ``wrote <out>``.

    This is the identical three-line tail every generator carried: ensure the
    destination directory exists, write the string as UTF-8, and print a
    one-line confirmation of where the file went. The confirmation is a
    user-facing CLI message (the generators are run by hand), not diagnostic
    logging, so it stays a plain ``print``.

    Parameters
    ----------
    out : pathlib.Path
        Destination file path — typically the return of
        :func:`svg_example_path`, or a caller-supplied ``--out`` override.
    svg : str
        The complete SVG document to write.

    Returns
    -------
    pathlib.Path
        ``out`` unchanged, so callers can chain or log it if they wish.

    Examples
    --------
    >>> # write_svg(Path("/tmp/venn.svg"), "<svg .../>")  # doctest: +SKIP
    >>> # prints: wrote /tmp/venn.svg
    """
    # ``parents=True`` mirrors the inline ``mkdir(parents=True, exist_ok=True)``
    # so a fresh checkout (no assets/ yet) still succeeds.
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    # User-facing confirmation, byte-identical to the generators' own line.
    print(f"wrote {out}")
    return out


def render_cli(
    script_file: str,
    figure_id: str,
    build_svg: Callable[[], str],
    *,
    description: str,
) -> None:
    """Run the standard ``--out`` command line for an SVG generator.

    Wraps the argparse boilerplate the ``--out``-exposing generators shared:
    a single optional ``--out`` argument that defaults to the canonical
    :func:`svg_example_path`, followed by a :func:`write_svg` of
    ``build_svg()``'s result. The default path and the ``wrote <path>`` output
    are unchanged from the inline version, so behaviour is preserved.

    Parameters
    ----------
    script_file : str
        The calling generator's ``__file__`` (used to resolve the default
        output path).
    figure_id : str
        The figure's short identifier; sets both the default file name and the
        wording of the ``--out`` help text.
    build_svg : callable
        Zero-argument function returning the complete SVG document string. It is
        called only after arguments parse, so ``--help`` stays cheap.
    description : str
        One-line description shown at the top of ``--help``.

    Returns
    -------
    None
        The SVG is written as a side effect; nothing is returned.
    """
    default_out = svg_example_path(script_file, figure_id)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--out",
        type=Path,
        default=default_out,
        help=f"output SVG path (default: the skill's svg-examples/{figure_id}.svg)",
    )
    parser.add_argument(
        "--mode",
        choices=("self-contained", "external", "static"),
        default="self-contained",
        help="interactivity mode of the emitted SVG (default: self-contained)",
    )
    parser.add_argument(
        "--accessibility",
        choices=(
            "universal", "high-contrast", "monochrome",
            "deuteranopia", "protanopia", "tritanopia",
        ),
        default="universal",
        help="palette accessibility level (default: universal, the CVD-safe standard)",
    )
    args = parser.parse_args()
    # Build lazily (after parsing) so ``--help`` never runs the figure code.
    # Pass ``mode`` / ``accessibility`` only to generators whose ``build_svg``
    # accepts them, so this helper keeps working for figures that have not
    # adopted these arguments yet.
    params = inspect.signature(build_svg).parameters
    kwargs = {}
    if "mode" in params:
        kwargs["mode"] = args.mode
    if "accessibility" in params:
        kwargs["accessibility"] = args.accessibility
    write_svg(args.out, build_svg(**kwargs))


if __name__ == "__main__":  # pragma: no cover - smoke check, not a generator
    # This module is a library for the generators, not a generator itself.
    # Running it directly just proves the path helper resolves sensibly.
    print(svg_example_path(__file__, "example"))
