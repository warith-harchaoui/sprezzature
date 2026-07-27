#!/usr/bin/env python3
"""
cleanup_local_skills
====================

Audit ``~/.claude/skills/`` and ``~/.opencode/skills/`` for orphan
``front-*`` folders left behind by past renames (notably the v0.9.0
``sprezzature-a11y`` → ``sprezzature-accessibility`` rename, the v0.7.0
``sprezzature-colors`` split, the v0.8.0 ``sprezzature-vision`` split, the
v0.9.0 ``sprezzature-audio`` split). Optionally remove them.

What "orphan" means
-------------------

A folder under one of the two skill directories that:

1. Starts with ``front-``, AND
2. Is **not** listed in this repo's canonical
   :file:`SKILLS.txt` manifest.

Folders that don't start with ``front-`` (i.e. another skill family
the user installs alongside this one) are left alone — we only audit
our own naming surface.

Two modes
---------

::

    python scripts/cleanup_local_skills.py
        Audit only. Lists what would be removed; never writes.
        Default — safe to alias in a shell.

    python scripts/cleanup_local_skills.py --apply
        Prompts ``y/N`` per orphan folder before ``rm -rf``.
        Use this when you actually want to clean up.

Both modes also report **missing** canonical skills — folders
listed in :file:`SKILLS.txt` that the user has *not* installed.
That report is informational only; we never auto-install (the user
controls which skills they want).

Exit codes
----------

* ``0`` — audit completed; with ``--apply``, all confirmed removals
  succeeded.
* ``1`` — a removal failed (permission / open file / I/O).
* ``2`` — :file:`SKILLS.txt` is missing or malformed.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _argparse import make_parser
from skills_manifest import SHIPPED_SKILLS


#: The two skill directories we audit. Order matters only for the
#: report — both are inspected unconditionally.
RUNTIME_DIRS: dict[str, Path] = {
    "Claude Code": Path.home() / ".claude" / "skills",
    "OpenCode": Path.home() / ".opencode" / "skills",
}


def _sprezzature_subdirs(root: Path) -> list[Path]:
    """
    Return every ``front-*`` subdirectory of ``root``.

    Returns an empty list when ``root`` does not exist — the runtime
    may simply not be installed on this machine.

    Parameters
    ----------
    root : Path
        Skill-directory root (e.g. ``~/.claude/skills``).

    Returns
    -------
    list of Path
        Sorted, deterministic, only the ``front-*`` subset.
    """
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_dir() and p.name.startswith("sprezzature-")
    )


def _confirm(prompt: str) -> bool:
    """
    Y/N prompt with a safe default of ``no``.

    Empty input, ``n``, ``N``, anything but ``y`` / ``Y`` / ``yes``
    is treated as a refusal — destructive operations should never
    happen by accident.
    """
    try:
        answer: str = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _remove(path: Path, *, dry_run: bool) -> bool:
    """
    Remove a directory tree.

    Parameters
    ----------
    path : Path
        Directory to remove.
    dry_run : bool
        If ``True``, print what would happen and return ``True``
        without touching disk.

    Returns
    -------
    bool
        ``True`` on success, ``False`` on I/O failure.
    """
    if dry_run:
        print(f"    would rm -rf {path}")
        return True
    try:
        shutil.rmtree(path)
    except OSError as exc:
        print(f"    rm -rf failed: {exc}", file=sys.stderr)
        return False
    print(f"    removed {path}")
    return True


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser: argparse.ArgumentParser = make_parser(
        prog="front-cleanup-local-skills",
        description=(
            "Audit ~/.claude/skills/ and ~/.opencode/skills/ for "
            "orphan front-* folders left behind by past skill "
            "renames or splits. Optionally remove them."
        ),
        epilog=(
            "Examples:\n"
            "  python scripts/cleanup_local_skills.py\n"
            "      audit only — list orphans without removing\n"
            "  python scripts/cleanup_local_skills.py --apply\n"
            "      prompt per orphan before rm -rf\n"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Prompt for confirmation per orphan folder, then remove "
            "the confirmed ones. Default: audit-only (no writes)."
        ),
    )
    args: argparse.Namespace = parser.parse_args(argv)

    canonical: set[str] = set(SHIPPED_SKILLS)
    if not canonical:
        print(
            "SKILLS.txt parses to an empty list. Refusing to operate.",
            file=sys.stderr,
        )
        return 2

    total_orphans: int = 0
    total_removed: int = 0
    total_failed: int = 0

    for runtime, root in RUNTIME_DIRS.items():
        print(f"\n=== {runtime} — {root}")
        if not root.is_dir():
            print(f"    {root} does not exist — runtime not installed (skipped).")
            continue

        sprezzature_dirs: list[Path] = _sprezzature_subdirs(root)
        if not sprezzature_dirs:
            print("    no front-* folders found.")
            continue

        # Orphans: front-* folders the canonical manifest does not name.
        orphans: list[Path] = [
            p for p in sprezzature_dirs if p.name not in canonical
        ]
        installed: set[str] = {p.name for p in sprezzature_dirs} & canonical
        missing: set[str] = canonical - installed

        if not orphans:
            print(f"    {len(installed)} canonical skill(s) installed, no orphans.")
        else:
            print(f"    {len(orphans)} orphan(s) found:")
            for p in orphans:
                print(f"      • {p.name}  ({p})")
                total_orphans += 1
                if args.apply and _confirm(f"      remove {p.name}?"):
                    if _remove(p, dry_run=False):
                        total_removed += 1
                    else:
                        total_failed += 1
                elif not args.apply:
                    _remove(p, dry_run=True)

        if missing:
            print(f"    {len(missing)} canonical skill(s) not installed (informational):")
            for name in sorted(missing):
                print(f"      • {name}  (cp -r {name} {root}/)")

    # ── Summary ────────────────────────────────────────────────────────
    print("")
    print("=== Summary")
    print(f"    orphan folders found:   {total_orphans}")
    if args.apply:
        print(f"    folders removed:        {total_removed}")
        print(f"    removals failed:        {total_failed}")
        if total_failed:
            return 1
    else:
        if total_orphans:
            print(
                "    Re-run with --apply to remove the confirmed "
                "orphans (each one prompts y/N)."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
