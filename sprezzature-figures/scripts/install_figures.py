#!/usr/bin/env python3
"""
install_figures
===============

Idempotent installer for the three sprezzature-figures tiers:

    dataviz   — matplotlib, seaborn, altair, vega_datasets, pandas
    explain   — shap, shapash, timeshap, lime, scikit-learn
    causal    — dowhy, econml, networkx, graphviz (Python wrapper)

The tiers are additive. ``--tier dataviz+explain`` installs the base
plotting stack plus the explainability engines. ``--tier all`` installs
everything.

The installer detects the active project's env manager (in order):

    1. ``uv``       — if ``uv.lock`` or ``pyproject.toml`` with ``[tool.uv]``.
    2. ``poetry``   — if ``poetry.lock`` or ``pyproject.toml`` with ``[tool.poetry]``.
    3. ``pixi``     — if ``pixi.toml`` or ``pixi.lock``.
    4. ``conda``    — if ``CONDA_PREFIX`` is set.
    5. ``pip``      — fallback (uses the interpreter's own pip).

Each tier's pinned requirements live in ``requirements-<tier>.txt``.

Usage
-----
::

    python install_figures.py --tier dataviz
    python install_figures.py --tier dataviz+explain
    python install_figures.py --tier all --dry-run

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402


TIERS = ("dataviz", "explain", "causal")


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = make_parser(
        prog="install_figures",
        description=(
            "Install the pinned data-viz / explainability / causality "
            "stack. Detects uv / poetry / pixi / conda / pip; falls "
            "back to the interpreter's pip."
        ),
    )
    parser.add_argument("--tier", default="dataviz",
                        help='Combination of tiers separated by "+" '
                             '(dataviz, explain, causal, or "all").')
    parser.add_argument("--manager", choices=("auto", "uv", "poetry", "pixi", "conda", "pip"),
                        default="auto", help="Env manager to use (default: auto-detect).")
    parser.add_argument("--dry-run", action="store_true", help="Print the install command without running it.")
    return parser


# ------------------------------------------------------------------
# Env manager detection
# ------------------------------------------------------------------
def detect_manager(cwd: Path) -> str:
    """Pick the env manager for the current project.

    Parameters
    ----------
    cwd : pathlib.Path
        Project root.

    Returns
    -------
    str
        One of ``uv`` / ``poetry`` / ``pixi`` / ``conda`` / ``pip``.
    """
    pyproject = cwd / "pyproject.toml"
    if (cwd / "uv.lock").exists() or _has_tool_section(pyproject, "uv"):
        if shutil.which("uv"):
            return "uv"
    if (cwd / "poetry.lock").exists() or _has_tool_section(pyproject, "poetry"):
        if shutil.which("poetry"):
            return "poetry"
    if (cwd / "pixi.toml").exists() or (cwd / "pixi.lock").exists():
        if shutil.which("pixi"):
            return "pixi"
    if os.environ.get("CONDA_PREFIX") and shutil.which("conda"):
        return "conda"
    return "pip"


def _has_tool_section(pyproject: Path, tool: str) -> bool:
    """Cheap check: does ``pyproject.toml`` contain a ``[tool.<tool>]`` block?"""
    if not pyproject.is_file():
        return False
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return False
    return f"[tool.{tool}]" in text or f"[tool.{tool}." in text


# ------------------------------------------------------------------
# Tier resolution
# ------------------------------------------------------------------
def resolve_tiers(flag: str) -> List[str]:
    """Turn a ``--tier`` argument into an ordered list of tier names."""
    flag = flag.strip().lower()
    if flag == "all":
        return list(TIERS)
    seen: List[str] = []
    for t in flag.split("+"):
        t = t.strip()
        if t in TIERS and t not in seen:
            seen.append(t)
    if not seen:
        raise SystemExit(f"Unknown tier '{flag}'. Valid: {', '.join(TIERS)}, all.")
    return seen


def requirements_for(tier: str, scripts_dir: Path) -> Path:
    """Return the path to a tier's requirements file."""
    return scripts_dir / f"requirements-{tier}.txt"


# ------------------------------------------------------------------
# Install commands
# ------------------------------------------------------------------
def build_command(manager: str, req_file: Path) -> List[str]:
    """Build the install command for a manager + requirements file."""
    if manager == "uv":
        return ["uv", "pip", "install", "-r", str(req_file)]
    if manager == "poetry":
        # Poetry doesn't consume plain requirements files; use its internal pip.
        return ["poetry", "run", "pip", "install", "-r", str(req_file)]
    if manager == "pixi":
        return ["pixi", "run", "pip", "install", "-r", str(req_file)]
    if manager == "conda":
        return ["conda", "run", "pip", "install", "-r", str(req_file)]
    return [sys.executable, "-m", "pip", "install", "-r", str(req_file)]


def run_command(cmd: List[str], dry_run: bool) -> int:
    """Print (and optionally run) an install command."""
    print("+ " + " ".join(cmd), file=sys.stderr)
    if dry_run:
        return 0
    return subprocess.call(cmd)


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    scripts_dir = Path(__file__).resolve().parent
    tiers = resolve_tiers(args.tier)

    manager = args.manager
    if manager == "auto":
        manager = detect_manager(Path.cwd())
    print(f"[info] env manager: {manager}", file=sys.stderr)
    print(f"[info] tiers: {'+'.join(tiers)}", file=sys.stderr)

    for tier in tiers:
        req = requirements_for(tier, scripts_dir)
        if not req.is_file():
            print(f"[warn] no requirements file for tier '{tier}' at {req}", file=sys.stderr)
            continue
        rc = run_command(build_command(manager, req), dry_run=args.dry_run)
        if rc != 0:
            print(f"[error] install failed for tier '{tier}' (exit {rc})", file=sys.stderr)
            return rc

    if "causal" in tiers:
        _hint_graphviz_system()
    return 0


def _hint_graphviz_system() -> None:
    """Print a reminder that graphviz needs the system package too."""
    print(
        "[hint] The 'graphviz' Python package needs the system Graphviz binary. "
        "Install via: brew install graphviz (macOS — https://brew.sh) / "
        "apt install graphviz (Linux) / winget install graphviz (Windows).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
